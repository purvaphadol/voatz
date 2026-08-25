import sys
import os
import json
import uuid
from datetime import datetime, timedelta, timezone

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRoleMapping
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from app.utils.constants import STATUS_ACTIVE
from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token

def run_proof():
    app = create_app()
    with app.app_context():
        db.create_all()
        company_id = 1

        # Setup admin user & permissions
        admin_user = User.query.filter_by(email='admin_item5@company-a.com').first()
        if not admin_user:
            admin_user = User(name='Admin Item5', email='admin_item5@company-a.com', company_id=company_id, status=STATUS_ACTIVE)
            admin_user.password_hash = generate_password_hash('Password123!')
            db.session.add(admin_user)
            db.session.flush()

        role = Role.query.filter_by(role_name='Super Admin', company_id=company_id).first()
        if not role:
            role = Role(role_name='Super Admin', company_id=company_id, status=STATUS_ACTIVE)
            db.session.add(role)
            db.session.flush()

        user_role = UserRoleMapping.query.filter_by(user_id=admin_user.id, role_id=role.id).first()
        if not user_role:
            user_role = UserRoleMapping(user_id=admin_user.id, role_id=role.id, company_id=company_id, status=1)
            db.session.add(user_role)

        for mod_name in ['Ballots', 'Candidates', 'Votes', 'Elections', 'Voters', 'VoterRegistrations']:
            sys_mod = SystemModule.query.filter_by(module_name=mod_name).first()
            if not sys_mod:
                sys_mod = SystemModule(module_name=mod_name, status=1)
                db.session.add(sys_mod)
                db.session.flush()
            
            cm = CompanyModule.query.filter_by(company_id=company_id, system_module_id=sys_mod.id).first()
            if not cm:
                cm = CompanyModule(company_id=company_id, system_module_id=sys_mod.id, status=1)
                db.session.add(cm)

            for act_name in ['view', 'create', 'update', 'delete']:
                act = SystemModuleAction.query.filter_by(action_name=act_name, system_module_id=sys_mod.id).first()
                if not act:
                    act = SystemModuleAction(action_name=act_name, action_url='', system_module_id=sys_mod.id, status=1)
                    db.session.add(act)
                    db.session.flush()
                
                rp = RolePermissionMapping.query.filter_by(role_id=role.id, module_id=sys_mod.id, action_id=act.id, company_id=company_id).first()
                if not rp:
                    rp = RolePermissionMapping(role_id=role.id, module_id=sys_mod.id, action_id=act.id, company_id=company_id, status=1)
                    db.session.add(rp)

        db.session.commit()

        client = app.test_client()
        token = create_access_token(identity=str(admin_user.id))
        headers = {'Authorization': f'Bearer {token}'}

        # --- SCENARIO 1: Activate Election with Ballot Having Zero Candidates ---
        uid1 = uuid.uuid4().hex[:6]
        now = datetime.now(timezone.utc)
        election1 = Election(
            company_id=company_id,
            title=f'Zero Candidates Election {uid1}',
            election_code=f'ELEC-{uid1}',
            election_type='general',
            status='draft',
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=5)
        )
        db.session.add(election1)
        db.session.flush()

        empty_ballot_title = f'Empty Ballot {uid1}'
        ballot1 = Ballot(
            company_id=company_id,
            election_id=election1.id,
            title=empty_ballot_title,
            ballot_code=f'BAL-{uid1}',
            ballot_type='single_choice',
            status=STATUS_ACTIVE,
            is_active=True
        )
        db.session.add(ballot1)
        db.session.commit()

        print('=== TEST 1: ACTIVATE ELECTION WITH 0-CANDIDATE BALLOT ===')
        act_res1 = client.post(f'/api/elections/{election1.id}/activate', headers=headers)
        print(f'HTTP Status: {act_res1.status_code}')
        print(json.dumps(act_res1.get_json(), indent=2))

        # --- SCENARIO 2: Add Candidate & Retry Activation ---
        cand1 = Candidate(
            company_id=company_id,
            ballot_id=ballot1.id,
            name=f'Candidate Item5 {uid1}',
            candidate_code=f'CAND-{uid1}',
            status=STATUS_ACTIVE,
            is_active=True
        )
        db.session.add(cand1)
        db.session.commit()

        print('\n=== TEST 2: RETRY ACTIVATION AFTER ADDING CANDIDATE ===')
        act_res2 = client.post(f'/api/elections/{election1.id}/activate', headers=headers)
        print(f'HTTP Status: {act_res2.status_code}')
        print(json.dumps(act_res2.get_json(), indent=2))

        # --- SCENARIO 3: Confirm Zero-Ballot Rejection Still Works ---
        uid3 = uuid.uuid4().hex[:6]
        election3 = Election(
            company_id=company_id,
            title=f'Zero Ballots Election {uid3}',
            election_code=f'ELEC-{uid3}',
            election_type='general',
            status='draft',
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=5)
        )
        db.session.add(election3)
        db.session.commit()

        print('\n=== TEST 3: ACTIVATE ELECTION WITH 0 BALLOTS (PRESERVED REGRESSION TEST) ===')
        act_res3 = client.post(f'/api/elections/{election3.id}/activate', headers=headers)
        print(f'HTTP Status: {act_res3.status_code}')
        print(json.dumps(act_res3.get_json(), indent=2))

if __name__ == '__main__':
    run_proof()

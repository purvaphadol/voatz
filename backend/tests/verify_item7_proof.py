import sys
import os
import json
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from app.models.vote import Vote
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

        admin_user = User.query.filter_by(email='admin_item7@company-a.com').first()
        if not admin_user:
            admin_user = User(name='Admin Item7', email='admin_item7@company-a.com', company_id=company_id, status=STATUS_ACTIVE)
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

        # Create Election, Ballot, Candidate, Voter, VoterRegistration
        uid = uuid.uuid4().hex[:6]
        now = datetime.now(timezone.utc)
        election = Election(
            company_id=company_id,
            title=f'Race Test Election {uid}',
            election_code=f'ELEC-{uid}',
            election_type='general',
            status='active',
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=5)
        )
        db.session.add(election)
        db.session.flush()

        ballot = Ballot(
            company_id=company_id,
            election_id=election.id,
            title=f'Race Test Ballot {uid}',
            ballot_code=f'BAL-{uid}',
            ballot_type='single_choice',
            status=STATUS_ACTIVE,
            is_active=True,
            is_published=True
        )
        db.session.add(ballot)
        db.session.flush()

        candidate = Candidate(
            company_id=company_id,
            ballot_id=ballot.id,
            name=f'Race Candidate {uid}',
            candidate_code=f'CAND-{uid}',
            status=STATUS_ACTIVE,
            is_active=True
        )
        db.session.add(candidate)
        db.session.flush()

        voter_user = User(name=f'Voter User {uid}', email=f'voter_{uid}@company-a.com', company_id=company_id, status=STATUS_ACTIVE)
        voter_user.password_hash = generate_password_hash('Password123!')
        db.session.add(voter_user)
        db.session.flush()

        voter = Voter(
            company_id=company_id,
            user_id=voter_user.id,
            voter_id=f'VOT-{uid}',
            phone_number=f'+1555000{uid[:4]}',
            status=STATUS_ACTIVE
        )
        db.session.add(voter)
        db.session.flush()

        reg = VoterRegistration(
            company_id=company_id,
            voter_id=voter.id,
            election_id=election.id,
            registration_id=f'REG-{uid}',
            status='approved',
            registered_at=now
        )
        db.session.add(reg)
        db.session.commit()

        # Insert a Vote record manually in DB first to simulate a concurrent vote already committed
        existing_vote = Vote(
            company_id=company_id,
            voter_id=voter.id,
            ballot_id=ballot.id,
            election_id=election.id,
            vote_data={'selections': [candidate.id]},
            vote_cast_time=now,
            vote_status='verified'
        )
        existing_vote.vote_id = f"VOTE-{uuid.uuid4().hex[:12].upper()}"
        existing_vote.generate_tracking_code()
        existing_vote.generate_vote_hash()
        existing_vote.generate_verification_hash()
        db.session.add(existing_vote)
        db.session.commit()

        print('=== TEST 1: SEQUENTIAL DUPLICATE VOTE (APP-LEVEL 400 PRE-CHECK) ===')
        payload = {
            'voter_id': voter.voter_id,
            'ballot_id': ballot.id,
            'vote_data': {'selections': [candidate.id]}
        }
        res1 = client.post('/api/votes/', json=payload, headers=headers)
        print(f'HTTP Status: {res1.status_code}')
        print(json.dumps(res1.get_json(), indent=2))

        print('\n=== TEST 2: CONCURRENT RACE DUPLICATE VOTE (DB-LEVEL IntegrityError 409 MAPPING) ===')
        # To test the DB-level unique_vote_per_ballot constraint mapping in safe_commit:
        # We manually insert a second Vote object for same (voter_id, ballot_id) into db.session
        # and invoke safe_commit directly, simulating a race where two requests bypassed the app-level check concurrently
        from app.utils.db_utils import safe_commit
        race_vote = Vote(
            company_id=company_id,
            voter_id=voter.id,
            ballot_id=ballot.id,
            election_id=election.id,
            vote_data={'selections': [candidate.id]},
            vote_cast_time=now,
            vote_status='verified'
        )
        race_vote.vote_id = f"VOTE-{uuid.uuid4().hex[:12].upper()}"
        race_vote.generate_tracking_code()
        race_vote.generate_vote_hash()
        race_vote.generate_verification_hash()
        
        db.session.add(race_vote)
        res2_tuple = safe_commit(({'message': 'Vote cast successfully'}, 201), 'Failed to cast vote')
        response_obj, status_code = res2_tuple
        print(f'HTTP Status: {status_code}')
        print(json.dumps(response_obj.get_json(), indent=2))

if __name__ == '__main__':
    run_proof()

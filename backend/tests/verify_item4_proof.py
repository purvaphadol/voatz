import sys
import os
import json
from datetime import datetime, timedelta, timezone

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.vote import Vote
from app.models.voter import Voter
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRoleMapping
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from app.models.voter_registration import VoterRegistration
from app.utils.constants import STATUS_ACTIVE

from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token

def run_proof():
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # 1. Setup Company Super Admin & Permissions
        company_id = 1
        admin_user = User.query.filter_by(email='admin_item4@company-a.com').first()
        if not admin_user:
            admin_user = User(name='Admin Item4', email='admin_item4@company-a.com', company_id=company_id, status=STATUS_ACTIVE)
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

        # Token generation
        token = create_access_token(identity=str(admin_user.id))
        headers = {'Authorization': f'Bearer {token}'}

        # 2. Setup Election, Ballot, Candidate, Voter, Registration
        import uuid
        uid = uuid.uuid4().hex[:6]

        now = datetime.now(timezone.utc)
        election = Election(
            company_id=company_id,
            title=f'Item 4 Proof Election {uid}',
            election_code=f'ELEC-{uid}',
            election_type='general',
            status='active',
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1)
        )
        db.session.add(election)
        db.session.flush()

        ballot = Ballot(
            company_id=company_id,
            election_id=election.id,
            title=f'Item 4 Proof Ballot {uid}',
            ballot_code=f'BAL-{uid}',
            ballot_type='single_choice',
            status=STATUS_ACTIVE,
            is_published=True
        )
        db.session.add(ballot)
        db.session.flush()

        candidate = Candidate(
            company_id=company_id,
            ballot_id=ballot.id,
            name=f'Candidate Item4 {uid}',
            candidate_code=f'CAND-{uid}',
            status=STATUS_ACTIVE
        )
        db.session.add(candidate)
        db.session.flush()

        voter_user = User(name=f'Voter Item4 {uid}', email=f'voter_{uid}@company-a.com', company_id=company_id, status=STATUS_ACTIVE)
        voter_user.password_hash = generate_password_hash('Password123!')
        db.session.add(voter_user)
        db.session.flush()

        voter = Voter(
            user_id=voter_user.id,
            company_id=company_id,
            voter_id=f'V-{uid}',
            name=f'Item4 Voter {uid}',
            phone_number='1234567890',
            status=STATUS_ACTIVE
        )
        db.session.add(voter)
        db.session.flush()

        reg = VoterRegistration(
            company_id=company_id,
            voter_id=voter.id,
            election_id=election.id,
            status='approved',
            registration_id=f'REG-{uid}'
        )
        db.session.add(reg)
        db.session.commit()

        # 3. Cast Vote via API
        cast_res = client.post('/api/votes/', json={
            'voter_id': voter.voter_id,
            'ballot_id': ballot.id,
            'vote_data': {'selections': [candidate.id]},
        }, headers=headers)
        
        cast_data = cast_res.get_json()
        print('=== STEP 1: CAST VOTE RESPONSE ===')
        print(f'HTTP Status: {cast_res.status_code}')
        print(json.dumps(cast_data, indent=2))
        
        vote_db = Vote.query.filter_by(vote_id=cast_data['vote_id']).first()
        vote_id = vote_db.id

        # 4. Untouched Vote Verification (GET & POST verify-integrity)
        get_untouched = client.get(f'/api/votes/{vote_id}', headers=headers)
        print('\n=== STEP 2: UNTOUCHED VOTE - GET /api/votes/<id> ===')
        print(f'HTTP Status: {get_untouched.status_code}')
        get_untouched_json = get_untouched.get_json()
        print(f"integrity_verified: {get_untouched_json.get('integrity_verified')}")
        print(json.dumps({
            'id': get_untouched_json['id'],
            'vote_hash': get_untouched_json['vote_hash'],
            'verification_hash': get_untouched_json['verification_hash'],
            'integrity_verified': get_untouched_json['integrity_verified'],
            'integrity_check': get_untouched_json['integrity_check']
        }, indent=2))

        verify_int_untouched = client.post(f'/api/votes/{vote_id}/verify-integrity', headers=headers)
        print('\n=== STEP 3: UNTOUCHED VOTE - POST /api/votes/<id>/verify-integrity ===')
        print(f'HTTP Status: {verify_int_untouched.status_code}')
        print(json.dumps(verify_int_untouched.get_json(), indent=2))

        # 5. Direct DB Mutation (Tampering with vote_data)
        print('\n=== STEP 4: DELIBERATE DB MUTATION (TAMPERING WITH STORED VOTE DATA) ===')
        vote_db_tamper = db.session.get(Vote, vote_id)
        print(f'Original vote_data in DB: {vote_db_tamper.vote_data}')
        vote_db_tamper.vote_data = {'selections': [99999], 'tampered': True}
        db.session.commit()
        print(f'Mutated vote_data in DB: {vote_db_tamper.vote_data}')
        print('Stored vote_hash in DB (unchanged):', vote_db_tamper.vote_hash)

        # 6. Tampered Vote Verification (GET, POST verify-integrity, POST verify)
        get_tampered = client.get(f'/api/votes/{vote_id}', headers=headers)
        print('\n=== STEP 5: TAMPERED VOTE - GET /api/votes/<id> ===')
        print(f'HTTP Status: {get_tampered.status_code}')
        get_tampered_json = get_tampered.get_json()
        print(f"integrity_verified: {get_tampered_json.get('integrity_verified')}")
        print(json.dumps({
            'id': get_tampered_json['id'],
            'vote_hash': get_tampered_json['vote_hash'],
            'verification_hash': get_tampered_json['verification_hash'],
            'integrity_verified': get_tampered_json['integrity_verified'],
            'integrity_check': get_tampered_json['integrity_check']
        }, indent=2))

        verify_int_tampered = client.post(f'/api/votes/{vote_id}/verify-integrity', headers=headers)
        print('\n=== STEP 6: TAMPERED VOTE - POST /api/votes/<id>/verify-integrity ===')
        print(f'HTTP Status: {verify_int_tampered.status_code}')
        print(json.dumps(verify_int_tampered.get_json(), indent=2))

        verify_admin_tampered = client.post(f'/api/votes/{vote_id}/verify', json={'verification_type': 'all'}, headers=headers)
        print('\n=== STEP 7: TAMPERED VOTE - POST /api/votes/<id>/verify (ADMIN VERIFICATION REJECTION) ===')
        print(f'HTTP Status: {verify_admin_tampered.status_code}')
        print(json.dumps(verify_admin_tampered.get_json(), indent=2))

if __name__ == '__main__':
    run_proof()

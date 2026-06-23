import pytest
import werkzeug.test
from app import db
from app.models.candidate import Candidate
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.vote import Vote
from app.models.module import Module
from app.models.module_action import ModuleAction
from app.models.role_permission import RolePermissionMapping
from app.models.role import Role

# Monkeypatch TestResponse to allow res.json() call syntax if needed
class CallableDict(dict):
    def __call__(self, *args, **kwargs):
        return self

@property
def custom_json(self):
    val = self.get_json()
    if isinstance(val, dict):
        return CallableDict(val)
    return val

werkzeug.test.TestResponse.json = custom_json

def create_election(client, headers, status='draft'):
    """Create a test election and return its id"""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'title': 'Test Election',
        'election_type': 'general',
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }, headers=headers)
    assert res.status_code == 201
    el_id = res.json()['election_id']
    if status != 'draft':
        with client.application.app_context():
            el = Election.query.get(el_id)
            el.status = status
            db.session.commit()
    return el_id

def create_ballot(client, headers, election_id):
    """Create a test ballot and return its id"""
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': election_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 201
    return res.json()['ballot_id']

@pytest.fixture(autouse=True)
def add_candidates_permissions(client, setup_data):
    with client.application.app_context():
        company_id = setup_data['company_id']
        role = Role.query.filter_by(role_name='Super Admin', company_id=company_id).first()
        if role:
            # First ensure Ballots permissions exist (since we create ballots/elections in tests)
            for mod_name in ['Ballots', 'Candidates', 'Elections']:
                mod = Module.query.filter_by(module_name=mod_name, company_id=company_id).first()
                if not mod:
                    mod = Module(module_name=mod_name, company_id=company_id)
                    db.session.add(mod)
                    db.session.flush()
                
                actions = ['view', 'create', 'update', 'delete']
                for act_name in actions:
                    act = ModuleAction.query.filter_by(action_name=act_name, module_id=mod.id, company_id=company_id).first()
                    if not act:
                        act = ModuleAction(action_name=act_name, action_url='', module_id=mod.id, company_id=company_id)
                        db.session.add(act)
                        db.session.flush()
                    
                    rp = RolePermissionMapping.query.filter_by(role_id=role.id, module_id=mod.id, action_id=act.id, company_id=company_id).first()
                    if not rp:
                        rp = RolePermissionMapping(role_id=role.id, module_id=mod.id, action_id=act.id, company_id=company_id)
                        db.session.add(rp)
            db.session.commit()

def test_candidate_create_and_read(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    # Create Candidate
    res = client.post('/api/candidates/', json={
        'name': 'Alice Candidate',
        'ballot_id': b_id,
        'party': 'Independent'
    }, headers=headers)
    assert res.status_code == 201
    body = res.get_json()
    assert 'candidate_id' in body
    assert 'candidate_code' in body
    assert body['candidate_code'].startswith('C')
    cand_id = body['candidate_id']
    
    # Get Candidate
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 200
    get_body = res_get.get_json()
    assert get_body['name'] == 'Alice Candidate'
    assert get_body['party'] == 'Independent'
    assert get_body['is_active'] is True

def test_candidate_create_validation(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    # Invalid ballot_id type
    res = client.post('/api/candidates/', json={
        'name': 'Bob Candidate',
        'ballot_id': 'not-an-int',
    }, headers=headers)
    assert res.status_code == 400
    assert 'ballot_id must be a valid integer' in res.get_json()['error']

    # Missing ballot_id
    res = client.post('/api/candidates/', json={
        'name': 'Bob Candidate',
    }, headers=headers)
    assert res.status_code == 400

    # Active election
    active_el_id = create_election(client, headers, 'draft')
    active_b_id = create_ballot(client, headers, active_el_id)
    
    # Set to active after ballot creation
    with client.application.app_context():
        el = Election.query.get(active_el_id)
        el.status = 'active'
        db.session.commit()

    res = client.post('/api/candidates/', json={
        'name': 'Bob Candidate',
        'ballot_id': active_b_id,
    }, headers=headers)
    assert res.status_code == 400
    assert 'Cannot create candidates for active, completed, or cancelled elections' in res.get_json()['error']

def test_candidate_list_and_pagination(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    # Create two candidates
    client.post('/api/candidates/', json={'name': 'C1', 'ballot_id': b_id}, headers=headers)
    client.post('/api/candidates/', json={'name': 'C2', 'ballot_id': b_id}, headers=headers)
    
    # List candidates with per_page=1
    res = client.get('/api/candidates/?per_page=1', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert len(body['data']) == 1
    assert body['summary']['total_candidates'] == 2

def test_candidate_update(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    res_create = client.post('/api/candidates/', json={'name': 'C1', 'ballot_id': b_id}, headers=headers)
    cand_id = res_create.get_json()['candidate_id']
    
    res_update = client.put(f'/api/candidates/{cand_id}', json={'name': 'C1 Updated', 'party': 'New Party'}, headers=headers)
    assert res_update.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.get_json()['name'] == 'C1 Updated'
    assert res_get.get_json()['party'] == 'New Party'

def test_candidate_soft_delete(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    res_create = client.post('/api/candidates/', json={'name': 'C1', 'ballot_id': b_id}, headers=headers)
    cand_id = res_create.get_json()['candidate_id']
    
    # Delete
    res_delete = client.delete(f'/api/candidates/{cand_id}', headers=headers)
    assert res_delete.status_code == 200
    
    # Should not be in details view (404)
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 404
    
    # Should not be in list by default
    res_list = client.get('/api/candidates/', headers=headers)
    assert cand_id not in [c['id'] for c in res_list.get_json()['data']]

def test_candidate_withdraw_and_reinstate(client, setup_data):
    headers = setup_data['headers']
    el_id = create_election(client, headers, 'draft')
    b_id = create_ballot(client, headers, el_id)
    
    res_create = client.post('/api/candidates/', json={'name': 'C1', 'ballot_id': b_id}, headers=headers)
    cand_id = res_create.get_json()['candidate_id']
    
    # Withdraw
    res_withdraw = client.post(f'/api/candidates/{cand_id}/withdraw', json={'withdrawal_reason': 'Voluntary withdrawal'}, headers=headers)
    assert res_withdraw.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 404 # Withdraw sets is_active to False, so it's soft-deleted too
    
    # Reinstate
    res_reinstate = client.post(f'/api/candidates/{cand_id}/reinstate', headers=headers)
    assert res_reinstate.status_code == 200
    
    res_get2 = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get2.status_code == 200
    assert res_get2.get_json()['is_withdrawn'] is False
    assert res_get2.get_json()['is_active'] is True

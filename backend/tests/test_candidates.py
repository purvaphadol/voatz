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
from sqlalchemy import or_

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

# --- Helper Functions ---

def create_election(client, headers):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'title': 'Test Election',
        'election_type': 'general',
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }, headers=headers)
    return res.get_json()['election_id']

def create_ballot(client, headers, election_id):
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': election_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    return res.get_json()['ballot_id']

def create_candidate(client, headers, ballot_id):
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': ballot_id,
    }, headers=headers)
    return res.get_json()['candidate_id']

# --- Permissions Setup Fixture ---

@pytest.fixture(autouse=True)
def add_candidates_permissions(client, setup_data):
    with client.application.app_context():
        company_id = setup_data['company_id']
        role = Role.query.filter_by(role_name='Super Admin', company_id=company_id).first()
        if role:
            # Ensure Ballots and Candidates permissions exist
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

# --- List and Stats ---

def test_candidate_list(client, setup_data):
    """GET /api/candidates/ — expect 200, response has data list, total, summary with keys"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    create_candidate(client, headers, b_id)
    
    res = client.get('/api/candidates/', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert 'data' in body
    assert isinstance(body['data'], list)
    assert 'total' in body
    assert 'summary' in body
    summary = body['summary']
    for key in ('total_candidates', 'active_candidates', 'incumbent_candidates', 'withdrawn_candidates'):
        assert key in summary

def test_candidate_stats(client, setup_data):
    """GET /api/candidates/stats — expect 200, response has stats keys"""
    headers = setup_data['headers']
    res = client.get('/api/candidates/stats', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    for key in ('total_candidates', 'active_candidates', 'incumbent_candidates', 'withdrawn_candidates'):
        assert key in body

# --- Create ---

def test_candidate_create(client, setup_data):
    """POST with valid name and ballot_id — expect 201, candidate_id, and candidate_code starting with C"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': b_id,
    }, headers=headers)
    assert res.status_code == 201
    body = res.get_json()
    assert 'candidate_id' in body
    assert 'candidate_code' in body
    assert body['candidate_code'].startswith('C')

def test_candidate_create_missing_name(client, setup_data):
    """POST without name — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    res = client.post('/api/candidates/', json={
        'ballot_id': b_id,
    }, headers=headers)
    assert res.status_code == 400

def test_candidate_create_missing_ballot_id(client, setup_data):
    """POST without ballot_id — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
    }, headers=headers)
    assert res.status_code == 400

def test_candidate_create_invalid_ballot_id(client, setup_data):
    """POST with ballot_id: "abc" — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': 'abc',
    }, headers=headers)
    assert res.status_code == 400

def test_candidate_create_active_election(client, setup_data):
    """Create ballot in draft election, set election to active in DB, then POST candidate — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'active'
        db.session.commit()
        
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': b_id,
    }, headers=headers)
    assert res.status_code == 400

def test_candidate_create_cancelled_election(client, setup_data):
    """Same but cancelled — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'cancelled'
        db.session.commit()
        
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': b_id,
    }, headers=headers)
    assert res.status_code == 400

def test_candidate_create_completed_election(client, setup_data):
    """Same but completed — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'completed'
        db.session.commit()
        
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': b_id,
    }, headers=headers)
    assert res.status_code == 400

# --- Read ---

def test_candidate_get(client, setup_data):
    """GET /api/candidates/<id> — expect 200, response has keys"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body['id'] == cand_id
    assert 'name' in body
    assert 'candidate_code' in body
    assert body['ballot_id'] == b_id
    assert 'is_active' in body
    assert 'is_withdrawn' in body
    assert 'vote_summary' in body

def test_candidate_get_not_found(client, setup_data):
    """GET /api/candidates/99999 — expect 404"""
    headers = setup_data['headers']
    res = client.get('/api/candidates/99999', headers=headers)
    assert res.status_code == 404

# --- Update ---

def test_candidate_update(client, setup_data):
    """PUT with dict — expect 200"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.put(f'/api/candidates/{cand_id}', json={
        'name': 'Updated Name',
        'party': 'Independent'
    }, headers=headers)
    assert res.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.get_json()['name'] == 'Updated Name'
    assert res_get.get_json()['party'] == 'Independent'

def test_candidate_update_active_election(client, setup_data):
    """Set election to active in DB, then PUT — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'active'
        db.session.commit()
        
    res = client.put(f'/api/candidates/{cand_id}', json={
        'name': 'Updated Name',
        'party': 'Independent'
    }, headers=headers)
    assert res.status_code == 400

# --- Delete (soft delete) ---

def test_candidate_delete(client, setup_data):
    """DELETE a candidate — expect 200, then GET same id — expect 404"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.delete(f'/api/candidates/{cand_id}', headers=headers)
    assert res.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 404

def test_candidate_delete_active_election(client, setup_data):
    """Set election to active in DB, then DELETE — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'active'
        db.session.commit()
        
    res = client.delete(f'/api/candidates/{cand_id}', headers=headers)
    assert res.status_code == 400

# --- Soft deleted excluded from list ---

def test_deleted_candidate_excluded_from_list(client, setup_data):
    """Create candidate, DELETE it, GET /api/candidates/ — confirm deleted candidate NOT in data list"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res_del = client.delete(f'/api/candidates/{cand_id}', headers=headers)
    assert res_del.status_code == 200
    
    res_list = client.get('/api/candidates/', headers=headers)
    assert res_list.status_code == 200
    body = res_list.get_json()
    candidate_ids = [c['id'] for c in body['data']]
    assert cand_id not in candidate_ids

# --- Summary counts full dataset ---

def test_summary_counts_full_dataset(client, setup_data):
    """Create 3 candidates for same ballot, GET /api/candidates/?per_page=1 — confirm summary.total_candidates is 3, not 1"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    cand_id1 = create_candidate(client, headers, b_id)
    cand_id2 = client.post('/api/candidates/', json={
        'name': 'Jane Doe 2',
        'ballot_id': b_id,
    }, headers=headers).get_json()['candidate_id']
    cand_id3 = client.post('/api/candidates/', json={
        'name': 'Jane Doe 3',
        'ballot_id': b_id,
    }, headers=headers).get_json()['candidate_id']
    
    res = client.get('/api/candidates/?per_page=1', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert len(body['data']) == 1
    assert body['summary']['total_candidates'] == 3

# --- Withdraw and Reinstate ---

def test_candidate_withdraw(client, setup_data):
    """POST /api/candidates/<id>/withdraw with reason — expect 200, then GET candidate and confirm is_withdrawn == True and withdrawal_reason"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.post(f'/api/candidates/{cand_id}/withdraw', json={
        'withdrawal_reason': 'Personal reasons'
    }, headers=headers)
    assert res.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 200
    body = res_get.get_json()
    assert body['is_withdrawn'] is True
    assert body['withdrawal_reason'] == 'Personal reasons'

def test_candidate_withdraw_missing_reason(client, setup_data):
    """POST withdraw without any body — expect 200 with default reason"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.post(f'/api/candidates/{cand_id}/withdraw', headers=headers)
    assert res.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 200
    body = res_get.get_json()
    assert body['is_withdrawn'] is True
    assert body['withdrawal_reason'] == 'Candidate withdrawal'

def test_candidate_reinstate(client, setup_data):
    """Withdraw a candidate first, then POST /api/candidates/<id>/reinstate — expect 200, then GET and confirm is_withdrawn == False and is_active == True"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    # Withdraw
    res_w = client.post(f'/api/candidates/{cand_id}/withdraw', json={'withdrawal_reason': 'Reason'}, headers=headers)
    assert res_w.status_code == 200
    
    # Reinstate
    res_r = client.post(f'/api/candidates/{cand_id}/reinstate', headers=headers)
    assert res_r.status_code == 200
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 200
    body = res_get.get_json()
    assert body['is_withdrawn'] is False
    assert body['is_active'] is True

def test_candidate_reinstate_not_withdrawn(client, setup_data):
    """POST reinstate on a candidate that is NOT withdrawn — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    cand_id = create_candidate(client, headers, b_id)
    
    res = client.post(f'/api/candidates/{cand_id}/reinstate', headers=headers)
    assert res.status_code == 400

# --- Incumbent flag ---

def test_candidate_create_incumbent(client, setup_data):
    """POST with is_incumbent: true — expect 201, then GET and confirm is_incumbent == True. Then GET stats and confirm incumbent_candidates >= 1"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    res = client.post('/api/candidates/', json={
        'name': 'Jane Doe',
        'ballot_id': b_id,
        'is_incumbent': True
    }, headers=headers)
    assert res.status_code == 201
    cand_id = res.get_json()['candidate_id']
    
    res_get = client.get(f'/api/candidates/{cand_id}', headers=headers)
    assert res_get.status_code == 200
    assert res_get.get_json()['is_incumbent'] is True
    
    res_stats = client.get('/api/candidates/stats', headers=headers)
    assert res_stats.status_code == 200
    assert res_stats.get_json()['incumbent_candidates'] >= 1

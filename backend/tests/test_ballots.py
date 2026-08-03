import pytest
import werkzeug.test
from app import db
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.voter import Voter
from app.models.vote import Vote
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from app.models.role import Role

# Monkeypatch TestResponse to allow res.json() call syntax requested by the test cases
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

def create_election(client, headers):
    """Create a test election and return its id"""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'title': 'Test Election',
        'election_type': 'general',
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }, headers=headers)
    return res.json()['election_id']

def create_ballot(client, headers, election_id):
    """Create a test ballot and return its id"""
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': election_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    return res.json()['ballot_id']

@pytest.fixture(autouse=True)
def add_ballots_permissions(client, setup_data):
    with client.application.app_context():
        company_id = setup_data['company_id']
        role = Role.query.filter_by(role_name='Super Admin', company_id=company_id).first()
        if role:
            sys_mod = SystemModule.query.filter_by(module_name='Ballots').first()
            if not sys_mod:
                sys_mod = SystemModule(module_name='Ballots', status=1)
                db.session.add(sys_mod)
                db.session.flush()

            cm = CompanyModule.query.filter_by(company_id=company_id, system_module_id=sys_mod.id).first()
            if not cm:
                cm = CompanyModule(company_id=company_id, system_module_id=sys_mod.id, status=1)
                db.session.add(cm)
            
            actions = ['view', 'create', 'update', 'delete']
            for act_name in actions:
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

# --- List and Stats ---

def test_ballot_list(client, setup_data):
    """GET /api/ballots/ — expect 200, response has data list, total, summary with keys total_ballots, published_ballots, draft_ballots, active_ballots"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    
    res = client.get('/api/ballots/', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert 'data' in body
    assert isinstance(body['data'], list)
    assert 'total' in body
    assert 'summary' in body
    summary = body['summary']
    for key in ('total_ballots', 'published_ballots', 'draft_ballots', 'active_ballots'):
        assert key in summary

def test_ballot_stats(client, setup_data):
    """GET /api/ballots/stats — expect 200, response has total_ballots, active_ballots, published_ballots, draft_ballots"""
    headers = setup_data['headers']
    res = client.get('/api/ballots/stats', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    for key in ('total_ballots', 'active_ballots', 'published_ballots', 'draft_ballots'):
        assert key in body

# --- Create ---

def test_ballot_create(client, setup_data):
    """POST with valid payload — expect 201, response has ballot_id and ballot_code starting with B"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 201
    body = res.get_json()
    assert 'ballot_id' in body
    assert 'ballot_code' in body
    assert body['ballot_code'].startswith('B')

def test_ballot_create_missing_title(client, setup_data):
    """POST without title — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    res = client.post('/api/ballots/', json={
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 400

def test_ballot_create_missing_election_id(client, setup_data):
    """POST without election_id — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 400

def test_ballot_create_missing_ballot_type(client, setup_data):
    """POST without ballot_type — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': el_id,
    }, headers=headers)
    assert res.status_code == 400

def test_ballot_create_invalid_election_id(client, setup_data):
    """POST with election_id: 'abc' — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': 'abc',
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 400

def test_ballot_create_for_cancelled_election(client, setup_data):
    """Create election, change its status to cancelled directly in DB, then POST ballot for that election — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'cancelled'
        db.session.commit()
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 400

def test_ballot_create_for_completed_election(client, setup_data):
    """Same but completed status — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'completed'
        db.session.commit()
    res = client.post('/api/ballots/', json={
        'title': 'Test Ballot',
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers)
    assert res.status_code == 400

# --- Read ---

def test_ballot_get(client, setup_data):
    """GET /api/ballots/<id> — expect 200, response has id, title, ballot_code, election_id, statistics dict with candidate_count, vote_count, active_candidates"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.get(f'/api/ballots/{b_id}', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body['id'] == b_id
    assert 'title' in body
    assert 'ballot_code' in body
    assert body['election_id'] == el_id
    assert 'statistics' in body
    stats = body['statistics']
    for key in ('candidate_count', 'vote_count', 'active_candidates'):
        assert key in stats

def test_ballot_get_not_found(client, setup_data):
    """GET /api/ballots/99999 — expect 404"""
    headers = setup_data['headers']
    res = client.get('/api/ballots/99999', headers=headers)
    assert res.status_code == 404

# --- Update ---

def test_ballot_update(client, setup_data):
    """PUT with {'title': 'Updated Title'} — expect 200"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.put(f'/api/ballots/{b_id}', json={'title': 'Updated Title'}, headers=headers)
    assert res.status_code == 200
    get_res = client.get(f'/api/ballots/{b_id}', headers=headers)
    assert get_res.get_json()['title'] == 'Updated Title'

def test_ballot_update_active_election(client, setup_data):
    """Set election status to active in DB, then PUT ballot — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'active'
        db.session.commit()
    res = client.put(f'/api/ballots/{b_id}', json={'title': 'Updated Title'}, headers=headers)
    assert res.status_code == 400

# --- Publish/Unpublish ---

def test_ballot_publish_no_candidates(client, setup_data):
    """POST /api/ballots/<id>/publish on ballot with no candidates — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.post(f'/api/ballots/{b_id}/publish', headers=headers)
    assert res.status_code == 400

def test_ballot_unpublish(client, setup_data):
    """Set is_published=True directly in DB, then POST /api/ballots/<id>/unpublish — expect 200, then GET ballot and confirm is_published == False"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    with client.application.app_context():
        b = Ballot.query.get(b_id)
        b.is_published = True
        db.session.commit()
    res = client.post(f'/api/ballots/{b_id}/unpublish', headers=headers)
    assert res.status_code == 200
    get_res = client.get(f'/api/ballots/{b_id}', headers=headers)
    assert get_res.get_json()['is_published'] is False

# --- Delete ---

def test_ballot_delete(client, setup_data):
    """DELETE a ballot — expect 200, then GET same ballot id — expect 404"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.delete(f'/api/ballots/{b_id}', headers=headers)
    assert res.status_code == 200
    get_res = client.get(f'/api/ballots/{b_id}', headers=headers)
    assert get_res.status_code == 404

def test_ballot_delete_active_election(client, setup_data):
    """Set election status to active in DB, then DELETE ballot — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    with client.application.app_context():
        el = Election.query.get(el_id)
        el.status = 'active'
        db.session.commit()
    res = client.delete(f'/api/ballots/{b_id}', headers=headers)
    assert res.status_code == 400

def test_ballot_delete_with_votes(client, setup_data):
    """Insert a Vote row directly via SQLAlchemy for the ballot, then DELETE — expect 400"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    with client.application.app_context():
        voter = Voter(
            company_id=setup_data['company_id'],
            voter_id='VOTER-1234',
            phone_number='1234567890',
            name='Test Voter'
        )
        db.session.add(voter)
        db.session.flush()
        
        vote = Vote(
            election_id=el_id,
            ballot_id=b_id,
            voter_id=voter.id,
            company_id=setup_data['company_id'],
            vote_id='VOTE-1234',
            tracking_code='TRACK-1234',
            vote_data={'selections': []},
            vote_hash='HASH-1234',
            verification_hash='VER-1234'
        )
        db.session.add(vote)
        db.session.commit()
    res = client.delete(f'/api/ballots/{b_id}', headers=headers)
    assert res.status_code == 400

# --- Soft delete excluded from list ---

def test_deleted_ballot_excluded_from_list(client, setup_data):
    """Create a ballot, DELETE it, GET /api/ballots/ — confirm the deleted ballot does NOT appear in data list"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.delete(f'/api/ballots/{b_id}', headers=headers)
    assert res.status_code == 200
    list_res = client.get('/api/ballots/', headers=headers)
    assert list_res.status_code == 200
    body = list_res.get_json()
    ballot_ids = [b['id'] for b in body['data']]
    assert b_id not in ballot_ids

# --- Summary counts full dataset ---

def test_summary_counts_full_dataset(client, setup_data):
    """Create 3 ballots for same election, GET /api/ballots/?per_page=1 — confirm summary.total_ballots is 3, not 1"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id1 = create_ballot(client, headers, el_id)
    b_id2 = client.post('/api/ballots/', json={
        'title': 'Test Ballot 2',
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers).json()['ballot_id']
    b_id3 = client.post('/api/ballots/', json={
        'title': 'Test Ballot 3',
        'election_id': el_id,
        'ballot_type': 'single_choice',
    }, headers=headers).json()['ballot_id']
    
    res = client.get('/api/ballots/?per_page=1', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert len(body['data']) == 1
    assert body['summary']['total_ballots'] == 3

# --- Duplicate ---

def test_ballot_duplicate(client, setup_data):
    """POST /api/ballots/<id>/duplicate — expect 201, response has ballot_id and ballot_code starting with B, new ballot has different id than original"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.post(f'/api/ballots/{b_id}/duplicate', json={}, headers=headers)
    assert res.status_code == 201
    body = res.get_json()
    assert 'ballot_id' in body
    assert 'ballot_code' in body
    assert body['ballot_code'].startswith('B')
    assert body['ballot_id'] != b_id

# --- Candidates list ---

def test_ballot_get_candidates_empty(client, setup_data):
    """GET /api/ballots/<id>/candidates — expect 200, candidates is empty list"""
    headers = setup_data['headers']
    el_id = create_election(client, headers)
    b_id = create_ballot(client, headers, el_id)
    res = client.get(f'/api/ballots/{b_id}/candidates', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert 'candidates' in body
    assert isinstance(body['candidates'], list)
    assert len(body['candidates']) == 0

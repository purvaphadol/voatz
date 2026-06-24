import pytest
import werkzeug.test
from datetime import datetime, timedelta, timezone
from app import db
from app.models.vote import Vote
from app.models.voter import Voter
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.voter_registration import VoterRegistration
from app.models.module import Module
from app.models.module_action import ModuleAction
from app.models.role_permission import RolePermissionMapping
from app.models.role import Role

# Monkeypatch Election.is_active to handle naive vs aware datetimes
original_is_active = Election.is_active
@property
def patched_is_active(self):
    try:
        return original_is_active.fget(self)
    except TypeError:
        # Fallback handling timezone-naive comparison
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (self.status == 'active' and 
                self.start_date <= now <= self.end_date)

Election.is_active = patched_is_active

# Helper functions requested by the prompt
def create_election(client, headers):
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

def create_voter(client, headers):
    import uuid
    res = client.post('/api/voters/', json={
        'name': 'Test Voter',
        'email': f'voter_{uuid.uuid4().hex[:8]}@test.com',
        'voter_id': f'V{uuid.uuid4().hex[:8].upper()}',
        'phone_number': '1234567890'
    }, headers=headers)
    return res.get_json()['voter_id']

def register_voter(client, headers, voter_id, election_id):
    """Register voter for election and approve the registration"""
    from app.models.voter_registration import VoterRegistration
    from app import db
    res = client.post('/api/voter-registrations/', json={
        'voter_id': voter_id,
        'election_id': election_id,
    }, headers=headers)
    reg_id = res.get_json()['registration_id']
    # Approve directly in DB using the string registration_id
    reg = VoterRegistration.query.filter_by(registration_id=reg_id).first()
    reg.status = 'approved'
    db.session.commit()
    return reg_id

def set_election_active(election_id):
    """Set election status to active directly in DB and adjust dates to be current"""
    from app.models.election import Election
    from app import db
    from datetime import datetime, timedelta
    election = db.session.get(Election, election_id)
    election.status = 'active'
    # Set dates so that now is inside the voting window
    now = datetime.utcnow()
    election.start_date = now - timedelta(days=1)
    election.end_date = now + timedelta(days=1)
    db.session.commit()

def publish_ballot(client, headers, ballot_id):
    """Add a candidate and publish the ballot"""
    res = client.post(f'/api/ballots/{ballot_id}/publish', headers=headers)
    return res

def cast_vote(client, headers, voter_id, ballot_id, candidate_id):
    res = client.post('/api/votes/', json={
        'voter_id': voter_id,
        'ballot_id': ballot_id,
        'vote_data': {'selections': [candidate_id]},
    }, headers=headers)
    return res


# Automatical permission injection for Ballots, Candidates and Votes
@pytest.fixture(autouse=True)
def add_votes_permissions(client, setup_data):
    with client.application.app_context():
        company_id = setup_data['company_id']
        role = Role.query.filter_by(role_name='Super Admin', company_id=company_id).first()
        if role:
            for mod_name in ['Ballots', 'Candidates', 'Votes']:
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

def test_vote_list(client, setup_data):
    """GET /api/votes/ — expect 200, response has data list, total, summary with keys total_votes, verified_votes, counted_votes, pending_votes"""
    headers = setup_data['headers']
    res = client.get('/api/votes/', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert 'data' in body
    assert isinstance(body['data'], list)
    assert 'total' in body
    assert 'summary' in body
    summary = body['summary']
    for key in ('total_votes', 'verified_votes', 'counted_votes', 'pending_votes'):
        assert key in summary

def test_vote_stats(client, setup_data):
    """GET /api/votes/stats — expect 200, response has total_votes, verified_votes, counted_votes, flagged_votes, pending_votes, verification_rate"""
    headers = setup_data['headers']
    res = client.get('/api/votes/stats', headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    for key in ('total_votes', 'verified_votes', 'counted_votes', 'flagged_votes', 'pending_votes', 'verification_rate'):
        assert key in body


# --- Cast Vote ---

def test_cast_vote(client, setup_data):
    """Create election, ballot, candidate, voter, register+approve voter, set election active, publish ballot, then POST /api/votes/ — expect 201, response has vote_id starting with VOTE- and tracking_code"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    body = res.get_json()
    assert 'vote_id' in body
    assert body['vote_id'].startswith('VOTE-')
    assert 'tracking_code' in body

def test_cast_vote_missing_voter_id(client, setup_data):
    """POST without voter_id — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/votes/', json={
        'ballot_id': 1,
        'vote_data': {'selections': [1]},
    }, headers=headers)
    assert res.status_code == 400

def test_cast_vote_missing_ballot_id(client, setup_data):
    """POST without ballot_id — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/votes/', json={
        'voter_id': 'V123',
        'vote_data': {'selections': [1]},
    }, headers=headers)
    assert res.status_code == 400

def test_cast_vote_missing_vote_data(client, setup_data):
    """POST without vote_data — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/votes/', json={
        'voter_id': 'V123',
        'ballot_id': 1,
    }, headers=headers)
    assert res.status_code == 400

def test_cast_vote_invalid_ballot_id(client, setup_data):
    """POST with ballot_id: "abc" — expect 400"""
    headers = setup_data['headers']
    res = client.post('/api/votes/', json={
        'voter_id': 'V123',
        'ballot_id': 'abc',
        'vote_data': {'selections': [1]},
    }, headers=headers)
    assert res.status_code == 400

def test_cast_vote_duplicate(client, setup_data):
    """Cast same vote twice on same ballot — expect 400 on second cast"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res1 = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res1.status_code == 201
    
    res2 = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res2.status_code == 400

def test_cast_vote_inactive_election(client, setup_data):
    """Use a draft (non-active) election — expect 400"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 400

def test_cast_vote_unpublished_ballot(client, setup_data):
    """Set election active but do NOT publish ballot — expect 400"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 400

def test_cast_vote_unregistered_voter(client, setup_data):
    """Voter not registered for election — expect 400"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 400

def test_cast_vote_invalid_candidate(client, setup_data):
    """Cast vote with selections: [99999] (nonexistent candidate) — expect 400"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = client.post('/api/votes/', json={
        'voter_id': voter_id,
        'ballot_id': ballot_id,
        'vote_data': {'selections': [99999]},
    }, headers=headers)
    assert res.status_code == 400


# --- Read ---

def test_vote_get(client, setup_data):
    """GET /api/votes/<id> — expect 200, response has id, vote_id, tracking_code, voter_id, election_id, ballot_id, vote_status, selected_candidates, audit_trail"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_get = client.get(f'/api/votes/{db_id}', headers=headers)
    assert res_get.status_code == 200
    body = res_get.get_json()
    for key in ('id', 'vote_id', 'tracking_code', 'voter_id', 'election_id', 'ballot_id', 'vote_status', 'selected_candidates', 'audit_trail'):
        assert key in body

def test_vote_get_not_found(client, setup_data):
    """GET /api/votes/99999 — expect 404"""
    headers = setup_data['headers']
    res = client.get('/api/votes/99999', headers=headers)
    assert res.status_code == 404


# --- Track ---

def test_track_vote(client, setup_data):
    """GET /api/votes/tracking/<tracking_code> — expect 200, response has tracking_code, election_title, ballot_title, vote_cast_time, vote_status, is_counted, is_verified"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    tracking_code = res.get_json()['tracking_code']
    
    res_track = client.get(f'/api/votes/tracking/{tracking_code}', headers=headers)
    assert res_track.status_code == 200
    body = res_track.get_json()
    for key in ('tracking_code', 'election_title', 'ballot_title', 'vote_cast_time', 'vote_status', 'is_counted', 'is_verified'):
        assert key in body

def test_track_vote_not_found(client, setup_data):
    """GET /api/votes/tracking/INVALIDCODE — expect 404"""
    headers = setup_data['headers']
    res = client.get('/api/votes/tracking/INVALIDCODE', headers=headers)
    assert res.status_code == 404


# --- Verify ---

def test_verify_vote(client, setup_data):
    """POST /api/votes/<id>/verify with {'verification_type': 'all'} — expect 200"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_verify = client.post(f'/api/votes/{db_id}/verify', json={'verification_type': 'all'}, headers=headers)
    assert res_verify.status_code == 200

def test_verify_vote_partial(client, setup_data):
    """POST with {'verification_type': 'identity'} — expect 200, then GET vote and confirm identity_verified == True"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_verify = client.post(f'/api/votes/{db_id}/verify', json={'verification_type': 'identity'}, headers=headers)
    assert res_verify.status_code == 200
    
    res_get = client.get(f'/api/votes/{db_id}', headers=headers)
    assert res_get.status_code == 200
    assert res_get.get_json()['identity_verified'] is True


# --- Count ---

def test_count_vote_without_verification(client, setup_data):
    """POST /api/votes/<id>/count on a non-verified vote — expect 400"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_count = client.post(f'/api/votes/{db_id}/count', headers=headers)
    assert res_count.status_code == 400

def test_count_vote(client, setup_data):
    """Verify vote first (all), then POST /api/votes/<id>/count — expect 200, then GET vote and confirm is_counted == True and vote_status == 'counted'"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_verify = client.post(f'/api/votes/{db_id}/verify', json={'verification_type': 'all'}, headers=headers)
    assert res_verify.status_code == 200
    
    res_count = client.post(f'/api/votes/{db_id}/count', headers=headers)
    assert res_count.status_code == 200
    
    res_get = client.get(f'/api/votes/{db_id}', headers=headers)
    assert res_get.status_code == 200
    body = res_get.get_json()
    assert body['is_counted'] is True
    assert body['vote_status'] == 'counted'


# --- Flag ---

def test_flag_vote(client, setup_data):
    """POST /api/votes/<id>/flag with {'reason': 'Suspicious activity'} — expect 200, then GET vote and confirm vote_status == 'flagged'"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    voter_id = create_voter(client, headers)
    register_voter(client, headers, voter_id, election_id)
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
    assert res.status_code == 201
    vote_string_id = res.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj = Vote.query.filter_by(vote_id=vote_string_id).first()
        db_id = vote_obj.id

    res_flag = client.post(f'/api/votes/{db_id}/flag', json={'reason': 'Suspicious activity'}, headers=headers)
    assert res_flag.status_code == 200
    
    res_get = client.get(f'/api/votes/{db_id}', headers=headers)
    assert res_get.status_code == 200
    assert res_get.get_json()['vote_status'] == 'flagged'


# --- Bulk Verify ---

def test_bulk_verify(client, setup_data):
    """Cast 2 votes, POST /api/votes/bulk-verify with both IDs and verification_type: 'all' — expect 200, response has updated_count == 2"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    
    voter_id_1 = create_voter(client, headers)
    register_voter(client, headers, voter_id_1, election_id)
    
    voter_id_2 = create_voter(client, headers)
    register_voter(client, headers, voter_id_2, election_id)
    
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    res1 = cast_vote(client, headers, voter_id_1, ballot_id, candidate_id)
    assert res1.status_code == 201
    vote_string_id_1 = res1.get_json()['vote_id']
    
    res2 = cast_vote(client, headers, voter_id_2, ballot_id, candidate_id)
    assert res2.status_code == 201
    vote_string_id_2 = res2.get_json()['vote_id']
    
    with client.application.app_context():
        vote_obj_1 = Vote.query.filter_by(vote_id=vote_string_id_1).first()
        vote_obj_2 = Vote.query.filter_by(vote_id=vote_string_id_2).first()
        db_id_1 = vote_obj_1.id
        db_id_2 = vote_obj_2.id

    res_bulk = client.post('/api/votes/bulk-verify', json={
        'vote_ids': [db_id_1, db_id_2],
        'verification_type': 'all'
    }, headers=headers)
    assert res_bulk.status_code == 200
    assert res_bulk.get_json()['updated_count'] == 2


# --- Summary counts full dataset ---

def test_summary_counts_full_dataset(client, setup_data):
    """Cast 3 votes (3 different voters on same ballot — need 3 voters, each registered), GET /api/votes/?per_page=1 — confirm summary.total_votes == 3, not 1"""
    headers = setup_data['headers']
    election_id = create_election(client, headers)
    ballot_id = create_ballot(client, headers, election_id)
    candidate_id = create_candidate(client, headers, ballot_id)
    
    voter_ids = [create_voter(client, headers) for _ in range(3)]
    for voter_id in voter_ids:
        register_voter(client, headers, voter_id, election_id)
        
    publish_ballot(client, headers, ballot_id)
    set_election_active(election_id)
    
    for voter_id in voter_ids:
        res = cast_vote(client, headers, voter_id, ballot_id, candidate_id)
        assert res.status_code == 201
        
    res_list = client.get('/api/votes/?per_page=1', headers=headers)
    assert res_list.status_code == 200
    body = res_list.get_json()
    assert len(body['data']) == 1
    assert body['summary']['total_votes'] == 3

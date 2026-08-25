import pytest
from app import db
from app.models.election import Election
from datetime import datetime, timezone, timedelta

# Fixtures (app, client, setup_data) are auto-imported from conftest.py


def create_election(client, headers, title='Test Election', election_type='general'):
    """Helper that POSTs a valid election and returns the response."""
    now = datetime.now(timezone.utc)
    payload = {
        'title': title,
        'election_type': election_type,
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }
    return client.post('/api/elections/', json=payload, headers=headers)


# --- List and Stats ---

def test_election_list(client, setup_data):
    """GET /api/elections/ — 200, has data, total, summary with all expected keys"""
    res = client.get('/api/elections/', headers=setup_data['headers'])
    assert res.status_code == 200
    body = res.get_json()
    assert 'data' in body
    assert isinstance(body['data'], list)
    assert 'total' in body
    summary = body['summary']
    for key in ('total_elections', 'active_elections', 'draft_elections',
                'completed_elections', 'upcoming_elections'):
        assert key in summary, f"Missing summary key: {key}"


def test_election_stats(client, setup_data):
    """GET /api/elections/stats — 200, has all stat fields the frontend expects"""
    res = client.get('/api/elections/stats', headers=setup_data['headers'])
    assert res.status_code == 200
    body = res.get_json()
    for key in ('total_elections', 'active_elections', 'upcoming_elections',
                'completed_elections'):
        assert key in body, f"Missing stats key: {key}"


# --- Create ---

def test_election_create(client, setup_data):
    """POST valid election — 201, has election_id and election_code starting with E"""
    res = create_election(client, setup_data['headers'])
    assert res.status_code == 201
    body = res.get_json()
    assert 'election_id' in body
    assert 'election_code' in body
    assert body['election_code'].startswith('E')


def test_election_create_missing_title(client, setup_data):
    """POST without title — 400"""
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'election_type': 'general',
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }, headers=setup_data['headers'])
    assert res.status_code == 400


def test_election_create_missing_type(client, setup_data):
    """POST without election_type — 400"""
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'title': 'No Type',
        'start_date': (now + timedelta(days=7)).isoformat(),
        'end_date': (now + timedelta(days=14)).isoformat(),
    }, headers=setup_data['headers'])
    assert res.status_code == 400


def test_election_create_invalid_dates(client, setup_data):
    """POST with start_date after end_date — 400"""
    now = datetime.now(timezone.utc)
    res = client.post('/api/elections/', json={
        'title': 'Bad Dates',
        'election_type': 'general',
        'start_date': (now + timedelta(days=14)).isoformat(),
        'end_date': (now + timedelta(days=7)).isoformat(),
    }, headers=setup_data['headers'])
    assert res.status_code == 400


def test_election_create_missing_dates(client, setup_data):
    """POST without start_date — 400"""
    res = client.post('/api/elections/', json={
        'title': 'No Dates',
        'election_type': 'general',
    }, headers=setup_data['headers'])
    assert res.status_code == 400


# --- Read ---

def test_election_get(client, setup_data):
    """GET /api/elections/<id> — 200, has expected fields"""
    create_res = create_election(client, setup_data['headers'], title='Detail Election')
    election_id = create_res.get_json()['election_id']
    res = client.get(f'/api/elections/{election_id}', headers=setup_data['headers'])
    assert res.status_code == 200
    body = res.get_json()
    assert body['id'] == election_id
    assert body['title'] == 'Detail Election'
    assert 'election_code' in body
    assert body['status'] == 'draft'
    stats = body['statistics']
    for key in ('ballot_count', 'registration_count', 'vote_count'):
        assert key in stats, f"Missing statistics key: {key}"


def test_election_get_not_found(client, setup_data):
    """GET /api/elections/99999 — 404"""
    res = client.get('/api/elections/99999', headers=setup_data['headers'])
    assert res.status_code == 404


# --- Update ---

def test_election_update(client, setup_data):
    """PUT with title change — 200"""
    create_res = create_election(client, setup_data['headers'], title='Original Title')
    election_id = create_res.get_json()['election_id']
    res = client.put(f'/api/elections/{election_id}',
                     json={'title': 'Updated Title'},
                     headers=setup_data['headers'])
    assert res.status_code == 200


def test_election_update_active_dates(client, setup_data):
    """PUT with start_date on active election — 400 (date change blocked)"""
    create_res = create_election(client, setup_data['headers'], title='Active Date Block')
    election_id = create_res.get_json()['election_id']
    # Set status to active directly in DB
    with client.application.app_context():
        election = Election.query.filter_by(id=election_id).first()
        election.status = 'active'
        db.session.commit()
    now = datetime.now(timezone.utc)
    res = client.put(f'/api/elections/{election_id}',
                     json={'start_date': (now + timedelta(days=10)).isoformat()},
                     headers=setup_data['headers'])
    assert res.status_code == 400
    assert 'date' in res.get_json()['error'].lower()


# --- Status Changes ---

def test_election_change_status_to_cancelled(client, setup_data):
    """POST change-status to cancelled — 200, then GET confirms cancelled"""
    create_res = create_election(client, setup_data['headers'], title='Cancel Me')
    election_id = create_res.get_json()['election_id']
    res = client.post(f'/api/elections/{election_id}/change-status',
                      json={'status': 'cancelled'},
                      headers=setup_data['headers'])
    assert res.status_code == 200
    get_res = client.get(f'/api/elections/{election_id}', headers=setup_data['headers'])
    assert get_res.status_code == 200
    assert get_res.get_json()['status'] == 'cancelled'


def test_election_change_status_invalid(client, setup_data):
    """POST change-status with invalid status — 400"""
    create_res = create_election(client, setup_data['headers'], title='Bad Status')
    election_id = create_res.get_json()['election_id']
    res = client.post(f'/api/elections/{election_id}/change-status',
                      json={'status': 'invalid_status'},
                      headers=setup_data['headers'])
    assert res.status_code == 400


def test_election_activate_no_ballots(client, setup_data):
    """POST activate on draft election with no ballots — 400"""
    create_res = create_election(client, setup_data['headers'], title='No Ballots')
    election_id = create_res.get_json()['election_id']
    res = client.post(f'/api/elections/{election_id}/activate',
                      headers=setup_data['headers'])
    assert res.status_code == 400
    assert 'ballot' in res.get_json()['error'].lower()


def test_election_activate_empty_ballot(client, setup_data):
    """POST activate on draft election with ballot having zero candidates — 400 with ballot name"""
    from app.models.ballot import Ballot
    from app.utils.constants import STATUS_ACTIVE

    create_res = create_election(client, setup_data['headers'], title='Empty Ballot Election')
    election_id = create_res.get_json()['election_id']
    
    with client.application.app_context():
        ballot = Ballot(
            company_id=setup_data['company_id'],
            election_id=election_id,
            title='Unpopulated Ballot',
            ballot_code='BAL-EMPTY-1',
            ballot_type='single_choice',
            status=STATUS_ACTIVE,
            is_active=True
        )
        db.session.add(ballot)
        db.session.commit()

    res = client.post(f'/api/elections/{election_id}/activate', headers=setup_data['headers'])
    assert res.status_code == 400
    err_msg = res.get_json()['error']
    assert 'Unpopulated Ballot' in err_msg
    assert 'no active candidates' in err_msg.lower()



# --- Delete ---

def test_election_delete(client, setup_data):
    """DELETE a draft election — 200"""
    create_res = create_election(client, setup_data['headers'], title='Delete Me')
    election_id = create_res.get_json()['election_id']
    res = client.delete(f'/api/elections/{election_id}',
                        headers=setup_data['headers'])
    assert res.status_code == 200


def test_election_delete_active(client, setup_data):
    """DELETE an active election — 400"""
    create_res = create_election(client, setup_data['headers'], title='Active No Delete')
    election_id = create_res.get_json()['election_id']
    with client.application.app_context():
        election = Election.query.filter_by(id=election_id).first()
        election.status = 'active'
        db.session.commit()
    res = client.delete(f'/api/elections/{election_id}',
                        headers=setup_data['headers'])
    assert res.status_code == 400


# --- Cancelled excluded from list ---

def test_cancelled_election_excluded_from_list(client, setup_data):
    """Cancelled elections excluded by default, included with show_cancelled=true"""
    create_res = create_election(client, setup_data['headers'], title='Will Cancel')
    election_id = create_res.get_json()['election_id']
    # Cancel the election
    client.post(f'/api/elections/{election_id}/change-status',
                json={'status': 'cancelled'},
                headers=setup_data['headers'])
    # Default list should NOT include cancelled
    list_res = client.get('/api/elections/', headers=setup_data['headers'])
    ids = [e['id'] for e in list_res.get_json()['data']]
    assert election_id not in ids
    # With show_cancelled=true, should include it
    list_res2 = client.get('/api/elections/?show_cancelled=true', headers=setup_data['headers'])
    ids2 = [e['id'] for e in list_res2.get_json()['data']]
    assert election_id in ids2


# --- Summary counts are full-dataset not page-only ---

def test_summary_counts_full_dataset(client, setup_data):
    """Create 3 elections, GET with per_page=1 — summary.total_elections should be >= 3"""
    for i in range(3):
        create_election(client, setup_data['headers'], title=f'Bulk {i}')
    res = client.get('/api/elections/?per_page=1', headers=setup_data['headers'])
    assert res.status_code == 200
    body = res.get_json()
    # Only 1 item on the page
    assert len(body['data']) == 1
    # But summary.total_elections reflects all non-cancelled elections
    assert body['summary']['total_elections'] >= 3

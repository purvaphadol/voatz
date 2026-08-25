import pytest
from datetime import datetime, timedelta, timezone
from app import db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.vote import Vote
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE

def provision_votes_permissions(company_id):
    """Ensure Votes module and update action are provisioned for role 1."""
    votes_mod = SystemModule.query.filter_by(module_name="Votes").first()
    if not votes_mod:
        votes_mod = SystemModule(module_name="Votes", status=STATUS_ACTIVE)
        db.session.add(votes_mod)
        db.session.flush()
        db.session.add(CompanyModule(company_id=company_id, system_module_id=votes_mod.id, status=STATUS_ACTIVE))
        update_v_act = SystemModuleAction(action_name="update", action_url="", system_module_id=votes_mod.id, status=STATUS_ACTIVE)
        db.session.add(update_v_act)
        db.session.flush()
        db.session.add(RolePermissionMapping(role_id=1, module_id=votes_mod.id, action_id=update_v_act.id, company_id=company_id, status=STATUS_ACTIVE))
        db.session.commit()
    else:
        update_v_act = SystemModuleAction.query.filter_by(system_module_id=votes_mod.id, action_name="update").first()
        if not update_v_act:
            update_v_act = SystemModuleAction(action_name="update", action_url="", system_module_id=votes_mod.id, status=STATUS_ACTIVE)
            db.session.add(update_v_act)
            db.session.flush()
            db.session.add(RolePermissionMapping(role_id=1, module_id=votes_mod.id, action_id=update_v_act.id, company_id=company_id, status=STATUS_ACTIVE))
            db.session.commit()

def test_bug2_falsy_zero_status_update_and_cascade(client, setup_data):
    """
    Dedicated test for Bug #2: Verify that updating status to integer 0 (STATUS_INACTIVE)
    is NOT ignored as falsy, actually updates election.status to 0, and triggers cascading deactivation.
    """
    headers = setup_data['headers']
    company_id = setup_data['company_id']
    
    now = datetime.now(timezone.utc)
    election = Election(
        title="Falsy Zero Test Election",
        election_code="E_FALSY_ZERO",
        election_type="general",
        start_date=now,
        end_date=now + timedelta(days=1),
        status="active",
        company_id=company_id
    )
    db.session.add(election)
    db.session.commit()

    ballot = Ballot(
        election_id=election.id,
        title="Falsy Zero Ballot",
        ballot_code="B_FALSY_ZERO",
        ballot_type="single_choice",
        status=STATUS_ACTIVE,
        is_active=True,
        company_id=company_id
    )
    db.session.add(ballot)
    db.session.commit()

    candidate = Candidate(
        ballot_id=ballot.id,
        candidate_code="C_FALSY_ZERO",
        name="Candidate Zero",
        status=STATUS_ACTIVE,
        is_active=True,
        company_id=company_id
    )
    db.session.add(candidate)
    db.session.commit()

    # Pre-condition assertion
    assert election.status in ("active", "1", 1)
    assert ballot.is_active is True
    assert candidate.is_active is True

    # Update election status to integer 0 (STATUS_INACTIVE)
    res = client.put(f'/api/elections/{election.id}', headers=headers, json={'status': STATUS_INACTIVE})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.get_json()}"

    # Refresh from DB and verify status changed to 0 (or '0' / 'inactive') AND cascading occurred
    db.session.refresh(election)
    db.session.refresh(ballot)
    db.session.refresh(candidate)

    assert str(election.status) in ("0", "inactive", "STATUS_INACTIVE"), f"Expected status 0/inactive, got {election.status}"
    assert ballot.is_active is False, "Expected ballot.is_active to be False after cascade"
    assert candidate.is_active is False, "Expected candidate.is_active to be False after cascade"


def test_bug1_tally_votes_no_body_and_malformed_body(client, setup_data):
    """
    Dedicated test for Bug #1: Verify tally_election_votes handles no body gracefully
    without 415 error, and handles malformed JSON without crashing.
    """
    headers = setup_data['headers']
    company_id = setup_data['company_id']
    provision_votes_permissions(company_id)
    
    now = datetime.now(timezone.utc)
    election = Election(
        title="Tally Test Election",
        election_code="E_TALLY_TEST",
        election_type="general",
        start_date=now,
        end_date=now + timedelta(days=1),
        status="active",
        company_id=company_id
    )
    db.session.add(election)
    db.session.commit()

    # Call POST /api/elections/<id>/tally with NO body and NO content-type header
    res_no_body = client.post(f'/api/elections/{election.id}/tally', headers=headers)
    assert res_no_body.status_code == 200, f"Expected 200 OK when posting with no body, got {res_no_body.status_code}"
    assert "tally" in res_no_body.get_json()['message'].lower()

    # Call POST with malformed JSON body
    res_malformed = client.post(
        f'/api/elections/{election.id}/tally',
        headers={**headers, 'Content-Type': 'application/json'},
        data='{"auto_verify": ' # truncated invalid JSON
    )
    assert res_malformed.status_code == 200, "Expected silent fallback to default dict, got error"
    assert "tally" in res_malformed.get_json()['message'].lower()


def test_status_dependents_endpoint_permissions_and_response_shape(client, setup_data):
    """
    Dedicated test for get_election_status_dependents endpoint:
    - Verifies permissions & response shape
    - Verifies zero vote leakage
    """
    headers = setup_data['headers']
    company_id = setup_data['company_id']

    now = datetime.now(timezone.utc)
    election = Election(
        title="Deps Test Election",
        election_code="E_DEPS_TEST",
        election_type="general",
        start_date=now,
        end_date=now + timedelta(days=1),
        status="active",
        company_id=company_id
    )
    db.session.add(election)
    db.session.commit()

    ballot = Ballot(
        election_id=election.id,
        title="Deps Ballot",
        ballot_code="B_DEPS",
        ballot_type="single_choice",
        status=STATUS_ACTIVE,
        is_active=True,
        company_id=company_id
    )
    db.session.add(ballot)
    db.session.commit()

    candidate = Candidate(
        ballot_id=ballot.id,
        candidate_code="C_DEPS",
        name="Candidate Deps",
        status=STATUS_ACTIVE,
        is_active=True,
        company_id=company_id
    )
    db.session.add(candidate)
    db.session.commit()

    res = client.get(f'/api/elections/{election.id}/status_dependents', headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert 'current_status' in data
    assert 'dependents' in data
    deps = data['dependents']
    assert deps['ballots'] == 1
    assert deps['candidates'] == 1
    assert deps['voter_registrations'] == 0
    # Confirm NO vote counts or result metrics are included
    assert 'total_votes_received' not in deps
    assert 'total_votes' not in deps
    assert 'vote_percentage' not in deps

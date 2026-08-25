import pytest
from app import create_app, db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED
from datetime import datetime, timedelta, timezone

def test_delete_election_candidate_count_alignment(client, admin_headers):
    """
    Item 8 Verification:
    Verify that delete_election pre-delete dependency count uses Candidate.status != STATUS_DEACTIVATED
    matching the actual deactivation loop count.
    """
    now = datetime.now(timezone.utc)
    election = Election(
        title="Test Item 8 Election",
        election_code="E8_TEST_CODE",
        election_type="general",
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=2),
        status="draft",
        company_id=1
    )
    db.session.add(election)
    db.session.commit()

    ballot = Ballot(
        election_id=election.id,
        title="Test Item 8 Ballot",
        ballot_code="B8_TEST_CODE",
        position_title="President",
        company_id=1
    )
    db.session.add(ballot)
    db.session.commit()

    # Create 1 Active candidate and 1 Inactive candidate
    cand_active = Candidate(
        ballot_id=ballot.id,
        name="Active Candidate 8",
        status=STATUS_ACTIVE,
        company_id=1
    )
    cand_inactive = Candidate(
        ballot_id=ballot.id,
        name="Inactive Candidate 8",
        status=STATUS_INACTIVE,
        company_id=1
    )
    db.session.add_all([cand_active, cand_inactive])
    db.session.commit()

    # 1. Pre-delete call without force: check dependency count returned by backend
    res = client.delete(f'/api/elections/{election.id}', headers=admin_headers)
    assert res.status_code == 400
    data = res.get_json()
    active_deps = data.get('active_dependencies', {})
    candidate_count_reported = active_deps.get('candidates')

    # Candidate count should be 2 because both STATUS_ACTIVE and STATUS_INACTIVE are != STATUS_DEACTIVATED
    assert candidate_count_reported == 2, f"Expected 2 candidate dependencies reported, got {candidate_count_reported}"

    # 2. Force delete call
    res_force = client.delete(f'/api/elections/{election.id}?force=true', headers=admin_headers)
    assert res_force.status_code == 200

    # 3. Verify candidates actually transitioned to STATUS_DEACTIVATED
    db.session.refresh(cand_active)
    db.session.refresh(cand_inactive)
    assert cand_active.status == STATUS_DEACTIVATED
    assert cand_inactive.status == STATUS_DEACTIVATED
    print(f"\nItem 8 Verified: Pre-delete reported {candidate_count_reported} candidates; exactly 2 candidates transitioned to {STATUS_DEACTIVATED}.")

import pytest
from app import db
from app.models.election import Election
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from datetime import datetime, timedelta, timezone

def test_get_voter_registration_excludes_cancelled_election(client, company_a_headers):
    """
    Item 9 Verification:
    Verify that GET /api/voter-registrations/<id> excludes registrations for cancelled elections (returning 404).
    Before fix, Election.status != str(STATUS_INACTIVE) compared against '0' (no-op) and would have allowed cancelled elections.
    """
    now = datetime.now(timezone.utc)
    
    # Create cancelled election
    election = Election(
        title="Cancelled Election Item 9",
        election_code="E9_CANCELLED",
        election_type="general",
        start_date=now - timedelta(days=2),
        end_date=now - timedelta(days=1),
        status="cancelled",
        company_id=1
    )
    db.session.add(election)
    db.session.commit()

    # Create voter
    voter = Voter(
        name="Voter Item 9",
        phone_number="9990009999",
        status=1,
        company_id=1
    )
    db.session.add(voter)
    db.session.commit()

    # Create voter registration for cancelled election
    reg = VoterRegistration(
        voter_id=voter.id,
        election_id=election.id,
        registration_id="REG-ITEM9-TEST",
        status="approved",
        company_id=1
    )
    db.session.add(reg)
    db.session.commit()

    # GET /api/voter-registrations/<id> should return 404 because election is cancelled
    res = client.get(f'/api/voter-registrations/{reg.id}', headers=company_a_headers)
    assert res.status_code == 404, f"Expected 404 for registration under cancelled election, got {res.status_code}"

    # Also test an active/draft election's registration returns 200
    election.status = "draft"
    db.session.commit()

    res_active = client.get(f'/api/voter-registrations/{reg.id}', headers=company_a_headers)
    assert res_active.status_code == 200, f"Expected 200 for registration under active/draft election, got {res_active.status_code}"

    print(f"\nItem 9 Verified: Registration for cancelled election correctly returns 404 (excluded), draft election returns 200.")

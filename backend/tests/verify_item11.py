import pytest
from app import db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from datetime import datetime, timedelta, timezone
from app.utils.constants import STATUS_ACTIVE

def test_election_results_rank_position_and_party(client, admin_headers):
    """
    Item 11 Verification:
    Verify that vote tallying sets candidate.rank_position = 1 for the winner,
    and that the candidates list API returns rank_position and party_display / party for ElectionResults.js rendering.
    """
    now = datetime.now(timezone.utc)
    
    election = Election(
        title="Item 11 Results Test Election",
        election_code="E11_TEST_CODE",
        election_type="general",
        start_date=now - timedelta(hours=2),
        end_date=now + timedelta(hours=2),
        status="draft",
        company_id=1
    )
    db.session.add(election)
    db.session.commit()

    ballot = Ballot(
        election_id=election.id,
        title="Presidential Race",
        ballot_code="B11_TEST_CODE",
        ballot_type="single_choice",
        position_title="President",
        is_active=True,
        is_published=True,
        company_id=1
    )
    db.session.add(ballot)
    db.session.commit()

    cand1 = Candidate(
        ballot_id=ballot.id,
        name="Alice Winner",
        party="Democrat Party",
        party_abbreviation="DEM",
        status=STATUS_ACTIVE,
        company_id=1
    )
    cand2 = Candidate(
        ballot_id=ballot.id,
        name="Bob Runnerup",
        party="Republican Party",
        party_abbreviation="GOP",
        status=STATUS_ACTIVE,
        company_id=1
    )
    db.session.add_all([cand1, cand2])
    db.session.commit()

    # Activate election
    election.status = "active"
    db.session.commit()

    # Register voter
    voter = Voter(name="Voter 11", phone_number="1112223333", status=1, company_id=1)
    db.session.add(voter)
    db.session.commit()

    vreg = VoterRegistration(
        voter_id=voter.id,
        election_id=election.id,
        registration_id="REG11_TEST",
        status="approved",
        company_id=1
    )
    db.session.add(vreg)
    db.session.commit()

    # Cast vote for cand1
    vote_res = client.post('/api/votes/', headers=admin_headers, json={
        'voter_id': voter.id,
        'ballot_id': ballot.id,
        'vote_data': {'selected_candidates': [cand1.id]}
    })
    assert vote_res.status_code == 201

    # End election voting window to allow publishing results
    election.end_date = now - timedelta(minutes=1)
    db.session.commit()

    # Publish results (triggers tally_election_votes)
    pub_res = client.post(f'/api/elections/{election.id}/publish-results', headers=admin_headers)
    assert pub_res.status_code == 200

    # Fetch candidates for election
    res = client.get(f'/api/candidates/?election_id={election.id}', headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()['data']

    cand1_data = next(c for c in data if c['id'] == cand1.id)
    cand2_data = next(c for c in data if c['id'] == cand2.id)

    assert cand1_data['rank_position'] == 1, f"Expected cand1 rank_position=1, got {cand1_data['rank_position']}"
    assert cand1_data['party'] == "Democrat Party"
    assert cand1_data['party_display'] == "DEM"

    assert cand2_data['rank_position'] in [2, None]
    assert cand2_data['party'] == "Republican Party"
    assert cand2_data['party_display'] == "GOP"

    print("\nItem 11 Verified: Winner candidate rank_position set to 1, party display verified for UI rendering.")

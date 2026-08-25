import pytest
from app import db
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from app.models.vote import Vote
from app.models.user import User
from app.models.company import Company
from app.models.department import Department
from app.models.role import Role
from app.models.user_role import UserRoleMapping
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta, timezone
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED

def test_scenario_a_full_election_lifecycle(client, setup_data):
    """
    Scenario A End-to-End Verification Protocol
    """
    headers = setup_data['headers']
    company_id = setup_data['company_id']
    user_id = setup_data['user_id']
    now = datetime.utcnow()
    
    # Ensure Votes module is provisioned for admin user role
    votes_mod = SystemModule.query.filter_by(module_name="Votes").first()
    if not votes_mod:
        votes_mod = SystemModule(module_name="Votes", status=STATUS_ACTIVE)
        db.session.add(votes_mod)
        db.session.flush()
        db.session.add(CompanyModule(company_id=company_id, system_module_id=votes_mod.id, status=STATUS_ACTIVE))
        create_v_act = SystemModuleAction(action_name="create", action_url="", system_module_id=votes_mod.id, status=STATUS_ACTIVE)
        view_v_act = SystemModuleAction(action_name="view", action_url="", system_module_id=votes_mod.id, status=STATUS_ACTIVE)
        update_v_act = SystemModuleAction(action_name="update", action_url="", system_module_id=votes_mod.id, status=STATUS_ACTIVE)
        db.session.add_all([create_v_act, view_v_act, update_v_act])
        db.session.flush()

        # Grant to super admin role (role_id 1 in setup_data)
        db.session.add(RolePermissionMapping(role_id=1, module_id=votes_mod.id, action_id=create_v_act.id, company_id=company_id, status=STATUS_ACTIVE))
        db.session.add(RolePermissionMapping(role_id=1, module_id=votes_mod.id, action_id=view_v_act.id, company_id=company_id, status=STATUS_ACTIVE))
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

    # Setup Candidates system module and actions if not present
    cand_mod = SystemModule.query.filter_by(module_name="Candidates").first()
    if not cand_mod:
        cand_mod = SystemModule(module_name="Candidates", status=STATUS_ACTIVE)
        db.session.add(cand_mod)
        db.session.flush()
        db.session.add(CompanyModule(company_id=company_id, system_module_id=cand_mod.id, status=STATUS_ACTIVE))
        view_act = SystemModuleAction(action_name="view", action_url="", system_module_id=cand_mod.id, status=STATUS_ACTIVE)
        db.session.add(view_act)
        db.session.flush()
    else:
        view_act = SystemModuleAction.query.filter_by(system_module_id=cand_mod.id, action_name="view").first()

    # Setup a non-privileged user who only has Candidates:view permission
    non_priv_user = User(
        name="Non Privileged User",
        email="nonpriv_scen_a@test.com",
        company_id=company_id,
        status=STATUS_ACTIVE
    )
    non_priv_user.password_hash = generate_password_hash("password123")
    db.session.add(non_priv_user)
    db.session.flush()

    non_priv_role = Role(role_name="Candidates Viewer Only", company_id=company_id, status=STATUS_ACTIVE)
    db.session.add(non_priv_role)
    db.session.flush()

    db.session.add(UserRoleMapping(user_id=non_priv_user.id, role_id=non_priv_role.id, company_id=company_id, status=STATUS_ACTIVE))
    db.session.add(RolePermissionMapping(role_id=non_priv_role.id, module_id=cand_mod.id, action_id=view_act.id, company_id=company_id, status=STATUS_ACTIVE))
    db.session.commit()

    non_priv_token = create_access_token(identity=str(non_priv_user.id))
    non_priv_headers = {'Authorization': f'Bearer {non_priv_token}'}

    # 1. Create election (draft), ballot, and two candidates
    election = Election(
        title="Scenario A Lifecycle Election",
        election_code="E_SCENARIO_A",
        election_type="general",
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=5),
        status="draft",
        company_id=company_id
    )
    db.session.add(election)
    db.session.commit()

    ballot = Ballot(
        election_id=election.id,
        title="Main Ballot Scenario A",
        ballot_code="B_SCENARIO_A",
        ballot_type="single_choice",
        status=STATUS_ACTIVE,
        is_active=True,
        is_published=True,
        company_id=company_id
    )
    db.session.add(ballot)
    db.session.commit()

    cand1 = Candidate(ballot_id=ballot.id, candidate_code="CAND-A1", name="Cand A1", party="Party Red", status=STATUS_ACTIVE, total_votes_received=0, company_id=company_id)
    cand2 = Candidate(ballot_id=ballot.id, candidate_code="CAND-A2", name="Cand A2", party="Party Blue", status=STATUS_ACTIVE, total_votes_received=0, company_id=company_id)
    db.session.add_all([cand1, cand2])
    db.session.commit()
    print(f"\n[Step 1] Created election {election.id}, ballot {ballot.id}, candidates {cand1.id}, {cand2.id}")

    # 2. Withdraw/deactivate cand1 and cand2 so ballot has zero active candidates (Item 5)
    cand1.status = STATUS_INACTIVE
    cand1.is_active = False
    cand2.status = STATUS_INACTIVE
    cand2.is_active = False
    db.session.commit()

    res_act = client.post(f'/api/elections/{election.id}/activate', headers=headers)
    print(f"[Step 2] Activate with 0 active candidates status: {res_act.status_code}, response: {res_act.get_json()}")
    assert res_act.status_code == 400
    assert "Main Ballot Scenario A" in res_act.get_json()['error']

    # 3. Reinstate candidates and activate election successfully
    cand1.status = STATUS_ACTIVE
    cand1.is_active = True
    cand2.status = STATUS_ACTIVE
    cand2.is_active = True
    db.session.commit()

    res_act_ok = client.post(f'/api/elections/{election.id}/activate', headers=headers)
    print(f"[Step 3] Activate election with active candidates status: {res_act_ok.status_code}, response: {res_act_ok.get_json()}")
    assert res_act_ok.status_code == 200

    # 4. Register and approve a voter (Item 3)
    voter = Voter(voter_id="VOTER-SCENARIO-A", name="Scenario A Voter", phone_number="5551112222", status=STATUS_ACTIVE, company_id=company_id)
    db.session.add(voter)
    db.session.commit()

    reg = VoterRegistration(voter_id=voter.id, election_id=election.id, registration_id="REG-SCENARIO-A", status="approved", company_id=company_id)
    db.session.add(reg)
    db.session.commit()
    print(f"[Step 4] Registered voter {voter.id} with approved registration {reg.id}")

    # 5. Cast a vote successfully
    res_vote1 = client.post('/api/votes/', headers=headers, json={
        'voter_id': voter.id,
        'ballot_id': ballot.id,
        'vote_data': {'candidate_selections': [cand1.id]}
    })
    print(f"[Step 5] Cast vote 1 status: {res_vote1.status_code}, response: {res_vote1.get_json()}")
    assert res_vote1.status_code == 201, f"Failed cast vote: {res_vote1.get_json()}"
    vote1_id_str = res_vote1.get_json()['vote_id']
    vote1_db = Vote.query.filter_by(vote_id=vote1_id_str).first()

    # 6. Attempt second vote for same voter+ballot -> confirm app-level 400 (Item 7)
    res_vote2 = client.post('/api/votes/', headers=headers, json={
        'voter_id': voter.id,
        'ballot_id': ballot.id,
        'vote_data': {'candidate_selections': [cand2.id]}
    })
    print(f"[Step 6] Cast vote 2 (duplicate) status: {res_vote2.status_code}, response: {res_vote2.get_json()}")
    assert res_vote2.status_code == 400
    assert "already voted" in res_vote2.get_json()['error']

    # 7. Query vote integrity via GET and verify-integrity (Item 4)
    res_get_v = client.get(f'/api/votes/{vote1_db.id}', headers=headers)
    assert res_get_v.status_code == 200
    assert res_get_v.get_json()['integrity_verified'] is True

    res_v_integ = client.get(f'/api/votes/{vote1_db.id}/verify-integrity', headers=headers)
    print(f"[Step 7] Verify vote integrity status: {res_v_integ.status_code}, response: {res_v_integ.get_json()}")
    assert res_v_integ.status_code == 200
    assert res_v_integ.get_json()['integrity_check']['is_valid'] is True

    # 8. Non-privileged user query candidate counts before results published (Item 1)
    res_cands_before = client.get(f'/api/candidates/?election_id={election.id}', headers=non_priv_headers)
    c1_before = next(c for c in res_cands_before.get_json()['data'] if c['id'] == cand1.id)
    print(f"[Step 8] Non-privileged candidate list before publish - total_votes_received: {c1_before['total_votes_received']}")
    assert c1_before['total_votes_received'] is None

    # 9. Publish results and re-check as non-privileged user
    election.end_date = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()

    res_pub = client.post(f'/api/elections/{election.id}/publish-results', headers=headers, json={})
    print(f"[Step 9] Publish response: {res_pub.status_code}, {res_pub.get_json()}")
    assert res_pub.status_code == 200, f"Publish results failed: {res_pub.get_json()}"
    res_cands_after = client.get(f'/api/candidates/?election_id={election.id}', headers=non_priv_headers)
    c1_after = next(c for c in res_cands_after.get_json()['data'] if c['id'] == cand1.id)
    print(f"[Step 9] Non-privileged candidate list after publish - total_votes_received: {c1_after['total_votes_received']}, rank_position: {c1_after['rank_position']}")
    assert c1_after['total_votes_received'] == 1
    assert c1_after['rank_position'] == 1

    # 10. Deactivate election -> confirm cascade sets is_active=False on ballot/candidates (Item 2)
    client.put(f'/api/elections/{election.id}', headers=headers, json={'status': STATUS_INACTIVE, 'is_active': False})
    db.session.refresh(ballot)
    db.session.refresh(cand1)
    print(f"[Step 10] DB check after deactivating election: ballot.is_active={ballot.is_active}, cand1.is_active={cand1.is_active}")
    assert ballot.is_active is False
    assert cand1.is_active is False

    # Confirm further vote attempt rejected
    voter2 = Voter(voter_id="VOTER-SCENARIO-A2", name="Voter Scenario A2", phone_number="5551113333", status=STATUS_ACTIVE, company_id=company_id)
    db.session.add(voter2)
    db.session.commit()
    reg2 = VoterRegistration(voter_id=voter2.id, election_id=election.id, registration_id="REG-SCENARIO-A2", status="approved", company_id=company_id)
    db.session.add(reg2)
    db.session.commit()

    res_vote_deact = client.post('/api/votes/', headers=headers, json={
        'voter_id': voter2.id,
        'ballot_id': ballot.id,
        'vote_data': {'candidate_selections': [cand1.id]}
    })
    print(f"[Step 10b] Vote attempt on deactivated election/ballot status: {res_vote_deact.status_code}, response: {res_vote_deact.get_json()}")
    assert res_vote_deact.status_code == 400

    # 11. Reactivate election -> confirm is_active restored
    client.put(f'/api/elections/{election.id}', headers=headers, json={'status': STATUS_ACTIVE, 'is_active': True})
    db.session.refresh(ballot)
    db.session.refresh(cand1)
    print(f"[Step 11] DB check after reactivating election: ballot.is_active={ballot.is_active}, cand1.is_active={cand1.is_active}")
    assert ballot.is_active is True
    assert cand1.is_active is True

    # 12. Pre-delete dependency count test (Item 8) with a mix of Active and Inactive candidates
    cand1.status = STATUS_ACTIVE
    cand1.is_active = True
    cand2.status = STATUS_INACTIVE
    cand2.is_active = False
    db.session.commit()

    res_deps = client.get(f'/api/elections/{election.id}/status_dependents', headers=headers)
    deps_data = res_deps.get_json()['dependents']
    print(f"[Step 12] Pre-delete dependents query result: {deps_data}")
    assert deps_data['candidates'] == 1, f"Expected 1 active candidate dependent, got {deps_data['candidates']}"

    print("\nScenario A Full End-to-End Test PASSED SUCCESSFULLY.")

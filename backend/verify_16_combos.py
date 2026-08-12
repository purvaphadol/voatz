import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.insert(0, '/home/dev82/Documents/voatz/backend')

from app import create_app, db
from app.models.company import Company
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.models.voter import Voter
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.module import SystemModule, CompanyModule, SystemModuleAction
from app.models.user_role import UserRoleMapping
from app.models.administrator import Administrator
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    client = app.test_client()

    # 1. Platform Admin setup
    admin = Administrator.query.filter_by(email="admin@gmail.com").first()
    if not admin:
        admin = Administrator(name="Platform Admin", email="admin@gmail.com", password_hash=generate_password_hash("Admin@123"))
        db.session.add(admin)
        db.session.commit()

    admin_token = create_access_token(identity=f"admin:{admin.id}", additional_claims={"is_administrator": True})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Setup Company and Company Super Admin
    uid = uuid.uuid4().hex[:6]
    test_company = Company(company_name=f"TestCorp_16Combos_{uid}", status=STATUS_ACTIVE)
    db.session.add(test_company)
    db.session.commit()

    # Provision all system modules to test_company
    sys_mods = SystemModule.query.filter(SystemModule.status != STATUS_DEACTIVATED).all()
    for sm in sys_mods:
        cm = CompanyModule(company_id=test_company.id, system_module_id=sm.id, status=STATUS_ACTIVE)
        db.session.add(cm)
    db.session.commit()

    # Super Admin Role
    super_role = Role(role_name="Company Super Admin", company_id=test_company.id, is_super_admin=True, status=STATUS_ACTIVE)
    db.session.add(super_role)
    db.session.commit()

    # Super Admin User
    super_user = User(
        name="Super Admin User",
        email=f"superadmin_{uid}@testcorp.com",
        password_hash=generate_password_hash("SuperPass123!"),
        company_id=test_company.id,
        status=STATUS_ACTIVE
    )
    db.session.add(super_user)
    db.session.commit()

    urm = UserRoleMapping(user_id=super_user.id, role_id=super_role.id, company_id=test_company.id, status=STATUS_ACTIVE)
    db.session.add(urm)
    db.session.commit()

    csa_token = create_access_token(identity=str(super_user.id), additional_claims={"company_id": test_company.id})
    csa_headers = {"Authorization": f"Bearer {csa_token}"}

    # 3. Setup Second Company for cross-tenant verification
    uid2 = uuid.uuid4().hex[:6]
    other_company = Company(company_name=f"OtherCorp_{uid2}", status=STATUS_ACTIVE)
    db.session.add(other_company)
    db.session.commit()

    print("=== STARTING 16 COMBINATION LIVE API INACTIVE DELETE VERIFICATION ===")

    results = []

    # Entity 1: Company
    # Caller 1: Platform Admin
    c1 = Company(company_name=f"DelComp_PA_{uuid.uuid4().hex[:4]}", status=STATUS_INACTIVE)
    db.session.add(c1)
    db.session.commit()
    res1 = client.delete(f'/api/companies/{c1.id}?force=true', headers=admin_headers)
    c1_db = Company.query.filter_by(id=c1.id).first()
    pass1 = res1.status_code == 200 and c1_db.status == STATUS_DEACTIVATED
    results.append(("Company", "Platform Administrator", res1.status_code, pass1))

    # Caller 2: Company Super Admin (Note: Company Delete is Platform Admin only)
    c2 = Company(company_name=f"DelComp_CSA_{uuid.uuid4().hex[:4]}", status=STATUS_INACTIVE)
    db.session.add(c2)
    db.session.commit()
    res2 = client.delete(f'/api/companies/{c2.id}?force=true', headers=csa_headers)
    pass2 = res2.status_code == 403 # Properly restricted to Platform Admin
    results.append(("Company", "Company Super Admin", f"{res2.status_code} (Forbidden as expected for Company entity)", pass2))

    # Entity 2: User
    # Caller 1: Platform Admin
    u1 = User(name="Inactive User PA", email=f"u_pa_{uuid.uuid4().hex[:4]}@test.com", password_hash="pass", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(u1)
    db.session.commit()
    res3 = client.delete(f'/api/users/{u1.id}', headers=admin_headers)
    u1_db = User.query.filter_by(id=u1.id).first()
    pass3 = res3.status_code == 200 and u1_db.status == STATUS_DEACTIVATED
    results.append(("User", "Platform Administrator", res3.status_code, pass3))

    # Caller 2: Company Super Admin
    u2 = User(name="Inactive User CSA", email=f"u_csa_{uuid.uuid4().hex[:4]}@test.com", password_hash="pass", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(u2)
    db.session.commit()
    res4 = client.delete(f'/api/users/{u2.id}', headers=csa_headers)
    u2_db = User.query.filter_by(id=u2.id).first()
    pass4 = res4.status_code == 200 and u2_db.status == STATUS_DEACTIVATED
    results.append(("User", "Company Super Admin", res4.status_code, pass4))

    # Entity 3: Role
    # Caller 1: Platform Admin
    r1 = Role(role_name=f"Role_PA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(r1)
    db.session.commit()
    res5 = client.delete(f'/api/roles/{r1.id}', headers=admin_headers)
    r1_db = Role.query.filter_by(id=r1.id).first()
    pass5 = res5.status_code == 200 and r1_db.status == STATUS_DEACTIVATED
    results.append(("Role", "Platform Administrator", res5.status_code, pass5))

    # Caller 2: Company Super Admin
    r2 = Role(role_name=f"Role_CSA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(r2)
    db.session.commit()
    res6 = client.delete(f'/api/roles/{r2.id}', headers=csa_headers)
    r2_db = Role.query.filter_by(id=r2.id).first()
    pass6 = res6.status_code == 200 and r2_db.status == STATUS_DEACTIVATED
    results.append(("Role", "Company Super Admin", res6.status_code, pass6))

    # Entity 4: Department
    # Caller 1: Platform Admin
    d1 = Department(department_name=f"Dept_PA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(d1)
    db.session.commit()
    res7 = client.delete(f'/api/departments/{d1.id}', headers=admin_headers)
    d1_db = Department.query.filter_by(id=d1.id).first()
    pass7 = res7.status_code == 200 and d1_db.status == STATUS_DEACTIVATED
    results.append(("Department", "Platform Administrator", res7.status_code, pass7))

    # Caller 2: Company Super Admin
    d2 = Department(department_name=f"Dept_CSA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(d2)
    db.session.commit()
    res8 = client.delete(f'/api/departments/{d2.id}', headers=csa_headers)
    d2_db = Department.query.filter_by(id=d2.id).first()
    pass8 = res8.status_code == 200 and d2_db.status == STATUS_DEACTIVATED
    results.append(("Department", "Company Super Admin", res8.status_code, pass8))

    # Entity 5: Voter
    # Caller 1: Platform Admin
    v1 = Voter(name=f"Voter PA {uuid.uuid4().hex[:4]}", voter_id=f"V_PA_{uuid.uuid4().hex[:4]}", phone_number=f"555{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(v1)
    db.session.commit()
    res9 = client.delete(f'/api/voters/{v1.id}', headers=admin_headers)
    v1_db = Voter.query.filter_by(id=v1.id).first()
    pass9 = res9.status_code == 200 and v1_db.status == STATUS_DEACTIVATED
    results.append(("Voter", "Platform Administrator", res9.status_code, pass9))

    # Caller 2: Company Super Admin
    v2 = Voter(name=f"Voter CSA {uuid.uuid4().hex[:4]}", voter_id=f"V_CSA_{uuid.uuid4().hex[:4]}", phone_number=f"555{uuid.uuid4().hex[:4]}", company_id=test_company.id, status=STATUS_INACTIVE)
    db.session.add(v2)
    db.session.commit()
    res10 = client.delete(f'/api/voters/{v2.id}', headers=csa_headers)
    v2_db = Voter.query.filter_by(id=v2.id).first()
    pass10 = res10.status_code == 200 and v2_db.status == STATUS_DEACTIVATED
    results.append(("Voter", "Company Super Admin", res10.status_code, pass10))

    # Setup Election for Ballot and Candidate tests
    now = datetime.now(timezone.utc)
    elec = Election(title="Test Elec", election_code=f"E_{uuid.uuid4().hex[:4]}", election_type="general", company_id=test_company.id, start_date=now, end_date=now + timedelta(days=1), status="draft")
    db.session.add(elec)
    db.session.commit()

    # Entity 6: Ballot
    # Caller 1: Platform Admin
    b1 = Ballot(title=f"Bal PA {uuid.uuid4().hex[:4]}", ballot_code=f"B_PA_{uuid.uuid4().hex[:4]}", ballot_type="single_choice", company_id=test_company.id, election_id=elec.id, status=STATUS_INACTIVE)
    db.session.add(b1)
    db.session.commit()
    res11 = client.delete(f'/api/ballots/{b1.id}', headers=admin_headers)
    b1_db = Ballot.query.filter_by(id=b1.id).first()
    pass11 = res11.status_code == 200 and b1_db.status == STATUS_DEACTIVATED
    results.append(("Ballot", "Platform Administrator", res11.status_code, pass11))

    # Caller 2: Company Super Admin
    b2 = Ballot(title=f"Bal CSA {uuid.uuid4().hex[:4]}", ballot_code=f"B_CSA_{uuid.uuid4().hex[:4]}", ballot_type="single_choice", company_id=test_company.id, election_id=elec.id, status=STATUS_INACTIVE)
    db.session.add(b2)
    db.session.commit()
    res12 = client.delete(f'/api/ballots/{b2.id}', headers=csa_headers)
    b2_db = Ballot.query.filter_by(id=b2.id).first()
    pass12 = res12.status_code == 200 and b2_db.status == STATUS_DEACTIVATED
    results.append(("Ballot", "Company Super Admin", res12.status_code, pass12))

    # Entity 7: Candidate
    # Caller 1: Platform Admin
    c_cand1 = Candidate(name=f"Cand PA {uuid.uuid4().hex[:4]}", candidate_code=f"C_PA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, ballot_id=b1.id, status=STATUS_INACTIVE)
    db.session.add(c_cand1)
    db.session.commit()
    res13 = client.delete(f'/api/candidates/{c_cand1.id}', headers=admin_headers)
    cand1_db = Candidate.query.filter_by(id=c_cand1.id).first()
    pass13 = res13.status_code == 200 and cand1_db.status == STATUS_DEACTIVATED
    results.append(("Candidate", "Platform Administrator", res13.status_code, pass13))

    # Caller 2: Company Super Admin
    c_cand2 = Candidate(name=f"Cand CSA {uuid.uuid4().hex[:4]}", candidate_code=f"C_CSA_{uuid.uuid4().hex[:4]}", company_id=test_company.id, ballot_id=b2.id, status=STATUS_INACTIVE)
    db.session.add(c_cand2)
    db.session.commit()
    res14 = client.delete(f'/api/candidates/{c_cand2.id}', headers=csa_headers)
    cand2_db = Candidate.query.filter_by(id=c_cand2.id).first()
    pass14 = res14.status_code == 200 and cand2_db.status == STATUS_DEACTIVATED
    results.append(("Candidate", "Company Super Admin", res14.status_code, pass14))

    # Entity 8: SystemModule
    # Caller 1: Platform Admin
    sm1 = SystemModule(module_name=f"Mod PA {uuid.uuid4().hex[:4]}", route_name=f"mod_pa_{uuid.uuid4().hex[:4]}", status=STATUS_INACTIVE)
    db.session.add(sm1)
    db.session.commit()
    res15 = client.delete(f'/api/modules/{sm1.id}', headers=admin_headers)
    sm1_db = SystemModule.query.filter_by(id=sm1.id).first()
    pass15 = res15.status_code == 200 and sm1_db.status == STATUS_DEACTIVATED
    results.append(("SystemModule", "Platform Administrator", res15.status_code, pass15))

    # Caller 2: Company Super Admin (SystemModule management is Platform Admin only)
    sm2 = SystemModule(module_name=f"Mod CSA {uuid.uuid4().hex[:4]}", route_name=f"mod_csa_{uuid.uuid4().hex[:4]}", status=STATUS_INACTIVE)
    db.session.add(sm2)
    db.session.commit()
    res16 = client.delete(f'/api/modules/{sm2.id}', headers=csa_headers)
    pass16 = res16.status_code in [403, 404] # Properly restricted/unmapped for Company Super Admin
    results.append(("SystemModule", "Company Super Admin", f"{res16.status_code} (Forbidden/Restricted as expected)", pass16))

    print("\n--- SUMMARY TABLE OF ALL 16 COMBINATIONS ---")
    print(f"{'Entity':<15} | {'Caller Type':<25} | {'HTTP Status':<45} | {'Result':<10}")
    print("-" * 102)
    all_passed = True
    for entity, caller, status_code, is_pass in results:
        print(f"{entity:<15} | {caller:<25} | {str(status_code):<45} | {'PASS' if is_pass else 'FAIL':<10}")
        if not is_pass:
            all_passed = False

    print("\nOVERALL 16-COMBINATION VERIFICATION:", "PASSED" if all_passed else "FAILED")

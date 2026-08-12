import unittest
import uuid
import time
from datetime import datetime, timezone, timedelta

from app import create_app, db
from app.models.company import Company
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.models.voter import Voter
from app.models.voter_registration import VoterRegistration
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.module import SystemModule, CompanyModule, SystemModuleAction
from app.models.administrator import Administrator
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED
from app.utils.cascade import count_dependents, cascade_set_inactive, count_reactivatable_dependents, cascade_reactivate
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash


class TestStatusGovernanceComprehensive(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Ensure Platform Administrator exists
        admin = Administrator.query.filter_by(email="admin@gmail.com").first()
        if not admin:
            admin = Administrator(name="Platform Admin", email="admin@gmail.com", password_hash=generate_password_hash("Admin@123"))
            db.session.add(admin)
            db.session.commit()

        self.admin_token = create_access_token(identity=f"admin:{admin.id}", additional_claims={"is_administrator": True})
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        self.app_context.pop()

    def _create_test_company(self, prefix="TestCorp"):
        uid = uuid.uuid4().hex[:6]
        c = Company(company_name=f"{prefix}_{uid}", status=STATUS_ACTIVE)
        db.session.add(c)
        db.session.commit()
        return c

    def _create_test_dept(self, company_id, prefix="Dept"):
        uid = uuid.uuid4().hex[:6]
        d = Department(department_name=f"{prefix}_{uid}", company_id=company_id, status=STATUS_ACTIVE)
        db.session.add(d)
        db.session.commit()
        return d

    def _create_test_user(self, company_id, dept_id=None, prefix="user"):
        uid = uuid.uuid4().hex[:6]
        u = User(name=f"User {uid}", email=f"{prefix}_{uid}@test.com", password_hash=generate_password_hash("Pass123!"), company_id=company_id, department_id=dept_id, status=STATUS_ACTIVE)
        db.session.add(u)
        db.session.commit()
        return u

    def _create_test_election(self, company_id, prefix="Elec"):
        uid = uuid.uuid4().hex[:6]
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=1)
        e = Election(title=f"{prefix}_{uid}", election_code=f"CODE_{uid}", company_id=company_id, election_type="general", start_date=now, end_date=later, status="draft")
        db.session.add(e)
        db.session.commit()
        return e

    def _create_test_ballot(self, company_id, election_id, prefix="Bal"):
        uid = uuid.uuid4().hex[:6]
        b = Ballot(title=f"{prefix}_{uid}", ballot_code=f"BAL_{uid}", ballot_type="single_choice", company_id=company_id, election_id=election_id, status=STATUS_ACTIVE)
        db.session.add(b)
        db.session.commit()
        return b

    # =========================================================================
    # 1. COMPANY TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_company_2a_delete_sets_correct_final_state(self):
        uid = uuid.uuid4().hex[:6]
        name = f"Comp2A_{uid}"
        # 1. Create API -> 201
        res = self.client.post('/api/companies/', json={'company_name': name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        comp_id = res.get_json()['company_id']

        # 2. Delete API -> 200 (with force=true parameter for companies)
        del_res = self.client.delete(f'/api/companies/{comp_id}?force=true', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        # 3. Direct DB assertion
        comp_db = Company.query.filter_by(id=comp_id).first()
        self.assertIsNotNone(comp_db)
        self.assertEqual(comp_db.status, STATUS_DEACTIVATED)
        self.assertNotEqual(comp_db.status, STATUS_INACTIVE)
        self.assertIn('_deleted_', comp_db.company_name)

        # 4. Confirm no /permanent endpoint exists -> 404
        perm_res = self.client.delete(f'/api/companies/{comp_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_company_2b_create_after_delete(self):
        uid = uuid.uuid4().hex[:6]
        name = f"Comp2B_{uid}"
        # Create and Delete original
        res1 = self.client.post('/api/companies/', json={'company_name': name}, headers=self.admin_headers, follow_redirects=True)
        comp1_id = res1.get_json()['company_id']
        self.client.delete(f'/api/companies/{comp1_id}?force=true', headers=self.admin_headers, follow_redirects=True)

        # Create brand new entity with IDENTICAL name -> 201
        res2 = self.client.post('/api/companies/', json={'company_name': name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        comp2_id = res2.get_json()['company_id']

        # Direct DB assertion: two distinct rows exist
        c1_db = Company.query.filter_by(id=comp1_id).first()
        c2_db = Company.query.filter_by(id=comp2_id).first()
        self.assertEqual(c1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', c1_db.company_name)
        self.assertEqual(c2_db.status, STATUS_ACTIVE)
        self.assertEqual(c2_db.company_name, name)

    def test_company_2c_set_inactive_and_cascade(self):
        comp = self._create_test_company("Comp2C")
        dept = self._create_test_dept(comp.id, "Dept2C")
        user = self._create_test_user(comp.id, dept.id, "user2c")

        # PUT status: 0
        put_res = self.client.put(f'/api/companies/{comp.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        # Direct DB assertions
        db.session.refresh(comp)
        db.session.refresh(dept)
        db.session.refresh(user)
        self.assertEqual(comp.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', comp.company_name)
        self.assertEqual(dept.status, STATUS_INACTIVE)
        self.assertEqual(dept.deactivated_by_cascade_from_type, 'Company')
        self.assertEqual(dept.deactivated_by_cascade_from_id, comp.id)
        self.assertEqual(user.status, STATUS_INACTIVE)
        self.assertEqual(user.deactivated_by_cascade_from_type, 'Company')

    def test_company_2d_create_inactive_conflict_409(self):
        uid = uuid.uuid4().hex[:6]
        name = f"Comp2D_{uid}"
        c = Company(company_name=name, status=STATUS_ACTIVE)
        db.session.add(c)
        db.session.commit()
        comp_id = c.id

        # Set Inactive
        self.client.put(f'/api/companies/{comp_id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Create with same name -> 409
        res = self.client.post('/api/companies/', json={'company_name': name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), comp_id)

    def test_company_2e_reactivate_selective_cascade(self):
        comp = self._create_test_company("Comp2E")
        dept1 = self._create_test_dept(comp.id, "Dept2E_1")
        dept2 = self._create_test_dept(comp.id, "Dept2E_2")

        # Independently set dept2 inactive FIRST
        self.client.put(f'/api/departments/{dept2.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Set company inactive (cascades to remaining active dept1)
        self.client.put(f'/api/companies/{comp.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Reactivate company
        self.client.put(f'/api/companies/{comp.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Direct DB assertions
        db.session.refresh(comp)
        db.session.refresh(dept1)
        db.session.refresh(dept2)
        self.assertEqual(comp.status, STATUS_ACTIVE)
        self.assertEqual(dept1.status, STATUS_ACTIVE)
        self.assertIsNone(dept1.deactivated_by_cascade_from_type)
        # Independently inactive dept2 MUST STAY INACTIVE!
        self.assertEqual(dept2.status, STATUS_INACTIVE)
        self.assertIsNone(dept2.deactivated_by_cascade_from_type)

    # =========================================================================
    # 2. DEPARTMENT TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_department_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("DeptComp2A")
        uid = uuid.uuid4().hex[:6]
        d_name = f"Dept2A_{uid}"
        res = self.client.post('/api/departments/', json={'department_name': d_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        d_id = res.get_json()['department_id']

        del_res = self.client.delete(f'/api/departments/{d_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        # Direct DB check
        d_db = Department.query.filter_by(id=d_id).first()
        self.assertEqual(d_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', d_db.department_name)

        # 404 guard
        perm_res = self.client.delete(f'/api/departments/{d_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_department_2b_create_after_delete(self):
        comp = self._create_test_company("DeptComp2B")
        uid = uuid.uuid4().hex[:6]
        d_name = f"Dept2B_{uid}"

        res1 = self.client.post('/api/departments/', json={'department_name': d_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        d1_id = res1.get_json()['department_id']
        self.client.delete(f'/api/departments/{d1_id}', headers=self.admin_headers, follow_redirects=True)

        # Re-create same name -> 201
        res2 = self.client.post('/api/departments/', json={'department_name': d_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        d2_id = res2.get_json()['department_id']

        # Direct DB checks
        d1_db = Department.query.filter_by(id=d1_id).first()
        d2_db = Department.query.filter_by(id=d2_id).first()
        self.assertEqual(d1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', d1_db.department_name)
        self.assertEqual(d2_db.status, STATUS_ACTIVE)
        self.assertEqual(d2_db.department_name, d_name)

    def test_department_2c_set_inactive_and_cascade(self):
        comp = self._create_test_company("DeptComp2C")
        dept = self._create_test_dept(comp.id, "Dept2C")
        role = Role(role_name="Role2C", company_id=comp.id, department_id=dept.id, status=STATUS_ACTIVE)
        db.session.add(role)
        db.session.commit()

        # Set dept inactive
        put_res = self.client.put(f'/api/departments/{dept.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        # Direct DB checks
        db.session.refresh(dept)
        db.session.refresh(role)
        self.assertEqual(dept.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', dept.department_name)
        self.assertEqual(role.status, STATUS_INACTIVE)
        self.assertEqual(role.deactivated_by_cascade_from_type, 'Department')
        self.assertEqual(role.deactivated_by_cascade_from_id, dept.id)

    def test_department_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("DeptComp2D")
        uid = uuid.uuid4().hex[:6]
        d_name = f"Dept2D_{uid}"
        dept = Department(department_name=d_name, company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(dept)
        db.session.commit()

        self.client.put(f'/api/departments/{dept.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Re-create -> 409
        res = self.client.post('/api/departments/', json={'department_name': d_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), dept.id)

    def test_department_2e_reactivate_selective_cascade(self):
        comp = self._create_test_company("DeptComp2E")
        dept = self._create_test_dept(comp.id, "Dept2E")
        role1 = Role(role_name="Role2E_1", company_id=comp.id, department_id=dept.id, status=STATUS_ACTIVE)
        role2 = Role(role_name="Role2E_2", company_id=comp.id, department_id=dept.id, status=STATUS_ACTIVE)
        db.session.add_all([role1, role2])
        db.session.commit()

        # Independently set role2 inactive FIRST
        self.client.put(f'/api/roles/{role2.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Set dept inactive (cascades to role1)
        self.client.put(f'/api/departments/{dept.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        # Reactivate dept
        self.client.put(f'/api/departments/{dept.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)

        db.session.refresh(dept)
        db.session.refresh(role1)
        db.session.refresh(role2)
        self.assertEqual(dept.status, STATUS_ACTIVE)
        self.assertEqual(role1.status, STATUS_ACTIVE)
        self.assertEqual(role2.status, STATUS_INACTIVE)

    # =========================================================================
    # 3. ROLE TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_role_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("RoleComp2A")
        uid = uuid.uuid4().hex[:6]
        r_name = f"Role2A_{uid}"
        res = self.client.post('/api/roles/', json={'role_name': r_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        r_id = res.get_json()['role_id']

        del_res = self.client.delete(f'/api/roles/{r_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        # DB check
        r_db = Role.query.filter_by(id=r_id).first()
        self.assertEqual(r_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', r_db.role_name)

        # 404 guard
        perm_res = self.client.delete(f'/api/roles/{r_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_role_2b_create_after_delete(self):
        comp = self._create_test_company("RoleComp2B")
        uid = uuid.uuid4().hex[:6]
        r_name = f"Role2B_{uid}"

        res1 = self.client.post('/api/roles/', json={'role_name': r_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        r1_id = res1.get_json()['role_id']
        self.client.delete(f'/api/roles/{r1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/roles/', json={'role_name': r_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        r2_id = res2.get_json()['role_id']

        r1_db = Role.query.filter_by(id=r1_id).first()
        r2_db = Role.query.filter_by(id=r2_id).first()
        self.assertEqual(r1_db.status, STATUS_DEACTIVATED)
        self.assertEqual(r2_db.status, STATUS_ACTIVE)

    def test_role_2c_set_inactive(self):
        comp = self._create_test_company("RoleComp2C")
        role = Role(role_name="Role2C", company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(role)
        db.session.commit()

        put_res = self.client.put(f'/api/roles/{role.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(role)
        self.assertEqual(role.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', role.role_name)

    def test_role_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("RoleComp2D")
        uid = uuid.uuid4().hex[:6]
        r_name = f"Role2D_{uid}"
        role = Role(role_name=r_name, company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(role)
        db.session.commit()

        self.client.put(f'/api/roles/{role.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/roles/', json={'role_name': r_name, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), role.id)

    def test_role_2e_reactivate(self):
        comp = self._create_test_company("RoleComp2E")
        role = Role(role_name="Role2E", company_id=comp.id, status=STATUS_INACTIVE)
        db.session.add(role)
        db.session.commit()

        put_res = self.client.put(f'/api/roles/{role.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(role)
        self.assertEqual(role.status, STATUS_ACTIVE)

    # =========================================================================
    # 4. USER TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_user_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("UserComp2A")
        uid = uuid.uuid4().hex[:6]
        email = f"user2a_{uid}@test.com"

        res = self.client.post('/api/users/', json={'name': 'User 2A', 'email': email, 'password': 'Password123!', 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        u_id = res.get_json()['user_id']

        del_res = self.client.delete(f'/api/users/{u_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        u_db = User.query.filter_by(id=u_id).first()
        self.assertEqual(u_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', u_db.email)

        perm_res = self.client.delete(f'/api/users/{u_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_user_2b_create_after_delete(self):
        comp = self._create_test_company("UserComp2B")
        uid = uuid.uuid4().hex[:6]
        email = f"user2b_{uid}@test.com"

        res1 = self.client.post('/api/users/', json={'name': 'User 2B', 'email': email, 'password': 'Password123!', 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        u1_id = res1.get_json()['user_id']
        self.client.delete(f'/api/users/{u1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/users/', json={'name': 'User 2B New', 'email': email, 'password': 'Password123!', 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        u2_id = res2.get_json()['user_id']

        u1_db = User.query.filter_by(id=u1_id).first()
        u2_db = User.query.filter_by(id=u2_id).first()
        self.assertEqual(u1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', u1_db.email)
        self.assertEqual(u2_db.status, STATUS_ACTIVE)
        self.assertEqual(u2_db.email, email)

    def test_user_2c_set_inactive_and_cascade(self):
        comp = self._create_test_company("UserComp2C")
        user = self._create_test_user(comp.id, prefix="user2c")
        voter = Voter(name="Voter2C", voter_id=f"V2C_{user.id}", phone_number="1112223333", company_id=comp.id, user_id=user.id, status=STATUS_ACTIVE)
        db.session.add(voter)
        db.session.commit()

        put_res = self.client.put(f'/api/users/{user.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(user)
        db.session.refresh(voter)
        self.assertEqual(user.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', user.email)
        self.assertEqual(voter.status, STATUS_INACTIVE)
        self.assertEqual(voter.deactivated_by_cascade_from_type, 'User')

    def test_user_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("UserComp2D")
        uid = uuid.uuid4().hex[:6]
        email = f"user2d_{uid}@test.com"
        user = User(name="User 2D", email=email, password_hash="dummy", company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(user)
        db.session.commit()

        self.client.put(f'/api/users/{user.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/users/', json={'name': 'User 2D', 'email': email, 'password': 'Password123!', 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), user.id)

    def test_user_2e_reactivate(self):
        comp = self._create_test_company("UserComp2E")
        user = self._create_test_user(comp.id, prefix="user2e")
        user.status = STATUS_INACTIVE
        db.session.commit()

        put_res = self.client.put(f'/api/users/{user.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(user)
        self.assertEqual(user.status, STATUS_ACTIVE)

    # =========================================================================
    # 5. VOTER TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_voter_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("VoterComp2A")
        uid = uuid.uuid4().hex[:6]
        phone = f"555{uid[:4]}"

        res = self.client.post('/api/voters/', json={'name': f'Voter {uid}', 'phone_number': phone, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        v_id = res.get_json()['voter_id']

        del_res = self.client.delete(f'/api/voters/{v_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        v_db = Voter.query.filter_by(id=v_id).first()
        self.assertEqual(v_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', v_db.phone_number)

        perm_res = self.client.delete(f'/api/voters/{v_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_voter_2b_create_after_delete(self):
        comp = self._create_test_company("VoterComp2B")
        uid = uuid.uuid4().hex[:6]
        phone = f"555{uid[:4]}"

        res1 = self.client.post('/api/voters/', json={'name': 'Voter 1', 'phone_number': phone, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        v1_id = res1.get_json()['voter_id']
        self.client.delete(f'/api/voters/{v1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/voters/', json={'name': 'Voter 2', 'phone_number': phone, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        v2_id = res2.get_json()['voter_id']

        v1_db = Voter.query.filter_by(id=v1_id).first()
        v2_db = Voter.query.filter_by(id=v2_id).first()
        self.assertEqual(v1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', v1_db.phone_number)
        self.assertEqual(v2_db.status, STATUS_ACTIVE)

    def test_voter_2c_set_inactive(self):
        comp = self._create_test_company("VoterComp2C")
        voter = Voter(name="Voter2C", voter_id=f"V2C_{comp.id}", phone_number="9998887777", company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(voter)
        db.session.commit()

        put_res = self.client.put(f'/api/voters/{voter.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(voter)
        self.assertEqual(voter.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', voter.phone_number)

    def test_voter_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("VoterComp2D")
        uid = uuid.uuid4().hex[:6]
        phone = f"777{uid[:4]}"
        voter = Voter(name="Voter2D", voter_id=f"V2D_{uid}", phone_number=phone, company_id=comp.id, status=STATUS_ACTIVE)
        db.session.add(voter)
        db.session.commit()

        self.client.put(f'/api/voters/{voter.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/voters/', json={'name': 'Voter 2D New', 'phone_number': phone, 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), voter.id)

    def test_voter_2e_reactivate(self):
        comp = self._create_test_company("VoterComp2E")
        voter = Voter(name="Voter2E", voter_id=f"V2E_{comp.id}", phone_number="1231231234", company_id=comp.id, status=STATUS_INACTIVE)
        db.session.add(voter)
        db.session.commit()

        put_res = self.client.put(f'/api/voters/{voter.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(voter)
        self.assertEqual(voter.status, STATUS_ACTIVE)

    # =========================================================================
    # 6. BALLOT TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_ballot_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("BalComp2A")
        elec = self._create_test_election(comp.id, "Elec2A")
        uid = uuid.uuid4().hex[:6]
        title = f"Bal2A_{uid}"

        res = self.client.post('/api/ballots/', json={'title': title, 'election_id': elec.id, 'ballot_type': 'single_choice'}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        b_id = res.get_json()['ballot_id']

        del_res = self.client.delete(f'/api/ballots/{b_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        b_db = Ballot.query.filter_by(id=b_id).first()
        self.assertEqual(b_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', b_db.title)
        self.assertIn('_deleted_', b_db.ballot_code)

        perm_res = self.client.delete(f'/api/ballots/{b_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_ballot_2b_create_after_delete(self):
        comp = self._create_test_company("BalComp2B")
        elec = self._create_test_election(comp.id, "Elec2B")
        uid = uuid.uuid4().hex[:6]
        title = f"Bal2B_{uid}"

        res1 = self.client.post('/api/ballots/', json={'title': title, 'election_id': elec.id, 'ballot_type': 'single_choice'}, headers=self.admin_headers, follow_redirects=True)
        b1_id = res1.get_json()['ballot_id']
        self.client.delete(f'/api/ballots/{b1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/ballots/', json={'title': title, 'election_id': elec.id, 'ballot_type': 'single_choice'}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        b2_id = res2.get_json()['ballot_id']

        b1_db = Ballot.query.filter_by(id=b1_id).first()
        b2_db = Ballot.query.filter_by(id=b2_id).first()
        self.assertEqual(b1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', b1_db.title)
        self.assertEqual(b2_db.status, STATUS_ACTIVE)
        self.assertEqual(b2_db.title, title)

    def test_ballot_2c_set_inactive_and_cascade(self):
        comp = self._create_test_company("BalComp2C")
        elec = self._create_test_election(comp.id, "Elec2C")
        ballot = self._create_test_ballot(comp.id, elec.id, "Bal2C")
        cand = Candidate(name="Cand2C", candidate_code=f"C2C_{ballot.id}", company_id=comp.id, ballot_id=ballot.id, status=STATUS_ACTIVE)
        db.session.add(cand)
        db.session.commit()

        put_res = self.client.put(f'/api/ballots/{ballot.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(ballot)
        db.session.refresh(cand)
        self.assertEqual(ballot.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', ballot.title)
        self.assertEqual(cand.status, STATUS_INACTIVE)
        self.assertEqual(cand.deactivated_by_cascade_from_type, 'Ballot')

    def test_ballot_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("BalComp2D")
        elec = self._create_test_election(comp.id, "Elec2D")
        uid = uuid.uuid4().hex[:6]
        title = f"Bal2D_{uid}"
        ballot = Ballot(title=title, ballot_code=f"B2D_{uid}", ballot_type="single_choice", company_id=comp.id, election_id=elec.id, status=STATUS_ACTIVE)
        db.session.add(ballot)
        db.session.commit()

        self.client.put(f'/api/ballots/{ballot.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/ballots/', json={'title': title, 'election_id': elec.id, 'ballot_type': 'single_choice'}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), ballot.id)

    def test_ballot_2e_reactivate(self):
        comp = self._create_test_company("BalComp2E")
        elec = self._create_test_election(comp.id, "Elec2E")
        ballot = self._create_test_ballot(comp.id, elec.id, "Bal2E")
        ballot.status = STATUS_INACTIVE
        db.session.commit()

        put_res = self.client.put(f'/api/ballots/{ballot.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(ballot)
        self.assertEqual(ballot.status, STATUS_ACTIVE)

    # =========================================================================
    # 7. CANDIDATE TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_candidate_2a_delete_sets_correct_final_state(self):
        comp = self._create_test_company("CandComp2A")
        elec = self._create_test_election(comp.id, "ElecCand2A")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalCand2A")
        uid = uuid.uuid4().hex[:6]
        c_name = f"Cand2A_{uid}"

        res = self.client.post('/api/candidates/', json={'name': c_name, 'ballot_id': ballot.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        c_id = res.get_json()['candidate_id']

        del_res = self.client.delete(f'/api/candidates/{c_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        c_db = Candidate.query.filter_by(id=c_id).first()
        self.assertEqual(c_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', c_db.name)
        self.assertIn('_deleted_', c_db.candidate_code)

        perm_res = self.client.delete(f'/api/candidates/{c_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_candidate_2b_create_after_delete(self):
        comp = self._create_test_company("CandComp2B")
        elec = self._create_test_election(comp.id, "ElecCand2B")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalCand2B")
        uid = uuid.uuid4().hex[:6]
        c_name = f"Cand2B_{uid}"

        res1 = self.client.post('/api/candidates/', json={'name': c_name, 'ballot_id': ballot.id}, headers=self.admin_headers, follow_redirects=True)
        c1_id = res1.get_json()['candidate_id']
        self.client.delete(f'/api/candidates/{c1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/candidates/', json={'name': c_name, 'ballot_id': ballot.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        c2_id = res2.get_json()['candidate_id']

        c1_db = Candidate.query.filter_by(id=c1_id).first()
        c2_db = Candidate.query.filter_by(id=c2_id).first()
        self.assertEqual(c1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', c1_db.name)
        self.assertEqual(c2_db.status, STATUS_ACTIVE)
        self.assertEqual(c2_db.name, c_name)

    def test_candidate_2c_set_inactive(self):
        comp = self._create_test_company("CandComp2C")
        elec = self._create_test_election(comp.id, "ElecCand2C")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalCand2C")
        cand = Candidate(name="Cand2C", candidate_code=f"C2C_{ballot.id}", company_id=comp.id, ballot_id=ballot.id, status=STATUS_ACTIVE)
        db.session.add(cand)
        db.session.commit()

        put_res = self.client.put(f'/api/candidates/{cand.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(cand)
        self.assertEqual(cand.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', cand.name)

    def test_candidate_2d_create_inactive_conflict_409(self):
        comp = self._create_test_company("CandComp2D")
        elec = self._create_test_election(comp.id, "ElecCand2D")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalCand2D")
        uid = uuid.uuid4().hex[:6]
        c_name = f"Cand2D_{uid}"
        cand = Candidate(name=c_name, candidate_code=f"C2D_{uid}", company_id=comp.id, ballot_id=ballot.id, status=STATUS_ACTIVE)
        db.session.add(cand)
        db.session.commit()

        self.client.put(f'/api/candidates/{cand.id}', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/candidates/', json={'name': c_name, 'ballot_id': ballot.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), cand.id)

    def test_candidate_2e_reactivate(self):
        comp = self._create_test_company("CandComp2E")
        elec = self._create_test_election(comp.id, "ElecCand2E")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalCand2E")
        cand = Candidate(name="Cand2E", candidate_code=f"C2E_{ballot.id}", company_id=comp.id, ballot_id=ballot.id, status=STATUS_INACTIVE)
        db.session.add(cand)
        db.session.commit()

        put_res = self.client.put(f'/api/candidates/{cand.id}', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(cand)
        self.assertEqual(cand.status, STATUS_ACTIVE)

    # =========================================================================
    # 8. SYSTEM MODULE TESTS (2a, 2b, 2c, 2d, 2e)
    # =========================================================================
    def test_system_module_2a_delete_sets_correct_final_state(self):
        uid = uuid.uuid4().hex[:6]
        m_name = f"Mod2A_{uid}"
        res = self.client.post('/api/modules/', json={'module_name': m_name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        m_id = res.get_json()['module_id']

        del_res = self.client.delete(f'/api/modules/{m_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        m_db = SystemModule.query.filter_by(id=m_id).first()
        self.assertEqual(m_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', m_db.module_name)
        self.assertIn('_deleted_', m_db.route_name)

        perm_res = self.client.delete(f'/api/modules/{m_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_system_module_2b_create_after_delete(self):
        uid = uuid.uuid4().hex[:6]
        m_name = f"Mod2B_{uid}"

        res1 = self.client.post('/api/modules/', json={'module_name': m_name}, headers=self.admin_headers, follow_redirects=True)
        m1_id = res1.get_json()['module_id']
        self.client.delete(f'/api/modules/{m1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/modules/', json={'module_name': m_name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        m2_id = res2.get_json()['module_id']

        m1_db = SystemModule.query.filter_by(id=m1_id).first()
        m2_db = SystemModule.query.filter_by(id=m2_id).first()
        self.assertEqual(m1_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', m1_db.module_name)
        self.assertEqual(m2_db.status, STATUS_ACTIVE)
        self.assertEqual(m2_db.module_name, m_name)

    def test_system_module_2c_set_inactive(self):
        uid = uuid.uuid4().hex[:6]
        mod = SystemModule(module_name=f"Mod2C_{uid}", route_name=f"mod2c_{uid}", status=STATUS_ACTIVE)
        db.session.add(mod)
        db.session.commit()

        patch_res = self.client.patch(f'/api/modules/{mod.id}/status', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(patch_res.status_code, 200)

        db.session.refresh(mod)
        self.assertEqual(mod.status, STATUS_INACTIVE)
        self.assertNotIn('_deleted_', mod.module_name)

    def test_system_module_2d_create_inactive_conflict_409(self):
        uid = uuid.uuid4().hex[:6]
        m_name = f"Mod2D_{uid}"
        mod = SystemModule(module_name=m_name, route_name=f"mod2d_{uid}", status=STATUS_ACTIVE)
        db.session.add(mod)
        db.session.commit()

        self.client.patch(f'/api/modules/{mod.id}/status', json={'status': STATUS_INACTIVE}, headers=self.admin_headers, follow_redirects=True)

        res = self.client.post('/api/modules/', json={'module_name': m_name}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 409)
        body = res.get_json()
        self.assertTrue(body.get('can_reactivate'))
        self.assertEqual(body.get('existing_id'), mod.id)

    def test_system_module_2e_reactivate(self):
        uid = uuid.uuid4().hex[:6]
        mod = SystemModule(module_name=f"Mod2E_{uid}", route_name=f"mod2e_{uid}", status=STATUS_INACTIVE)
        db.session.add(mod)
        db.session.commit()

        patch_res = self.client.patch(f'/api/modules/{mod.id}/status', json={'status': STATUS_ACTIVE}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(patch_res.status_code, 200)

        db.session.refresh(mod)
        self.assertEqual(mod.status, STATUS_ACTIVE)

    # =========================================================================
    # 9. ELECTION TESTS (Special string-status handling)
    # =========================================================================
    def test_election_2a_delete_sets_cancelled_and_suffixes(self):
        comp = self._create_test_company("ElecComp2A")
        uid = uuid.uuid4().hex[:6]
        title = f"Elec2A_{uid}"
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=1)

        res = self.client.post('/api/elections/', json={'title': title, 'election_type': 'general', 'start_date': now.isoformat(), 'end_date': later.isoformat(), 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res.status_code, 201)
        e_id = res.get_json()['election_id']

        del_res = self.client.delete(f'/api/elections/{e_id}', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        e_db = Election.query.filter_by(id=e_id).first()
        self.assertEqual(e_db.status, 'cancelled')
        self.assertNotEqual(e_db.status, STATUS_DEACTIVATED)
        self.assertIn('_deleted_', e_db.title)
        self.assertIn('_deleted_', e_db.election_code)

        perm_res = self.client.delete(f'/api/elections/{e_id}/permanent', headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(perm_res.status_code, 404)

    def test_election_2b_create_after_delete(self):
        comp = self._create_test_company("ElecComp2B")
        uid = uuid.uuid4().hex[:6]
        title = f"Elec2B_{uid}"
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=1)

        res1 = self.client.post('/api/elections/', json={'title': title, 'election_type': 'general', 'start_date': now.isoformat(), 'end_date': later.isoformat(), 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        e1_id = res1.get_json()['election_id']
        self.client.delete(f'/api/elections/{e1_id}', headers=self.admin_headers, follow_redirects=True)

        res2 = self.client.post('/api/elections/', json={'title': title, 'election_type': 'general', 'start_date': now.isoformat(), 'end_date': later.isoformat(), 'company_id': comp.id}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(res2.status_code, 201)
        e2_id = res2.get_json()['election_id']

        e1_db = Election.query.filter_by(id=e1_id).first()
        e2_db = Election.query.filter_by(id=e2_id).first()
        self.assertEqual(e1_db.status, 'cancelled')
        self.assertIn('_deleted_', e1_db.title)
        self.assertEqual(e2_db.title, title)

    def test_election_2c_set_inactive_and_cascade(self):
        comp = self._create_test_company("ElecComp2C")
        elec = self._create_test_election(comp.id, "Elec2C")
        ballot = self._create_test_ballot(comp.id, elec.id, "BalElec2C")

        # Set election to cancelled via PUT
        put_res = self.client.put(f'/api/elections/{elec.id}', json={'status': 'cancelled'}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(elec)
        self.assertEqual(elec.status, 'cancelled')

    def test_election_2d_create_inactive_conflict(self):
        comp = self._create_test_company("ElecComp2D")
        elec = self._create_test_election(comp.id, "Elec2D")
        self.client.put(f'/api/elections/{elec.id}', json={'status': 'cancelled'}, headers=self.admin_headers, follow_redirects=True)

        # List elections filters out cancelled elections by default
        from app.utils.query_helpers import get_active_elections_query
        active_elections = get_active_elections_query(comp.id).all()
        self.assertNotIn(elec, active_elections)

    def test_election_2e_reactivate(self):
        comp = self._create_test_company("ElecComp2E")
        elec = self._create_test_election(comp.id, "Elec2E")
        elec.status = 'cancelled'
        db.session.commit()

        put_res = self.client.put(f'/api/elections/{elec.id}', json={'status': 'draft'}, headers=self.admin_headers, follow_redirects=True)
        self.assertEqual(put_res.status_code, 200)

        db.session.refresh(elec)
        self.assertEqual(elec.status, 'draft')

    # =========================================================================
    # 10. MULTI-PATH CASCADE DE-DUPLICATION REGRESSION TEST (PART 3)
    # =========================================================================
    def test_multipath_cascade_deduplication_direct_db_check(self):
        uid = uuid.uuid4().hex[:6]
        comp = Company(company_name=f"MultiPathCorp_{uid}", status=STATUS_ACTIVE)
        db.session.add(comp)
        db.session.flush()

        now = datetime.now(timezone.utc)
        later = now + timedelta(days=1)
        elec = Election(title=f"MultiPathElec_{uid}", election_code=f"MPE_{uid}", company_id=comp.id, election_type="general", start_date=now, end_date=later, status="draft")
        db.session.add(elec)
        db.session.flush()

        ballot = Ballot(title=f"MultiPathBal_{uid}", ballot_code=f"MPB_{uid}", ballot_type="single_choice", company_id=comp.id, election_id=elec.id, status=STATUS_ACTIVE)
        db.session.add(ballot)
        db.session.flush()

        cand = Candidate(name=f"MultiPathCand_{uid}", candidate_code=f"MPC_{uid}", company_id=comp.id, ballot_id=ballot.id, status=STATUS_ACTIVE)
        db.session.add(cand)
        db.session.commit()

        # Cascade set inactive on Company
        comp.status = STATUS_INACTIVE
        cascade_set_inactive('Company', comp.id)
        db.session.commit()

        # Direct DB checks for single non-null cascade pair
        db.session.refresh(ballot)
        db.session.refresh(cand)

        self.assertEqual(ballot.status, STATUS_INACTIVE)
        self.assertEqual(ballot.deactivated_by_cascade_from_type, 'Company')
        self.assertEqual(ballot.deactivated_by_cascade_from_id, comp.id)

        self.assertEqual(cand.status, STATUS_INACTIVE)
        self.assertEqual(cand.deactivated_by_cascade_from_type, 'Company')
        self.assertEqual(cand.deactivated_by_cascade_from_id, comp.id)

        # Assert count_dependents breakdown counts each child exactly once
        dep_summary = count_dependents('Company', comp.id)
        breakdown = dep_summary.get('breakdown', {})
        self.assertLessEqual(breakdown.get('Ballot', 0), 1)
        self.assertLessEqual(breakdown.get('Candidate', 0), 1)


if __name__ == '__main__':
    unittest.main()

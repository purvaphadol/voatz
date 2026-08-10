import pytest
from app import db
from app.models.company import Company
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import check_user_permission, get_user_permissions_summary

def test_superadmin_explicit_permissions(app):
    with app.app_context():
        # 1. Create a test company and Super Admin role
        company = Company(company_name="Test Explicit Co", status=1)
        db.session.add(company)
        db.session.commit()

        dept = Department(department_name="Admin", company_id=company.id, status=1)
        db.session.add(dept)
        db.session.commit()

        super_admin_role = Role(
            role_name="Company Super Admin",
            company_id=company.id,
            department_id=dept.id,
            is_super_admin=True,
            status=1
        )
        db.session.add(super_admin_role)
        db.session.commit()

        user = User(
            name="Explicit Super Admin",
            email="superadmin_test@explicit.com",
            company_id=company.id,
            password_hash="hashed_password",
            status=1
        )
        db.session.add(user)
        db.session.commit()

        from app.models.user_role import UserRoleMapping
        urm = UserRoleMapping(
            user_id=user.id,
            role_id=super_admin_role.id,
            company_id=company.id,
            department_id=dept.id,
            status=1
        )
        db.session.add(urm)
        db.session.commit()

        from app.routes.permissions import _build_user_permissions
        # Initial check: No RolePermissionMapping exists -> Empty permissions list
        perms_initial = _build_user_permissions(user.id, company.id)
        assert len(perms_initial) == 0

        # 2. Simulate Platform Admin assigning "Users" view permission
        users_mod = SystemModule.query.filter_by(code="users").first()
        if not users_mod:
            users_mod = SystemModule(module_name="Users", code="users", status=1)
            db.session.add(users_mod)
            db.session.commit()

        users_view_action = SystemModuleAction.query.filter_by(
            system_module_id=users_mod.id, action_name="view"
        ).first()
        if not users_view_action:
            users_view_action = SystemModuleAction(
                system_module_id=users_mod.id, action_name="view", action_url="/view", status=1
            )
            db.session.add(users_view_action)
            db.session.commit()

        # Provision CompanyModule and RolePermissionMapping
        cm = CompanyModule(company_id=company.id, system_module_id=users_mod.id, status=1)
        rpm = RolePermissionMapping(
            company_id=company.id,
            role_id=super_admin_role.id,
            module_id=users_mod.id,
            action_id=users_view_action.id,
            status=1
        )
        db.session.add(cm)
        db.session.add(rpm)
        db.session.commit()

        # Post-assignment check: User now has "Users:view" permission, but NOT unassigned modules
        perms_after = _build_user_permissions(user.id, company.id)
        assert len(perms_after) == 1
        assert perms_after[0]["module"] == "Users"
        assert perms_after[0]["action"] == "view"

def test_update_role_permissions_idempotency(app):
    with app.app_context():
        company = Company(company_name="Test Idempotency Co", status=1)
        db.session.add(company)
        db.session.commit()

        role = Role(role_name="Test Role", company_id=company.id, status=1)
        db.session.add(role)
        db.session.commit()

        mod = SystemModule.query.first()
        if not mod:
            mod = SystemModule(module_name="TestMod", code="testmod", status=1)
            db.session.add(mod)
            db.session.commit()

        act = SystemModuleAction.query.filter_by(system_module_id=mod.id).first()
        if not act:
            act = SystemModuleAction(system_module_id=mod.id, action_name="view", action_url="/view", status=1)
            db.session.add(act)
            db.session.commit()

        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity="admin_1", additional_claims={"is_administrator": True})
        headers = {"Authorization": f"Bearer {access_token}"}

        payload = {
            'permissions': {
                str(mod.id): {
                    str(act.id): True
                }
            }
        }

        # Update 1
        from app.routes.permissions import update_role_permissions
        with app.test_request_context(json=payload, headers=headers):
            response = update_role_permissions(role.id)
            # Response is a tuple (jsonify(), status_code) or a Response object
            status_code = response[1] if isinstance(response, tuple) else response.status_code
            assert status_code == 200

        # Update 2 (re-granting exact same permission should reactivate/reuse existing row without 500 UniqueViolation)
        with app.test_request_context(json=payload, headers=headers):
            response = update_role_permissions(role.id)
            status_code = response[1] if isinstance(response, tuple) else response.status_code
            assert status_code == 200


def test_update_user_permissions_auto_provisioning(app):
    """
    Part 4 regression test: update_user_permissions() must auto-provision a CompanyModule
    row (just like update_role_permissions() does) whenever a user-level override grants
    a permission for a module that is not yet provisioned to the user's company.

    Acceptance criteria:
    1. Before the grant: no CompanyModule row exists for (company, module).
    2. After calling update_user_permissions() with granted=True for that module:
       - A CompanyModule row exists and is active.
       - A UserPermissionMapping row exists and is active.
    3. check_user_permission() resolves True for the user/module/action triple,
       proving the grant is not silently inert.
    4. Idempotency: calling update_user_permissions() again with the same payload
       does not raise a UniqueViolation or 500 error.
    """
    with app.app_context():
        from app.models.user_role import UserRoleMapping
        from app.routes.permissions import update_user_permissions
        from flask_jwt_extended import create_access_token
        from app.utils.constants import STATUS_ACTIVE

        # 1. Fresh company — no CompanyModule rows at start
        company = Company(company_name="Test UserPerm AutoProvision Co", status=1)
        db.session.add(company)
        db.session.commit()

        # Ordinary role (NOT super admin) — no RolePermissionMapping rows
        role = Role(role_name="RegularRole", company_id=company.id, status=1)
        db.session.add(role)
        db.session.commit()

        user = User(
            name="Test UserPerm User",
            email="userperm_autoprovision@test.com",
            company_id=company.id,
            password_hash="hashed_password",
            status=1
        )
        db.session.add(user)
        db.session.commit()

        urm = UserRoleMapping(
            user_id=user.id,
            role_id=role.id,
            company_id=company.id,
            status=1
        )
        db.session.add(urm)
        db.session.commit()

        # 2. Ensure a test module + action exist (reuse or create)
        target_mod = SystemModule.query.filter_by(code="users").first()
        if not target_mod:
            target_mod = SystemModule(module_name="Users", code="users", status=1)
            db.session.add(target_mod)
            db.session.commit()

        target_act = SystemModuleAction.query.filter_by(
            system_module_id=target_mod.id, action_name="view"
        ).first()
        if not target_act:
            target_act = SystemModuleAction(
                system_module_id=target_mod.id, action_name="view", action_url="/view", status=1
            )
            db.session.add(target_act)
            db.session.commit()

        # 3. Confirm no CompanyModule exists yet for this company+module
        cm_before = CompanyModule.query.filter_by(
            company_id=company.id, system_module_id=target_mod.id
        ).first()
        assert cm_before is None, "Precondition: CompanyModule must not exist before the grant"

        # 4. Call update_user_permissions() as a Platform Administrator
        access_token = create_access_token(
            identity="admin_1", additional_claims={"is_administrator": True}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "permissions": {
                str(target_mod.id): {
                    str(target_act.id): True
                }
            }
        }

        with app.test_request_context(json=payload, headers=headers):
            response = update_user_permissions(user.id)
            status_code = response[1] if isinstance(response, tuple) else response.status_code
            assert status_code == 200, f"update_user_permissions returned {status_code}"

        # 5. CompanyModule must now exist and be active
        cm_after = CompanyModule.query.filter_by(
            company_id=company.id, system_module_id=target_mod.id
        ).first()
        assert cm_after is not None, "CompanyModule row was NOT created by update_user_permissions()"
        assert cm_after.status == STATUS_ACTIVE, "CompanyModule row is not active after the grant"

        # 6. UserPermissionMapping must exist and be active
        upm = UserPermissionMapping.query.filter_by(
            user_id=user.id,
            company_id=company.id,
            module_id=target_mod.id,
            action_id=target_act.id
        ).first()
        assert upm is not None, "UserPermissionMapping row was NOT created by update_user_permissions()"
        assert upm.status == STATUS_ACTIVE, "UserPermissionMapping row is not active"
        assert upm.permission_type == 1, "UserPermissionMapping permission_type must be 1 (allow)"

        # 7. _build_user_permissions() must include the granted module/action — grant is NOT silently inert
        from app.routes.permissions import _build_user_permissions
        perms = _build_user_permissions(user.id, company.id)
        perm_keys = {(p["module"], p["action"]) for p in perms}
        assert (target_mod.module_name, "view") in perm_keys, (
            f"_build_user_permissions() did not include ({target_mod.module_name}, view) after user override grant — "
            "the grant is silently inert (CompanyModule provisioning likely missing)"
        )

        # 8. Idempotency: second call with identical payload must not 500
        with app.test_request_context(json=payload, headers=headers):
            response2 = update_user_permissions(user.id)
            status_code2 = response2[1] if isinstance(response2, tuple) else response2.status_code
            assert status_code2 == 200, f"Idempotent update_user_permissions returned {status_code2}"

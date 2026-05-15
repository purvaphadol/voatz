from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.company import Company
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE
from sqlalchemy.orm import joinedload

def get_active_users_query(company_id):
    """
    Returns a SQLAlchemy query for all active users in a given company.
    A user is considered active if their status is not STATUS_INACTIVE.
    """
    return User.query.filter(
        User.company_id == company_id, 
        User.status != STATUS_INACTIVE
    )

def get_active_roles_query(company_id):
    """
    Returns a SQLAlchemy query for all active roles in a given company.
    A role is considered active if its status is STATUS_ACTIVE.
    """
    return Role.query.filter(
        Role.company_id == company_id,
        Role.status == STATUS_ACTIVE
    )

def get_active_departments_query(company_id):
    """
    Returns a SQLAlchemy query for all active departments in a given company.
    A department is considered active if its status is STATUS_ACTIVE.
    """
    return Department.query.filter(
        Department.company_id == company_id,
        Department.status == STATUS_ACTIVE
    )

def get_active_user_role_mappings(user_id, company_id):
    """
    Returns active UserRoleMapping rows for a user, joined with Role to
    exclude mappings pointing to soft-deleted roles.
    Use this everywhere role_ids need to be derived for permission checks.
    """
    from app import db
    from app.models.user_role import UserRoleMapping
    from app.models.role import Role
    return db.session.query(UserRoleMapping).join(
        Role, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id,
        UserRoleMapping.status != STATUS_INACTIVE,
        Role.status != STATUS_INACTIVE
    ).all()

def get_active_role_permissions(role_ids, company_id):
    """
    Returns active RolePermissionMapping rows for a list of role_ids.
    Excludes soft-deleted permission rows.
    """
    from app import db
    from app.models.role_permission import RolePermissionMapping
    if not role_ids:
        return []
    return RolePermissionMapping.query.filter(
        RolePermissionMapping.role_id.in_(role_ids),
        RolePermissionMapping.company_id == company_id,
        RolePermissionMapping.status != STATUS_INACTIVE
    ).all()


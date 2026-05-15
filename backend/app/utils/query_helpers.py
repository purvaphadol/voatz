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

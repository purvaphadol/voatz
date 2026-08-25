from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.company import Company
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED
from sqlalchemy.orm import joinedload

def active_only(model_class, **filters):
    """Query records with status == STATUS_ACTIVE (1)."""
    return model_class.query.filter_by(status=STATUS_ACTIVE, **filters)

def inactive_only(model_class, **filters):
    """Query records with status == STATUS_INACTIVE (0)."""
    return model_class.query.filter_by(status=STATUS_INACTIVE, **filters)

def excluding_deactivated(model_class, **filters):
    """Query Active + Inactive records (status != STATUS_DEACTIVATED (9))."""
    return model_class.query.filter(model_class.status != STATUS_DEACTIVATED).filter_by(**filters)


def get_active_users_query(company_id):
    """
    Returns a SQLAlchemy query for all active users in a given company.
    A user is considered active if their status is not STATUS_INACTIVE.
    """
    return User.query.filter(
        User.company_id == company_id, 
        User.status != STATUS_INACTIVE
    )

def get_active_voters_query(company_id):
    from app.models.voter import Voter
    return Voter.query.filter(
        Voter.company_id == company_id,
        Voter.status != STATUS_INACTIVE
    )

def get_active_elections_query(company_id):
    from app.models.election import Election
    return Election.query.filter(
        Election.company_id == company_id,
        Election.status != 'cancelled'
    )

def get_active_ballots_query(company_id):
    from app.models.ballot import Ballot
    return Ballot.query.filter(
        Ballot.company_id == company_id,
        Ballot.status == STATUS_ACTIVE,
        Ballot.is_active == True
    )

def get_active_candidates_query(company_id):
    from app.models.candidate import Candidate
    return Candidate.query.filter(
        Candidate.company_id == company_id,
        Candidate.status == STATUS_ACTIVE,
        Candidate.is_active == True
    )


def get_election_registrations_query(election_id, company_id):
    from app.models.voter_registration import VoterRegistration
    return VoterRegistration.query.filter(
        VoterRegistration.election_id == election_id,
        VoterRegistration.company_id == company_id,
        VoterRegistration.status != 'deleted'
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
    return Department.query.join(Company).filter(
        Department.company_id == company_id,
        Department.status == STATUS_ACTIVE,
        Company.status == STATUS_ACTIVE
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


def get_active_companies_query():
    """
    Returns a SQLAlchemy query for all active companies.
    A company is considered active if its status is STATUS_ACTIVE.
    """
    from app.models.company import Company
    from app.utils.constants import STATUS_ACTIVE
    return Company.query.filter(
        Company.status == STATUS_ACTIVE
    )


def get_active_modules_query(company_id):
    """
    Returns a SQLAlchemy query for all provisioned non-deactivated system modules for a given company.
    """
    from app.models.module import SystemModule, CompanyModule
    from app.utils.constants import STATUS_DEACTIVATED
    return SystemModule.query.join(
        CompanyModule, CompanyModule.system_module_id == SystemModule.id
    ).filter(
        CompanyModule.company_id == company_id,
        CompanyModule.status != STATUS_DEACTIVATED,
        SystemModule.status != STATUS_DEACTIVATED
    ).order_by(SystemModule.order_index.asc(), SystemModule.module_name.asc())


def get_admin_modules_query(company_id):
    """
    Returns a SQLAlchemy query for non-deactivated modules provisioned for a given company.
    """
    return get_active_modules_query(company_id)


def get_active_module_actions_query(module_id, company_id=None):
    """
    Returns a SQLAlchemy query for non-deactivated system module actions for a specific system module.
    """
    from app.models.module import SystemModuleAction
    from app.utils.constants import STATUS_DEACTIVATED
    return SystemModuleAction.query.filter(
        SystemModuleAction.system_module_id == module_id,
        SystemModuleAction.status != STATUS_DEACTIVATED
    )

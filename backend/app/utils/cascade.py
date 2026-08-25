from app import db
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED

CASCADE_RULES = {
    'Company': [
        {'model': 'Department', 'fk': 'company_id'},
        {'model': 'Role', 'fk': 'company_id'},
        {'model': 'User', 'fk': 'company_id'},
        {'model': 'Voter', 'fk': 'company_id'},
        {'model': 'CompanyModule', 'fk': 'company_id'},
        {'model': 'Election', 'fk': 'company_id'},
        {'model': 'Ballot', 'fk': 'company_id'},
        {'model': 'Candidate', 'fk': 'company_id'},
    ],
    'Department': [
        {'model': 'Role', 'fk': 'department_id'},
        {'model': 'User', 'fk': 'department_id'},
    ],
    'Role': [
        {'model': 'UserRoleMapping', 'fk': 'role_id'},
        {'model': 'RolePermissionMapping', 'fk': 'role_id'},
    ],
    'User': [
        {'model': 'UserRoleMapping', 'fk': 'user_id'},
        {'model': 'UserPermissionMapping', 'fk': 'user_id'},
        {'model': 'Voter', 'fk': 'user_id'},  # Two-hop: User -> Voter -> VoterRegistration
    ],
    'Voter': [
        {'model': 'VoterRegistration', 'fk': 'voter_id'},
    ],
    'Ballot': [
        {'model': 'Candidate', 'fk': 'ballot_id'},
    ],
    'Election': [
        {'model': 'Ballot', 'fk': 'election_id'},
        {'model': 'Candidate', 'fk': 'election_id'},
        {'model': 'VoterRegistration', 'fk': 'election_id'},
    ],
    'SystemModule': [
        {'model': 'CompanyModule', 'fk': 'system_module_id'},
        {'model': 'SystemModuleAction', 'fk': 'system_module_id'},
        {'model': 'RolePermissionMapping', 'fk': 'module_id'},
        {'model': 'UserPermissionMapping', 'fk': 'module_id'},
    ]
}


def get_model_class(model_name):
    """Dynamic import helper to resolve model classes without circular dependencies."""
    if model_name == 'Company':
        from app.models.company import Company
        return Company
    elif model_name == 'Department':
        from app.models.department import Department
        return Department
    elif model_name == 'Role':
        from app.models.role import Role
        return Role
    elif model_name == 'User':
        from app.models.user import User
        return User
    elif model_name == 'Voter':
        from app.models.voter import Voter
        return Voter
    elif model_name == 'Election':
        from app.models.election import Election
        return Election
    elif model_name == 'Ballot':
        from app.models.ballot import Ballot
        return Ballot
    elif model_name == 'Candidate':
        from app.models.candidate import Candidate
        return Candidate
    elif model_name == 'SystemModule':
        from app.models.module import SystemModule
        return SystemModule
    elif model_name == 'CompanyModule':
        from app.models.module import CompanyModule
        return CompanyModule
    elif model_name == 'SystemModuleAction':
        from app.models.module import SystemModuleAction
        return SystemModuleAction
    elif model_name == 'UserRoleMapping':
        from app.models.user_role import UserRoleMapping
        return UserRoleMapping
    elif model_name == 'RolePermissionMapping':
        from app.models.role_permission import RolePermissionMapping
        return RolePermissionMapping
    elif model_name == 'UserPermissionMapping':
        from app.models.user_permission import UserPermissionMapping
        return UserPermissionMapping
    elif model_name == 'VoterRegistration':
        from app.models.voter_registration import VoterRegistration
        return VoterRegistration
    return None


def count_dependents(entity_type, entity_id):
    """
    Recursively counts all active (STATUS_ACTIVE=1) child dependents of entity_type(entity_id).
    Uses a visited set to ensure multi-path reachable entities (e.g. Candidate/Ballot via Company or Election)
    are counted exactly ONCE without duplicate counting.
    """
    visited = set()  # Set of (model_name, id)
    breakdown = {}

    def _traverse(current_type, current_id):
        child_rules = CASCADE_RULES.get(current_type, [])
        for rule in child_rules:
            child_model_name = rule['model']
            child_class = get_model_class(child_model_name)
            if not child_class:
                continue

            fk_field = getattr(child_class, rule['fk'], None)
            if not fk_field:
                continue

            # Query active children
            query = child_class.query.filter(fk_field == current_id)
            if hasattr(child_class, 'status'):
                # Handle both integer status and string status if any
                if child_model_name in ['VoterRegistration', 'Election']:
                    query = query.filter(child_class.status != 'deleted', child_class.status != 'cancelled')
                else:
                    query = query.filter(child_class.status == STATUS_ACTIVE)
            elif hasattr(child_class, 'is_active'):
                query = query.filter(child_class.is_active == True)

            active_children = query.all()
            for child in active_children:
                key = (child_model_name, child.id)
                if key not in visited:
                    visited.add(key)
                    breakdown[child_model_name] = breakdown.get(child_model_name, 0) + 1
                    # Recurse downstream
                    _traverse(child_model_name, child.id)

    _traverse(entity_type, entity_id)

    return {
        'total_count': len(visited),
        'breakdown': breakdown
    }


def cascade_set_inactive(entity_type, entity_id, top_parent_type=None, top_parent_id=None, visited=None):
    """
    Recursively cascades STATUS_INACTIVE (0) to all downstream child records.
    Populates deactivated_by_cascade_from_type and deactivated_by_cascade_from_id on affected children.

    Multi-path Reachability & De-duplication:
    - Uses a `visited` set to ensure each row is updated exactly ONCE per cascade.
    - Direct/shallower parent relationships take priority (evaluated first in CASCADE_RULES).
    """
    if visited is None:
        visited = set()

    root_type = top_parent_type or entity_type
    root_id = top_parent_id or entity_id

    child_rules = CASCADE_RULES.get(entity_type, [])
    affected_count = 0

    for rule in child_rules:
        child_model_name = rule['model']
        child_class = get_model_class(child_model_name)
        if not child_class:
            continue

        fk_field = getattr(child_class, rule['fk'], None)
        if not fk_field:
            continue

        # Find active children to cascade
        query = child_class.query.filter(fk_field == entity_id)
        if hasattr(child_class, 'status'):
            if child_model_name not in ['VoterRegistration', 'Election']:
                query = query.filter(child_class.status == STATUS_ACTIVE)

        active_children = query.all()

        for child in active_children:
            key = (child_model_name, child.id)
            if key in visited:
                continue

            visited.add(key)
            affected_count += 1

            # Update child status and cascade tracking fields
            if hasattr(child, 'status'):
                if child_model_name == 'VoterRegistration':
                    child.status = 'cancelled'
                elif child_model_name == 'Election':
                    child.status = 'cancelled'
                else:
                    child.status = STATUS_INACTIVE

            if hasattr(child, 'is_active'):
                try:
                    child.is_active = False
                except AttributeError:
                    pass

            if hasattr(child, 'deactivated_by_cascade_from_type'):
                child.deactivated_by_cascade_from_type = root_type
            if hasattr(child, 'deactivated_by_cascade_from_id'):
                child.deactivated_by_cascade_from_id = root_id

            # Recurse downstream
            affected_count += cascade_set_inactive(
                child_model_name, child.id,
                top_parent_type=root_type, top_parent_id=root_id,
                visited=visited
            )

    return affected_count


def cascade_reactivate(entity_type, entity_id, top_parent_type=None, top_parent_id=None, visited=None):
    """
    Recursively reactivates child records that were set to STATUS_INACTIVE (0) as a direct result
    of this parent's cascade (matching deactivated_by_cascade_from_type / id against entity or root parent).

    Children that were independently deactivated (tracking columns IS NULL or != parent/root) are left inactive.
    """
    if visited is None:
        visited = set()

    root_type = top_parent_type or entity_type
    root_id = top_parent_id or entity_id

    reactivated_count = 0
    independent_count = 0

    child_rules = CASCADE_RULES.get(entity_type, [])

    for rule in child_rules:
        child_model_name = rule['model']
        child_class = get_model_class(child_model_name)
        if not child_class:
            continue

        fk_field = getattr(child_class, rule['fk'], None)
        if not fk_field:
            continue

        # Find inactive children linked to entity
        query = child_class.query.filter(fk_field == entity_id)
        if hasattr(child_class, 'status'):
            if child_model_name not in ['VoterRegistration', 'Election']:
                query = query.filter(child_class.status == STATUS_INACTIVE)

        inactive_children = query.all()

        for child in inactive_children:
            key = (child_model_name, child.id)
            if key in visited:
                continue

            visited.add(key)

            # Check if this child was deactivated by this parent or root parent's cascade
            was_cascaded_by_this_parent = False
            if hasattr(child, 'deactivated_by_cascade_from_type') and hasattr(child, 'deactivated_by_cascade_from_id'):
                was_cascaded_by_this_parent = (
                    (child.deactivated_by_cascade_from_type == entity_type and child.deactivated_by_cascade_from_id == entity_id) or
                    (child.deactivated_by_cascade_from_type == root_type and child.deactivated_by_cascade_from_id == root_id)
                )

            if was_cascaded_by_this_parent:
                reactivated_count += 1
                if hasattr(child, 'status'):
                    if child_model_name == 'VoterRegistration':
                        child.status = 'approved'
                    elif child_model_name == 'Election':
                        child.status = 'draft'
                    else:
                        child.status = STATUS_ACTIVE

                if hasattr(child, 'is_active'):
                    try:
                        child.is_active = True
                    except AttributeError:
                        pass

                child.deactivated_by_cascade_from_type = None
                child.deactivated_by_cascade_from_id = None

                # Recurse downstream to reactivate its children as well
                sub_res = cascade_reactivate(
                    child_model_name, child.id,
                    top_parent_type=root_type, top_parent_id=root_id,
                    visited=visited
                )
                reactivated_count += sub_res['reactivated_count']
                independent_count += sub_res['independent_count']
            else:
                independent_count += 1

    return {
        'reactivated_count': reactivated_count,
        'independent_count': independent_count
    }


def count_reactivatable_dependents(entity_type, entity_id):
    """
    Returns counts of children that WILL be reactivated vs children that will remain inactive.
    Used for pre-save reactivation warning dialogs.
    """
    res = cascade_reactivate(entity_type, entity_id, visited=set())
    # Note: DB rollback must be called by caller or dry_run if called for read-only inspection
    db.session.rollback()
    return res

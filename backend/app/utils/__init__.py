from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from functools import wraps
from flask import jsonify
from app import db
from werkzeug.exceptions import NotFound, HTTPException
import logging
import warnings

# Set up logging
logger = logging.getLogger(__name__)

def get_current_user():
    """Get the current authenticated user"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None
        
        # Handle both string and integer identities
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return None
        elif not isinstance(user_id, int):
            return None
            
        return User.query.get(user_id)
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None

def get_current_company_id():
    """Get the current user's company ID"""
    user = get_current_user()
    return user.company_id if user else None


def is_administrator():
    """Check whether the current JWT corresponds to a platform Administrator.

    Administrator tokens carry an ``is_administrator: true`` custom claim
    set at login time (see ``POST /api/auth/administrator/login``).  This
    function inspects that claim directly — no database query is needed.

    This is intentionally distinct from :func:`is_company_super_admin`, which
    checks whether a *User* holds the Company Super Admin *role* inside their
    own company.  Conflating the two was the root cause of several privilege-
    escalation bugs (a Company Super Admin could perform platform-level
    operations).

    Returns:
        bool: True only when the current JWT carries the administrator
              claim; False otherwise.
    """
    try:
        claims = get_jwt()
        return claims.get('is_administrator', False) is True
    except Exception:
        return False


def get_current_administrator():
    """Load the :class:`Administrator` row for the current JWT identity.

    Administrator tokens use an identity string of the form ``"admin:<id>"``.
    This helper parses the numeric id out of that string and returns the
    corresponding ``Administrator`` row, or ``None`` if the current token is
    not an administrator token or the row cannot be found.

    Returns:
        Administrator | None
    """
    try:
        if not is_administrator():
            return None

        from app.models.administrator import Administrator

        identity = get_jwt_identity()
        if not identity or not isinstance(identity, str) or not identity.startswith('admin:'):
            return None

        admin_id_str = identity.split(':', 1)[1]
        admin_id = int(admin_id_str)
        return Administrator.query.get(admin_id)
    except Exception as e:
        logger.error(f"Error in get_current_administrator: {str(e)}")
        return None


def is_company_super_admin():
    """Check whether the current user holds the Company Super Admin role.

    The Company Super Admin is a protected ``Role`` row with
    ``Role.is_super_admin = True`` within the user's own company.  This grants
    full access **within that company only** — it does *not* confer any
    platform-level privileges (use :func:`is_administrator` for that).

    The check uses the boolean ``Role.is_super_admin`` column rather than
    matching on a role-name string, which avoids false positives from
    similarly-named regular roles.

    Returns:
        bool: True if the current user is mapped to an active super-admin
              role in their own company; False otherwise.
    """
    try:
        from app.models.role import Role

        user = get_current_user()
        if not user or not user.company_id:
            return False

        super_admin_role = Role.query.filter(
            Role.is_super_admin.is_(True),
            Role.company_id == user.company_id,
            Role.status != 0
        ).first()

        if not super_admin_role:
            return False

        mapping = UserRoleMapping.query.filter_by(
            user_id=user.id,
            role_id=super_admin_role.id,
            status=1
        ).first()

        return mapping is not None

    except Exception as e:
        logger.error(f"Error in is_company_super_admin: {str(e)}")
        return False


def is_current_user_super_admin():
    """**Deprecated** — use :func:`is_company_super_admin` or
    :func:`is_administrator` instead.

    Kept as a thin wrapper around :func:`is_company_super_admin` so that
    call-sites not yet migrated continue to work without silently breaking.
    """
    warnings.warn(
        "is_current_user_super_admin() is deprecated. "
        "Use is_company_super_admin() or is_administrator() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return is_company_super_admin()


def require_same_company_or_administrator(target_company_id):
    """Return a (response, status_code) tuple if the caller is neither a
    platform Administrator nor a member of *target_company_id*.

    Use this at the top of any route that needs the "same company unless
    you're a platform admin" guard.  If the check passes, the function
    returns ``None`` and the caller should continue normally.

    Args:
        target_company_id: The company_id the action is being performed on.

    Returns:
        None on success, or a ``(jsonify({...}), 403)`` tuple to return
        directly from the calling route on failure.
    """
    if is_administrator():
        return None

    current_company = get_current_company_id()
    if current_company != target_company_id:
        return jsonify({'error': 'Forbidden: you can only access your own company'}), 403

    return None


def require_company_context(f):
    """Decorator to ensure the user has a valid company context"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            if is_administrator():
                return f(*args, **kwargs)
            user = get_current_user()
            if not user or not user.company_id:
                return jsonify({'error': 'Invalid company context'}), 403
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in require_company_context: {str(e)}")
            return jsonify({'error': 'Authentication error', 'message': str(e)}), 401
    return decorated_function

def check_user_permission(module_name, action_name):
    """Check if current user has permission for a specific module/action using SystemModule catalog."""
    try:
        user = get_current_user()
        if not user:
            logger.warning(f"No user found for permission check: {module_name}.{action_name}")
            return False
        
        company_id = user.company_id
        if not company_id:
            logger.warning(f"No company_id for user {user.id} in permission check: {module_name}.{action_name}")
            return False
        
        from app.models.module import SystemModule, SystemModuleAction, CompanyModule
        from app.utils.query_helpers import get_active_user_role_mappings, get_active_role_permissions

        # 1. Fetch user's active role mappings
        active_mappings = get_active_user_role_mappings(user.id, company_id)
        role_ids = [ur.role_id for ur in active_mappings]
        from app.models.role import Role
        is_company_super_admin = Role.query.filter(
            Role.id.in_(role_ids),
            Role.is_super_admin == True,
            Role.status != 0,
            Role.status != 9
        ).count() > 0 if role_ids else False

        # 2. Get system module by name
        sys_module = SystemModule.query.filter_by(module_name=module_name).filter(SystemModule.status != 9).first()
        if not sys_module:
            logger.warning(f"SystemModule '{module_name}' not found")
            return False

        # 3. Check if module is provisioned for this company
        comp_module = CompanyModule.query.filter_by(
            company_id=company_id,
            system_module_id=sys_module.id
        ).filter(CompanyModule.status != 9).first()
        if not comp_module:
            # If company_modules mappings exist for this company, enforce strict provisioning
            has_any_provisioned = CompanyModule.query.filter_by(company_id=company_id).filter(CompanyModule.status != 9).count() > 0
            if has_any_provisioned:
                logger.warning(f"SystemModule '{module_name}' not provisioned for company {company_id}")
                return False

        # Company Super Admin carries automatic full permission for all provisioned modules
        if is_company_super_admin:
            return True

        # 4. Get system action by name
        sys_action = SystemModuleAction.query.filter_by(
            action_name=action_name,
            system_module_id=sys_module.id
        ).filter(SystemModuleAction.status != 9).first()
        if not sys_action:
            logger.warning(f"SystemModuleAction '{action_name}' not found for module '{module_name}'")
            return False

        # 5. Check role permissions
        role_ids = [ur.role_id for ur in active_mappings]
        active_role_perms = get_active_role_permissions(role_ids, company_id)
        role_permission = next(
            (rp for rp in active_role_perms
             if rp.module_id == sys_module.id and rp.action_id == sys_action.id),
            None
        )

        if role_permission:
            user_override = UserPermissionMapping.query.filter_by(
                user_id=user.id,
                module_id=sys_module.id,
                action_id=sys_action.id,
                company_id=company_id
            ).filter(UserPermissionMapping.status != 9).first()
            if user_override:
                return user_override.permission_type == 1
            return True

        user_permission = UserPermissionMapping.query.filter_by(
            user_id=user.id,
            module_id=sys_module.id,
            action_id=sys_action.id,
            company_id=company_id,
            permission_type=1
        ).filter(UserPermissionMapping.status != 9).first()
        if user_permission:
            return True

        return False
        
    except Exception as e:
        logger.error(f"Exception in check_user_permission({module_name}, {action_name}): {str(e)}")
        return False

def require_permission(module_name, action_name):
    """Decorator to require specific permission for accessing an endpoint."""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                if is_administrator():
                    logger.info(f"Administrator granted access to {module_name}.{action_name}")
                    return f(*args, **kwargs)

                user = get_current_user()
                if not user:
                    logger.warning(f"No user found for {module_name}.{action_name} endpoint")
                    return jsonify({'error': 'Authentication required'}), 401
                
                if not user.company_id:
                    logger.warning(f"User {user.id} has no company context for {module_name}.{action_name}")
                    return jsonify({'error': 'Invalid company context'}), 403
                
                if not check_user_permission(module_name, action_name):
                    logger.warning(f"User {user.id} denied access to {module_name}.{action_name}")
                    return jsonify({
                        'error': 'Access denied',
                        'message': f'You do not have permission to {action_name} {module_name}'
                    }), 403
                
                logger.info(f"User {user.id} granted access to {module_name}.{action_name}")
                return f(*args, **kwargs)
                
            except Exception as e:
                if isinstance(e, HTTPException):
                    return jsonify({'error': e.description}), e.code
                
                logger.error(f"Exception in require_permission decorator for {module_name}.{action_name}: {str(e)}", exc_info=True)
                return jsonify({
                    'error': 'Internal server error', 
                    'message': 'An error occurred while checking permissions'
                }), 500
                
        return decorated_function
    return decorator

def get_user_permissions_summary():
    """Get comprehensive permissions summary for current user using SystemModule catalog."""
    from app.models.module import SystemModule, SystemModuleAction, CompanyModule
    if is_administrator():
        sys_modules = SystemModule.query.filter(SystemModule.status != 9).order_by(SystemModule.order_index.asc()).all()
        permissions = {}
        for m in sys_modules:
            permissions[m.module_name] = [
                {'action': act, 'source': 'administrator', 'url': f'/{act}'}
                for act in ['view', 'create', 'update', 'delete']
            ]
        return permissions

    from app.utils.query_helpers import get_active_user_role_mappings, get_active_role_permissions
    user = get_current_user()
    if not user:
        return {}

    company_id = user.company_id

    active_mappings = get_active_user_role_mappings(user.id, company_id)
    role_ids = [ur.role_id for ur in active_mappings]
    role_permissions = get_active_role_permissions(role_ids, company_id)

    user_permissions = UserPermissionMapping.query.filter(
        UserPermissionMapping.user_id == user.id,
        UserPermissionMapping.company_id == company_id,
        UserPermissionMapping.status != 9
    ).all()

    sys_modules = SystemModule.query.join(
        CompanyModule, CompanyModule.system_module_id == SystemModule.id
    ).filter(
        CompanyModule.company_id == company_id,
        CompanyModule.status != 9,
        SystemModule.status != 9
    ).all()
    if not sys_modules:
        sys_modules = SystemModule.query.filter(SystemModule.status != 9).all()

    modules_map = {m.id: m for m in sys_modules}
    actions_map = {a.id: a for a in SystemModuleAction.query.filter(SystemModuleAction.status != 9).all()}

    permissions = {}

    for rp in role_permissions:
        module = modules_map.get(rp.module_id)
        action = actions_map.get(rp.action_id)
        if module and action:
            if module.module_name not in permissions:
                permissions[module.module_name] = []
            permissions[module.module_name].append({
                'action': action.action_name,
                'source': 'role',
                'url': action.action_url
            })

    for up in user_permissions:
        module = modules_map.get(up.module_id)
        action = actions_map.get(up.action_id)
        if module and action:
            if module.module_name not in permissions:
                permissions[module.module_name] = []
            permissions[module.module_name] = [
                p for p in permissions[module.module_name]
                if p['action'] != action.action_name
            ]
            if up.permission_type == 1:
                permissions[module.module_name].append({
                    'action': action.action_name,
                    'source': 'user-override',
                    'url': action.action_url
                })

    return permissions

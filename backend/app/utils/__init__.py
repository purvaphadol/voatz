from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.models.module import Module
from app.models.module_action import ModuleAction
from functools import wraps
from flask import jsonify
import logging

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

def require_company_context(f):
    """Decorator to ensure the user has a valid company context"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user = get_current_user()
            if not user or not user.company_id:
                return jsonify({'error': 'Invalid company context'}), 403
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in require_company_context: {str(e)}")
            return jsonify({'error': 'Authentication error', 'message': str(e)}), 401
    return decorated_function

def check_user_permission(module_name, action_name):
    """Check if current user has permission for a specific module/action"""
    try:
        user = get_current_user()
        if not user:
            logger.warning(f"No user found for permission check: {module_name}.{action_name}")
            return False
        
        company_id = user.company_id
        if not company_id:
            logger.warning(f"No company_id for user {user.id} in permission check: {module_name}.{action_name}")
            return False
        
        # Get module by name
        module = Module.query.filter_by(module_name=module_name, company_id=company_id).first()
        if not module:
            logger.warning(f"Module '{module_name}' not found for company {company_id}")
            return False
        
        # Get action by name for this module
        action = ModuleAction.query.filter_by(
            action_name=action_name, 
            module_id=module.id,
            company_id=company_id
        ).first()
        if not action:
            logger.warning(f"Action '{action_name}' not found for module '{module_name}' in company {company_id}")
            return False
        
        # Check user's roles and their permissions
        user_roles = UserRoleMapping.query.filter_by(
            user_id=user.id,
            company_id=company_id,
            status=1  # Active roles only
        ).all()
        
        role_ids = [ur.role_id for ur in user_roles]
        
        # Check if any role has this permission
        role_permission = RolePermissionMapping.query.filter(
            RolePermissionMapping.role_id.in_(role_ids),
            RolePermissionMapping.module_id == module.id,
            RolePermissionMapping.action_id == action.id,
            RolePermissionMapping.company_id == company_id
        ).first()
        
        if role_permission:
            # Check for user-specific overrides
            user_override = UserPermissionMapping.query.filter_by(
                user_id=user.id,
                module_id=module.id,
                action_id=action.id,
                company_id=company_id
            ).first()
            
            if user_override:
                result = user_override.permission_type == 1  # 1 = allow, 0 = deny
                logger.info(f"User {user.id} permission override for {module_name}.{action_name}: {'ALLOW' if result else 'DENY'}")
                return result
            
            logger.info(f"User {user.id} has role permission for {module_name}.{action_name}: ALLOW")
            return True  # Role has permission and no user override
        
        # Check for user-specific allow permissions
        user_permission = UserPermissionMapping.query.filter_by(
            user_id=user.id,
            module_id=module.id,
            action_id=action.id,
            company_id=company_id,
            permission_type=1  # Allow
        ).first()
        
        if user_permission:
            logger.info(f"User {user.id} has direct permission for {module_name}.{action_name}: ALLOW")
            return True
        
        logger.warning(f"User {user.id} has no permission for {module_name}.{action_name}: DENY")
        return False
        
    except Exception as e:
        logger.error(f"Exception in check_user_permission({module_name}, {action_name}): {str(e)}")
        # For permission checks, return False instead of raising
        return False

def require_permission(module_name, action_name):
    """Decorator to require specific permission for accessing an endpoint"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
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
                logger.error(f"Exception in require_permission decorator for {module_name}.{action_name}: {str(e)}", exc_info=True)
                # Instead of masking with 401, return 500 for actual errors
                return jsonify({
                    'error': 'Internal server error', 
                    'message': 'An error occurred while checking permissions'
                }), 500
                
        return decorated_function
    return decorator

def get_user_permissions_summary():
    """Get comprehensive permissions summary for current user"""
    user = get_current_user()
    if not user:
        return {}
    
    company_id = user.company_id
    
    # Get user roles
    user_roles = UserRoleMapping.query.filter_by(
        user_id=user.id,
        company_id=company_id,
        status=1
    ).all()
    
    role_ids = [ur.role_id for ur in user_roles]
    
    # Get role permissions
    role_permissions = RolePermissionMapping.query.filter(
        RolePermissionMapping.role_id.in_(role_ids),
        RolePermissionMapping.company_id == company_id
    ).all()
    
    # Get user-specific permissions
    user_permissions = UserPermissionMapping.query.filter_by(
        user_id=user.id,
        company_id=company_id
    ).all()
    
    # Build permission map
    permissions = {}
    
    # Add role permissions
    for rp in role_permissions:
        module = Module.query.get(rp.module_id)
        action = ModuleAction.query.get(rp.action_id)
        if module and action:
            if module.module_name not in permissions:
                permissions[module.module_name] = []
            permissions[module.module_name].append({
                'action': action.action_name,
                'source': 'role',
                'url': action.action_url
            })
    
    # Apply user-specific overrides
    for up in user_permissions:
        module = Module.query.get(up.module_id)
        action = ModuleAction.query.get(up.action_id)
        if module and action:
            if module.module_name not in permissions:
                permissions[module.module_name] = []
            
            # Remove existing role permission if being overridden
            permissions[module.module_name] = [
                p for p in permissions[module.module_name] 
                if p['action'] != action.action_name
            ]
            
            # Add user permission if it's an allow
            if up.permission_type == 1:
                permissions[module.module_name].append({
                    'action': action.action_name,
                    'source': 'user-allow',
                    'url': action.action_url
                })
    
    return permissions

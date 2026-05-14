from flask import Blueprint, jsonify, request
from app import db
from app.models.user_role import UserRoleMapping
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.models.module import Module
from app.models.module_action import ModuleAction
from app.models.role import Role
from app.utils import get_current_company_id, require_company_context

permissions_bp = Blueprint('permissions', __name__)

@permissions_bp.route('/user', methods=['GET'])
@require_company_context
def get_current_user_permissions():
    """Get permissions for the current authenticated user"""
    from app.utils import get_current_user
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Use the existing function with current user's ID
    return get_user_permissions(user.id)

@permissions_bp.route('/user/<int:user_id>', methods=['GET'])
@require_company_context
def get_user_permissions(user_id):
    company_id = get_current_company_id()
    
    # Step 1: Fetch roles assigned to the user within the company
    user_roles = UserRoleMapping.query.filter_by(
        user_id=user_id, 
        company_id=company_id
    ).all()
    role_ids = [ur.role_id for ur in user_roles]

    # Step 2: Get permissions from roles (company-specific)
    role_permissions = RolePermissionMapping.query.filter(
        RolePermissionMapping.role_id.in_(role_ids),
        RolePermissionMapping.company_id == company_id
    ).all()
    permission_map = {(rp.module_id, rp.action_id): 'role' for rp in role_permissions}

    # Step 3: Apply user-specific overrides (company-specific)
    user_permissions = UserPermissionMapping.query.filter_by(
        user_id=user_id,
        company_id=company_id
    ).all()
    for up in user_permissions:
        key = (up.module_id, up.action_id)
        if up.permission_type == 1:
            permission_map[key] = 'user-allow'
        elif up.permission_type == 0:
            permission_map.pop(key, None)  # override to deny

    # Step 4: Format for API response (only include company-specific modules/actions)
    results = []
    for (module_id, action_id), source in permission_map.items():
        module = Module.query.filter_by(id=module_id, company_id=company_id).first()
        action = ModuleAction.query.filter_by(id=action_id, company_id=company_id).first()
        if module and action:
            results.append({
                'module': module.module_name,
                'action': action.action_name,
                'url': action.action_url,
                'source': source,
                'module_id': module.id,
                'action_id': action.id
            })

    return jsonify(results)

@permissions_bp.route('/user/<int:user_id>/roles', methods=['GET'])
@require_company_context
def get_user_roles(user_id):
    company_id = get_current_company_id()
    
    user_roles = db.session.query(
        UserRoleMapping, 
        Role.role_name.label('role_name')
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id
    ).all()
    
    return jsonify([{
        'role_id': ur.UserRoleMapping.role_id,
        'role_name': ur.role_name,
        'department_id': ur.UserRoleMapping.department_id,
        'status': ur.UserRoleMapping.status
    } for ur in user_roles])

@permissions_bp.route('/modules', methods=['GET'])
@require_company_context
def get_modules_with_actions():
    company_id = get_current_company_id()
    
    modules = Module.query.filter_by(company_id=company_id).all()
    result = []
    
    for module in modules:
        actions = ModuleAction.query.filter_by(
            module_id=module.id,
            company_id=company_id
        ).all()
        
        result.append({
            'id': module.id,
            'module_name': module.module_name,
            'actions': [{
                'id': action.id,
                'action_name': action.action_name,
                'action_url': action.action_url
            } for action in actions]
        })
    
    return jsonify(result)

# Add the missing endpoint that React frontend is calling
@permissions_bp.route('/module-actions', methods=['GET'])
@require_company_context
def get_module_actions():
    """Get all modules with their actions - same as /modules but with different endpoint name"""
    return get_modules_with_actions()

@permissions_bp.route('/role/<int:role_id>', methods=['GET'])
@require_company_context
def get_role_permissions(role_id):
    """Get permissions for a specific role"""
    company_id = get_current_company_id()
    
    # Get role permissions
    role_permissions = RolePermissionMapping.query.filter_by(
        role_id=role_id,
        company_id=company_id
    ).all()
    
    # Build permissions dictionary
    permissions = {}
    for rp in role_permissions:
        module = Module.query.filter_by(id=rp.module_id, company_id=company_id).first()
        action = ModuleAction.query.filter_by(id=rp.action_id, company_id=company_id).first()
        
        if module and action:
            if module.id not in permissions:
                permissions[module.id] = {}
            permissions[module.id][action.id] = True
    
    return jsonify({
        'role_id': role_id,
        'permissions': permissions
    })

@permissions_bp.route('/role/<int:role_id>', methods=['POST'])
@require_company_context
def update_role_permissions(role_id):
    """Update permissions for a specific role"""
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or 'permissions' not in data:
        return jsonify({'error': 'Missing permissions data'}), 400
    
    try:
        # Delete existing permissions for this role
        RolePermissionMapping.query.filter_by(
            role_id=role_id,
            company_id=company_id
        ).delete()
        
        # Add new permissions
        permissions_data = data['permissions']
        for module_id, actions in permissions_data.items():
            for action_id, granted in actions.items():
                if granted:  # Only add permissions that are granted
                    permission = RolePermissionMapping(
                        role_id=role_id,
                        module_id=int(module_id),
                        action_id=int(action_id),
                        company_id=company_id
                    )
                    db.session.add(permission)
        
        db.session.commit()
        return jsonify({'message': 'Role permissions updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@permissions_bp.route('/user/<int:user_id>', methods=['POST'])
@require_company_context
def update_user_permissions(user_id):
    """Update permissions for a specific user - only creates overrides that differ from role permissions"""
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or 'permissions' not in data:
        return jsonify({'error': 'Missing permissions data'}), 400
    
    try:
        # Step 1: Get user's current role-based permissions
        user_roles = UserRoleMapping.query.filter_by(
            user_id=user_id, 
            company_id=company_id
        ).all()
        role_ids = [ur.role_id for ur in user_roles]

        role_permissions = RolePermissionMapping.query.filter(
            RolePermissionMapping.role_id.in_(role_ids),
            RolePermissionMapping.company_id == company_id
        ).all()
        role_perm_map = {(rp.module_id, rp.action_id): True for rp in role_permissions}
        
        # Step 2: Delete existing user permissions
        UserPermissionMapping.query.filter_by(
            user_id=user_id,
            company_id=company_id
        ).delete()
        
        # Step 3: Create user-specific overrides only where they differ from role permissions
        permissions_data = data['permissions']
        overrides_created = 0
        
        for module_id, actions in permissions_data.items():
            for action_id, granted in actions.items():
                module_id_int = int(module_id)
                action_id_int = int(action_id)
                key = (module_id_int, action_id_int)
                
                # Check what the user would have from roles
                has_from_role = key in role_perm_map
                
                # Only create user-specific override if it's different from role permission
                # Convert to boolean for comparison
                granted_bool = bool(granted)
                has_from_role_bool = bool(has_from_role)
                
                if granted_bool != has_from_role_bool:
                    permission_type = 1 if granted_bool else 0  # 1 = Allow, 0 = Deny
                    permission = UserPermissionMapping(
                        user_id=user_id,
                        role_id=None,  # Direct user permission
                        module_id=module_id_int,
                        action_id=action_id_int,
                        permission_type=permission_type,
                        company_id=company_id
                    )
                    db.session.add(permission)
                    overrides_created += 1
                    
                    # Debug logging
                    override_type = "ALLOW" if permission_type == 1 else "DENY"
                    print(f"DEBUG: Created {override_type} override for Module {module_id_int}, Action {action_id_int} (granted={granted_bool}, has_from_role={has_from_role_bool})")
        
        db.session.commit()
        return jsonify({
            'message': 'User permissions updated successfully',
            'overrides_created': overrides_created,
            'debug_info': f'Processed {len(permissions_data)} modules'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error in update_user_permissions: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_bp.route('/user/<int:user_id>/management', methods=['GET'])
@require_company_context
def get_user_permissions_for_management(user_id):
    """Get user permissions in management format - shows all actions with current effective state"""
    company_id = get_current_company_id()
    
    # Get all modules and actions for this company
    modules = Module.query.filter_by(company_id=company_id).all()
    
    # Step 1: Get user's role-based permissions
    user_roles = UserRoleMapping.query.filter_by(
        user_id=user_id, 
        company_id=company_id
    ).all()
    role_ids = [ur.role_id for ur in user_roles]

    role_permissions = RolePermissionMapping.query.filter(
        RolePermissionMapping.role_id.in_(role_ids),
        RolePermissionMapping.company_id == company_id
    ).all()
    role_perm_map = {(rp.module_id, rp.action_id): True for rp in role_permissions}

    # Step 2: Get user-specific overrides
    user_permissions = UserPermissionMapping.query.filter_by(
        user_id=user_id,
        company_id=company_id
    ).all()
    
    user_overrides = {}
    for up in user_permissions:
        key = (up.module_id, up.action_id)
        if up.permission_type == 1:  # ALLOW override
            user_overrides[key] = True
        elif up.permission_type == 0:  # DENY override
            user_overrides[key] = False
    
    # Step 3: Build response with effective permissions (role + user overrides)
    permissions = {}
    permission_sources = {}  # Track where each permission comes from
    
    for module in modules:
        actions = ModuleAction.query.filter_by(
            module_id=module.id,
            company_id=company_id
        ).all()
        
        if actions:  # Only include modules that have actions
            permissions[str(module.id)] = {}
            permission_sources[str(module.id)] = {}
            
            for action in actions:
                key = (module.id, action.id)
                
                # Determine effective permission and source
                if key in user_overrides:
                    # User has an override
                    effective_permission = user_overrides[key]
                    source = 'user-override'
                elif key in role_perm_map:
                    # User has permission from role
                    effective_permission = True
                    source = 'role'
                else:
                    # No permission
                    effective_permission = False
                    source = 'none'
                
                permissions[str(module.id)][str(action.id)] = effective_permission
                permission_sources[str(module.id)][str(action.id)] = source
    
    return jsonify({
        'user_id': user_id,
        'permissions': permissions,
        'sources': permission_sources  # Include source information for frontend
    })

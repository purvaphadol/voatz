from flask import Blueprint, jsonify, request, current_app
from app import db
from app.models.user_role import UserRoleMapping
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.models.module import Module
from app.models.module_action import ModuleAction
from app.models.role import Role
from app.utils import get_current_company_id, require_company_context, require_permission
from app.utils.constants import STATUS_INACTIVE
from app.utils.audit import set_audit_fields
from app.utils.db_utils import safe_commit
from app.utils.query_helpers import get_active_user_role_mappings, get_active_role_permissions

permissions_bp = Blueprint('permissions', __name__)


def _build_user_permissions(user_id, company_id):
    """Shared helper that builds user permissions list. Returns a list, not a Response."""
    # Step 1: Fetch roles assigned to the user within the company (only active mappings to active roles)
    active_mappings = get_active_user_role_mappings(user_id, company_id)
    role_ids = [ur.role_id for ur in active_mappings]

    # Step 2: Get permissions from roles (company-specific)
    role_permissions = get_active_role_permissions(role_ids, company_id)
    permission_map = {(rp.module_id, rp.action_id): 'role' for rp in role_permissions}

    # Step 3: Apply user-specific overrides (company-specific)
    user_permissions = UserPermissionMapping.query.filter(
        UserPermissionMapping.user_id == user_id,
        UserPermissionMapping.company_id == company_id,
        UserPermissionMapping.status != STATUS_INACTIVE
    ).all()
    for up in user_permissions:
        key = (up.module_id, up.action_id)
        if up.permission_type == 1:
            permission_map[key] = 'user-allow'
        elif up.permission_type == 0:
            permission_map.pop(key, None)

    # Step 4: Pre-load all modules and actions to avoid N+1
    modules_map = {m.id: m for m in Module.query.filter_by(company_id=company_id).all()}
    actions_map = {a.id: a for a in ModuleAction.query.filter_by(company_id=company_id).all()}

    # Step 5: Format for API response
    results = []
    for (module_id, action_id), source in permission_map.items():
        module = modules_map.get(module_id)
        action = actions_map.get(action_id)
        if module and action:
            results.append({
                'module': module.module_name,
                'action': action.action_name,
                'url': action.action_url,
                'source': source,
                'module_id': module.id,
                'action_id': action.id
            })

    return results


@permissions_bp.route('/user', methods=['GET'])
@require_company_context
def get_current_user_permissions():
    """Get permissions for the current authenticated user"""
    from app.utils import get_current_user, is_administrator

    if is_administrator():
        modules = Module.query.filter(Module.status != STATUS_INACTIVE).all()
        results = []
        for m in modules:
            actions = ModuleAction.query.filter(ModuleAction.module_id == m.id, ModuleAction.status != STATUS_INACTIVE).all()
            for a in actions:
                results.append({
                    'module': m.module_name,
                    'action': a.action_name,
                    'url': a.action_url,
                    'source': 'administrator',
                    'module_id': m.id,
                    'action_id': a.id
                })
        return jsonify(results)

    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    company_id = get_current_company_id()
    results = _build_user_permissions(user.id, company_id)
    return jsonify(results)


@permissions_bp.route('/user/<int:user_id>', methods=['GET'])
@require_permission('Permissions', 'view')
def get_user_permissions(user_id):
    from app.utils import is_administrator
    if is_administrator():
        from app.models.user import User
        user = User.query.filter_by(id=user_id).filter(User.status != STATUS_INACTIVE).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        from app.models.user import User
        user = User.query.filter_by(id=user_id, company_id=company_id).filter(User.status != STATUS_INACTIVE).first_or_404()
    results = _build_user_permissions(user_id, company_id)
    return jsonify(results)


@permissions_bp.route('/user/<int:user_id>/roles', methods=['GET'])
@require_permission('Permissions', 'view')
def get_user_roles(user_id):
    from app.utils import is_administrator
    if is_administrator():
        from app.models.user import User
        user = User.query.filter_by(id=user_id).filter(User.status != STATUS_INACTIVE).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        from app.models.user import User
        user = User.query.filter_by(id=user_id, company_id=company_id).filter(User.status != STATUS_INACTIVE).first_or_404()

    user_roles = db.session.query(
        UserRoleMapping,
        Role.role_name.label('role_name')
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id,
        UserRoleMapping.status != STATUS_INACTIVE,
        Role.status != STATUS_INACTIVE
    ).all()

    return jsonify([{
        'role_id': ur.UserRoleMapping.role_id,
        'role_name': ur.role_name,
        'department_id': ur.UserRoleMapping.department_id,
        'status': ur.UserRoleMapping.status
    } for ur in user_roles])


@permissions_bp.route('/modules', methods=['GET'])
@require_permission('Permissions', 'view')
def get_modules_with_actions():
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id')
    
    if is_administrator():
        if filter_company_id:
            try:
                company_id = int(filter_company_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
            modules = Module.query.filter_by(company_id=company_id).all()
        else:
            modules = Module.query.all()
    else:
        company_id = get_current_company_id()
        modules = Module.query.filter_by(company_id=company_id).all()
        
    result = []

    for module in modules:
        actions = ModuleAction.query.filter_by(
            module_id=module.id,
            company_id=module.company_id
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


@permissions_bp.route('/module-actions', methods=['GET'])
@require_permission('Permissions', 'view')
def get_module_actions():
    """Get all modules with their actions - same as /modules but with different endpoint name"""
    return get_modules_with_actions()


@permissions_bp.route('/role/<int:role_id>', methods=['GET'])
@require_permission('Permissions', 'view')
def get_role_permissions(role_id):
    """Get permissions for a specific role"""
    from app.utils import is_administrator
    if is_administrator():
        role = Role.query.filter_by(id=role_id).filter(Role.status != STATUS_INACTIVE).first_or_404()
        company_id = role.company_id
    else:
        company_id = get_current_company_id()
        role = Role.query.filter_by(id=role_id, company_id=company_id).filter(Role.status != STATUS_INACTIVE).first_or_404()

    role_permissions = RolePermissionMapping.query.filter(
        RolePermissionMapping.role_id == role_id,
        RolePermissionMapping.company_id == company_id,
        RolePermissionMapping.status != STATUS_INACTIVE
    ).all()

    # Pre-load modules and actions
    modules_map = {m.id: m for m in Module.query.filter_by(company_id=company_id).all()}
    actions_map = {a.id: a for a in ModuleAction.query.filter_by(company_id=company_id).all()}

    permissions = {}
    for rp in role_permissions:
        module = modules_map.get(rp.module_id)
        action = actions_map.get(rp.action_id)

        if module and action:
            if module.id not in permissions:
                permissions[module.id] = {}
            permissions[module.id][action.id] = True

    return jsonify({
        'role_id': role_id,
        'permissions': permissions
    })


@permissions_bp.route('/role/<int:role_id>', methods=['POST'])
@require_permission('Permissions', 'update')
def update_role_permissions(role_id):
    """Update permissions for a specific role"""
    from app.utils import is_administrator
    if is_administrator():
        role = Role.query.filter_by(id=role_id).first_or_404()
        company_id = role.company_id
    else:
        company_id = get_current_company_id()
        role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
        
    data = request.get_json()

    if not data or 'permissions' not in data:
        return jsonify({'error': 'Missing permissions data'}), 400

    if role.status == STATUS_INACTIVE:
        return jsonify({'error': 'Role is inactive'}), 400

    try:
        permissions_data = data['permissions']
        valid_module_ids = {m.id for m in Module.query.filter_by(company_id=company_id).filter(Module.status != STATUS_INACTIVE).all()}
        valid_action_ids = {a.id for a in ModuleAction.query.filter_by(company_id=company_id).filter(ModuleAction.status != STATUS_INACTIVE).all()}

        # Validate all modules and actions belong to this company before mutating any state
        for module_id_str, actions in permissions_data.items():
            try:
                module_id = int(module_id_str)
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid module_id: {module_id_str}'}), 400
            if module_id not in valid_module_ids:
                return jsonify({'error': f'Module {module_id} not found in this company'}), 404

            for action_id_str, granted in actions.items():
                try:
                    action_id = int(action_id_str)
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid action_id: {action_id_str}'}), 400
                if action_id not in valid_action_ids:
                    return jsonify({'error': f'Module action {action_id} not found in this company'}), 404

        # Delete existing permissions for this role
        RolePermissionMapping.query.filter_by(
            role_id=role_id,
            company_id=company_id
        ).delete()

        # Add new permissions
        for module_id, actions in permissions_data.items():
            for action_id, granted in actions.items():
                if granted:
                    permission = RolePermissionMapping(
                        role_id=role_id,
                        module_id=int(module_id),
                        action_id=int(action_id),
                        company_id=company_id
                    )
                    set_audit_fields(permission, is_create=True)
                    db.session.add(permission)

        return safe_commit(
            (jsonify({'message': 'Role permissions updated successfully'}), 200),
            'Internal server error during role permissions update'
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@permissions_bp.route('/user/<int:user_id>', methods=['POST'])
@require_permission('Permissions', 'update')
def update_user_permissions(user_id):
    """Update permissions for a specific user - only creates overrides that differ from role permissions"""
    from app.utils import is_administrator
    if is_administrator():
        from app.models.user import User
        user = User.query.filter_by(id=user_id).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        from app.models.user import User
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
        
    data = request.get_json()

    if not data or 'permissions' not in data:
        return jsonify({'error': 'Missing permissions data'}), 400

    if user.status == STATUS_INACTIVE:
        return jsonify({'error': 'User is inactive'}), 400

    try:
        permissions_data = data['permissions']
        valid_module_ids = {m.id for m in Module.query.filter_by(company_id=company_id).filter(Module.status != STATUS_INACTIVE).all()}
        valid_action_ids = {a.id for a in ModuleAction.query.filter_by(company_id=company_id).filter(ModuleAction.status != STATUS_INACTIVE).all()}

        # Validate all modules and actions belong to this company before mutating any state
        for module_id_str, actions in permissions_data.items():
            try:
                module_id = int(module_id_str)
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid module_id: {module_id_str}'}), 400
            if module_id not in valid_module_ids:
                return jsonify({'error': f'Module {module_id} not found in this company'}), 404

            for action_id_str, granted in actions.items():
                try:
                    action_id = int(action_id_str)
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid action_id: {action_id_str}'}), 400
                if action_id not in valid_action_ids:
                    return jsonify({'error': f'Module action {action_id} not found in this company'}), 404

        # Step 1: Get role-based permissions using active mappings only
        active_mappings = get_active_user_role_mappings(user_id, company_id)
        role_ids = [ur.role_id for ur in active_mappings]
        role_permissions = get_active_role_permissions(role_ids, company_id)
        role_perm_map = {(rp.module_id, rp.action_id): True for rp in role_permissions}

        # Step 2: Fetch existing active user-specific overrides
        existing_overrides = UserPermissionMapping.query.filter(
            UserPermissionMapping.user_id == user_id,
            UserPermissionMapping.company_id == company_id,
            UserPermissionMapping.status != STATUS_INACTIVE
        ).all()

        # Build a map of existing overrides keyed by (module_id, action_id)
        existing_map = {
            (up.module_id, up.action_id): up
            for up in existing_overrides
        }

        # Step 3: Process incoming permissions — diff against existing overrides
        overrides_added = 0
        overrides_removed = 0
        overrides_unchanged = 0

        # Track which keys are covered by incoming data
        incoming_keys = set()

        for module_id, actions in permissions_data.items():
            for action_id, granted in actions.items():
                module_id_int = int(module_id)
                action_id_int = int(action_id)
                key = (module_id_int, action_id_int)
                incoming_keys.add(key)

                has_from_role = key in role_perm_map
                granted_bool = bool(granted)
                needs_override = granted_bool != has_from_role

                existing = existing_map.get(key)

                if needs_override:
                    permission_type = 1 if granted_bool else 0
                    if existing:
                        if existing.permission_type != permission_type:
                            # Override type changed — update it
                            existing.permission_type = permission_type
                            set_audit_fields(existing, is_create=False)
                            overrides_added += 1
                        else:
                            overrides_unchanged += 1
                    else:
                        # New override needed
                        new_perm = UserPermissionMapping(
                            user_id=user_id,
                            role_id=None,
                            module_id=module_id_int,
                            action_id=action_id_int,
                            permission_type=permission_type,
                            company_id=company_id
                        )
                        set_audit_fields(new_perm, is_create=True)
                        db.session.add(new_perm)
                        overrides_added += 1

                        override_type = "ALLOW" if permission_type == 1 else "DENY"
                        current_app.logger.debug(
                            f"Added {override_type} override: Module {module_id_int}, "
                            f"Action {action_id_int}"
                        )
                else:
                    # No override needed — if one exists, soft-delete it
                    if existing:
                        existing.status = STATUS_INACTIVE
                        set_audit_fields(existing, is_create=False)
                        overrides_removed += 1

        # Step 4: Soft-delete existing overrides for keys NOT in incoming data
        # These are permissions the admin didn't include — treat as remove
        for key, existing in existing_map.items():
            if key not in incoming_keys:
                existing.status = STATUS_INACTIVE
                set_audit_fields(existing, is_create=False)
                overrides_removed += 1

        return safe_commit(
            (jsonify({
                'message': 'User permissions updated successfully',
                'overrides_added': overrides_added,
                'overrides_removed': overrides_removed,
                'overrides_unchanged': overrides_unchanged
            }), 200),
            'Internal server error during user permissions update'
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in update_user_permissions: {e}")
        return jsonify({'error': str(e)}), 500


@permissions_bp.route('/user/<int:user_id>/management', methods=['GET'])
@require_permission('Permissions', 'view')
def get_user_permissions_for_management(user_id):
    """Get user permissions in management format - shows all actions with current effective state"""
    from app.utils import is_administrator
    if is_administrator():
        from app.models.user import User
        user = User.query.filter_by(id=user_id).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        from app.models.user import User
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()

    modules = Module.query.filter_by(company_id=company_id).all()

    # Step 1: Get user's role-based permissions
    active_mappings = get_active_user_role_mappings(user_id, company_id)
    role_ids = [ur.role_id for ur in active_mappings]
    role_permissions = get_active_role_permissions(role_ids, company_id)
    role_perm_map = {(rp.module_id, rp.action_id): True for rp in role_permissions}

    # Step 2: Get user-specific overrides
    user_permissions = UserPermissionMapping.query.filter(
        UserPermissionMapping.user_id == user_id,
        UserPermissionMapping.company_id == company_id,
        UserPermissionMapping.status != STATUS_INACTIVE
    ).all()

    user_overrides = {}
    for up in user_permissions:
        key = (up.module_id, up.action_id)
        if up.permission_type == 1:
            user_overrides[key] = True
        elif up.permission_type == 0:
            user_overrides[key] = False

    # Step 3: Build response with effective permissions
    permissions = {}
    permission_sources = {}

    for module in modules:
        actions = ModuleAction.query.filter_by(
            module_id=module.id,
            company_id=company_id
        ).all()

        if actions:
            permissions[str(module.id)] = {}
            permission_sources[str(module.id)] = {}

            for action in actions:
                key = (module.id, action.id)

                if key in user_overrides:
                    effective_permission = user_overrides[key]
                    source = 'user-override'
                elif key in role_perm_map:
                    effective_permission = True
                    source = 'role'
                else:
                    effective_permission = False
                    source = 'none'

                permissions[str(module.id)][str(action.id)] = effective_permission
                permission_sources[str(module.id)][str(action.id)] = source

    return jsonify({
        'user_id': user_id,
        'permissions': permissions,
        'sources': permission_sources
    })

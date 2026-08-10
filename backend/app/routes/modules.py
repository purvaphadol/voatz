from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import exc, or_
from app.models.module import SystemModule, SystemModuleAction, CompanyModule
from app.models.company import Company
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import get_current_company_id, require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.constants import (
    STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED,
    MSG_PLATFORM_ADMIN_ONLY_MODULE_CREATE,
    MSG_PLATFORM_ADMIN_ONLY_MODULE_UPDATE,
    MSG_PLATFORM_ADMIN_ONLY_MODULE_DELETE
)
from app.utils.validators import validate_module_input

modules_bp = Blueprint('modules', __name__)

@modules_bp.route('/', methods=['GET'])
@require_permission('Modules', 'view')
def list_modules():
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id')
    search = request.args.get('search', '').strip()
    
    if is_administrator():
        if filter_company_id:
            try:
                comp_id = int(filter_company_id)
                query = SystemModule.query.join(
                    CompanyModule, CompanyModule.system_module_id == SystemModule.id
                ).filter(
                    CompanyModule.company_id == comp_id,
                    CompanyModule.status != STATUS_DEACTIVATED,
                    SystemModule.status != STATUS_DEACTIVATED
                )
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
        else:
            query = SystemModule.query.filter(SystemModule.status != STATUS_DEACTIVATED)
    else:
        company_id = get_current_company_id()
        query = SystemModule.query.join(
            CompanyModule, CompanyModule.system_module_id == SystemModule.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.status != STATUS_DEACTIVATED,
            SystemModule.status != STATUS_DEACTIVATED
        )
        
    if search:
        query = query.filter(SystemModule.module_name.ilike(f"%{search}%"))
        
    modules_list = query.order_by(SystemModule.order_index.asc(), SystemModule.module_name.asc()).all()
    
    module_data = []
    for m in modules_list:
        module_data.append({
            'id': m.id, 
            'module_name': m.module_name,
            'description': m.description if m.description else '',
            'icon': m.icon if m.icon else '',
            'route_name': m.route_name if m.route_name else '',
            'display_route': m.display_route,
            'is_active': m.is_active,
            'order_index': m.order_index,
            'status': m.status,
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'updated_at': m.updated_at.isoformat() if m.updated_at else None
        })
    
    return jsonify({
        'data': module_data,
        'total': len(module_data)
    })

@modules_bp.route('/', methods=['POST'])
@require_permission('Modules', 'create')
@audit_action('create_module', module='Modules', description='Created a module')
def create_module():
    from app.utils import is_administrator
    if not is_administrator():
        return jsonify({'error': MSG_PLATFORM_ADMIN_ONLY_MODULE_CREATE}), 403

    data = request.get_json()
    
    cleaned_data, error = validate_module_input(data, is_create=True)
    if error:
        return error
        
    # Duplicate check on module_name
    if SystemModule.query.filter(
        SystemModule.module_name.ilike(cleaned_data['module_name']),
        SystemModule.status != STATUS_DEACTIVATED
    ).first():
        return jsonify({'error': 'Module name already exists'}), 400
        
    # Auto-generate route_name if missing, or auto-suffix if route_name collides with active module
    req_route = cleaned_data.get('route_name')
    if not req_route or not req_route.strip():
        req_route = cleaned_data['module_name'].lower().replace(' ', '')

    base_slug = req_route.strip()
    final_slug = base_slug
    suffix = 2
    while SystemModule.query.filter(
        SystemModule.route_name.ilike(final_slug),
        SystemModule.status != STATUS_DEACTIVATED
    ).first():
        final_slug = f"{base_slug}{suffix}"
        suffix += 1

    cleaned_data['route_name'] = final_slug

    # Auto-suffix legacy soft-deleted modules matching the new module_name or route_name
    legacy_deleted = SystemModule.query.filter(
        or_(
            SystemModule.module_name.ilike(cleaned_data['module_name']),
            SystemModule.route_name.ilike(cleaned_data['route_name'])
        ),
        SystemModule.status == STATUS_DEACTIVATED
    ).all()

    if legacy_deleted:
        import time
        ts = int(time.time())
        for old_m in legacy_deleted:
            old_m.module_name = f"{old_m.module_name}_deleted_{old_m.id}_{ts}"
            if old_m.route_name:
                old_m.route_name = f"{old_m.route_name}_deleted_{old_m.id}_{ts}"
            set_audit_fields(old_m, is_create=False)

    module = SystemModule()
    module.module_name = cleaned_data['module_name']
    module.route_name = cleaned_data.get('route_name')
    module.description = cleaned_data.get('description')
    module.icon = cleaned_data.get('icon')
    module.order_index = cleaned_data.get('order_index', 0)
    module.status = STATUS_ACTIVE
    
    set_audit_fields(module, is_create=True)
    db.session.add(module)
        
    target_company_id = None
    if is_administrator():
        body_company_id = data.get('company_id') if data else None
        if body_company_id:
            try:
                target_company_id = int(body_company_id)
            except (ValueError, TypeError):
                pass
    else:
        target_company_id = get_current_company_id()

    if target_company_id:
        existing_cm = CompanyModule.query.filter_by(
            company_id=target_company_id,
            system_module_id=module.id
        ).first()
        if not existing_cm:
            cm = CompanyModule(company_id=target_company_id, system_module_id=module.id, status=STATUS_ACTIVE)
            set_audit_fields(cm, is_create=True)
            db.session.add(cm)

    response_data = {
        'message': 'Module created',
        'module_id': module.id,
        'display_route': module.display_route
    }
    return safe_commit((jsonify(response_data), 201), 'Internal server error during module creation')

@modules_bp.route('/<int:module_id>', methods=['GET'])
@require_permission('Modules', 'view')
def get_module(module_id):
    m = SystemModule.query.filter(
        SystemModule.id == module_id,
        SystemModule.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    return jsonify({
        'id': m.id, 
        'module_name': m.module_name,
        'description': m.description if m.description else '',
        'icon': m.icon if m.icon else '',
        'route_name': m.route_name if m.route_name else '',
        'display_route': m.display_route,
        'is_active': m.is_active,
        'order_index': m.order_index,
        'status': m.status,
        'created_at': m.created_at.isoformat() if m.created_at else None,
        'updated_at': m.updated_at.isoformat() if m.updated_at else None
    })

@modules_bp.route('/<int:module_id>', methods=['PUT'])
@require_permission('Modules', 'update')
@audit_action('update_module', module='Modules', description='Updated a module', get_target_id=lambda *a, **kw: kw.get('module_id'))
def update_module(module_id):
    from app.utils import is_administrator
    if not is_administrator():
        return jsonify({'error': MSG_PLATFORM_ADMIN_ONLY_MODULE_UPDATE}), 403

    module = SystemModule.query.filter(
        SystemModule.id == module_id,
        SystemModule.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    data = request.get_json()
    
    cleaned_data, error = validate_module_input(data, is_create=False)
    if error:
        return error
        
    if 'module_name' in cleaned_data:
        if SystemModule.query.filter(
            SystemModule.module_name.ilike(cleaned_data['module_name']),
            SystemModule.status != STATUS_DEACTIVATED,
            SystemModule.id != module_id
        ).first():
            return jsonify({'error': 'Module name already exists'}), 400
    target_name = cleaned_data.get('module_name')
    target_route = cleaned_data.get('route_name')

    if target_name or target_route:
        legacy_deleted = SystemModule.query.filter(
            or_(
                SystemModule.module_name.ilike(target_name) if target_name else False,
                SystemModule.route_name.ilike(target_route) if target_route else False
            ),
            SystemModule.status == STATUS_DEACTIVATED,
            SystemModule.id != module_id
        ).all()

        if legacy_deleted:
            import time
            ts = int(time.time())
            for old_m in legacy_deleted:
                old_m.module_name = f"{old_m.module_name}_deleted_{old_m.id}_{ts}"
                if old_m.route_name:
                    old_m.route_name = f"{old_m.route_name}_deleted_{old_m.id}_{ts}"
                set_audit_fields(old_m, is_create=False)

    if 'module_name' in cleaned_data:
        module.module_name = cleaned_data['module_name']
        
    if 'route_name' in cleaned_data:
        module.route_name = cleaned_data['route_name']
        
    if 'description' in cleaned_data:
        module.description = cleaned_data['description']
        
    if 'icon' in cleaned_data:
        module.icon = cleaned_data['icon']
        
    if 'order_index' in cleaned_data:
        module.order_index = cleaned_data['order_index']
        
    if 'status' in cleaned_data:
        if cleaned_data['status'] == STATUS_DEACTIVATED:
            return jsonify({'error': 'Cannot delete module through this endpoint'}), 400
        module.status = cleaned_data['status']
        
    set_audit_fields(module, is_create=False)
        
    response_data = {
        'message': 'Module updated',
        'display_route': module.display_route
    }
    return safe_commit((jsonify(response_data), 200), 'Internal server error during module update')

@modules_bp.route('/<int:module_id>/status', methods=['PATCH'])
@require_permission('Modules', 'update')
def update_module_status(module_id):
    from app.utils import is_administrator
    if not is_administrator():
        return jsonify({'error': MSG_PLATFORM_ADMIN_ONLY_MODULE_UPDATE}), 403

    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status field is required'}), 400
        
    status = data.get('status')
    if status not in (1, 0, 9):
        return jsonify({'error': 'Status must be 1 (active), 0 (inactive), or 9 (deactivated)'}), 400
        
    module = SystemModule.query.filter(
        SystemModule.id == module_id,
        SystemModule.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    module.status = status
    set_audit_fields(module, is_create=False)
    
    return safe_commit((jsonify({'message': 'Module status updated'}), 200), 'Internal server error during module status update')

@modules_bp.route('/<int:module_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
@audit_action('delete_module', module='Modules', description='Deleted a module', get_target_id=lambda *a, **kw: kw.get('module_id'))
def delete_module(module_id):
    from app.utils import is_administrator
    if not is_administrator():
        return jsonify({'error': MSG_PLATFORM_ADMIN_ONLY_MODULE_DELETE}), 403


    module = SystemModule.query.filter(
        SystemModule.id == module_id,
        SystemModule.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    force = request.args.get('force', 'false').lower() == 'true'

    company_mods = CompanyModule.query.filter(
        CompanyModule.system_module_id == module_id,
        CompanyModule.status != STATUS_DEACTIVATED
    ).count()

    role_perms = RolePermissionMapping.query.filter(
        RolePermissionMapping.module_id == module_id,
        RolePermissionMapping.status != STATUS_INACTIVE
    ).count()

    user_perms = UserPermissionMapping.query.filter(
        UserPermissionMapping.module_id == module_id,
        UserPermissionMapping.status != STATUS_INACTIVE
    ).count()

    total_active_deps = company_mods + role_perms + user_perms

    if total_active_deps > 0 and not force:
        parts = []
        if company_mods > 0:
            parts.append(f"{company_mods} provisioned company assignment(s)")
        if role_perms > 0:
            parts.append(f"{role_perms} role permission mapping(s)")
        if user_perms > 0:
            parts.append(f"{user_perms} user permission mapping(s)")

        deps_str = ", ".join(parts)
        user_friendly_error = f"Cannot delete system module: It currently has {deps_str}. Please unassign these items first."

        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'company_modules': company_mods,
                'role_permissions': role_perms,
                'user_permissions': user_perms
            },
            'message': 'Are you sure you want to delete this system module (and unassign all related company and role permissions)?'
        }), 400

    # Force cascade deactivations
    if company_mods > 0:
        cms = CompanyModule.query.filter(CompanyModule.system_module_id == module_id, CompanyModule.status != STATUS_DEACTIVATED).all()
        for cm in cms:
            cm.status = STATUS_DEACTIVATED
            set_audit_fields(cm, is_create=False)

    if role_perms > 0:
        rps = RolePermissionMapping.query.filter(RolePermissionMapping.module_id == module_id, RolePermissionMapping.status != STATUS_INACTIVE).all()
        for rp in rps:
            rp.status = STATUS_INACTIVE
            set_audit_fields(rp, is_create=False)

    if user_perms > 0:
        ups = UserPermissionMapping.query.filter(UserPermissionMapping.module_id == module_id, UserPermissionMapping.status != STATUS_INACTIVE).all()
        for up in ups:
            up.status = STATUS_INACTIVE
            set_audit_fields(up, is_create=False)

    actions = SystemModuleAction.query.filter(
        SystemModuleAction.system_module_id == module_id,
        SystemModuleAction.status != STATUS_DEACTIVATED
    ).all()

    for action in actions:
        action.status = STATUS_DEACTIVATED
        set_audit_fields(action, is_create=False)

    import time
    ts = int(time.time())
    module.status = STATUS_DEACTIVATED
    module.module_name = f"{module.module_name}_deleted_{module.id}_{ts}"
    if module.route_name:
        module.route_name = f"{module.route_name}_deleted_{module.id}_{ts}"
    set_audit_fields(module, is_create=False)

    return safe_commit((jsonify({'message': 'Module deleted successfully'}), 200), 'Internal server error during module deletion')

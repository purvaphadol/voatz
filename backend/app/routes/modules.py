from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import exc
from app.models.module import Module
from app.models.company import Company
from app.models.module_action import ModuleAction
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import get_current_company_id, require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE
from app.utils.query_helpers import get_active_modules_query, get_admin_modules_query
from app.utils.validators import validate_module_input

modules_bp = Blueprint('modules', __name__)

@modules_bp.route('/', methods=['GET'])
@require_permission('Modules', 'view')
def list_modules():
    company_id = get_current_company_id()
    
    query = get_admin_modules_query(company_id)
    
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(Module.module_name.ilike(f"%{search}%"))
        
    modules_list = query.all()
    
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
            'company_id': m.company_id,
            'company_name': m.company.company_name if m.company else '',
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
    company_id = get_current_company_id()
    data = request.get_json()
    
    cleaned_data, error = validate_module_input(data, is_create=True)
    if error:
        return error
        
    # Duplicate check on module_name
    if Module.query.filter(
        Module.module_name.ilike(cleaned_data['module_name']),
        Module.company_id == company_id,
        Module.status != STATUS_INACTIVE
    ).first():
        return jsonify({'error': 'Module name already exists in this company'}), 400
        
    # Duplicate check on route_name
    if cleaned_data.get('route_name'):
        if Module.query.filter(
            Module.route_name.ilike(cleaned_data['route_name']),
            Module.company_id == company_id,
            Module.status != STATUS_INACTIVE
        ).first():
            return jsonify({'error': 'Route name already exists in this company'}), 400
            
    module = Module()
    module.module_name = cleaned_data['module_name']
    module.route_name = cleaned_data.get('route_name')
    module.description = cleaned_data.get('description')
    module.icon = cleaned_data.get('icon')
    module.order_index = cleaned_data.get('order_index', 0)
    module.company_id = company_id
    module.status = STATUS_ACTIVE
    
    set_audit_fields(module, is_create=True)
    
    db.session.add(module)
    try:
        db.session.flush()
    except exc.IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database constraint violation. Ensure unique names.'}), 400
        
    response_data = {
        'message': 'Module created',
        'module_id': module.id,
        'display_route': module.display_route
    }
    return safe_commit((jsonify(response_data), 201), 'Internal server error during module creation')

@modules_bp.route('/<int:module_id>', methods=['GET'])
@require_permission('Modules', 'view')
def get_module(module_id):
    company_id = get_current_company_id()
    m = Module.query.filter(
        Module.id == module_id, 
        Module.company_id == company_id,
        Module.status != STATUS_INACTIVE
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
        'company_id': m.company_id,
        'company_name': m.company.company_name if m.company else '',
        'created_at': m.created_at.isoformat() if m.created_at else None,
        'updated_at': m.updated_at.isoformat() if m.updated_at else None
    })

@modules_bp.route('/<int:module_id>', methods=['PUT'])
@require_permission('Modules', 'update')
@audit_action('update_module', module='Modules', description='Updated a module', get_target_id=lambda *a, **kw: kw.get('module_id'))
def update_module(module_id):
    company_id = get_current_company_id()
    module = Module.query.filter(
        Module.id == module_id, 
        Module.company_id == company_id,
        Module.status != STATUS_INACTIVE
    ).first_or_404()
    
    data = request.get_json()
    
    cleaned_data, error = validate_module_input(data, is_create=False)
    if error:
        return error
        
    if 'module_name' in cleaned_data:
        if Module.query.filter(
            Module.module_name.ilike(cleaned_data['module_name']),
            Module.company_id == company_id,
            Module.status != STATUS_INACTIVE,
            Module.id != module_id
        ).first():
            return jsonify({'error': 'Module name already exists in this company'}), 400
        module.module_name = cleaned_data['module_name']
        
    if 'route_name' in cleaned_data:
        if cleaned_data['route_name']:
            if Module.query.filter(
                Module.route_name.ilike(cleaned_data['route_name']),
                Module.company_id == company_id,
                Module.status != STATUS_INACTIVE,
                Module.id != module_id
            ).first():
                return jsonify({'error': 'Route name already exists in this company'}), 400
        module.route_name = cleaned_data['route_name']
        
    if 'description' in cleaned_data:
        module.description = cleaned_data['description']
        
    if 'icon' in cleaned_data:
        module.icon = cleaned_data['icon']
        
    if 'order_index' in cleaned_data:
        module.order_index = cleaned_data['order_index']
        
    if 'status' in cleaned_data:
        # Prevent soft-delete via PUT
        if cleaned_data['status'] == STATUS_INACTIVE:
            return jsonify({'error': 'Cannot delete module through this endpoint'}), 400
        module.status = cleaned_data['status']
        
    set_audit_fields(module, is_create=False)
    
    try:
        db.session.flush()
    except exc.IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database constraint violation. Ensure unique names.'}), 400
        
    response_data = {
        'message': 'Module updated',
        'display_route': module.display_route
    }
    return safe_commit((jsonify(response_data), 200), 'Internal server error during module update')

@modules_bp.route('/<int:module_id>/status', methods=['PATCH'])
@require_permission('Modules', 'update')
def update_module_status(module_id):
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status field is required'}), 400
        
    status = data.get('status')
    if status not in (1, 9):
        return jsonify({'error': 'Status must be 1 (active) or 9 (deactivated)'}), 400
        
    module = Module.query.filter(
        Module.id == module_id, 
        Module.company_id == company_id,
        Module.status != STATUS_INACTIVE
    ).first_or_404()
    
    module.status = status
    set_audit_fields(module, is_create=False)
    
    return safe_commit((jsonify({'message': 'Module status updated'}), 200), 'Internal server error during module status update')

@modules_bp.route('/<int:module_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
@audit_action('delete_module', module='Modules', description='Deleted a module', get_target_id=lambda *a, **kw: kw.get('module_id'))
def delete_module(module_id):
    company_id = get_current_company_id()
    module = Module.query.filter(
        Module.id == module_id, 
        Module.company_id == company_id,
        Module.status != STATUS_INACTIVE
    ).first_or_404()
    
    # Check active role permissions
    role_perms = RolePermissionMapping.query.filter(
        RolePermissionMapping.module_id == module_id,
        RolePermissionMapping.company_id == company_id,
        RolePermissionMapping.status != STATUS_INACTIVE
    ).count()
    
    # Check active user permissions
    user_perms = UserPermissionMapping.query.filter(
        UserPermissionMapping.module_id == module_id,
        UserPermissionMapping.company_id == company_id,
        UserPermissionMapping.status != STATUS_INACTIVE
    ).count()
    
    if role_perms > 0 or user_perms > 0:
        return jsonify({
            'error': 'Cannot delete module as it is being used in permissions',
            'details': f'Found {role_perms} active role permissions and {user_perms} active user permissions'
        }), 400
        
    # Soft delete module actions
    actions = ModuleAction.query.filter(
        ModuleAction.module_id == module_id,
        ModuleAction.company_id == company_id,
        ModuleAction.status != STATUS_INACTIVE
    ).all()
    
    for action in actions:
        action.status = STATUS_INACTIVE
        set_audit_fields(action, is_create=False)
        
    # Soft delete module
    module.status = STATUS_INACTIVE
    set_audit_fields(module, is_create=False)
    
    return safe_commit((jsonify({'message': 'Module deleted successfully'}), 200), 'Internal server error during module deletion')

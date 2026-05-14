from flask import Blueprint, request, jsonify
from app import db
from app.models.module import Module
from app.models.company import Company
from app.utils import get_current_company_id, require_permission

modules_bp = Blueprint('modules', __name__)

@modules_bp.route('/', methods=['GET'])
@require_permission('Modules', 'view')
def list_modules():
    company_id = get_current_company_id()
    modules = Module.query.join(Company).filter(Module.company_id == company_id).order_by(Module.order_index.asc(), Module.module_name.asc()).all()
    
    # Build module data with all available fields
    module_data = []
    for m in modules:
        module_info = {
            'id': m.id, 
            'module_name': m.module_name,
            'route_name': m.route_name,
            'display_route': m.display_route,
            'is_active': m.is_active,
            'order_index': m.order_index,
            'company_id': m.company_id,
            'company_name': m.company.company_name,
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'updated_at': m.updated_at.isoformat() if m.updated_at else None
        }
        # Add additional fields if the model has them
        if hasattr(m, 'description') and m.description:
            module_info['description'] = m.description
        if hasattr(m, 'icon') and m.icon:
            module_info['icon'] = m.icon
        module_data.append(module_info)
    
    return jsonify({
        'data': module_data,
        'total': len(module_data),
        'page': 1,
        'pages': 1
    })

@modules_bp.route('/', methods=['POST'])
@require_permission('Modules', 'create')
def create_module():
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('module_name'):
        return jsonify({'error': 'Module name is required'}), 400
    
    # Check if module name already exists within the company
    if Module.query.filter_by(module_name=data['module_name'], company_id=company_id).first():
        return jsonify({'error': 'Module name already exists in this company'}), 400
    
    # Check if route name already exists within the company (if provided)
    route_name = data.get('route_name', '').strip()
    if route_name and Module.query.filter_by(route_name=route_name, company_id=company_id).first():
        return jsonify({'error': 'Route name already exists in this company'}), 400
    
    module = Module()
    module.module_name = data['module_name']
    module.route_name = route_name if route_name else None
    module.is_active = data.get('is_active', True)
    module.order_index = data.get('order_index', 0)
    module.company_id = company_id
    db.session.add(module)
    db.session.commit()
    return jsonify({
        'message': 'Module created', 
        'module_id': module.id,
        'display_route': module.display_route
    }), 201

@modules_bp.route('/<int:module_id>', methods=['GET'])
@require_permission('Modules', 'view')
def get_module(module_id):
    company_id = get_current_company_id()
    module = Module.query.join(Company).filter(
        Module.id == module_id, 
        Module.company_id == company_id
    ).first_or_404()
    return jsonify({
        'id': module.id,
        'module_name': module.module_name,
        'route_name': module.route_name,
        'display_route': module.display_route,
        'is_active': module.is_active,
        'order_index': module.order_index,
        'company_id': module.company_id,
        'company_name': module.company.company_name,
        'created_at': module.created_at.isoformat() if module.created_at else None,
        'updated_at': module.updated_at.isoformat() if module.updated_at else None
    })

@modules_bp.route('/<int:module_id>', methods=['PUT'])
@require_permission('Modules', 'update')
def update_module(module_id):
    company_id = get_current_company_id()
    module = Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    if data.get('module_name'):
        # Check if module name already exists within the company (excluding current module)
        existing_module = Module.query.filter_by(
            module_name=data['module_name'], 
            company_id=company_id
        ).first()
        if existing_module and existing_module.id != module_id:
            return jsonify({'error': 'Module name already exists in this company'}), 400
        
        module.module_name = data['module_name']
    
    if 'route_name' in data:
        route_name = data['route_name'].strip() if data['route_name'] else None
        if route_name:
            # Check if route name already exists within the company (excluding current module)
            existing_module = Module.query.filter_by(
                route_name=route_name, 
                company_id=company_id
            ).first()
            if existing_module and existing_module.id != module_id:
                return jsonify({'error': 'Route name already exists in this company'}), 400
        
        module.route_name = route_name
    
    # Update new fields
    if 'is_active' in data:
        module.is_active = data['is_active']
    
    if 'order_index' in data:
        module.order_index = data['order_index']
    
    db.session.commit()
    return jsonify({
        'message': 'Module updated',
        'display_route': module.display_route
    }), 200

@modules_bp.route('/<int:module_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
def delete_module(module_id):
    company_id = get_current_company_id()
    module = Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
    
    # Check if this module is being used in permissions
    from app.models.role_permission import RolePermissionMapping
    from app.models.user_permission import UserPermissionMapping
    from app.models.module_action import ModuleAction
    
    # Count related permissions
    role_perms = RolePermissionMapping.query.filter_by(
        module_id=module_id,
        company_id=company_id
    ).count()
    
    user_perms = UserPermissionMapping.query.filter_by(
        module_id=module_id,
        company_id=company_id
    ).count()
    
    if role_perms > 0 or user_perms > 0:
        return jsonify({
            'error': 'Cannot delete module as it is being used in permissions',
            'details': f'Found {role_perms} role permissions and {user_perms} user permissions'
        }), 400
    
    # Delete related module actions first
    ModuleAction.query.filter_by(
        module_id=module_id,
        company_id=company_id
    ).delete()
    
    # Now delete the module
    db.session.delete(module)
    db.session.commit()
    return jsonify({'message': 'Module deleted successfully'}), 200

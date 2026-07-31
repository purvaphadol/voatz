from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import exc
from app.models.module_action import ModuleAction
from app.models.module import Module
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import get_current_company_id, require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE
from app.utils.query_helpers import get_active_module_actions_query
from app.utils.validators import validate_module_action_input

module_actions_bp = Blueprint('module_actions', __name__)

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['GET'])
@require_permission('Modules', 'view')
def get_module_actions(module_id):
    from app.utils import is_administrator
    if is_administrator():
        Module.query.filter_by(id=module_id).first_or_404()
        actions = ModuleAction.query.filter(
            ModuleAction.module_id == module_id,
            ModuleAction.status == STATUS_ACTIVE
        ).all()
    else:
        company_id = get_current_company_id()
        Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
        actions = get_active_module_actions_query(module_id, company_id).all()
    
    return jsonify({
        'data': [{
            'id': a.id,
            'action_name': a.action_name,
            'action_url': a.action_url,
            'module_id': a.module_id,
            'status': a.status,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'updated_at': a.updated_at.isoformat() if a.updated_at else None
        } for a in actions]
    })

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['POST'])
@require_permission('Modules', 'create')
def create_module_action(module_id):
    from app.utils import is_administrator
    if is_administrator():
        module = Module.query.filter(
            Module.id == module_id,
            Module.status == STATUS_ACTIVE
        ).first_or_404()
        company_id = module.company_id
    else:
        company_id = get_current_company_id()
        module = Module.query.filter(
            Module.id == module_id,
            Module.company_id == company_id,
            Module.status == STATUS_ACTIVE
        ).first_or_404()
    
    data = request.get_json()
    cleaned_data, error = validate_module_action_input(data, is_create=True)
    if error:
        return error
        
    if ModuleAction.query.filter(
        ModuleAction.module_id == module_id,
        ModuleAction.company_id == company_id,
        ModuleAction.action_name.ilike(cleaned_data['action_name']),
        ModuleAction.status != STATUS_INACTIVE
    ).first():
        return jsonify({'error': 'Action name already exists for this module'}), 400
        
    action = ModuleAction()
    action.action_name = cleaned_data['action_name']
    action.action_url = cleaned_data['action_url']
    action.module_id = module_id
    action.company_id = company_id
    action.status = cleaned_data.get('status', STATUS_ACTIVE)
    
    set_audit_fields(action, is_create=True)
    
    db.session.add(action)
    try:
        db.session.flush()
    except exc.IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database constraint violation.'}), 400
        
    return safe_commit({
        'message': 'Module action created successfully',
        'action_id': action.id
    }, 201)

@module_actions_bp.route('/actions/bulk', methods=['POST'])
@require_permission('Modules', 'create')
def create_bulk_module_actions():
    from app.utils import is_administrator
    data = request.get_json()
    
    if not data or not data.get('module_id') or not data.get('actions'):
        return jsonify({'error': 'Module ID and actions array are required'}), 400
        
    module_id = data['module_id']
    actions_data = data['actions']
    
    if is_administrator():
        module = Module.query.filter(
            Module.id == module_id,
            Module.status == STATUS_ACTIVE
        ).first_or_404()
        company_id = module.company_id
    else:
        company_id = get_current_company_id()
        module = Module.query.filter(
            Module.id == module_id,
            Module.company_id == company_id,
            Module.status == STATUS_ACTIVE
        ).first_or_404()
    
    created_actions = []
    skipped_duplicates = []
    errors = []
    
    for action_data in actions_data:
        cleaned_data, error = validate_module_action_input(action_data, is_create=True)
        if error:
            errors.append(f"Invalid input: {error[0].get_json().get('error', 'unknown error')}")
            continue
            
        if ModuleAction.query.filter(
            ModuleAction.module_id == module_id,
            ModuleAction.company_id == company_id,
            ModuleAction.action_name.ilike(cleaned_data['action_name']),
            ModuleAction.status != STATUS_INACTIVE
        ).first():
            skipped_duplicates.append(cleaned_data['action_name'])
            continue
            
        action = ModuleAction()
        action.action_name = cleaned_data['action_name']
        action.action_url = cleaned_data['action_url']
        action.module_id = module_id
        action.company_id = company_id
        action.status = cleaned_data.get('status', STATUS_ACTIVE)
        
        set_audit_fields(action, is_create=True)
        db.session.add(action)
        created_actions.append(cleaned_data['action_name'])
        
    response = {
        'message': f'Created {len(created_actions)} actions successfully',
        'created_actions': created_actions,
        'skipped_duplicates': skipped_duplicates
    }
    
    if errors:
        response['errors'] = errors
        
    return safe_commit(response, 201 if created_actions else 400)

@module_actions_bp.route('/action/<int:action_id>', methods=['PUT'])
@require_permission('Modules', 'update')
def update_module_action(action_id):
    from app.utils import is_administrator
    if is_administrator():
        action = ModuleAction.query.filter(
            ModuleAction.id == action_id,
            ModuleAction.status != STATUS_INACTIVE
        ).first_or_404()
        company_id = action.company_id
    else:
        company_id = get_current_company_id()
        action = ModuleAction.query.filter(
            ModuleAction.id == action_id,
            ModuleAction.company_id == company_id,
            ModuleAction.status != STATUS_INACTIVE
        ).first_or_404()
    
    data = request.get_json()
    cleaned_data, error = validate_module_action_input(data, is_create=False)
    if error:
        return error
        
    if 'action_name' in cleaned_data:
        if ModuleAction.query.filter(
            ModuleAction.module_id == action.module_id,
            ModuleAction.company_id == company_id,
            ModuleAction.action_name.ilike(cleaned_data['action_name']),
            ModuleAction.status != STATUS_INACTIVE,
            ModuleAction.id != action_id
        ).first():
            return jsonify({'error': 'Action name already exists for this module'}), 400
        action.action_name = cleaned_data['action_name']
        
    if 'action_url' in cleaned_data:
        action.action_url = cleaned_data['action_url']
        
    if 'status' in cleaned_data:
        if cleaned_data['status'] == STATUS_INACTIVE:
            return jsonify({'error': 'Cannot delete action through this endpoint'}), 400
        action.status = cleaned_data['status']
        
    set_audit_fields(action, is_create=False)
    
    return safe_commit({'message': 'Module action updated successfully'}, 200)

@module_actions_bp.route('/action/<int:action_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
def delete_module_action(action_id):
    from app.utils import is_administrator
    if is_administrator():
        action = ModuleAction.query.filter(
            ModuleAction.id == action_id,
            ModuleAction.status != STATUS_INACTIVE
        ).first_or_404()
        company_id = action.company_id
    else:
        company_id = get_current_company_id()
        action = ModuleAction.query.filter(
            ModuleAction.id == action_id,
            ModuleAction.company_id == company_id,
            ModuleAction.status != STATUS_INACTIVE
        ).first_or_404()
    
    role_perms = RolePermissionMapping.query.filter(
        RolePermissionMapping.action_id == action_id,
        RolePermissionMapping.company_id == company_id,
        RolePermissionMapping.status != STATUS_INACTIVE
    ).count()
    
    user_perms = UserPermissionMapping.query.filter(
        UserPermissionMapping.action_id == action_id,
        UserPermissionMapping.company_id == company_id,
        UserPermissionMapping.status != STATUS_INACTIVE
    ).count()
    
    if role_perms > 0 or user_perms > 0:
        return jsonify({
            'error': 'Cannot delete action as it is being used in permissions',
            'details': f'Found {role_perms} active role permissions and {user_perms} active user permissions'
        }), 400
        
    action.status = STATUS_INACTIVE
    set_audit_fields(action, is_create=False)
    
    return safe_commit({'message': 'Module action deleted successfully'}, 200)
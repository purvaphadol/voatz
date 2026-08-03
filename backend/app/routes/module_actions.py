from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import exc
from app.models.module import SystemModule, SystemModuleAction
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields
from app.utils.constants import STATUS_ACTIVE, STATUS_INACTIVE, STATUS_DEACTIVATED
from app.utils.validators import validate_module_action_input

module_actions_bp = Blueprint('module_actions', __name__)

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['GET'])
@require_permission('Modules', 'view')
def get_module_actions(module_id):
    SystemModule.query.filter_by(id=module_id).filter(SystemModule.status != STATUS_DEACTIVATED).first_or_404()
    actions = SystemModuleAction.query.filter(
        SystemModuleAction.system_module_id == module_id,
        SystemModuleAction.status != STATUS_DEACTIVATED
    ).all()
    
    return jsonify({
        'data': [{
            'id': a.id,
            'action_name': a.action_name,
            'action_url': a.action_url,
            'module_id': a.system_module_id,
            'status': a.status,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'updated_at': a.updated_at.isoformat() if a.updated_at else None
        } for a in actions]
    })

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['POST'])
@require_permission('Modules', 'create')
def create_module_action(module_id):
    SystemModule.query.filter_by(id=module_id).filter(SystemModule.status != STATUS_DEACTIVATED).first_or_404()
    
    data = request.get_json()
    cleaned_data, error = validate_module_action_input(data, is_create=True)
    if error:
        return error
        
    if SystemModuleAction.query.filter(
        SystemModuleAction.system_module_id == module_id,
        SystemModuleAction.action_name.ilike(cleaned_data['action_name']),
        SystemModuleAction.status != STATUS_DEACTIVATED
    ).first():
        return jsonify({'error': 'Action name already exists for this module'}), 400
        
    action = SystemModuleAction()
    action.action_name = cleaned_data['action_name']
    action.action_url = cleaned_data['action_url']
    action.system_module_id = module_id
    action.status = cleaned_data.get('status', STATUS_ACTIVE)
    
    set_audit_fields(action, is_create=True)
    
    db.session.add(action)
    try:
        db.session.flush()
    except exc.IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Database constraint violation.'}), 400
        
    return safe_commit({
        'message': 'Module action created successfully',
        'action_id': action.id
    }, 201)

@module_actions_bp.route('/actions/bulk', methods=['POST'])
@require_permission('Modules', 'create')
def create_bulk_module_actions():
    data = request.get_json()
    
    if not data or not data.get('module_id') or not data.get('actions'):
        return jsonify({'error': 'Module ID and actions array are required'}), 400
        
    module_id = data['module_id']
    actions_data = data['actions']
    
    SystemModule.query.filter_by(id=module_id).filter(SystemModule.status != STATUS_DEACTIVATED).first_or_404()
    
    created_actions = []
    skipped_duplicates = []
    errors = []
    
    for action_data in actions_data:
        cleaned_data, error = validate_module_action_input(action_data, is_create=True)
        if error:
            errors.append(f"Invalid input: {error[0].get_json().get('error', 'unknown error')}")
            continue
            
        if SystemModuleAction.query.filter(
            SystemModuleAction.system_module_id == module_id,
            SystemModuleAction.action_name.ilike(cleaned_data['action_name']),
            SystemModuleAction.status != STATUS_DEACTIVATED
        ).first():
            skipped_duplicates.append(cleaned_data['action_name'])
            continue
            
        action = SystemModuleAction()
        action.action_name = cleaned_data['action_name']
        action.action_url = cleaned_data['action_url']
        action.system_module_id = module_id
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
    action = SystemModuleAction.query.filter(
        SystemModuleAction.id == action_id,
        SystemModuleAction.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    data = request.get_json()
    cleaned_data, error = validate_module_action_input(data, is_create=False)
    if error:
        return error
        
    if 'action_name' in cleaned_data:
        if SystemModuleAction.query.filter(
            SystemModuleAction.system_module_id == action.system_module_id,
            SystemModuleAction.action_name.ilike(cleaned_data['action_name']),
            SystemModuleAction.status != STATUS_DEACTIVATED,
            SystemModuleAction.id != action_id
        ).first():
            return jsonify({'error': 'Action name already exists for this module'}), 400
        action.action_name = cleaned_data['action_name']
        
    if 'action_url' in cleaned_data:
        action.action_url = cleaned_data['action_url']
        
    if 'status' in cleaned_data:
        if cleaned_data['status'] == STATUS_DEACTIVATED:
            return jsonify({'error': 'Cannot delete action through this endpoint'}), 400
        action.status = cleaned_data['status']
        
    set_audit_fields(action, is_create=False)
    
    return safe_commit({'message': 'Module action updated successfully'}, 200)

@module_actions_bp.route('/action/<int:action_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
def delete_module_action(action_id):
    action = SystemModuleAction.query.filter(
        SystemModuleAction.id == action_id,
        SystemModuleAction.status != STATUS_DEACTIVATED
    ).first_or_404()
    
    role_perms = RolePermissionMapping.query.filter(
        RolePermissionMapping.action_id == action_id,
        RolePermissionMapping.status != STATUS_DEACTIVATED
    ).count()
    
    user_perms = UserPermissionMapping.query.filter(
        UserPermissionMapping.action_id == action_id,
        UserPermissionMapping.status != STATUS_DEACTIVATED
    ).count()
    
    if role_perms > 0 or user_perms > 0:
        return jsonify({
            'error': 'Cannot delete action as it is being used in permissions',
            'details': f'Found {role_perms} active role permissions and {user_perms} active user permissions'
        }), 400
        
    action.status = STATUS_DEACTIVATED
    set_audit_fields(action, is_create=False)
    
    return safe_commit({'message': 'Module action deleted successfully'}, 200)
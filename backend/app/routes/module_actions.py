from flask import Blueprint, request, jsonify
from app import db
from app.models.module_action import ModuleAction
from app.models.module import Module
from app.utils import get_current_company_id, require_permission

module_actions_bp = Blueprint('module_actions', __name__)

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['GET'])
@require_permission('Modules', 'view')
def get_module_actions(module_id):
    """Get all actions for a specific module"""
    company_id = get_current_company_id()
    
    # Verify module belongs to the company
    module = Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
    
    actions = ModuleAction.query.filter_by(
        module_id=module_id,
        company_id=company_id
    ).all()
    
    return jsonify({
        'data': [{
            'id': action.id,
            'action_name': action.action_name,
            'action_url': action.action_url,
            'module_id': action.module_id,
            'status': action.status
        } for action in actions]
    })

@module_actions_bp.route('/module/<int:module_id>/actions', methods=['POST'])
@require_permission('Modules', 'create')
def create_module_action(module_id):
    """Create a new action for a specific module"""
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('action_name') or not data.get('action_url'):
        return jsonify({'error': 'Action name and URL are required'}), 400
    
    # Verify module belongs to the company
    module = Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
    
    # Check if action name already exists for this module
    existing_action = ModuleAction.query.filter_by(
        module_id=module_id,
        action_name=data['action_name'],
        company_id=company_id
    ).first()
    
    if existing_action:
        return jsonify({'error': 'Action name already exists for this module'}), 400
    
    # Create new action
    action = ModuleAction()
    action.action_name = data['action_name']
    action.action_url = data['action_url']
    action.module_id = module_id
    action.company_id = company_id
    action.status = data.get('status', 1)
    
    db.session.add(action)
    db.session.commit()
    
    return jsonify({
        'message': 'Module action created successfully',
        'action_id': action.id
    }), 201

@module_actions_bp.route('/action/<int:action_id>', methods=['PUT'])
@require_permission('Modules', 'update')
def update_module_action(action_id):
    """Update a specific module action"""
    company_id = get_current_company_id()
    data = request.get_json()
    
    action = ModuleAction.query.filter_by(
        id=action_id,
        company_id=company_id
    ).first_or_404()
    
    if data.get('action_name'):
        # Check if action name already exists for this module (excluding current action)
        existing_action = ModuleAction.query.filter_by(
            module_id=action.module_id,
            action_name=data['action_name'],
            company_id=company_id
        ).first()
        
        if existing_action and existing_action.id != action_id:
            return jsonify({'error': 'Action name already exists for this module'}), 400
        
        action.action_name = data['action_name']
    
    if data.get('action_url'):
        action.action_url = data['action_url']
    
    if 'status' in data:
        action.status = data['status']
    
    db.session.commit()
    return jsonify({'message': 'Module action updated successfully'}), 200

@module_actions_bp.route('/action/<int:action_id>', methods=['DELETE'])
@require_permission('Modules', 'delete')
def delete_module_action(action_id):
    """Delete a specific module action"""
    company_id = get_current_company_id()
    
    action = ModuleAction.query.filter_by(
        id=action_id,
        company_id=company_id
    ).first_or_404()
    
    # Check if this action is being used in permissions
    from app.models.role_permission import RolePermissionMapping
    from app.models.user_permission import UserPermissionMapping
    
    role_perms = RolePermissionMapping.query.filter_by(
        action_id=action_id,
        company_id=company_id
    ).count()
    
    user_perms = UserPermissionMapping.query.filter_by(
        action_id=action_id,
        company_id=company_id
    ).count()
    
    if role_perms > 0 or user_perms > 0:
        return jsonify({
            'error': 'Cannot delete action as it is being used in permissions'
        }), 400
    
    db.session.delete(action)
    db.session.commit()
    return jsonify({'message': 'Module action deleted successfully'}), 200

@module_actions_bp.route('/actions/bulk', methods=['POST'])
@require_permission('Modules', 'create')
def create_bulk_module_actions():
    """Create multiple actions for a module at once"""
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('module_id') or not data.get('actions'):
        return jsonify({'error': 'Module ID and actions array are required'}), 400
    
    module_id = data['module_id']
    actions_data = data['actions']
    
    # Verify module belongs to the company
    module = Module.query.filter_by(id=module_id, company_id=company_id).first_or_404()
    
    created_actions = []
    errors = []
    
    for action_data in actions_data:
        if not action_data.get('action_name') or not action_data.get('action_url'):
            errors.append(f"Missing action_name or action_url for one of the actions")
            continue
        
        # Check if action already exists
        existing_action = ModuleAction.query.filter_by(
            module_id=module_id,
            action_name=action_data['action_name'],
            company_id=company_id
        ).first()
        
        if existing_action:
            errors.append(f"Action '{action_data['action_name']}' already exists")
            continue
        
        # Create new action
        action = ModuleAction()
        action.action_name = action_data['action_name']
        action.action_url = action_data['action_url']
        action.module_id = module_id
        action.company_id = company_id
        action.status = action_data.get('status', 1)
        
        db.session.add(action)
        created_actions.append(action_data['action_name'])
    
    if created_actions:
        db.session.commit()
    
    response = {
        'message': f'Created {len(created_actions)} actions successfully',
        'created_actions': created_actions
    }
    
    if errors:
        response['errors'] = errors
    
    return jsonify(response), 201 if created_actions else 400 
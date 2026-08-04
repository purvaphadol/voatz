from flask import Blueprint, request, jsonify
from app import db
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields
from app.utils.constants import STATUS_DEACTIVATED

permissions_crud_bp = Blueprint('permissions_crud', __name__)

@permissions_crud_bp.route('/role', methods=['POST'])
@require_permission('Permissions', 'create')
def assign_role_permission():
    from app.utils import is_administrator, get_current_company_id
    from app.models.role import Role
    from app.models.module import SystemModule, SystemModuleAction
    data = request.get_json()

    # Input validation
    required = ['role_id', 'module_id', 'action_id']
    if is_administrator():
        required.append('company_id')
    missing = [f for f in required if not data or f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if is_administrator():
        company_id = data['company_id']
    else:
        company_id = get_current_company_id()

    # Validate that role, module, and action exist
    role = Role.query.filter_by(id=data['role_id'], company_id=company_id).first()
    if not role:
        return jsonify({'error': 'Role not found in this company'}), 404
        
    module = SystemModule.query.filter_by(id=data['module_id']).filter(SystemModule.status != STATUS_DEACTIVATED).first()
    if not module:
        return jsonify({'error': 'System module not found'}), 404
        
    action = SystemModuleAction.query.filter_by(id=data['action_id'], system_module_id=data['module_id']).filter(SystemModuleAction.status != STATUS_DEACTIVATED).first()
    if not action:
        return jsonify({'error': 'System module action not found'}), 404

    rp = RolePermissionMapping(
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        company_id=company_id
    )
    set_audit_fields(rp, is_create=True)
    db.session.add(rp)
    return safe_commit(
        (jsonify({'message': 'Role permission added'}), 201),
        'Internal server error during role permission creation'
    )

@permissions_crud_bp.route('/user', methods=['POST'])
@require_permission('Permissions', 'create')
def assign_user_permission():
    from app.utils import is_administrator, get_current_company_id
    from app.models.user import User
    from app.models.role import Role
    from app.models.module import SystemModule, SystemModuleAction
    data = request.get_json()

    # Input validation
    required = ['user_id', 'role_id', 'module_id', 'action_id', 'permission_type']
    if is_administrator():
        required.append('company_id')
    missing = [f for f in required if not data or f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if is_administrator():
        company_id = data['company_id']
    else:
        company_id = get_current_company_id()

    # Validate that user, role, module, and action exist
    user = User.query.filter_by(id=data['user_id'], company_id=company_id).filter(User.status != STATUS_DEACTIVATED).first()
    if not user:
        return jsonify({'error': 'User not found in this company'}), 404
        
    role = Role.query.filter_by(id=data['role_id'], company_id=company_id).first()
    if not role:
        return jsonify({'error': 'Role not found in this company'}), 404
        
    module = SystemModule.query.filter_by(id=data['module_id']).filter(SystemModule.status != STATUS_DEACTIVATED).first()
    if not module:
        return jsonify({'error': 'System module not found'}), 404
        
    action = SystemModuleAction.query.filter_by(id=data['action_id'], system_module_id=data['module_id']).filter(SystemModuleAction.status != STATUS_DEACTIVATED).first()
    if not action:
        return jsonify({'error': 'System module action not found'}), 404

    up = UserPermissionMapping(
        user_id=data['user_id'],
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        permission_type=data['permission_type'],
        company_id=company_id
    )
    set_audit_fields(up, is_create=True)
    db.session.add(up)
    return safe_commit(
        (jsonify({'message': 'User permission added'}), 201),
        'Internal server error during user permission creation'
    )

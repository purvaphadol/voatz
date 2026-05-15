from flask import Blueprint, request, jsonify
from app import db
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping
from app.utils import require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields

permissions_crud_bp = Blueprint('permissions_crud', __name__)

@permissions_crud_bp.route('/role', methods=['POST'])
@require_permission('Permissions', 'create')
def assign_role_permission():
    data = request.get_json()

    # Input validation
    required = ['role_id', 'module_id', 'action_id', 'company_id']
    missing = [f for f in required if not data or f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    rp = RolePermissionMapping(
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        company_id=data['company_id']
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
    data = request.get_json()

    # Input validation
    required = ['user_id', 'role_id', 'module_id', 'action_id', 'permission_type', 'company_id']
    missing = [f for f in required if not data or f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    up = UserPermissionMapping(
        user_id=data['user_id'],
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        permission_type=data['permission_type'],
        company_id=data['company_id']
    )
    set_audit_fields(up, is_create=True)
    db.session.add(up)
    return safe_commit(
        (jsonify({'message': 'User permission added'}), 201),
        'Internal server error during user permission creation'
    )

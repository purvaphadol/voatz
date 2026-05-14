from flask import Blueprint, request, jsonify
from app import db
from app.models.role_permission import RolePermissionMapping
from app.models.user_permission import UserPermissionMapping

permissions_crud_bp = Blueprint('permissions_crud', __name__)

@permissions_crud_bp.route('/role', methods=['POST'])
def assign_role_permission():
    data = request.get_json()
    rp = RolePermissionMapping(
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        company_id=data['company_id']
    )
    db.session.add(rp)
    db.session.commit()
    return jsonify({'message': 'Role permission added'}), 201

@permissions_crud_bp.route('/user', methods=['POST'])
def assign_user_permission():
    data = request.get_json()
    up = UserPermissionMapping(
        user_id=data['user_id'],
        role_id=data['role_id'],
        module_id=data['module_id'],
        action_id=data['action_id'],
        permission_type=data['permission_type'],
        company_id=data['company_id']
    )
    db.session.add(up)
    db.session.commit()
    return jsonify({'message': 'User permission added'}), 201

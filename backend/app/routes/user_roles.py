from flask import Blueprint, request, jsonify
from app import db
from app.models.user_role import UserRoleMapping
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.utils import get_current_company_id, require_company_context, require_permission

user_roles_bp = Blueprint('user_roles', __name__)

@user_roles_bp.route('/', methods=['GET'])
@require_permission('UserRoles', 'view')
def list_user_roles():
    """Get all user-role mappings for the current company"""
    company_id = get_current_company_id()
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Query user role mappings with joins
    query = db.session.query(
        UserRoleMapping,
        User.name.label('user_name'),
        User.email.label('user_email'),
        Role.role_name,
        Department.department_name
    ).join(
        User, UserRoleMapping.user_id == User.id
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).join(
        Department, UserRoleMapping.department_id == Department.id
    ).filter(
        UserRoleMapping.company_id == company_id
    )
    
    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    user_roles = pagination.items
    
    return jsonify({
        'data': [{
            'id': ur.UserRoleMapping.id,
            'user_id': ur.UserRoleMapping.user_id,
            'user_name': ur.user_name,
            'user_email': ur.user_email,
            'role_id': ur.UserRoleMapping.role_id,
            'role_name': ur.role_name,
            'department_id': ur.UserRoleMapping.department_id,
            'department_name': ur.department_name,
            'status': ur.UserRoleMapping.status,
            'company_id': ur.UserRoleMapping.company_id
        } for ur in user_roles],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@user_roles_bp.route('/user/<int:user_id>/roles', methods=['GET'])
@require_permission('UserRoles', 'view')
def get_user_roles(user_id):
    company_id = get_current_company_id()
    
    # Verify user belongs to the company
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    
    user_roles = db.session.query(
        UserRoleMapping,
        Role.role_name,
        Department.department_name
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).join(
        Department, UserRoleMapping.department_id == Department.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id
    ).all()
    
    return jsonify([{
        'id': ur.UserRoleMapping.id,
        'role_id': ur.UserRoleMapping.role_id,
        'role_name': ur.role_name,
        'department_id': ur.UserRoleMapping.department_id,
        'department_name': ur.department_name,
        'status': ur.UserRoleMapping.status
    } for ur in user_roles])

@user_roles_bp.route('/user/<int:user_id>/roles', methods=['POST'])
@require_permission('UserRoles', 'create')
def assign_role_to_user(user_id):
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('role_id') or not data.get('department_id'):
        return jsonify({'error': 'Role ID and Department ID are required'}), 400
    
    # Verify user belongs to the company
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    
    # Verify role belongs to the company
    role = Role.query.filter_by(id=data['role_id'], company_id=company_id).first()
    if not role:
        return jsonify({'error': 'Role not found in this company'}), 404
    
    # Verify department belongs to the company
    department = Department.query.filter_by(id=data['department_id'], company_id=company_id).first()
    if not department:
        return jsonify({'error': 'Department not found in this company'}), 404
    
    # Check if mapping already exists
    existing_mapping = UserRoleMapping.query.filter_by(
        user_id=user_id,
        role_id=data['role_id'],
        department_id=data['department_id'],
        company_id=company_id
    ).first()
    
    if existing_mapping:
        return jsonify({'error': 'User already has this role in this department'}), 400
    
    # Create new mapping
    user_role = UserRoleMapping()
    user_role.user_id = user_id
    user_role.role_id = data['role_id']
    user_role.department_id = data['department_id']
    user_role.company_id = company_id
    user_role.status = data.get('status', 1)
    
    
    db.session.add(user_role)
    db.session.commit()
    
    return jsonify({'message': 'Role assigned to user successfully'}), 201

@user_roles_bp.route('/user-role/<int:mapping_id>', methods=['DELETE'])
@require_permission('UserRoles', 'delete')
def remove_role_from_user(mapping_id):
    company_id = get_current_company_id()
    
    user_role = UserRoleMapping.query.filter_by(
        id=mapping_id,
        company_id=company_id
    ).first_or_404()
    
    db.session.delete(user_role)
    db.session.commit()
    
    return jsonify({'message': 'Role removed from user successfully'}), 200

@user_roles_bp.route('/user-role/<int:mapping_id>', methods=['PUT'])
@require_permission('UserRoles', 'update')
def update_user_role(mapping_id):
    company_id = get_current_company_id()
    data = request.get_json()
    
    user_role = UserRoleMapping.query.filter_by(
        id=mapping_id,
        company_id=company_id
    ).first_or_404()
    
    if data.get('status') is not None:
        user_role.status = data['status']
    
    if data.get('department_id'):
        # Verify department belongs to the company
        department = Department.query.filter_by(id=data['department_id'], company_id=company_id).first()
        if not department:
            return jsonify({'error': 'Department not found in this company'}), 404
        user_role.department_id = data['department_id']
    
    db.session.commit()
    return jsonify({'message': 'User role updated successfully'}), 200 
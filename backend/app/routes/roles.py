from flask import Blueprint, request, jsonify
from app import db
from app.models.role import Role
from app.models.department import Department
from app.utils import get_current_company_id, require_company_context
from app.utils.query_helpers import get_active_roles_query

roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/', methods=['GET'])
@require_company_context
def list_roles():
    company_id = get_current_company_id()
    search = request.args.get('search')
    department_id = request.args.get('department_id')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    query = get_active_roles_query(company_id).join(Department)
    
    if search:
        query = query.filter(Role.role_name.ilike(f'%{search}%'))
    
    if department_id:
        query = query.filter(Role.department_id == department_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    roles = pagination.items
    return jsonify({
        'data': [{
            'id': r.id, 
            'role_name': r.role_name, 
            'description': r.description,
            'company_id': r.company_id,
            'department_id': r.department_id,
            'department_name': r.department.department_name,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            'status': r.status if hasattr(r, 'status') else 1
        } for r in roles],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@roles_bp.route('/', methods=['POST'])
@require_company_context
def create_role():
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('role_name') or not data.get('department_id'):
        return jsonify({'error': 'Role name and department_id are required'}), 400
    
    # Verify department belongs to the same company
    department = Department.query.filter_by(
        id=data['department_id'], 
        company_id=company_id
    ).first()
    if not department:
        return jsonify({'error': 'Invalid department for this company'}), 400
    
    # Check if role name already exists within the department
    if Role.query.filter_by(
        role_name=data['role_name'], 
        department_id=data['department_id']
    ).first():
        return jsonify({'error': 'Role name already exists in this department'}), 400
    
    role = Role()
    role.role_name = data['role_name']
    role.description = data.get('description', '')
    role.department_id = data['department_id']
    role.company_id = company_id
    db.session.add(role)
    db.session.commit()
    return jsonify({'message': 'Role created', 'role_id': role.id}), 201

@roles_bp.route('/<int:role_id>', methods=['GET'])
@require_company_context
def get_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.join(Department).filter(
        Role.id == role_id, 
        Role.company_id == company_id
    ).first_or_404()
    return jsonify({
        'id': role.id,
        'role_name': role.role_name,
        'description': role.description,
        'company_id': role.company_id,
        'department_id': role.department_id,
        'department_name': role.department.department_name,
        'created_at': role.created_at.isoformat() if role.created_at else None,
        'updated_at': role.updated_at.isoformat() if role.updated_at else None,
        'status': role.status if hasattr(role, 'status') else 1
    })

@roles_bp.route('/<int:role_id>', methods=['PUT'])
@require_company_context
def update_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    if data.get('department_id'):
        # Verify department belongs to the same company
        department = Department.query.filter_by(
            id=data['department_id'], 
            company_id=company_id
        ).first()
        if not department:
            return jsonify({'error': 'Invalid department for this company'}), 400
        role.department_id = data['department_id']
    
    if data.get('role_name'):
        # Check if role name already exists within the department (excluding current role)
        existing_role = Role.query.filter_by(
            role_name=data['role_name'], 
            department_id=role.department_id
        ).first()
        if existing_role and existing_role.id != role_id:
            return jsonify({'error': 'Role name already exists in this department'}), 400
        
        role.role_name = data['role_name']
    
    if 'description' in data:
        role.description = data['description']
    
    db.session.commit()
    return jsonify({'message': 'Role updated'}), 200

@roles_bp.route('/<int:role_id>', methods=['DELETE'])
@require_company_context
def delete_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    db.session.delete(role)
    db.session.commit()
    return jsonify({'message': 'Role deleted'}), 200

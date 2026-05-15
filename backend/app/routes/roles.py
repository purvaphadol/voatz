# FILE: routes/roles.py
from flask import Blueprint, request, jsonify
from app import db
from app.models.role import Role
from app.models.department import Department
from app.utils import get_current_company_id, require_permission
from app.utils.query_helpers import get_active_roles_query
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination, validate_role_input, validate_department_active
from app.utils.constants import STATUS_INACTIVE

roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/', methods=['GET'])
@require_permission('Roles', 'view')
def list_roles():
    company_id = get_current_company_id()
    search = request.args.get('search')
    department_id = request.args.get('department_id')

    page, per_page, error = parse_pagination(request)
    if error:
        return error

    query = get_active_roles_query(company_id).filter(
        Role.status != STATUS_INACTIVE
    ).outerjoin(Department).order_by(Role.updated_at.desc(), Role.created_at.desc())

    if search:
        query = query.filter(Role.role_name.ilike(f'%{search}%'))

    if department_id:
        try:
            department_id_int = int(department_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid department_id parameter'}), 400
        query = query.filter(Role.department_id == department_id_int)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    roles = pagination.items
    return jsonify({
        'data': [{
            'id': r.id,
            'role_name': r.role_name,
            'description': r.description or '',
            'company_id': r.company_id,
            'department_id': r.department_id,
            'department_name': r.department.department_name if r.department else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            'status': r.status
        } for r in roles],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@roles_bp.route('/', methods=['POST'])
@require_permission('Roles', 'create')
@audit_action('create_role', module='Roles', description='Created a role')
def create_role():
    company_id = get_current_company_id()
    data = request.get_json()

    cleaned_data, error = validate_role_input(data, is_create=True)
    if error:
        return error[0], error[1]

    role_name = cleaned_data['role_name']
    dept_id = data['department_id']

    department = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    dept_error = validate_department_active(department)
    if dept_error:
        return dept_error[0], dept_error[1]

    if Role.query.filter_by(
        role_name=role_name,
        department_id=dept_id
    ).filter(Role.status != STATUS_INACTIVE).first():
        return jsonify({'error': 'Role name already exists in this department'}), 400

    role = Role()
    role.role_name = role_name
    role.description = cleaned_data.get('description', '')
    role.department_id = dept_id
    role.company_id = company_id
    set_audit_fields(role, is_create=True)
    db.session.add(role)
    return safe_commit(
        (jsonify({'message': 'Role created', 'role_id': role.id}), 201),
        'Internal server error during role creation'
    )

@roles_bp.route('/<int:role_id>', methods=['GET'])
@require_permission('Roles', 'view')
def get_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.outerjoin(Department).filter(
        Role.id == role_id,
        Role.company_id == company_id,
        Role.status != STATUS_INACTIVE
    ).first_or_404()
    return jsonify({
        'id': role.id,
        'role_name': role.role_name,
        'description': role.description or '',
        'company_id': role.company_id,
        'department_id': role.department_id,
        'department_name': role.department.department_name if role.department else None,
        'created_at': role.created_at.isoformat() if role.created_at else None,
        'updated_at': role.updated_at.isoformat() if role.updated_at else None,
        'status': role.status
    })

@roles_bp.route('/<int:role_id>', methods=['PUT'])
@require_permission('Roles', 'update')
@audit_action('update_role', module='Roles', description='Updated a role',
              get_target_id=lambda *a, **kw: kw.get('role_id'))
def update_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.filter_by(id=role_id, company_id=company_id).filter(
        Role.status != STATUS_INACTIVE
    ).first_or_404()
    data = request.get_json()

    cleaned_data, error = validate_role_input(data, is_create=False)
    if error:
        return error[0], error[1]

    if 'department_id' in cleaned_data:
        department = Department.query.filter_by(
            id=cleaned_data['department_id'], company_id=company_id
        ).first()
        dept_error = validate_department_active(department)
        if dept_error:
            return dept_error[0], dept_error[1]
        role.department_id = cleaned_data['department_id']

    if 'role_name' in cleaned_data:
        existing_role = Role.query.filter_by(
            role_name=cleaned_data['role_name'],
            department_id=role.department_id
        ).filter(Role.status != STATUS_INACTIVE).first()
        if existing_role and existing_role.id != role_id:
            return jsonify({'error': 'Role name already exists in this department'}), 400
        role.role_name = cleaned_data['role_name']

    if 'description' in cleaned_data:
        role.description = cleaned_data['description']

    set_audit_fields(role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Role updated'}), 200),
        'Internal server error during role update'
    )

@roles_bp.route('/<int:role_id>', methods=['DELETE'])
@require_permission('Roles', 'delete')
@audit_action('delete_role', module='Roles', description='Deleted a role',
              get_target_id=lambda *a, **kw: kw.get('role_id'))
def delete_role(role_id):
    company_id = get_current_company_id()
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()

    if role.role_name.lower() == 'super admin':
        return jsonify({'error': 'Super Admin role cannot be deleted'}), 403

    role.status = STATUS_INACTIVE
    set_audit_fields(role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Role deleted'}), 200),
        'Internal server error during role deletion'
    )

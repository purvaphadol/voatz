from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from app import db
from app.models.user_role import UserRoleMapping
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.company import Company
from app.utils import get_current_company_id, require_permission
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED

user_roles_bp = Blueprint('user_roles', __name__)

# ---------------------------------------------------------------------------
# Allowed values for the ``?status=`` query-string filter on list endpoints.
# STATUS_DEACTIVATED records are *never* returned regardless of filter value.
# ---------------------------------------------------------------------------
_STATUS_FILTER_MAP = {
    'active': [STATUS_ACTIVE],
    'inactive': [STATUS_INACTIVE],
    'all': [STATUS_ACTIVE, STATUS_INACTIVE],
}

@user_roles_bp.route('/', methods=['GET'])
@require_permission('UserRoles', 'view')
def list_user_roles():
    """Get all user-role mappings for the current company.

    Supports ``?status=active|inactive|all`` (default ``active``).
    STATUS_DEACTIVATED records are never returned.
    """
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id')

    page, per_page, error = parse_pagination(request)
    if error:
        return error

    # --- status filter ---
    status_param = request.args.get('status', 'active').lower()
    if status_param not in _STATUS_FILTER_MAP:
        return jsonify({'error': 'Invalid status filter'}), 400
    allowed = _STATUS_FILTER_MAP[status_param]

    query = db.session.query(
        UserRoleMapping,
        User.name.label('user_name'),
        User.email.label('user_email'),
        Role.role_name,
        Department.department_name,
        Company.company_name
    ).join(
        User, UserRoleMapping.user_id == User.id
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).outerjoin(
        Department, UserRoleMapping.department_id == Department.id
    ).outerjoin(
        Company, UserRoleMapping.company_id == Company.id
    ).filter(
        UserRoleMapping.status.in_(allowed),
        UserRoleMapping.status != STATUS_DEACTIVATED,
        User.status != STATUS_DEACTIVATED,
        Role.status != STATUS_DEACTIVATED,
    )

    if is_administrator():
        if filter_company_id:
            try:
                query = query.filter(UserRoleMapping.company_id == int(filter_company_id))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
    else:
        company_id = get_current_company_id()
        query = query.filter(UserRoleMapping.company_id == company_id)

    # Apply search and filter params
    search = request.args.get('search', '').strip()
    filter_user_id = request.args.get('user_id')
    filter_role_id = request.args.get('role_id')
    filter_department_id = request.args.get('department_id')

    if search:
        query = query.filter(
            or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        )
    if filter_user_id:
        try:
            query = query.filter(UserRoleMapping.user_id == int(filter_user_id))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user_id parameter'}), 400
    if filter_role_id:
        try:
            query = query.filter(UserRoleMapping.role_id == int(filter_role_id))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid role_id parameter'}), 400
    if filter_department_id:
        try:
            query = query.filter(UserRoleMapping.department_id == int(filter_department_id))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid department_id parameter'}), 400

    query = query.order_by(UserRoleMapping.updated_at.desc(), UserRoleMapping.created_at.desc())

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
            'company_id': ur.UserRoleMapping.company_id,
            'company_name': ur.company_name
        } for ur in user_roles],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@user_roles_bp.route('/user/<int:user_id>/roles', methods=['GET'])
@require_permission('UserRoles', 'view')
def get_user_roles(user_id):
    """Get roles for a specific user.  STATUS_DEACTIVATED records are never returned."""
    from app.utils import is_administrator
    if is_administrator():
        user = User.query.filter_by(id=user_id).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()

    user_roles = db.session.query(
        UserRoleMapping,
        Role.role_name,
        Department.department_name
    ).join(
        Role, UserRoleMapping.role_id == Role.id
    ).outerjoin(
        Department, UserRoleMapping.department_id == Department.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id,
        UserRoleMapping.status != STATUS_INACTIVE,
        UserRoleMapping.status != STATUS_DEACTIVATED,
        Role.status != STATUS_INACTIVE,
        Role.status != STATUS_DEACTIVATED,
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
@audit_action('assign_role', module='UserRoles', description='Assigned role to user')
def assign_role_to_user(user_id):
    from app.utils import is_administrator
    data = request.get_json()

    if not data or not data.get('role_id'):
        return jsonify({'error': 'Role ID is required'}), 400

    if is_administrator():
        user = User.query.filter_by(id=user_id).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()

    role = Role.query.filter_by(id=data['role_id'], company_id=company_id).first()
    if not role:
        return jsonify({'error': 'Role not found in this company'}), 404

    if role.is_super_admin and not is_administrator():
        return jsonify({'error': 'The Company Super Admin role cannot be assigned via API'}), 403

    dept_id = data.get('department_id')
    if not role.is_super_admin:
        if not dept_id:
            return jsonify({'error': 'Department ID is required for non-super admin roles'}), 400
        department = Department.query.filter_by(id=dept_id, company_id=company_id).first()
        if not department:
            return jsonify({'error': 'Department not found in this company'}), 404

    existing_mapping = UserRoleMapping.query.filter_by(
        user_id=user_id,
        role_id=data['role_id'],
        department_id=dept_id,
        company_id=company_id
    ).filter(UserRoleMapping.status != STATUS_INACTIVE).first()

    if existing_mapping:
        return jsonify({'error': 'User already has this role'}), 400

    user_role = UserRoleMapping()
    user_role.user_id = user_id
    user_role.role_id = data['role_id']
    user_role.department_id = dept_id
    user_role.company_id = company_id
    user_role.status = data.get('status', 1)

    set_audit_fields(user_role, is_create=True)
    db.session.add(user_role)
    return safe_commit(
        (jsonify({'message': 'Role assigned to user successfully'}), 201),
        'Internal server error during role assignment'
    )

@user_roles_bp.route('/user-role/<int:mapping_id>', methods=['DELETE'])
@require_permission('UserRoles', 'delete')
@audit_action('remove_role', module='UserRoles', description='Removed role from user',
              get_target_id=lambda *a, **kw: kw.get('mapping_id'))
def remove_role_from_user(mapping_id):
    from app.utils import is_administrator
    if is_administrator():
        user_role = UserRoleMapping.query.filter_by(
            id=mapping_id
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        user_role = UserRoleMapping.query.filter_by(
            id=mapping_id,
            company_id=company_id
        ).first_or_404()

    user_role.status = STATUS_INACTIVE
    set_audit_fields(user_role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Role removed from user successfully'}), 200),
        'Internal server error during role removal'
    )

@user_roles_bp.route('/user-role/<int:mapping_id>', methods=['PUT'])
@require_permission('UserRoles', 'update')
@audit_action('update_user_role', module='UserRoles', description='Updated user role',
              get_target_id=lambda *a, **kw: kw.get('mapping_id'))
def update_user_role(mapping_id):
    from app.utils import is_administrator
    company_id = get_current_company_id()
    data = request.get_json()

    if is_administrator():
        user_role = UserRoleMapping.query.filter_by(
            id=mapping_id
        ).first_or_404()
        company_id = user_role.company_id
    else:
        company_id = get_current_company_id()
        user_role = UserRoleMapping.query.filter_by(
            id=mapping_id,
            company_id=company_id
        ).first_or_404()

    if data.get('status') is not None:
        user_role.status = data['status']

    if data.get('department_id'):
        department = Department.query.filter_by(id=data['department_id'], company_id=company_id).first()
        if not department:
            return jsonify({'error': 'Department not found in this company'}), 404
        user_role.department_id = data['department_id']

    set_audit_fields(user_role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'User role updated successfully'}), 200),
        'Internal server error during user role update'
    )
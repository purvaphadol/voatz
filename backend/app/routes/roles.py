# FILE: routes/roles.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.role import Role
from app.models.department import Department
from app.utils import get_current_company_id, require_permission, is_administrator
from app.utils.query_helpers import get_active_roles_query
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination, validate_role_input, validate_department_active
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED

roles_bp = Blueprint('roles', __name__)

# ---------------------------------------------------------------------------
# Allowed values for the ``?status=`` query-string filter on list endpoints.
# STATUS_DEACTIVATED records are *never* returned regardless of filter value.
# ---------------------------------------------------------------------------
_STATUS_FILTER_MAP = {
    'active': [STATUS_ACTIVE],
    'inactive': [STATUS_INACTIVE],
    'all': [STATUS_ACTIVE, STATUS_INACTIVE],
}

@roles_bp.route('/', methods=['GET'])
@require_permission('Roles', 'view')
def list_roles():
    """List roles.

    Platform Administrators see roles across all companies (optionally
    filtered by ``company_id``). Regular users see only their own company.

    Supports ``?status=active|inactive|all`` (default ``active``).
    STATUS_DEACTIVATED records are never returned.
    """
    search = request.args.get('search')
    department_id = request.args.get('department_id')
    filter_company_id = request.args.get('company_id')

    page, per_page, error = parse_pagination(request)
    if error:
        return error

    # --- status filter ---
    status_param = request.args.get('status', 'active').lower()
    if status_param not in _STATUS_FILTER_MAP:
        return jsonify({'error': 'Invalid status filter'}), 400
    allowed = _STATUS_FILTER_MAP[status_param]

    if is_administrator():
        # Administrator: query across all companies
        query = Role.query.filter(
            Role.status.in_(allowed),
            Role.status != STATUS_DEACTIVATED,
        ).outerjoin(Department)

        if filter_company_id:
            try:
                query = query.filter(Role.company_id == int(filter_company_id))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
    else:
        # Regular user: scoped to own company only
        company_id = get_current_company_id()
        query = Role.query.filter(
            Role.company_id == company_id,
            Role.status.in_(allowed),
            Role.status != STATUS_DEACTIVATED,
        ).outerjoin(Department)

    query = query.order_by(Role.updated_at.desc(), Role.created_at.desc())

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
            'company_name': r.company.company_name if r.company else None,
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
    data = request.get_json()

    # Resolve company_id:
    # - Administrators carry no company context in their JWT, so they must
    #   supply an explicit company_id in the request body (same pattern as
    #   create_user and create_department).
    # - Regular company users are always scoped to their session company;
    #   any company_id in the body is silently ignored to prevent cross-tenant
    #   overrides (same cross-tenant protection as create_user).
    if is_administrator():
        body_company_id = data.get('company_id') if data else None
        if not body_company_id:
            return jsonify({
                'error': 'company_id is required for platform Administrators'
            }), 400
        try:
            company_id = int(body_company_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid company_id format'}), 400
    else:
        company_id = get_current_company_id()

    cleaned_data, error = validate_role_input(data, is_create=True)
    if error:
        return error[0], error[1]

    role_name = cleaned_data['role_name']
    dept_id = data.get('department_id') if data and data.get('department_id') else None
    is_super_admin = bool(data.get('is_super_admin', False))

    if dept_id:
        department = Department.query.filter_by(id=dept_id, company_id=company_id).first()
        dept_error = validate_department_active(department)
        if dept_error:
            return dept_error[0], dept_error[1]

    existing_query = Role.query.filter(
        Role.role_name.ilike(role_name),
        Role.company_id == company_id,
        Role.status == STATUS_ACTIVE
    )
    if dept_id:
        existing_query = existing_query.filter(Role.department_id == dept_id)
    else:
        existing_query = existing_query.filter(Role.department_id.is_(None))

    if existing_query.first():
        return jsonify({'error': 'Role name already exists'}), 400

    role = Role()
    role.role_name = role_name
    role.description = cleaned_data.get('description', '')
    role.department_id = dept_id
    role.company_id = company_id
    role.is_super_admin = is_super_admin
    set_audit_fields(role, is_create=True)
    db.session.add(role)
    db.session.flush()  # populate role.id before building the response
    return safe_commit(
        (jsonify({'message': 'Role created', 'role_id': role.id}), 201),
        'Internal server error during role creation'
    )

@roles_bp.route('/<int:role_id>', methods=['GET'])
@require_permission('Roles', 'view')
def get_role(role_id):
    """Retrieve a single role by ID.

    Regular users may only view roles in their company. Platform
    Administrators may view any role. STATUS_DEACTIVATED records are
    never returned.
    """
    if is_administrator():
        role = Role.query.filter_by(id=role_id).filter(
            Role.status != STATUS_INACTIVE
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        role = Role.query.filter_by(id=role_id, company_id=company_id).filter(
            Role.status != STATUS_INACTIVE
        ).first_or_404()

    return jsonify({
        'id': role.id,
        'role_name': role.role_name,
        'description': role.description or '',
        'company_id': role.company_id,
        'company_name': role.company.company_name if role.company else None,
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
    """Update a role's attributes.

    If the role is the protected Company Super Admin (``is_super_admin=True``),
    only ``description`` may be changed — renaming it or moving it to a
    different department is rejected with a 403.
    """
    if is_administrator():
        role = Role.query.filter_by(id=role_id).filter(
            Role.status != STATUS_INACTIVE
        ).first_or_404()
        company_id = role.company_id
    else:
        company_id = get_current_company_id()
        role = Role.query.filter_by(id=role_id, company_id=company_id).filter(
            Role.status != STATUS_INACTIVE
        ).first_or_404()
    data = request.get_json()

    cleaned_data, error = validate_role_input(data, is_create=False)
    if error:
        return error[0], error[1]

    # Guard: the protected Company Super Admin role cannot be renamed or
    # moved to a different department.
    if role.is_super_admin:
        new_name = cleaned_data.get('role_name')
        if new_name and new_name.strip().lower() != role.role_name.lower():
            return jsonify({
                'error': 'The Company Super Admin role cannot be renamed '
                         'or reassigned to a different department'
            }), 403

        if 'department_id' in data and data['department_id'] is not None and data['department_id'] != '':
            try:
                dept_val = int(data['department_id'])
            except (ValueError, TypeError):
                dept_val = None
            if dept_val != role.department_id:
                return jsonify({
                    'error': 'The Company Super Admin role cannot be renamed '
                             'or reassigned to a different department'
                }), 403

    # Calculate target department_id
    if 'department_id' in data:
        dept_id_val = data['department_id'] if data['department_id'] else None
        if dept_id_val:
            try:
                dept_id_val = int(dept_id_val)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid department_id format'}), 400
            department = Department.query.filter_by(
                id=dept_id_val, company_id=company_id
            ).first()
            dept_error = validate_department_active(department)
            if dept_error:
                return dept_error[0], dept_error[1]
            target_dept_id = dept_id_val
        else:
            target_dept_id = None
    else:
        target_dept_id = role.department_id

    target_role_name = cleaned_data.get('role_name', role.role_name)

    # Check for duplicate role name in the target department/company
    existing_query = Role.query.filter(
        Role.role_name.ilike(target_role_name),
        Role.company_id == company_id,
        Role.status != STATUS_INACTIVE,
        Role.id != role_id
    )
    if target_dept_id:
        existing_query = existing_query.filter(Role.department_id == target_dept_id)
    else:
        existing_query = existing_query.filter(Role.department_id.is_(None))

    if existing_query.first():
        return jsonify({'error': 'Role name already exists'}), 400

    # Apply modifications
    if 'department_id' in data:
        role.department_id = target_dept_id
    if 'role_name' in cleaned_data:
        role.role_name = cleaned_data['role_name']
    if 'description' in cleaned_data:
        role.description = cleaned_data['description']

    set_audit_fields(role, is_create=False)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Role name already exists in this department'}), 400

    return safe_commit(
        (jsonify({'message': 'Role updated'}), 200),
        'Internal server error during role update'
    )

@roles_bp.route('/<int:role_id>', methods=['DELETE'])
@require_permission('Roles', 'delete')
@audit_action('delete_role', module='Roles', description='Deleted a role',
              get_target_id=lambda *a, **kw: kw.get('role_id'))
def delete_role(role_id):
    if is_administrator():
        role = Role.query.filter_by(id=role_id).filter(Role.status != STATUS_INACTIVE).first_or_404()
    else:
        company_id = get_current_company_id()
        role = Role.query.filter_by(id=role_id, company_id=company_id).filter(Role.status != STATUS_INACTIVE).first_or_404()

    if role.is_super_admin:
        return jsonify({'error': 'The Company Super Admin role cannot be deleted'}), 403

    force = request.args.get('force', 'false').lower() == 'true'

    from app.models.user_role import UserRoleMapping
    from app.models.role_permission import RolePermissionMapping

    assigned_users = UserRoleMapping.query.filter_by(
        role_id=role_id,
        company_id=role.company_id
    ).filter(UserRoleMapping.status != STATUS_INACTIVE).count()

    if assigned_users > 0 and not force:
        user_friendly_error = f"Cannot delete role: It currently has {assigned_users} active user assignment(s). Please reassign these users first."
        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'assigned_users': assigned_users
            },
            'message': 'Are you sure you want to delete this role (and deactivate all related user role mappings)?'
        }), 400

    # Deactivate active user role mappings for this role
    active_mappings = UserRoleMapping.query.filter_by(
        role_id=role_id,
        company_id=role.company_id
    ).filter(UserRoleMapping.status != STATUS_INACTIVE).all()

    for m in active_mappings:
        m.status = STATUS_INACTIVE
        set_audit_fields(m, is_create=False)

    # Deactivate active role permission mappings for this role
    active_perms = RolePermissionMapping.query.filter_by(
        role_id=role_id,
        company_id=role.company_id
    ).filter(RolePermissionMapping.status != STATUS_INACTIVE).all()

    for p in active_perms:
        p.status = STATUS_INACTIVE
        set_audit_fields(p, is_create=False)

    role.status = STATUS_INACTIVE
    set_audit_fields(role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Role deleted successfully'}), 200),
        'Internal server error during role deletion'
    )


@roles_bp.route('/<int:role_id>/permanent', methods=['DELETE'])
@require_permission('Roles', 'delete')
@audit_action('permanent_delete_role', module='Roles',
              description='Permanently deleted a role',
              get_target_id=lambda *a, **kw: kw.get('role_id'))
def permanent_delete_role(role_id):
    """Permanently delete a role (set status to STATUS_DEACTIVATED).

    Platform Administrators only.  The role must already be soft-deleted
    (STATUS_INACTIVE) before it can be permanently deleted.  The protected
    Company Super Admin role can never be permanently deleted.
    """
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can permanently delete roles'}), 403

    role = Role.query.filter_by(id=role_id).first()
    if not role or role.status == STATUS_DEACTIVATED:
        return jsonify({'error': 'Role not found'}), 404

    if role.is_super_admin:
        return jsonify({'error': 'The Company Super Admin role cannot be permanently deleted'}), 403

    if role.status != STATUS_INACTIVE:
        return jsonify({'error': 'Deactivate this record before permanently deleting it'}), 400

    role.status = STATUS_DEACTIVATED
    set_audit_fields(role, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Role permanently deleted'}), 200),
        'Internal server error during permanent role deletion'
    )

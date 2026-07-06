from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.department import Department
from app.models.company import Company
from app.utils import get_current_company_id, require_permission, \
    is_administrator, is_company_super_admin
from app.utils.query_helpers import get_active_departments_query
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination, validate_department_input
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED

departments_bp = Blueprint('departments', __name__)

# ---------------------------------------------------------------------------
# Allowed values for the ``?status=`` query-string filter on list endpoints.
# STATUS_DEACTIVATED records are *never* returned regardless of filter value.
# ---------------------------------------------------------------------------
_STATUS_FILTER_MAP = {
    'active': [STATUS_ACTIVE],
    'inactive': [STATUS_INACTIVE],
    'all': [STATUS_ACTIVE, STATUS_INACTIVE],
}


@departments_bp.route('/', methods=['GET'])
@require_permission('Departments', 'view')
def list_departments():
    """List departments.

    Company Super Admins see departments across all companies (optionally
    filtered by ``company_id``).  Regular users see only their own company.

    Supports ``?status=active|inactive|all`` (default ``active``).
    STATUS_DEACTIVATED records are never returned.
    """
    search = request.args.get('search')
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
        # Super Admin: query across all companies, optionally filtered
        query = Department.query.filter(
            Department.status.in_(allowed),
            Department.status != STATUS_DEACTIVATED,
        ).outerjoin(Company)

        if filter_company_id:
            try:
                query = query.filter(
                    Department.company_id == int(filter_company_id)
                )
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
    else:
        # Regular user & Company Super Admin: scoped to own company only
        company_id = get_current_company_id()
        query = Department.query.join(Company).filter(
            Department.company_id == company_id,
            Department.status.in_(allowed),
            Department.status != STATUS_DEACTIVATED,
            Company.status == STATUS_ACTIVE,
        )

    if search:
        query = query.filter(
            Department.department_name.ilike(f'%{search}%')
        )

    query = query.order_by(
        Department.updated_at.desc(), Department.created_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    departments = pagination.items

    return jsonify({
        'data': [{
            'id': d.id,
            'department_name': d.department_name,
            'description': d.description or '',
            'company_id': d.company_id,
            'company_name': d.company.company_name if d.company else None,
            'created_at': d.created_at.isoformat() if d.created_at else None,
            'updated_at': d.updated_at.isoformat() if d.updated_at else None,
            'status': d.status
        } for d in departments],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })


@departments_bp.route('/', methods=['POST'])
@require_permission('Departments', 'create')
@audit_action('create_department', module='Departments',
              description='Created a department')
def create_department():
    data = request.get_json()

    # Super Admin can create for any company via request body
    # Regular users always use their JWT company
    if is_administrator():
        body_company_id = data.get('company_id') if data else None
        if body_company_id:
            try:
                company_id = int(body_company_id)
                # Verify the target company exists
                from app.models.company import Company as CompanyModel
                target_company = CompanyModel.query.filter_by(
                    id=company_id
                ).first()
                if not target_company:
                    return jsonify({'error': 'Company not found or inactive'}), 404
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id'}), 400
        else:
            company_id = get_current_company_id()
    else:
        company_id = get_current_company_id()

    cleaned_data, error = validate_department_input(data, is_create=True)
    if error:
        return error[0], error[1]

    cleaned_name = cleaned_data['department_name']

    # Duplicate check excluding soft-deleted records
    if Department.query.filter(
        Department.department_name.ilike(cleaned_name),
        Department.company_id == company_id
    ).filter(Department.status != STATUS_INACTIVE).first():
        return jsonify({'error': 'Department name already exists in this company'}), 400

    department = Department()
    department.department_name = cleaned_name
    department.description = cleaned_data.get('description', '')
    department.company_id = company_id
    set_audit_fields(department, is_create=True)
    db.session.add(department)
    try:
        db.session.flush()  # catch constraint violations before commit
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Department name already exists in this company'}), 400
    return safe_commit(
        (jsonify({'message': 'Department created', 'department_id': department.id}), 201),
        'Internal server error during department creation'
    )


@departments_bp.route('/<int:department_id>', methods=['GET'])
@require_permission('Departments', 'view')
def get_department(department_id):
    """Retrieve a single department.  STATUS_DEACTIVATED records are never returned."""
    if is_administrator():
        department = Department.query.outerjoin(Company).filter(
            Department.id == department_id,
            Department.status != STATUS_INACTIVE,
            Department.status != STATUS_DEACTIVATED,
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        department = Department.query.outerjoin(Company).filter(
            Department.id == department_id,
            Department.company_id == company_id,
            Department.status != STATUS_INACTIVE,
            Department.status != STATUS_DEACTIVATED,
        ).first_or_404()
    return jsonify({
        'id': department.id,
        'department_name': department.department_name,
        'description': department.description or '',
        'company_id': department.company_id,
        'company_name': department.company.company_name if department.company else None,
        'created_at': department.created_at.isoformat() if department.created_at else None,
        'updated_at': department.updated_at.isoformat() if department.updated_at else None,
        'status': department.status
    })


@departments_bp.route('/<int:department_id>', methods=['PUT'])
@require_permission('Departments', 'update')
@audit_action('update_department', module='Departments',
              description='Updated a department',
              get_target_id=lambda *a, **kw: kw.get('department_id'))
def update_department(department_id):
    if is_administrator():
        department = Department.query.filter(
            Department.id == department_id,
            Department.status != STATUS_INACTIVE
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        department = Department.query.filter_by(
            id=department_id, company_id=company_id
        ).filter(Department.status != STATUS_INACTIVE).first_or_404()
    
    # Needs to extract company_id from department for duplication checks
    company_id = department.company_id
    
    data = request.get_json()

    cleaned_data, error = validate_department_input(data, is_create=False)
    if error:
        return error[0], error[1]

    if 'department_name' in cleaned_data:
        existing = Department.query.filter(
            Department.department_name.ilike(cleaned_data['department_name']),
            Department.company_id == company_id
        ).filter(Department.status != STATUS_INACTIVE).first()
        if existing and existing.id != department_id:
            return jsonify({'error': 'Department name already exists in this company'}), 400
        department.department_name = cleaned_data['department_name']

    if 'description' in cleaned_data:
        department.description = cleaned_data['description']

    set_audit_fields(department, is_create=False)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Department name already exists in this company'}), 400
    return safe_commit(
        (jsonify({'message': 'Department updated'}), 200),
        'Internal server error during department update'
    )


@departments_bp.route('/<int:department_id>', methods=['DELETE'])
@require_permission('Departments', 'delete')
@audit_action('delete_department', module='Departments',
              description='Deleted a department',
              get_target_id=lambda *a, **kw: kw.get('department_id'))
def delete_department(department_id):
    if is_administrator():
        department = Department.query.filter(
            Department.id == department_id,
            Department.status != STATUS_INACTIVE
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        department = Department.query.filter_by(
            id=department_id, company_id=company_id
        ).filter(Department.status != STATUS_INACTIVE).first_or_404()

    # Check for active roles before deleting
    from app.models.role import Role
    active_roles = Role.query.filter(
        Role.department_id == department_id,
        Role.status != STATUS_INACTIVE
    ).count()
    if active_roles > 0:
        return jsonify({
            'error': f'Cannot delete department with {active_roles} '
                     f'active role(s). Delete or reassign roles first.'
        }), 400

    # Soft delete
    department.status = STATUS_INACTIVE
    set_audit_fields(department, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Department deleted'}), 200),
        'Internal server error during department deletion'
    )


@departments_bp.route('/<int:department_id>/permanent', methods=['DELETE'])
@require_permission('Departments', 'delete')
@audit_action('permanent_delete_department', module='Departments',
              description='Permanently deleted a department',
              get_target_id=lambda *a, **kw: kw.get('department_id'))
def permanent_delete_department(department_id):
    """Permanently delete a department (set status to STATUS_DEACTIVATED).

    Platform Administrators only.  The department must already be soft-deleted
    (STATUS_INACTIVE) before it can be permanently deleted.
    """
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can permanently delete departments'}), 403

    department = Department.query.filter_by(id=department_id).first()
    if not department or department.status == STATUS_DEACTIVATED:
        return jsonify({'error': 'Department not found'}), 404

    if department.status != STATUS_INACTIVE:
        return jsonify({'error': 'Deactivate this record before permanently deleting it'}), 400

    department.status = STATUS_DEACTIVATED
    set_audit_fields(department, is_create=False)
    return safe_commit(
        (jsonify({'message': 'Department permanently deleted'}), 200),
        'Internal server error during permanent department deletion'
    )

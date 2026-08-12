from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models.company import Company
from app.models.user import User
from app.utils import (
    require_permission, get_current_company_id,
    is_administrator, require_same_company_or_administrator,
)
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination, validate_company_input
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED
from app.utils.query_helpers import get_active_companies_query

companies_bp = Blueprint('companies', __name__)

# ---------------------------------------------------------------------------
# Allowed values for the ``?status=`` query-string filter on list endpoints.
# STATUS_DEACTIVATED records are *never* returned regardless of filter value.
# ---------------------------------------------------------------------------
_STATUS_FILTER_MAP = {
    'active': [STATUS_ACTIVE],
    'inactive': [STATUS_INACTIVE],
    'all': [STATUS_ACTIVE, STATUS_INACTIVE],
}


def _serialize_company(c):
    return {
        'id': c.id,
        'company_name': c.company_name,
        'description': c.description or '',
        'email': c.email or '',
        'phone': c.phone or '',
        'website': c.website or '',
        'address': c.address or '',
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        'status': c.status
    }

@companies_bp.route('/', methods=['GET'])
@require_permission('Companies', 'view')
def list_companies():
    """List companies visible to the current user.

    Platform Administrators see every company (with pagination, search, and
    an optional ``?status=active|inactive|all`` filter).  All other users
    see only their own company.

    STATUS_DEACTIVATED records are never returned regardless of filter.
    """
    if is_administrator():
        # --- status filter ---
        show_inactive_raw = request.args.get('show_inactive')
        status_param = request.args.get('status', '').lower()
        if status_param == 'all':
            allowed = [STATUS_ACTIVE, STATUS_INACTIVE]
        elif show_inactive_raw is not None and show_inactive_raw.lower() == 'true':
            allowed = [STATUS_INACTIVE]
        elif status_param == 'inactive':
            allowed = [STATUS_INACTIVE]
        elif status_param in _STATUS_FILTER_MAP:
            allowed = _STATUS_FILTER_MAP[status_param]
        else:
            allowed = [STATUS_ACTIVE]

        query = Company.query.filter(
            Company.status.in_(allowed),
            Company.status != STATUS_DEACTIVATED,
        )

        search = request.args.get('search', '').strip()
        if search:
            query = query.filter(Company.company_name.ilike(f'%{search}%'))
            
        query = query.order_by(Company.updated_at.desc(), Company.created_at.desc())
        
        page, per_page, error = parse_pagination(request)
        if error:
            return error
            
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'data': [_serialize_company(c) for c in paginated.items],
            'total': paginated.total,
            'page': paginated.page,
            'pages': paginated.pages
        })
    else:
        company_id = get_current_company_id()
        company = Company.query.filter_by(id=company_id).filter(
            Company.status == STATUS_ACTIVE,
        ).first()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
            
        return jsonify({
            'data': [_serialize_company(company)],
            'total': 1,
            'page': 1,
            'pages': 1
        })

@companies_bp.route('/', methods=['POST'])
@require_permission('Companies', 'create')
@audit_action('create_company', module='Companies', description='Created a company')
def create_company():
    """Create a new company.  Platform Administrators only."""
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can create companies'}), 403
        
    data = request.get_json()
    cleaned_data, error = validate_company_input(data, is_create=True)
    if error:
        return error[0], error[1]
        
    # Case-insensitive check for active vs inactive collisions
    inactive_existing = Company.query.filter(
        Company.company_name.ilike(cleaned_data['company_name']),
        Company.status == STATUS_INACTIVE
    ).first()

    if inactive_existing:
        return jsonify({
            'error': 'An inactive company with this name already exists.',
            'existing_id': inactive_existing.id,
            'can_reactivate': True
        }), 409

    active_existing = Company.query.filter(
        Company.company_name.ilike(cleaned_data['company_name']),
        Company.status == STATUS_ACTIVE
    ).first()

    if active_existing:
        return jsonify({'error': 'Company name already exists'}), 400

    company = Company()
    for key, value in cleaned_data.items():
        setattr(company, key, value)
    set_audit_fields(company, is_create=True)
    db.session.add(company)
    
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during company create flush: {str(e)}")
        return jsonify({'error': f'Failed to create company: {str(e)}'}), 400

    # Provision specified SystemModules for the company (or empty if none specified)
    from app.models.module import SystemModule, CompanyModule
    system_module_ids = data.get('system_module_ids') if data else None
    
    if system_module_ids and isinstance(system_module_ids, list) and len(system_module_ids) > 0:
        target_sys_mods = SystemModule.query.filter(SystemModule.id.in_(system_module_ids), SystemModule.status == STATUS_ACTIVE).all()
    else:
        target_sys_mods = []

    for sys_mod in target_sys_mods:
        existing_cm = CompanyModule.query.filter_by(company_id=company.id, system_module_id=sys_mod.id).first()



        if existing_cm:
            existing_cm.status = STATUS_ACTIVE
            set_audit_fields(existing_cm, is_create=False)
        else:
            comp_mod = CompanyModule()
            comp_mod.company_id = company.id
            comp_mod.system_module_id = sys_mod.id
            comp_mod.status = STATUS_ACTIVE
            set_audit_fields(comp_mod, is_create=True)
            db.session.add(comp_mod)

    # Automatically provision protected Company Super Admin role
    from app.models.role import Role
    existing_root_role = Role.query.filter_by(company_id=company.id, is_super_admin=True).first()
    if not existing_root_role:
        root_role = Role()
        root_role.role_name = "Company Super Admin"
        root_role.company_id = company.id
        root_role.department_id = None
        root_role.is_super_admin = True
        root_role.status = STATUS_ACTIVE
        root_role.description = "Protected Company Super Admin role"
        set_audit_fields(root_role, is_create=True)
        db.session.add(root_role)
        
    return safe_commit(
        (jsonify({'message': 'Company created', 'company_id': company.id}), 201),
        'Internal server error during company creation'
    )

@companies_bp.route('/<int:company_id>', methods=['GET'])
@require_permission('Companies', 'view')
def get_company(company_id):
    """Retrieve a single company.

    Users may only view their own company unless they are a platform
    Administrator.  STATUS_DEACTIVATED records are never returned.
    """
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(
        Company.status != STATUS_DEACTIVATED,
    ).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    return jsonify(_serialize_company(company))

@companies_bp.route('/<int:company_id>/status_dependents', methods=['GET'])
@require_permission('Companies', 'view')
def get_company_status_dependents(company_id):
    """Retrieve dependent counts for status transitions (Inactive or Reactivate)."""
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied

    company = Company.query.filter_by(id=company_id).filter(
        Company.status != STATUS_DEACTIVATED
    ).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    from app.utils.cascade import count_dependents, count_reactivatable_dependents
    dep_data = count_dependents('Company', company_id)
    react_data = count_reactivatable_dependents('Company', company_id)

    return jsonify({
        'company_id': company_id,
        'current_status': company.status,
        'deactivate_dependents': dep_data,
        'reactivate_dependents': react_data
    })

@companies_bp.route('/<int:company_id>', methods=['PUT'])
@require_permission('Companies', 'update')
@audit_action('update_company', module='Companies', description='Updated a company', get_target_id=lambda *a, **kw: kw.get('company_id'))
def update_company(company_id):
    """Update company details and handle status transitions."""
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(
        Company.status != STATUS_DEACTIVATED,
    ).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    data = request.get_json() or {}
    cleaned_data, error = validate_company_input(data, is_create=False)
    if error:
        return error[0], error[1]
        
    if 'company_name' in cleaned_data:
        existing = Company.query.filter(
            Company.company_name.ilike(cleaned_data['company_name']),
            Company.status == STATUS_ACTIVE,
            Company.id != company_id
        ).first()
        if existing:
            return jsonify({'error': 'Company name already exists'}), 400

    # Status transition logic
    old_status = company.status
    new_status = data.get('status', old_status)

    from app.utils.cascade import cascade_set_inactive, cascade_reactivate
    reactivate_summary = None

    if old_status != new_status:
        if new_status == STATUS_INACTIVE:
            company.status = STATUS_INACTIVE
            cascade_set_inactive('Company', company_id)
        elif new_status == STATUS_ACTIVE:
            company.status = STATUS_ACTIVE
            reactivate_summary = cascade_reactivate('Company', company_id)

    for key, value in cleaned_data.items():
        setattr(company, key, value)
        
    set_audit_fields(company, is_create=False)
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during company update flush: {str(e)}")
        return jsonify({'error': f'Failed to update company: {str(e)}'}), 400
        
    response_data = {'message': 'Company updated'}
    if reactivate_summary:
        response_data['reactivate_summary'] = reactivate_summary

    return safe_commit(
        (jsonify(response_data), 200),
        'Internal server error during company update'
    )

@companies_bp.route('/<int:company_id>', methods=['DELETE'])
@require_permission('Companies', 'delete')
@audit_action('delete_company', module='Companies', description='Deleted a company', get_target_id=lambda *a, **kw: kw.get('company_id'))
def delete_company(company_id):
    """Soft-delete a company.  Platform Administrators only.

    Defense-in-depth: even after the Administrator check, we explicitly
    verify the caller's own company matches the target unless the caller
    is an Administrator (prevents bugs in future permission changes from
    silently widening the blast radius).
    """
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can delete companies'}), 403

    # Defense-in-depth: non-administrators must target their own company
    # (already blocked above, but kept as an explicit second gate).
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(
        Company.status != STATUS_DEACTIVATED,
    ).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    force = request.args.get('force', 'false').lower() == 'true'
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'

    from app.models.department import Department
    from app.models.role import Role
    from app.models.election import Election
    from app.models.voter import Voter
    from app.models.module import CompanyModule

    active_users = User.query.filter(User.company_id == company_id, User.status != STATUS_INACTIVE, User.status != STATUS_DEACTIVATED).count()
    active_departments = Department.query.filter(Department.company_id == company_id, Department.status != STATUS_INACTIVE, Department.status != STATUS_DEACTIVATED).count()
    active_roles = Role.query.filter(Role.company_id == company_id, Role.status != STATUS_INACTIVE, Role.status != STATUS_DEACTIVATED).count()
    active_elections = Election.query.filter(Election.company_id == company_id, Election.status != 'cancelled').count()
    active_voters = Voter.query.filter(Voter.company_id == company_id, Voter.status != STATUS_INACTIVE, Voter.status != STATUS_DEACTIVATED).count()

    total_active_deps = active_users + active_departments + active_roles + active_elections + active_voters

    if total_active_deps > 0 and not force:
        parts = []
        if active_users > 0:
            parts.append(f"{active_users} active user(s)")
        if active_departments > 0:
            parts.append(f"{active_departments} active department(s)")
        if active_roles > 0:
            parts.append(f"{active_roles} active role(s)")
        if active_elections > 0:
            parts.append(f"{active_elections} active election(s)")
        if active_voters > 0:
            parts.append(f"{active_voters} active voter(s)")

        deps_str = ", ".join(parts)
        user_friendly_error = f"Cannot delete company: It currently has {deps_str}. Please deactivate these items first."

        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'users': active_users,
                'departments': active_departments,
                'roles': active_roles,
                'elections': active_elections,
                'voters': active_voters
            },
            'message': 'Are you sure you want to delete this company (and all related user, department, role, election, and voter data)?'
        }), 400

    if dry_run:
        return jsonify({'message': 'Pre-flight check passed', 'can_delete': True}), 200

    # Cascade deletion across all associated entities
    import time
    ts = int(time.time())

    associated_users = User.query.filter(User.company_id == company_id, User.status != STATUS_DEACTIVATED).all()
    for u in associated_users:
        u.status = STATUS_DEACTIVATED
        if "_deleted_" not in u.email:
            u.email = f"{u.email}_deleted_{u.id}_{ts}"
        set_audit_fields(u, is_create=False)

    associated_depts = Department.query.filter(Department.company_id == company_id, Department.status != STATUS_DEACTIVATED).all()
    for d in associated_depts:
        d.status = STATUS_DEACTIVATED
        if "_deleted_" not in d.department_name:
            d.department_name = f"{d.department_name}_deleted_{d.id}_{ts}"
        set_audit_fields(d, is_create=False)

    associated_roles = Role.query.filter(Role.company_id == company_id, Role.status != STATUS_DEACTIVATED).all()
    for r in associated_roles:
        r.status = STATUS_DEACTIVATED
        if "_deleted_" not in r.role_name:
            r.role_name = f"{r.role_name}_deleted_{r.id}_{ts}"
        set_audit_fields(r, is_create=False)

    associated_cms = CompanyModule.query.filter(CompanyModule.company_id == company_id, CompanyModule.status != STATUS_DEACTIVATED).all()
    for cm in associated_cms:
        cm.status = STATUS_DEACTIVATED
        set_audit_fields(cm, is_create=False)

    associated_elections = Election.query.filter(Election.company_id == company_id, Election.status != 'cancelled').all()
    for el in associated_elections:
        el.status = 'cancelled'
        if "_deleted_" not in el.title:
            el.title = f"{el.title}_deleted_{el.id}_{ts}"
        if el.election_code and "_deleted_" not in el.election_code:
            el.election_code = f"{el.election_code}_deleted_{el.id}_{ts}"
        set_audit_fields(el, is_create=False)

    associated_voters = Voter.query.filter(Voter.company_id == company_id, Voter.status != STATUS_DEACTIVATED).all()
    for v in associated_voters:
        v.status = STATUS_DEACTIVATED
        if v.voter_id and "_deleted_" not in v.voter_id:
            v.voter_id = f"{v.voter_id}_deleted_{v.id}_{ts}"
        if v.phone_number and "_deleted_" not in v.phone_number:
            v.phone_number = f"{v.phone_number}_deleted_{v.id}_{ts}"
        set_audit_fields(v, is_create=False)

    company.status = STATUS_DEACTIVATED
    if "_deleted_" not in company.company_name:
        company.company_name = f"{company.company_name}_deleted_{company.id}_{ts}"
    set_audit_fields(company, is_create=False)

    return safe_commit(
        (jsonify({'message': 'Company deleted successfully'}), 200),
        'Internal server error during company deletion'
    )


# ---------------------------------------------------------------------------
# Company Module Provisioning Endpoints (Issue A5 / ISSUE-3.7)
# ---------------------------------------------------------------------------

@companies_bp.route('/<int:company_id>/modules', methods=['GET'])
@require_permission('Companies', 'view')
def get_company_modules(company_id):
    """List provisioned system modules for a company."""
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied

    from app.models.module import CompanyModule, SystemModule
    company = Company.query.filter_by(id=company_id).filter(Company.status == STATUS_ACTIVE).first_or_404()

    provisioned = db.session.query(
        CompanyModule,
        SystemModule.module_name,
        SystemModule.route_name,
        SystemModule.description,
        SystemModule.icon
    ).join(
        SystemModule, CompanyModule.system_module_id == SystemModule.id
    ).filter(
        CompanyModule.company_id == company_id,
        CompanyModule.status == STATUS_ACTIVE,
        SystemModule.status == STATUS_ACTIVE
    ).all()

    return jsonify({
        'data': [{
            'id': p.CompanyModule.id,
            'company_id': p.CompanyModule.company_id,
            'system_module_id': p.CompanyModule.system_module_id,
            'module_name': p.module_name,
            'route_name': p.route_name,
            'description': p.description or '',
            'icon': p.icon,
            'created_at': p.CompanyModule.created_at.isoformat() if p.CompanyModule.created_at else None
        } for p in provisioned]
    })


@companies_bp.route('/<int:company_id>/modules', methods=['POST'])
@require_permission('Companies', 'update')
@audit_action('provision_company_module', module='Companies', description='Provisioned modules to company',
              get_target_id=lambda *a, **kw: kw.get('company_id'))
def provision_company_modules(company_id):
    """Provision module(s) to a company. Platform Administrators only."""
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can provision modules'}), 403

    company = Company.query.filter_by(id=company_id).filter(Company.status == STATUS_ACTIVE).first_or_404()
    data = request.get_json()

    if not data or not data.get('module_ids') or not isinstance(data.get('module_ids'), list):
        return jsonify({'error': 'module_ids array is required'}), 400

    from app.models.module import SystemModule, CompanyModule
    module_ids = [int(m) for m in data['module_ids'] if isinstance(m, (int, str)) and str(m).isdigit()]

    system_modules = SystemModule.query.filter(
        SystemModule.id.in_(module_ids),
        SystemModule.status == STATUS_ACTIVE
    ).all()

    provisioned_count = 0
    for sys_mod in system_modules:
        cm = CompanyModule.query.filter_by(
            company_id=company_id,
            system_module_id=sys_mod.id
        ).first()


        if cm:
            if cm.status != STATUS_ACTIVE:
                cm.status = STATUS_ACTIVE
                set_audit_fields(cm, is_create=False)
                provisioned_count += 1
        else:
            comp_mod = CompanyModule()
            comp_mod.company_id = company_id
            comp_mod.system_module_id = sys_mod.id
            comp_mod.status = STATUS_ACTIVE
            set_audit_fields(comp_mod, is_create=True)
            db.session.add(comp_mod)
            provisioned_count += 1

    return safe_commit(
        (jsonify({'message': f'Successfully provisioned {provisioned_count} module(s)', 'company_id': company_id}), 200),
        'Failed to provision modules'
    )


@companies_bp.route('/<int:company_id>/modules/<int:module_id>', methods=['DELETE'])
@require_permission('Companies', 'update')
@audit_action('deprovision_company_module', module='Companies', description='Deprovisioned module from company',
              get_target_id=lambda *a, **kw: kw.get('company_id'))
def deprovision_company_module(company_id, module_id):
    """Deprovision a single module from a company. Platform Administrators only."""
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can deprovision modules'}), 403

    from app.models.module import CompanyModule
    cm = CompanyModule.query.filter_by(
        company_id=company_id,
        system_module_id=module_id
    ).filter(CompanyModule.status == STATUS_ACTIVE).first_or_404()

    cm.status = STATUS_DEACTIVATED
    set_audit_fields(cm, is_create=False)

    return safe_commit(
        (jsonify({'message': 'Module deprovisioned successfully'}), 200),
        'Failed to deprovision module'
    )


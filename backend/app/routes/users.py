from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.company import Company
from app.models.role import Role
from app.utils import get_current_company_id, require_company_context, require_permission, is_administrator
from app.utils.audit import audit_action, set_audit_fields
from app.models.department import Department
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from datetime import datetime

from app.utils.validators import (
    validate_user_input,
    validate_password,
    validate_department,
    parse_pagination
)
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED
from app.utils.db_utils import safe_commit
from app.utils.query_helpers import get_active_users_query

users_bp = Blueprint('users', __name__)

# ---------------------------------------------------------------------------
# Allowed values for the ``?status=`` query-string filter on list endpoints.
# STATUS_DEACTIVATED records are *never* returned regardless of filter value.
# ---------------------------------------------------------------------------
_STATUS_FILTER_MAP = {
    'active': [STATUS_ACTIVE],
    'inactive': [STATUS_INACTIVE],
    'all': [STATUS_ACTIVE, STATUS_INACTIVE],
}

@users_bp.route('/', methods=['GET'])
@require_permission('Users', 'view')
def list_users():
    """List users.

    Platform Administrators see users across all companies (optionally
    filtered by ``company_id``). Regular users see only their own company.

    Supports ``?status=active|inactive|all`` (default ``active``).
    STATUS_DEACTIVATED records are never returned.
    """
    search = request.args.get('search')
    filter_company_id = request.args.get('company_id')
    filter_department_id = request.args.get('department_id')
    
    page, per_page, error = parse_pagination(request)
    if error:
        return error[0], error[1]

    # --- status filter ---
    status_param = request.args.get('status', 'active').lower()
    if status_param not in _STATUS_FILTER_MAP:
        return jsonify({'error': 'Invalid status filter'}), 400
    allowed = _STATUS_FILTER_MAP[status_param]

    if is_administrator():
        # Administrator: query across all companies
        query = User.query.filter(
            User.status.in_(allowed),
            User.status != STATUS_DEACTIVATED,
        ).join(Company).options(
            joinedload(User.company), 
            joinedload(User.department)
        ).filter(Company.status == STATUS_ACTIVE)

        if filter_company_id:
            try:
                query = query.filter(User.company_id == int(filter_company_id))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid company_id parameter'}), 400
    else:
        # Regular user: scoped to own company only
        company_id = get_current_company_id()
        query = User.query.filter(
            User.company_id == company_id,
            User.status.in_(allowed),
            User.status != STATUS_DEACTIVATED,
        ).join(Company).options(
            joinedload(User.company), 
            joinedload(User.department)
        ).filter(Company.status == STATUS_ACTIVE)

    if filter_department_id:
        try:
            query = query.filter(User.department_id == int(filter_department_id))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid department_id parameter'}), 400

    query = query.order_by(User.updated_at.desc(), User.created_at.desc())

    if search:
        query = query.filter(or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%')))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return jsonify({
        'data': [{
            'id': u.id, 
            'name': u.name, 
            'email': u.email, 
            'company_id': u.company_id,
            'company_name': u.company.company_name,
            'department_id': u.department_id,
            'department_name': u.department.department_name if u.department else None,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'updated_at': u.updated_at.isoformat() if u.updated_at else None,
            'status': u.status
        } for u in users],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@users_bp.route('/', methods=['POST'])
@require_permission('Users', 'create')
@audit_action('create_user', module='Users', description='Created a new user')
def create_user():
    data = request.get_json()
    
    if is_administrator():
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id is required for platform Administrators'}), 400
        try:
            company_id = int(company_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid company_id format'}), 400
            
        company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
        if not company:
            return jsonify({'error': 'Company not found or inactive'}), 404
    else:
        company_id = get_current_company_id()
    
    cleaned_data, error = validate_user_input(data, is_create=True)
    if error:
        return error[0], error[1]
        
    pwd_error = validate_password(data.get('password'))
    if pwd_error:
        return pwd_error[0], pwd_error[1]
        
    dept_id, dept_error = validate_department(data.get('department_id'), company_id)
    if dept_error:
        return dept_error[0], dept_error[1]
    
    email = cleaned_data['email']
    name = cleaned_data['name']
    
    # Check if email already exists within active users in the company
    if User.query.filter_by(email=email, company_id=company_id).filter(User.status == STATUS_ACTIVE).first():
        return jsonify({'error': 'Email already exists in this company'}), 400
    
    user = User()
    user.name = name
    user.email = email
    user.password_hash = generate_password_hash(data['password'])
    user.company_id = company_id
    user.department_id = dept_id
    user.status = STATUS_ACTIVE
    
    db.session.add(user)
    set_audit_fields(user, is_create=True)
    db.session.flush()
    return safe_commit(
        (jsonify({'message': 'User created', 'user_id': user.id}), 201),
        'Internal server error during user creation'
    )

@users_bp.route('/<int:user_id>', methods=['GET'])
@require_permission('Users', 'view')
def get_user(user_id):
    """Retrieve a single user.  STATUS_DEACTIVATED records are never returned."""
    if is_administrator():
        user = User.query.join(Company).filter(
            User.id == user_id, 
            User.status != STATUS_INACTIVE,
            User.status != STATUS_DEACTIVATED,
            Company.status != STATUS_INACTIVE
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        user = User.query.join(Company).filter(
            User.id == user_id, 
            User.company_id == company_id,
            User.status != STATUS_INACTIVE,
            User.status != STATUS_DEACTIVATED,
            Company.status != STATUS_INACTIVE
        ).first_or_404()
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': user.company.company_name,
        'department_id': user.department_id,
        'department_name': user.department.department_name if user.department else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'status': user.status
    })

@users_bp.route('/<int:user_id>', methods=['PUT'])
@require_permission('Users', 'update')
@audit_action('update_user', module='Users', description='Updated a user', get_target_id=lambda *args, **kwargs: kwargs.get('user_id'))
def update_user(user_id):
    if is_administrator():
        user = User.query.filter_by(id=user_id).filter(User.status != STATUS_INACTIVE).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        user = User.query.filter_by(id=user_id, company_id=company_id).filter(User.status != STATUS_INACTIVE).first_or_404()
    data = request.get_json()
    
    cleaned_data, error = validate_user_input(data, is_create=False)
    if error:
        return error[0], error[1]
        
    if data.get('password'):
        pwd_error = validate_password(data.get('password'))
        if pwd_error:
            return pwd_error[0], pwd_error[1]
            
    if 'department_id' in data:
        dept_id, dept_error = validate_department(data.get('department_id'), company_id)
        if dept_error:
            return dept_error[0], dept_error[1]
    
    if 'name' in cleaned_data:
        user.name = cleaned_data['name']
        
    if 'email' in cleaned_data:
        email = cleaned_data['email']
        # Check if email already exists within active users in the same company (excluding current user)
        existing_user = User.query.filter(
            User.email.ilike(email),
            User.company_id == company_id,
            User.status == STATUS_ACTIVE,
            User.id != user_id
        ).first()
        if existing_user:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = email
        
    if data.get('password'):
        user.password_hash = generate_password_hash(data['password'])
        
    if 'department_id' in data:
        user.department_id = dept_id
        
    if data.get('status') is not None:
        try:
            status_val = int(data['status'])
            if status_val in (0, 1):
                user.status = status_val
        except (ValueError, TypeError):
            pass
        
    set_audit_fields(user, is_create=False)
    
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during user update flush: {str(e)}")
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 400

    return safe_commit((jsonify({'message': 'User updated'}), 200), 'Internal server error during user update')

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_permission('Users', 'delete')
@audit_action('delete_user', module='Users', description='Deleted a user', get_target_id=lambda *args, **kwargs: kwargs.get('user_id'))
def delete_user(user_id):
    """Soft-delete a user by setting status to inactive.

    The self-delete guard is skipped for platform Administrators because
    an Administrator is not a User row — they cannot be "deleting
    themselves" via this endpoint.
    """
    # Self-delete guard — before any DB queries.
    # Administrators are not User rows, so this check is irrelevant for them.
    if not is_administrator():
        current_user_id = int(get_jwt_identity())
        if current_user_id == user_id:
            return jsonify({"error": "You cannot delete your own account"}), 403

    if is_administrator():
        user = User.query.filter_by(id=user_id).filter(User.status != STATUS_INACTIVE).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        user = User.query.filter_by(id=user_id, company_id=company_id).filter(User.status != STATUS_INACTIVE).first_or_404()
    
    # Check if target user holds protected is_super_admin role
    from app.models.role import Role
    from app.models.voter import Voter
    from app.models.user_permission import UserPermissionMapping

    has_protected_role = db.session.query(UserRoleMapping).join(
        Role, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user_id,
        UserRoleMapping.company_id == company_id,
        UserRoleMapping.status != STATUS_INACTIVE,
        Role.is_super_admin == True
    ).first()

    if has_protected_role:
        return jsonify({"error": "Super Admin users cannot be deleted"}), 403

    force = request.args.get('force', 'false').lower() == 'true'
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'

    active_voters = Voter.query.filter_by(user_id=user_id, company_id=company_id).filter(Voter.status != STATUS_INACTIVE).count()
    active_roles = UserRoleMapping.query.filter_by(user_id=user_id, company_id=company_id).filter(UserRoleMapping.status != STATUS_INACTIVE).count()
    active_perms = UserPermissionMapping.query.filter_by(user_id=user_id, company_id=company_id).filter(UserPermissionMapping.status != STATUS_INACTIVE).count()

    total_active_deps = active_voters + active_roles + active_perms

    if total_active_deps > 0 and not force:
        parts = []
        if active_voters > 0:
            parts.append(f"{active_voters} linked voter profile")
        if active_roles > 0:
            parts.append(f"{active_roles} assigned role(s)")
        if active_perms > 0:
            parts.append(f"{active_perms} custom permission override(s)")

        deps_str = ", ".join(parts)
        user_friendly_error = f"Cannot delete user: It currently has {deps_str}. Please deactivate these items first."

        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'voter_profile': active_voters,
                'user_roles': active_roles,
                'user_permissions': active_perms
            },
            'message': 'Are you sure you want to delete this user (and all related voter profile and role mapping data)?'
        }), 400

    if dry_run:
        return jsonify({'message': 'Pre-flight check passed', 'can_delete': True}), 200

    # Deactivate linked voter profile
    if active_voters > 0:
        voters = Voter.query.filter_by(user_id=user_id, company_id=company_id).filter(Voter.status != STATUS_INACTIVE).all()
        for v in voters:
            v.status = STATUS_INACTIVE
            set_audit_fields(v, is_create=False)

    # Deactivate user roles & permissions
    if active_roles > 0:
        user_roles = UserRoleMapping.query.filter_by(user_id=user_id, company_id=company_id).filter(UserRoleMapping.status != STATUS_INACTIVE).all()
        for ur in user_roles:
            ur.status = STATUS_INACTIVE
            set_audit_fields(ur, is_create=False)

    if active_perms > 0:
        user_perms = UserPermissionMapping.query.filter_by(user_id=user_id, company_id=company_id).filter(UserPermissionMapping.status != STATUS_INACTIVE).all()
        for up in user_perms:
            up.status = STATUS_INACTIVE
            set_audit_fields(up, is_create=False)

    # Soft delete user
    user.status = STATUS_INACTIVE
    if not user.email.endswith(f"__del_{user.id}"):
        user.email = f"{user.email}__del_{user.id}"
    set_audit_fields(user, is_create=False)
    
    return safe_commit((jsonify({'message': 'User deleted successfully'}), 200), 'Internal server error during user deletion')


@users_bp.route('/<int:user_id>/permanent', methods=['DELETE'])
@require_permission('Users', 'delete')
@audit_action('permanent_delete_user', module='Users',
              description='Permanently deleted a user',
              get_target_id=lambda *a, **kw: kw.get('user_id'))
def permanent_delete_user(user_id):
    """Permanently delete a user (set status to STATUS_DEACTIVATED).

    Platform Administrators only.  The user must already be soft-deleted
    (STATUS_INACTIVE) before they can be permanently deleted.
    """
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can permanently delete users'}), 403

    user = User.query.filter_by(id=user_id).first()
    if not user or user.status == STATUS_DEACTIVATED:
        return jsonify({'error': 'User not found'}), 404

    if user.status != STATUS_INACTIVE:
        return jsonify({'error': 'Deactivate this record before permanently deleting it'}), 400

    user.status = STATUS_DEACTIVATED
    set_audit_fields(user, is_create=False)

    return safe_commit(
        (jsonify({'message': 'User permanently deleted'}), 200),
        'Internal server error during permanent user deletion'
    )


@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current user's profile information.

    Administrators do not have a User row, so this endpoint returns 404
    for administrator tokens.
    """
    if is_administrator():
        return jsonify({'error': 'Administrators do not have a user profile'}), 404

    from flask_jwt_extended import get_jwt_identity
    from app.models.voter import Voter
    from app.models.vote import Vote
    
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    if getattr(user, 'status', STATUS_ACTIVE) == STATUS_INACTIVE:
        return jsonify({'error': 'User inactive'}), 403
    
    # Get voter profile if exists
    voter = Voter.query.filter_by(user_id=user_id).first()
    
    # Get voting statistics
    if voter:
        total_votes = Vote.query.filter_by(voter_id=voter.id).count()
        verified_votes = Vote.query.filter_by(voter_id=voter.id, vote_status='verified').count()
        counted_votes = Vote.query.filter_by(voter_id=voter.id, is_counted=True).count()
    else:
        total_votes = verified_votes = counted_votes = 0
    
    profile_data = {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': user.company.company_name if user.company else None,
        'department_id': user.department_id,
        'department_name': user.department.department_name if getattr(user, 'department', None) else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'status': getattr(user, 'status', 1),
        'voting_stats': {
            'total_votes': total_votes,
            'verified_votes': verified_votes,
            'counted_votes': counted_votes,
            'participation_rate': (verified_votes / max(total_votes, 1)) * 100
        }
    }
    
    # Add voter-specific information if available
    if voter:
        profile_data['voter'] = {
            'voter_id': voter.voter_id,
            'phone_number': voter.phone_number,
            'date_of_birth': voter.date_of_birth.isoformat() if voter.date_of_birth else None,
            'is_verified': voter.is_verified,
            'verification_level': voter.verification_level,
            'voter_type': voter.voter_type,
            'jurisdiction': voter.jurisdiction,
            'registered_address': voter.registered_address,
            'two_factor_enabled': voter.two_factor_enabled,
            'phone_verified_at': voter.phone_verified_at.isoformat() if voter.phone_verified_at else None,
            'identity_verified_at': voter.identity_verified_at.isoformat() if voter.identity_verified_at else None,
            'biometric_verified_at': voter.biometric_verified_at.isoformat() if voter.biometric_verified_at else None
        }
    
    return jsonify(profile_data)

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_current_user_profile():
    """Update current user's profile information.

    Administrators do not have a User row, so this endpoint returns 404
    for administrator tokens.
    """
    if is_administrator():
        return jsonify({'error': 'Administrators do not have a user profile'}), 404

    from flask_jwt_extended import get_jwt_identity
    from app.models.voter import Voter
    
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    if getattr(user, 'status', STATUS_ACTIVE) == STATUS_INACTIVE:
        return jsonify({'error': 'User inactive'}), 403
        
    data = request.get_json()
    
    cleaned_data, error = validate_user_input(data, is_create=False)
    if error:
        return error[0], error[1]
    
    # Update user information
    if 'name' in cleaned_data:
        user.name = cleaned_data['name']
        
    if 'email' in cleaned_data:
        email = cleaned_data['email']
        # Check if email already exists (excluding current user)
        existing_user = User.query.filter_by(email=email, company_id=user.company_id).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = email
    
    # Update voter information if exists
    voter = Voter.query.filter_by(user_id=user_id).first()
    if voter and data.get('voter'):
        voter_data = data['voter']
        if voter_data.get('phone_number'):
            voter.phone_number = voter_data['phone_number']
        if voter_data.get('registered_address'):
            voter.registered_address = voter_data['registered_address']
        if voter_data.get('date_of_birth'):
            voter.date_of_birth = datetime.strptime(voter_data['date_of_birth'], '%Y-%m-%d').date()
    
    return safe_commit((jsonify({'message': 'Profile updated successfully'}), 200), 'Internal server error during profile update')

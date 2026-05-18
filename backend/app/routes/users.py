from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.company import Company
from app.models.role import Role
from app.utils import get_current_company_id, require_company_context, require_permission, is_current_user_super_admin
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
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE
from app.utils.db_utils import safe_commit
from app.utils.query_helpers import get_active_users_query

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@require_permission('Users', 'view')
def list_users():
    company_id = get_current_company_id()
    search = request.args.get('search')
    
    page, per_page, error = parse_pagination(request)
    if error:
        return error[0], error[1]

    query = get_active_users_query(company_id).join(Company).options(
        joinedload(User.company), 
        joinedload(User.department)
    ).filter(Company.status != STATUS_INACTIVE).order_by(User.updated_at.desc(), User.created_at.desc())
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
    
    if is_current_user_super_admin():
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id is required for Super Admin'}), 400
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
    
    # Check if email already exists within the company
    if User.query.filter_by(email=email, company_id=company_id).first():
        return jsonify({'error': 'Email already exists in this company'}), 400
    
    user = User()
    user.name = name
    user.email = email
    user.password_hash = generate_password_hash(data['password'])
    user.company_id = company_id
    user.department_id = dept_id
    
    db.session.add(user)
    set_audit_fields(user, is_create=True)
    return safe_commit(
        (jsonify({'message': 'User created', 'user_id': user.id}), 201),
        'Internal server error during user creation'
    )

@users_bp.route('/<int:user_id>', methods=['GET'])
@require_permission('Users', 'view')
def get_user(user_id):
    company_id = get_current_company_id()
    user = User.query.join(Company).filter(
        User.id == user_id, 
        User.company_id == company_id,
        User.status != STATUS_INACTIVE,
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
        # Check if email already exists within the company (excluding current user)
        existing_user = User.query.filter_by(email=email, company_id=company_id).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already exists in this company'}), 400
        user.email = email
        
    if data.get('password'):
        user.password_hash = generate_password_hash(data['password'])
        
    if 'department_id' in data:
        user.department_id = dept_id
        
    set_audit_fields(user, is_create=False)
    
    return safe_commit((jsonify({'message': 'User updated'}), 200), 'Internal server error during user update')

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_permission('Users', 'delete')
@audit_action('delete_user', module='Users', description='Deleted a user', get_target_id=lambda *args, **kwargs: kwargs.get('user_id'))
def delete_user(user_id):
    # Self-delete guard — before any DB queries
    current_user_id = int(get_jwt_identity())
    if current_user_id == user_id:
        return jsonify({"error": "You cannot delete your own account"}), 403

    company_id = get_current_company_id()
    user = User.query.filter_by(id=user_id, company_id=company_id).filter(User.status != STATUS_INACTIVE).first_or_404()
    
    # Check if target user has Super Admin role
    super_admin_role = Role.query.filter(
        Role.role_name.ilike('super admin'),
        Role.company_id == company_id
    ).first()

    if super_admin_role:
        is_super_admin = UserRoleMapping.query.filter_by(
            user_id=user_id, 
            role_id=super_admin_role.id
        ).first()
        if is_super_admin:
            return jsonify({"error": "Super Admin users cannot be deleted"}), 403
    
    # Do NOT delete related user role mappings physically for now
    # UserRoleMapping.query.filter_by(user_id=user_id).delete()
    
    # Soft delete instead of hard delete
    user.status = STATUS_INACTIVE
    set_audit_fields(user, is_create=False)
    
    return safe_commit((jsonify({'message': 'User deleted'}), 200), 'Internal server error during user deletion')

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current user's profile information"""
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
    """Update current user's profile information"""
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

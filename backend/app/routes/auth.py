from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.user import User
from app.models.company import Company
from app.models.role import Role
from app.models.user_role import UserRoleMapping
from app.utils import get_current_user
import logging

from app.utils.constants import STATUS_INACTIVE
from app.utils.validators import safe_get_json, validate_password, validate_email
from app.utils.db_utils import safe_commit

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/administrator/login', methods=['POST'])
def administrator_login():
    """Authenticate a platform Administrator.

    Looks up the email in the ``administrators`` table (not ``users``),
    verifies the password, and issues a JWT with:

    - ``identity`` = ``"admin:<administrator.id>"``
    - ``additional_claims`` = ``{"is_administrator": True}``

    The custom claim is what :func:`app.utils.is_administrator` checks on
    every subsequent request.  The ``"admin:"`` prefix in the identity lets
    :func:`app.utils.get_current_administrator` load the correct row.

    Returns 401 with a generic message on any failure (wrong email, wrong
    password, missing fields) to avoid leaking whether an email exists.
    """
    from app.models.administrator import Administrator

    data, error = safe_get_json(request)
    if error:
        return error

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Invalid credentials'}), 401

    administrator = Administrator.query.filter_by(email=data['email']).first()

    if not administrator or not check_password_hash(
        administrator.password_hash, str(data['password'])
    ):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(
        identity=f"admin:{administrator.id}",
        additional_claims={"is_administrator": True},
    )

    return jsonify({
        'access_token': access_token,
        'administrator': {
            'id': administrator.id,
            'name': administrator.name,
            'email': administrator.email,
        }
    }), 200



@auth_bp.route('/login', methods=['POST'])
def login():
    from app.models.administrator import Administrator

    data, error = safe_get_json(request)
    if error:
        return error
        
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    # 1. First check the administrators table for the given email
    administrator = Administrator.query.filter_by(email=data['email']).first()
    if administrator:
        if not check_password_hash(administrator.password_hash, str(data['password'])):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        access_token = create_access_token(
            identity=f"admin:{administrator.id}",
            additional_claims={"is_administrator": True},
        )
        return jsonify({
            'is_administrator': True,
            'access_token': access_token,
            'administrator': {
                'id': administrator.id,
                'name': administrator.name,
                'email': administrator.email,
            }
        }), 200
        
    # 2. If not found in administrators, fall through to User table lookup
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or getattr(user, 'status', 1) == STATUS_INACTIVE:
        return jsonify({'error': 'Invalid credentials'}), 401
        
    if not check_password_hash(user.password_hash, str(data['password'])):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Get company information
    company = Company.query.get(user.company_id)
    
    # Fetch active roles
    from app import db
    active_roles = db.session.query(Role).join(
        UserRoleMapping, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user.id,
        UserRoleMapping.company_id == user.company_id,
        UserRoleMapping.status == 1,
        Role.status != 0
    ).all()
    roles_list = [{'id': role.id, 'role_name': role.role_name} for role in active_roles]
    
    # Create access token with string identity
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'company_id': user.company_id,
            'company_name': company.company_name if company else None,
            'roles': roles_list
        }
    }), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile information"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    company = Company.query.get(user.company_id)
    
    # Fetch active roles
    from app import db
    active_roles = db.session.query(Role).join(
        UserRoleMapping, UserRoleMapping.role_id == Role.id
    ).filter(
        UserRoleMapping.user_id == user.id,
        UserRoleMapping.company_id == user.company_id,
        UserRoleMapping.status == 1,
        Role.status != 0
    ).all()
    roles_list = [{'id': role.id, 'role_name': role.role_name} for role in active_roles]
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None,
        'roles': roles_list
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data, error = safe_get_json(request)
    if error:
        return error
        
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        email, error = validate_email(data['email'])
        if error:
            return error
            
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(
            email=email, 
            company_id=user.company_id
        ).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Email already in use'}), 400
        user.email = email
    
    from app import db
    
    company = Company.query.get(user.company_id)
    success_tuple = (jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None
    }), 200)
    
    return safe_commit(success_tuple, 'Internal server error during profile update', logger=logger)

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    data, error = safe_get_json(request)
    if error:
        return error

    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    # Always return the same response to prevent email enumeration
    if user:
        from app import db
        reset_token = user.generate_reset_token(expires_in_minutes=30)
        
        # Only expose the token in debug / development mode (NOT in production).
        from flask import current_app
        if current_app.debug:
            success_tuple = (jsonify({
                'message': 'Password reset instructions sent to your email',
                'reset_token': reset_token  # Development only — remove in production
            }), 200)
        else:
            success_tuple = (jsonify({
                'message': 'If that email is registered, you will receive reset instructions shortly.'
            }), 200)
            
        result = safe_commit(success_tuple, 'Internal server error during token generation', logger=logger)
        
        # In production: send reset_token via email instead of returning it.
        # For development, we log it server-side only.
        logger.info(f"Password reset requested for user {user.id} (email: {user.email}). Token stored in DB.")
        
        if current_app.debug:
            return result

    return jsonify({
        'message': 'If that email is registered, you will receive reset instructions shortly.'
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data, error = safe_get_json(request)
    if error:
        return error

    if not data or not data.get('token') or not data.get('new_password'):
        return jsonify({'error': 'token and new_password are required'}), 400

    pwd_error = validate_password(data['new_password'])
    if pwd_error:
        return pwd_error

    # Look up the token in the database
    user = User.query.filter_by(password_reset_token=data['token']).first()
    if not user or not user.verify_reset_token(data['token']):
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    from app import db
    user.password_hash = generate_password_hash(data['new_password'])
    user.clear_reset_token()
    
    result = safe_commit((jsonify({'message': 'Password reset successfully'}), 200), 'Internal server error during password reset', logger=logger)
    if result[1] == 200:
        logger.info(f"Password reset successfully for user {user.id}")
    return result

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password for authenticated user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data, error = safe_get_json(request)
    if error:
        return error
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    # Verify current password
    if not check_password_hash(user.password_hash, data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 400
        
    pwd_error = validate_password(data['new_password'])
    if pwd_error:
        return pwd_error
    
    # Update password
    user.password_hash = generate_password_hash(data['new_password'])
    from app import db
    
    return safe_commit((jsonify({'message': 'Password changed successfully'}), 200), 'Internal server error during password change', logger=logger)

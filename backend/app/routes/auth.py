from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.user import User
from app.models.company import Company
from app.utils import get_current_user
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        # Try to get JSON data
        data = request.get_json()
        
        # If data is None, try to get it from form data
        if data is None:
            data = {
                'email': request.form.get('email'),
                'password': request.form.get('password')
            }
        
        # Check if data is a string (malformed JSON)
        if isinstance(data, str):
            return jsonify({'error': 'Invalid JSON format in request'}), 400
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Request parsing error: {str(e)}'}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, str(data['password'])):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Get company information
    company = Company.query.get(user.company_id)
    
    # Create access token with string identity
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'company_id': user.company_id,
            'company_name': company.company_name if company else None
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
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(
            email=data['email'], 
            company_id=user.company_id
        ).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Email already in use'}), 400
        user.email = data['email']
    
    from app import db
    db.session.commit()
    
    company = Company.query.get(user.company_id)
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    data = request.get_json()

    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    # Always return the same response to prevent email enumeration
    if user:
        from app import db
        reset_token = user.generate_reset_token(expires_in_minutes=30)
        db.session.commit()

        # In production: send reset_token via email instead of returning it.
        # For development, we log it server-side only.
        logger.info(f"Password reset requested for user {user.id} (email: {user.email}). Token stored in DB.")

        # Only expose the token in debug / development mode (NOT in production).
        from flask import current_app
        if current_app.debug:
            return jsonify({
                'message': 'Password reset instructions sent to your email',
                'reset_token': reset_token  # Development only — remove in production
            }), 200

    return jsonify({
        'message': 'If that email is registered, you will receive reset instructions shortly.'
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data = request.get_json()

    if not data or not data.get('token') or not data.get('new_password'):
        return jsonify({'error': 'token and new_password are required'}), 400

    # Enforce minimum password length
    if len(data['new_password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400

    # Look up the token in the database
    user = User.query.filter_by(password_reset_token=data['token']).first()
    if not user or not user.verify_reset_token(data['token']):
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    from app import db
    user.password_hash = generate_password_hash(data['new_password'])
    user.clear_reset_token()
    db.session.commit()

    logger.info(f"Password reset successfully for user {user.id}")
    return jsonify({'message': 'Password reset successfully'}), 200

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password for authenticated user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    # Verify current password
    if not check_password_hash(user.password_hash, data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Update password
    user.password_hash = generate_password_hash(data['new_password'])
    from app import db
    db.session.commit()
    
    return jsonify({
        'message': 'Password changed successfully'
    }), 200

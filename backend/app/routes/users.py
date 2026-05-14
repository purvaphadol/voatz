from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.company import Company
from app.utils import get_current_company_id, require_company_context, require_permission
from sqlalchemy import or_
from datetime import datetime

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@require_permission('Users', 'view')
def list_users():
    company_id = get_current_company_id()
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    query = User.query.join(Company).filter(User.company_id == company_id)
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
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'updated_at': u.updated_at.isoformat() if u.updated_at else None,
            'status': u.status if hasattr(u, 'status') else 1
        } for u in users],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@users_bp.route('/', methods=['POST'])
@require_permission('Users', 'create')
def create_user():
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Name, email, and password are required'}), 400
    
    # Check if email already exists within the company
    if User.query.filter_by(email=data['email'], company_id=company_id).first():
        return jsonify({'error': 'Email already exists in this company'}), 400
    
    user = User()
    user.name = data['name']
    user.email = data['email']
    user.password_hash = generate_password_hash(data['password'])
    user.company_id = company_id
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User created', 'user_id': user.id}), 201

@users_bp.route('/<int:user_id>', methods=['GET'])
@require_permission('Users', 'view')
def get_user(user_id):
    company_id = get_current_company_id()
    user = User.query.join(Company).filter(
        User.id == user_id, 
        User.company_id == company_id
    ).first_or_404()
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'company_id': user.company_id,
        'company_name': user.company.company_name,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'status': user.status if hasattr(user, 'status') else 1
    })

@users_bp.route('/<int:user_id>', methods=['PUT'])
@require_permission('Users', 'update')
def update_user(user_id):
    company_id = get_current_company_id()
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    if data.get('name'):
        user.name = data['name']
    if data.get('email'):
        # Check if email already exists within the company (excluding current user)
        existing_user = User.query.filter_by(email=data['email'], company_id=company_id).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already exists in this company'}), 400
        user.email = data['email']
    if data.get('password'):
        user.password_hash = generate_password_hash(data['password'])
    
    db.session.commit()
    return jsonify({'message': 'User updated'}), 200

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_permission('Users', 'delete')
def delete_user(user_id):
    company_id = get_current_company_id()
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    
    # Delete related user role mappings first
    UserRoleMapping.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current user's profile information"""
    from flask_jwt_extended import get_jwt_identity
    from app.models.voter import Voter
    from app.models.vote import Vote
    
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
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
    data = request.get_json()
    
    # Update user information
    if data.get('name'):
        user.name = data['name']
    if data.get('email'):
        # Check if email already exists (excluding current user)
        existing_user = User.query.filter_by(email=data['email'], company_id=user.company_id).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    
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
    
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})

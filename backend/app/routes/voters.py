from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash
from app import db
from app.models.voter import Voter
from app.models.user import User
from app.models.company import Company
from app.utils import get_current_company_id, require_permission, get_current_user
from sqlalchemy import or_
from datetime import datetime, timezone
import secrets
import string

voters_bp = Blueprint('voters', __name__)

@voters_bp.route('/', methods=['GET'])
@require_permission('Voters', 'view')
def list_voters():
    """List all voters with filtering and pagination"""
    company_id = get_current_company_id()
    search = request.args.get('search')
    verification_level = request.args.get('verification_level')
    is_verified = request.args.get('is_verified')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    query = Voter.query.join(User).filter(Voter.company_id == company_id, Voter.status == 1)
    
    if search:
        query = query.filter(or_(
            User.name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            Voter.voter_id.ilike(f'%{search}%'),
            Voter.phone_number.ilike(f'%{search}%')
        ))
    
    if verification_level:
        query = query.filter(Voter.verification_level == verification_level)
    
    if is_verified is not None:
        query = query.filter(Voter.is_verified == (is_verified.lower() == 'true'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    voters = pagination.items
    
    return jsonify({
        'data': [{
            'id': v.id,
            'voter_id': v.voter_id,
            'user_id': v.user_id,
            'name': v.user.name,
            'email': v.user.email,
            'phone_number': v.phone_number,
            'date_of_birth': v.date_of_birth.isoformat() if v.date_of_birth else None,
            'is_verified': v.is_verified,
            'verification_level': v.verification_level,
            'voter_type': v.voter_type,
            'jurisdiction': v.jurisdiction,
            'two_factor_enabled': v.two_factor_enabled,
            'phone_verified_at': v.phone_verified_at.isoformat() if v.phone_verified_at else None,
            'identity_verified_at': v.identity_verified_at.isoformat() if v.identity_verified_at else None,
            'biometric_verified_at': v.biometric_verified_at.isoformat() if v.biometric_verified_at else None,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'updated_at': v.updated_at.isoformat() if v.updated_at else None,
            'status': v.status
        } for v in voters],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': {
            'total_voters': pagination.total,
            'verified_voters': sum(1 for v in voters if v.is_verified),
            'unverified_voters': sum(1 for v in voters if not v.is_verified)
        }
    })

@voters_bp.route('/', methods=['POST'])
@require_permission('Voters', 'create')
def create_voter():
    """Create a new voter (linked to existing user or create new user)"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('phone_number'):
        return jsonify({'error': 'Phone number is required'}), 400
    
    user = None
    user_id = data.get('user_id')
    if user_id:
        # Link to existing user
        user = User.query.filter_by(id=user_id, company_id=company_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user already has a voter profile
        existing_voter = Voter.query.filter_by(user_id=user_id, company_id=company_id).first()
        if existing_voter:
            return jsonify({'error': 'User already has a voter profile'}), 400
    elif data.get('name') and not data.get('password'):
        # Standalone voter, no user account
        pass
    elif data.get('name') and data.get('email') and data.get('password'):
        # Create new user
        # Check if email already exists
        if User.query.filter_by(email=data['email'], company_id=company_id).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User()
        user.name = data['name']
        user.email = data['email']
        user.password_hash = generate_password_hash(data['password'])
        user.company_id = company_id
        user.created_by = current_user.id if current_user else None
        db.session.add(user)
        db.session.flush()  # Get the user ID
    else:
        return jsonify({'error': 'Invalid request parameters for creating a voter'}), 400
    
    # Generate unique voter ID
    voter_id = generate_voter_id()
    while Voter.query.filter_by(voter_id=voter_id).first():
        voter_id = generate_voter_id()
    
    # Create voter profile
    voter = Voter()
    voter.user_id = user.id if user else None
    voter.company_id = company_id
    voter.voter_id = voter_id
    voter.phone_number = data['phone_number']
    voter.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None
    voter.registered_address = data.get('registered_address')
    voter.jurisdiction = data.get('jurisdiction')
    voter.voter_type = data.get('voter_type', 'standard')
    voter.two_factor_enabled = data.get('two_factor_enabled', False)
    voter.created_by = current_user.id if current_user else None
    
    db.session.add(voter)
    db.session.commit()
    
    return jsonify({
        'message': 'Voter created successfully',
        'voter_id': voter.id,
        'voter_registration_id': voter.voter_id
    }), 201

@voters_bp.route('/<int:voter_id>', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter(voter_id):
    """Get detailed voter information"""
    company_id = get_current_company_id()
    voter = Voter.query.join(User).filter(
        Voter.id == voter_id,
        Voter.company_id == company_id
    ).first_or_404()
    
    return jsonify({
        'id': voter.id,
        'voter_id': voter.voter_id,
        'user_id': voter.user_id,
        'name': voter.user.name,
        'email': voter.user.email,
        'phone_number': voter.phone_number,
        'date_of_birth': voter.date_of_birth.isoformat() if voter.date_of_birth else None,
        'is_verified': voter.is_verified,
        'verification_level': voter.verification_level,
        'voter_type': voter.voter_type,
        'jurisdiction': voter.jurisdiction,
        'registered_address': voter.registered_address,
        'two_factor_enabled': voter.two_factor_enabled,
        'registered_device_id': voter.registered_device_id,
        'phone_verified_at': voter.phone_verified_at.isoformat() if voter.phone_verified_at else None,
        'identity_verified_at': voter.identity_verified_at.isoformat() if voter.identity_verified_at else None,
        'biometric_verified_at': voter.biometric_verified_at.isoformat() if voter.biometric_verified_at else None,
        'created_at': voter.created_at.isoformat() if voter.created_at else None,
        'updated_at': voter.updated_at.isoformat() if voter.updated_at else None,
        'status': voter.status
    })

@voters_bp.route('/<int:voter_id>', methods=['PUT'])
@require_permission('Voters', 'update')
def update_voter(voter_id):
    """Update voter information"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    # Update allowed fields
    if data.get('phone_number'):
        voter.phone_number = data['phone_number']
    if data.get('date_of_birth'):
        voter.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    if data.get('registered_address'):
        voter.registered_address = data['registered_address']
    if data.get('jurisdiction'):
        voter.jurisdiction = data['jurisdiction']
    if data.get('voter_type'):
        voter.voter_type = data['voter_type']
    if 'two_factor_enabled' in data:
        voter.two_factor_enabled = data['two_factor_enabled']
    if data.get('registered_device_id'):
        voter.registered_device_id = data['registered_device_id']
    
    voter.updated_by = current_user.id if current_user else None
    voter.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    return jsonify({'message': 'Voter updated successfully'}), 200

@voters_bp.route('/<int:voter_id>', methods=['DELETE'])
@require_permission('Voters', 'delete')
def delete_voter(voter_id):
    """Delete voter profile (soft delete)"""
    company_id = get_current_company_id()
    voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first_or_404()
    
    # Soft delete by updating status
    voter.status = 0
    voter.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    return jsonify({'message': 'Voter deleted successfully'}), 200

@voters_bp.route('/<int:voter_id>/verify', methods=['POST'])
@require_permission('Voters', 'update')
def verify_voter(voter_id):
    """Manually verify a voter (admin function)"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    verification_type = data.get('verification_type')  # phone, identity, biometric
    
    if verification_type == 'phone':
        voter.phone_verified_at = datetime.now(timezone.utc)
        if voter.verification_level == 'none':
            voter.verification_level = 'phone'
    elif verification_type == 'identity':
        voter.identity_verified_at = datetime.now(timezone.utc)
        if voter.verification_level in ['none', 'phone']:
            voter.verification_level = 'identity'
    elif verification_type == 'biometric':
        voter.biometric_verified_at = datetime.now(timezone.utc)
        voter.verification_level = 'full'
    
    # Update overall verification status
    if voter.phone_verified_at and voter.identity_verified_at:
        voter.is_verified = True
        if voter.biometric_verified_at:
            voter.verification_level = 'full'
        else:
            voter.verification_level = 'standard'
    
    voter.updated_by = current_user.id if current_user else None
    voter.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    return jsonify({'message': f'Voter {verification_type} verification updated successfully'}), 200

@voters_bp.route('/<int:voter_id>/registrations', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_registrations(voter_id):
    """Get voter's election registrations"""
    company_id = get_current_company_id()
    voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first_or_404()
    
    registrations = []
    for reg in voter.registrations:
        registrations.append({
            'id': reg.id,
            'registration_id': reg.registration_id,
            'election_id': reg.election_id,
            'election_title': reg.election.title,
            'status': reg.status,
            'registration_type': reg.registration_type,
            'registered_at': reg.registered_at.isoformat(),
            'approved_at': reg.approved_at.isoformat() if reg.approved_at else None,
            'is_eligible': reg.is_eligible_to_vote,
            'verification_level': reg.verification_level_met
        })
    
    return jsonify({'registrations': registrations})

@voters_bp.route('/<int:voter_id>/votes', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_votes(voter_id):
    """Get voter's voting history"""
    company_id = get_current_company_id()
    voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first_or_404()
    
    votes = []
    for vote in voter.votes:
        votes.append({
            'id': vote.id,
            'vote_id': vote.vote_id,
            'tracking_code': vote.tracking_code,
            'election_id': vote.election_id,
            'election_title': vote.election.title,
            'ballot_id': vote.ballot_id,
            'ballot_title': vote.ballot.title,
            'vote_cast_time': vote.vote_cast_time.isoformat(),
            'vote_status': vote.vote_status,
            'vote_method': vote.vote_method,
            'is_verified': vote.is_verified,
            'verification_level': vote.verification_level
        })
    
    return jsonify({'votes': votes})

@voters_bp.route('/stats', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_stats():
    """Get voter statistics for the company"""
    company_id = get_current_company_id()
    
    total_voters = Voter.query.filter_by(company_id=company_id, status=1).count()
    verified_voters = Voter.query.filter_by(company_id=company_id, is_verified=True, status=1).count()
    unverified_voters = total_voters - verified_voters
    
    # Verification levels
    verification_levels = db.session.query(
        Voter.verification_level,
        db.func.count(Voter.id).label('count')
    ).filter_by(company_id=company_id, status=1).group_by(Voter.verification_level).all()
    
    # Voter types
    voter_types = db.session.query(
        Voter.voter_type,
        db.func.count(Voter.id).label('count')
    ).filter_by(company_id=company_id, status=1).group_by(Voter.voter_type).all()
    
    return jsonify({
        'total_voters': total_voters,
        'verified_voters': verified_voters,
        'unverified_voters': unverified_voters,
        'verification_rate': (verified_voters / total_voters * 100) if total_voters > 0 else 0,
        'verification_levels': {level: count for level, count in verification_levels},
        'voter_types': {vtype: count for vtype, count in voter_types}
    })

def generate_voter_id():
    """Generate a unique voter ID"""
    alphabet = string.ascii_uppercase + string.digits
    return 'V' + ''.join(secrets.choice(alphabet) for _ in range(8)) 
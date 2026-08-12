from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app import db
from app.models.voter import Voter
from app.models.user import User
from app.utils import get_current_company_id, require_permission, get_current_user, is_administrator
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from app.utils.validators import parse_pagination, validate_voter_input, validate_email
from app.utils.validators import parse_pagination, validate_voter_input, validate_email
from app.utils.query_helpers import get_active_voters_query
from app.utils.cascade import count_dependents, count_reactivatable_dependents, cascade_set_inactive, cascade_reactivate
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED
from sqlalchemy import or_
from datetime import datetime, timezone
import secrets
import string


voters_bp = Blueprint('voters', __name__)

@voters_bp.route('/<int:voter_id>/status_dependents', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_status_dependents(voter_id):
    """Retrieve dependent counts for status transitions (Inactive or Reactivate)."""
    if is_administrator():
        voter = Voter.query.filter(Voter.id == voter_id, Voter.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = Voter.query.filter(Voter.id == voter_id, Voter.company_id == company_id, Voter.status != STATUS_DEACTIVATED).first_or_404()

    if voter.status == STATUS_ACTIVE:
        result = count_dependents('Voter', voter_id)
        return jsonify({'current_status': STATUS_ACTIVE, 'target_status': STATUS_INACTIVE, 'dependents': result})
    else:
        result = count_reactivatable_dependents('Voter', voter_id)
        return jsonify({'current_status': STATUS_INACTIVE, 'target_status': STATUS_ACTIVE, 'dependents': result})


@voters_bp.route('/', methods=['GET'])
@require_permission('Voters', 'view')
def list_voters():
    """List all voters with filtering and pagination"""
    search = request.args.get('search')
    verification_level = request.args.get('verification_level')
    is_verified = request.args.get('is_verified')
    show_inactive_raw = request.args.get('show_inactive')
    status_param = request.args.get('status', '').lower()
    if status_param == 'all':
        allowed = [STATUS_ACTIVE, STATUS_INACTIVE]
    elif show_inactive_raw is not None and show_inactive_raw.lower() == 'true':
        allowed = [STATUS_INACTIVE]
    elif status_param == 'inactive':
        allowed = [STATUS_INACTIVE]
    else:
        allowed = [STATUS_ACTIVE]
    
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        query = Voter.query.outerjoin(User)
        if req_company_id:
            query = query.filter(Voter.company_id == req_company_id)
    else:
        company_id = get_current_company_id()
        query = Voter.query.filter(Voter.company_id == company_id).outerjoin(User)

    query = query.filter(Voter.status.in_(allowed), Voter.status != STATUS_DEACTIVATED)
    
    if search:
        query = query.filter(or_(
            User.name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            Voter.name.ilike(f'%{search}%'),
            Voter.email.ilike(f'%{search}%'),
            Voter.voter_id.ilike(f'%{search}%'),
            Voter.phone_number.ilike(f'%{search}%')
        ))
    
    if verification_level:
        query = query.filter(Voter.verification_level == verification_level)
    
    if is_verified is not None:
        query = query.filter(Voter.is_verified == (is_verified.lower() == 'true'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    voters = pagination.items
    
    summary = {
        'total_voters': pagination.total,
        'verified_voters': sum(1 for v in voters if v.is_verified),
        'unverified_voters': sum(1 for v in voters if not v.is_verified)
    }
    
    return jsonify({
        'data': [{
            'id': v.id,
            'voter_id': v.voter_id,
            'user_id': v.user_id,
            'is_linked_user': v.user_id is not None,
            'name': v.display_name,
            'email': v.display_email,
            'phone_number': v.phone_number,
            'date_of_birth': v.date_of_birth.isoformat() if v.date_of_birth else None,
            'is_verified': v.is_verified,
            'verification_level': v.verification_level or 'none',
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
        'summary': summary
    })


@voters_bp.route('/', methods=['POST'])
@require_permission('Voters', 'create')
@audit_action('create_voter', module='Voters', description='Created voter profile')
def create_voter():
    """Create a new voter (three paths: link to existing, standalone, or create user + link)"""
    data = request.get_json()
    if is_administrator():
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id is required for platform Administrators'}), 400
    else:
        company_id = get_current_company_id()
    
    cleaned_data, error = validate_voter_input(data, is_create=True)
    if error:
        return error
        
    # Check for inactive collision (409 Conflict)
    existing_inactive = Voter.query.filter(
        Voter.company_id == company_id,
        Voter.phone_number == cleaned_data['phone_number'],
        Voter.status == STATUS_INACTIVE
    ).first()
    if existing_inactive:
        return jsonify({
            'error': 'A voter profile with this phone number already exists in this company but is currently Inactive.',
            'existing_id': existing_inactive.id,
            'can_reactivate': True
        }), 409

    user_id = data.get('user_id')
    user = None
    
    # Path 1: link to existing user
    if user_id:
        user = User.query.filter_by(id=user_id, company_id=company_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        existing_voter = Voter.query.filter(
            Voter.user_id == user_id,
            Voter.company_id == company_id,
            Voter.status != STATUS_DEACTIVATED
        ).first()
        if existing_voter:
            return jsonify({'error': 'User already has a voter profile'}), 400
            
    # Path 2: name + phone_number provided but no user_id and no password -> standalone voter
    elif data.get('name') and not data.get('password'):
        user = None
        
    # Path 3: name + email + password provided -> create linked user first
    elif data.get('name') and data.get('email') and data.get('password'):
        email = cleaned_data.get('email')
        if not email:
            return jsonify({'error': 'Email is required to create a linked user account'}), 400
            
        if User.query.filter_by(email=email, company_id=company_id).filter(User.status == STATUS_ACTIVE).first():
            return jsonify({'error': 'Email already exists'}), 400
            
        from app.utils.validators import validate_password
        pwd_error = validate_password(data['password'])
        if pwd_error:
            return pwd_error
            
        user = User()
        user.name = cleaned_data['name']
        user.email = email
        user.password_hash = generate_password_hash(data['password'])
        user.company_id = company_id
        set_audit_fields(user, is_create=True)
        db.session.add(user)
        db.session.flush()
        
    else:
        return jsonify({'error': 'Invalid request data. Provide user_id to link, name + phone to create a standalone voter, or name + email + password to create a linked user.'}), 400
        
    # Generate unique voter ID scoped within company
    voter_id = generate_voter_id()
    while Voter.query.filter_by(voter_id=voter_id, company_id=company_id).first():
        voter_id = generate_voter_id()
        
    # Create voter profile
    voter = Voter()
    voter.user_id = user.id if user else None
    voter.company_id = company_id
    voter.voter_id = voter_id
    voter.phone_number = cleaned_data['phone_number']
    voter.date_of_birth = cleaned_data.get('date_of_birth')
    voter.registered_address = cleaned_data.get('registered_address')
    voter.jurisdiction = cleaned_data.get('jurisdiction')
    voter.voter_type = cleaned_data.get('voter_type', 'standard')
    voter.two_factor_enabled = data.get('two_factor_enabled', False)
    voter.status = data.get('status', STATUS_ACTIVE)
    
    # If standalone, save the name and email directly on the voter
    if not user:
        voter.name = cleaned_data['name']
        voter.email = cleaned_data.get('email')
        
    set_audit_fields(voter, is_create=True)
    db.session.add(voter)
    db.session.flush()
    
    return safe_commit(
        (jsonify({
            'message': 'Voter created successfully',
            'voter_id': voter.id,
            'voter_registration_id': voter.voter_id
        }), 201),
        'Internal server error during voter creation'
    )


@voters_bp.route('/<int:voter_id>', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter(voter_id):
    """Get detailed voter information"""
    if is_administrator():
        voter = Voter.query.filter(Voter.id == voter_id, Voter.status != STATUS_DEACTIVATED).outerjoin(User).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = Voter.query.filter(Voter.id == voter_id, Voter.company_id == company_id, Voter.status != STATUS_DEACTIVATED).outerjoin(User).first_or_404()
    
    return jsonify({
        'id': voter.id,
        'voter_id': voter.voter_id,
        'user_id': voter.user_id,
        'is_linked_user': voter.user_id is not None,
        'name': voter.display_name,
        'email': voter.display_email,
        'phone_number': voter.phone_number,
        'date_of_birth': voter.date_of_birth.isoformat() if voter.date_of_birth else None,
        'is_verified': voter.is_verified,
        'verification_level': voter.verification_level or 'none',
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
@audit_action('update_voter', module='Voters', description='Updated voter profile')
def update_voter(voter_id):
    """Update voter information"""
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = Voter.query.filter(Voter.id == voter_id, Voter.company_id == company_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    data = request.get_json()
    
    cleaned_data, error = validate_voter_input(data, is_create=False)
    if error:
        return error
        
    # Update allowed fields
    if 'phone_number' in cleaned_data:
        voter.phone_number = cleaned_data['phone_number']
    if 'date_of_birth' in cleaned_data:
        voter.date_of_birth = cleaned_data['date_of_birth']
    if 'registered_address' in cleaned_data:
        voter.registered_address = cleaned_data['registered_address']
    if 'jurisdiction' in cleaned_data:
        voter.jurisdiction = cleaned_data['jurisdiction']
    if 'voter_type' in cleaned_data:
        voter.voter_type = cleaned_data['voter_type']
    if 'two_factor_enabled' in data:
        voter.two_factor_enabled = data['two_factor_enabled']
    if 'registered_device_id' in data:
        voter.registered_device_id = data['registered_device_id']

    # Handle status transition and cascade
    new_status = data.get('status')
    if new_status is not None and new_status != voter.status:
        old_status = voter.status
        voter.status = new_status
        if old_status == STATUS_ACTIVE and new_status == STATUS_INACTIVE:
            cascade_set_inactive('Voter', voter.id)
        elif old_status == STATUS_INACTIVE and new_status == STATUS_ACTIVE:
            cascade_reactivate('Voter', voter.id)
        
    # If voter is standalone (no user_id) and data contains name or email, update voter.name and voter.email directly.
    if voter.user_id is None:
        if 'name' in cleaned_data:
            voter.name = cleaned_data['name']
        if 'email' in cleaned_data:
            voter.email = cleaned_data['email']
            
    set_audit_fields(voter, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Voter updated successfully'}), 200),
        'Internal server error during voter update'
    )

@voters_bp.route('/<int:voter_id>', methods=['DELETE'])
@require_permission('Voters', 'delete')
@audit_action('delete_voter', module='Voters', description='Soft deleted voter profile')
def delete_voter(voter_id):
    """Delete voter profile (soft delete)"""
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = Voter.query.filter_by(id=voter_id, company_id=company_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    
    # Check if voter has cast votes (cannot delete under any circumstances)
    from app.models.vote import Vote
    vote_count = Vote.query.filter_by(voter_id=voter_id).count()
    if vote_count > 0:
        return jsonify({'error': 'Cannot delete voter with submitted votes'}), 400

    force = request.args.get('force', 'false').lower() == 'true'

    from app.models.voter_registration import VoterRegistration
    active_regs = VoterRegistration.query.filter_by(voter_id=voter_id).filter(VoterRegistration.status.notin_(['inactive', 'cancelled', 'deleted'])).count()

    if active_regs > 0 and not force:
        user_friendly_error = f"Cannot delete voter: It currently has {active_regs} active election registration(s). Please cancel these registrations first."
        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'voter_registrations': active_regs
            },
            'message': 'Are you sure you want to delete this voter profile (and cancel all related election registrations)?'
        }), 400

    import time
    ts = int(time.time())

    # Deactivate active registrations
    if active_regs > 0:
        regs = VoterRegistration.query.filter_by(voter_id=voter_id).filter(VoterRegistration.status.notin_(['inactive', 'cancelled', 'deleted'])).all()
        for r in regs:
            r.status = 'cancelled'
            set_audit_fields(r, is_create=False)

    # Soft delete by updating status
    voter.status = STATUS_DEACTIVATED
    if voter.voter_id and "_deleted_" not in voter.voter_id:
        voter.voter_id = f"{voter.voter_id[:70]}_deleted_{voter.id}_{ts}"[:100]
    if voter.phone_number and "_deleted_" not in voter.phone_number:
        voter.phone_number = f"{voter.phone_number[:5]}_deleted_{voter.id}_{ts}"[:20]
    set_audit_fields(voter, is_create=False)

    return safe_commit(
        (jsonify({'message': 'Voter deleted successfully'}), 200),
        'Internal server error during voter deletion'
    )

@voters_bp.route('/<int:voter_id>/verify', methods=['POST'])
@require_permission('Voters', 'update')
@audit_action('verify_voter', module='Voters', description='Updated voter verification status')
def verify_voter(voter_id):
    """Manually verify a voter (admin function)"""
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = get_active_voters_query(company_id).filter_by(id=voter_id).first_or_404()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Data is required'}), 400
        
    verification_type = data.get('verification_type')  # phone, identity, biometric
    
    if verification_type not in ['phone', 'identity', 'biometric']:
        return jsonify({'error': 'Invalid verification_type'}), 400
    
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
            
    set_audit_fields(voter, is_create=False)
    
    return safe_commit(
        (jsonify({'message': f'Voter {verification_type} verification updated successfully'}), 200),
        'Internal server error during voter verification'
    )

@voters_bp.route('/<int:voter_id>/registrations', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_registrations(voter_id):
    """Get voter's election registrations"""
    from app.models.voter_registration import VoterRegistration
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
        registrations = VoterRegistration.query.filter_by(
            voter_id=voter_id
        ).filter(VoterRegistration.status != 'deleted'
        ).order_by(VoterRegistration.registered_at.desc()).all()
    else:
        company_id = get_current_company_id()
        voter = get_active_voters_query(company_id).filter_by(id=voter_id).first_or_404()
        registrations = VoterRegistration.query.filter_by(
            voter_id=voter_id, company_id=company_id
        ).filter(VoterRegistration.status != 'deleted'
        ).order_by(VoterRegistration.registered_at.desc()).all()
    
    serialized_regs = []
    for reg in registrations:
        serialized_regs.append({
            'id': reg.id,
            'registration_id': reg.registration_id,
            'election_id': reg.election_id,
            'election_title': reg.election.title,
            'status': reg.status,
            'registration_type': reg.registration_type,
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
            'approved_at': reg.approved_at.isoformat() if reg.approved_at else None,
            'is_eligible': reg.is_eligible_to_vote,
            'verification_level': reg.verification_level_met
        })
    
    return jsonify({'registrations': serialized_regs})

@voters_bp.route('/<int:voter_id>/votes', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_votes(voter_id):
    """Get voter's voting history"""
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).filter(Voter.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        voter = get_active_voters_query(company_id).filter_by(id=voter_id).first_or_404()
    
    from app.models.vote import Vote
    votes = Vote.query.filter_by(voter_id=voter_id
    ).filter(Vote.status != STATUS_INACTIVE
    ).order_by(Vote.vote_cast_time.desc()).all()
    
    serialized_votes = []
    for vote in votes:
        serialized_votes.append({
            'id': vote.id,
            'vote_id': vote.vote_id,
            'tracking_code': vote.tracking_code,
            'election_id': vote.election_id,
            'election_title': vote.election.title,
            'ballot_id': vote.ballot_id,
            'ballot_title': vote.ballot.title,
            'vote_cast_time': vote.vote_cast_time.isoformat() if vote.vote_cast_time else None,
            'vote_status': vote.vote_status,
            'vote_method': vote.vote_method,
            'is_verified': vote.is_verified,
            'verification_level': vote.verification_level
        })
    
    return jsonify({'votes': serialized_votes})

@voters_bp.route('/stats', methods=['GET'])
@require_permission('Voters', 'view')
def get_voter_stats():
    """Get voter statistics for the company"""
    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        query_filter = (Voter.company_id == req_company_id, Voter.status == 1) if req_company_id else (Voter.status == 1,)
        total_voters = Voter.query.filter(*query_filter).count()
        verified_voters = Voter.query.filter(*query_filter, Voter.is_verified == True).count()
        unverified_voters = total_voters - verified_voters
        
        verification_levels = db.session.query(
            Voter.verification_level,
            db.func.count(Voter.id).label('count')
        ).filter(*query_filter).group_by(Voter.verification_level).all()
        
        voter_types = db.session.query(
            Voter.voter_type,
            db.func.count(Voter.id).label('count')
        ).filter(*query_filter).group_by(Voter.voter_type).all()
    else:
        company_id = get_current_company_id()
        total_voters = Voter.query.filter_by(company_id=company_id, status=1).count()
        verified_voters = Voter.query.filter_by(company_id=company_id, is_verified=True, status=1).count()
        unverified_voters = total_voters - verified_voters
        
        verification_levels = db.session.query(
            Voter.verification_level,
            db.func.count(Voter.id).label('count')
        ).filter_by(company_id=company_id, status=1).group_by(Voter.verification_level).all()
        
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
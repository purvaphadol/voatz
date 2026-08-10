from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.voter_registration import VoterRegistration
from app.models.voter import Voter
from app.models.election import Election
from app.models.user import User
from app.utils import get_current_company_id, require_permission, get_current_user, is_administrator
from app.utils.query_helpers import STATUS_INACTIVE
from app.utils.validators import parse_pagination
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from sqlalchemy import or_
from datetime import datetime, timezone

voter_registrations_bp = Blueprint('voter_registrations', __name__)

@voter_registrations_bp.route('/', methods=['GET'])
@require_permission('VoterRegistrations', 'view')
def list_voter_registrations():
    """List all voter registrations with filtering and pagination"""
    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        if req_company_id:
            query = VoterRegistration.query.join(Voter).outerjoin(User).join(Election).filter(
                VoterRegistration.company_id == req_company_id,
                VoterRegistration.status != 'deleted',
                Voter.status != STATUS_INACTIVE,
                Election.status != 'cancelled'
            )
            base = VoterRegistration.query.join(Voter).join(Election).filter(
                VoterRegistration.company_id == req_company_id,
                VoterRegistration.status != 'deleted',
                Voter.status != STATUS_INACTIVE,
                Election.status != 'cancelled'
            )
        else:
            query = VoterRegistration.query.join(Voter).outerjoin(User).join(Election).filter(
                VoterRegistration.status != 'deleted',
                Voter.status != STATUS_INACTIVE,
                Election.status != 'cancelled'
            )
            base = VoterRegistration.query.join(Voter).join(Election).filter(
                VoterRegistration.status != 'deleted',
                Voter.status != STATUS_INACTIVE,
                Election.status != 'cancelled'
            )
    else:
        company_id = get_current_company_id()
        query = VoterRegistration.query.join(Voter).outerjoin(User).join(Election).filter(
            VoterRegistration.company_id == company_id,
            VoterRegistration.status != 'deleted',
            Voter.status != STATUS_INACTIVE,
            Election.status != 'cancelled'
        )
        base = VoterRegistration.query.join(Voter).join(Election).filter(
            VoterRegistration.company_id == company_id,
            VoterRegistration.status != 'deleted',
            Voter.status != STATUS_INACTIVE,
            Election.status != 'cancelled'
        )
    search = request.args.get('search')
    election_id = request.args.get('election_id')
    voter_id = request.args.get('voter_id')
    status = request.args.get('status')
    registration_type = request.args.get('registration_type')
    verification_level = request.args.get('verification_level')
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    if search:
        query = query.filter(or_(
            VoterRegistration.registration_id.ilike(f'%{search}%'),
            User.name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            Voter.voter_id.ilike(f'%{search}%'),
            Election.title.ilike(f'%{search}%')
        ))
    
    if election_id:
        query = query.filter(VoterRegistration.election_id == election_id)
    
    if voter_id:
        query = query.filter(VoterRegistration.voter_id == voter_id)
    
    if status:
        query = query.filter(VoterRegistration.status == status)
    
    if registration_type:
        query = query.filter(VoterRegistration.registration_type == registration_type)
    
    if verification_level:
        query = query.filter(VoterRegistration.verification_level_met == verification_level)

    pagination = query.order_by(VoterRegistration.registered_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    registrations = pagination.items
    
    return jsonify({
        'data': [{
            'id': r.id,
            'registration_id': r.registration_id,
            'voter_id': r.voter_id,
            'voter_name': r.voter.display_name,
            'voter_email': r.voter.display_email,
            'voter_phone': r.voter.phone_number,
            'election_id': r.election_id,
            'election_title': r.election.title,
            'status': r.status,
            'registration_type': r.registration_type,
            'registered_at': r.registered_at.isoformat(),
            'approved_at': r.approved_at.isoformat() if r.approved_at else None,
            'rejected_at': r.rejected_at.isoformat() if r.rejected_at else None,
            'expires_at': r.expires_at.isoformat() if r.expires_at else None,
            'verification_level_met': r.verification_level_met,
            'required_verification_level': r.required_verification_level,
            'verification_completion_percentage': r.verification_completion_percentage,
            'is_eligible': r.is_eligible_to_vote,
            'eligibility_verified': r.eligibility_verified,
            'identity_verified': r.identity_verified,
            'address_verified': r.address_verified,
            'age_verified': r.age_verified,
            'jurisdiction': r.jurisdiction,
            'registration_source': r.registration_source,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None
        } for r in registrations],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': {
            'total_registrations': pagination.total,
            'approved_registrations': base.filter_by(status='approved').count(),
            'pending_registrations': base.filter_by(status='pending').count(),
            'rejected_registrations': base.filter_by(status='rejected').count(),
            'eligible_voters': base.filter_by(status='approved').filter(
                VoterRegistration.verification_level_met.in_(['standard', 'full'])
            ).count()
        }
    })

@voter_registrations_bp.route('/', methods=['POST'])
@require_permission('VoterRegistrations', 'create')
@audit_action('create_voter_registration', module='VoterRegistrations', description='Created voter registration')
def create_voter_registration():
    """Create a new voter registration"""
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('voter_id') or not data.get('election_id'):
        return jsonify({'error': 'voter_id and election_id are required'}), 400
    
    try:
        voter_id = int(data['voter_id'])
        election_id = int(data['election_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'voter_id and election_id must be valid integers'}), 400
    
    # Validate voter exists and belongs to company
    if is_administrator():
        voter = Voter.query.filter_by(id=voter_id).first()
        election = Election.query.filter_by(id=election_id).first()
    else:
        company_id = get_current_company_id()
        voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first()

    if not voter:
        return jsonify({'error': 'Voter not found'}), 404
    
    if not election:
        return jsonify({'error': 'Election not found'}), 404
    
    company_id = election.company_id
    
    # Check if voter is already registered for this election
    existing_registration = VoterRegistration.query.filter_by(
        voter_id=voter_id,
        election_id=election_id
    ).first()
    if existing_registration:
        return jsonify({'error': 'Voter is already registered for this election'}), 400
    
    # Check registration deadline
    if election.registration_deadline and datetime.now(timezone.utc) > election.registration_deadline:
        return jsonify({'error': 'Registration deadline has passed'}), 400
    
    # Create voter registration
    registration = VoterRegistration()
    registration.company_id = company_id
    registration.voter_id = voter_id
    registration.election_id = election_id
    registration.generate_registration_id()
    while VoterRegistration.query.filter_by(registration_id=registration.registration_id).first():
        registration.generate_registration_id()
    registration.registration_type = data.get('registration_type', 'standard')
    registration.registered_at = datetime.now(timezone.utc)
    
    # Set initial verification requirements
    registration.required_verification_level = data.get('required_verification_level', 'standard')
    registration.eligibility_verified = data.get('eligibility_verified', False)
    registration.identity_verified = data.get('identity_verified', False)
    registration.address_verified = data.get('address_verified', False)
    registration.age_verified = data.get('age_verified', False)
    
    # Geographic and jurisdictional
    registration.registered_address = data.get('registered_address', voter.registered_address)
    registration.jurisdiction = data.get('jurisdiction', voter.jurisdiction)
    registration.precinct = data.get('precinct')
    registration.district = data.get('district')
    
    # Preferences and accommodations
    registration.preferred_language = data.get('preferred_language', 'en')
    registration.accessibility_needs = data.get('accessibility_needs')
    registration.special_accommodations = data.get('special_accommodations')
    registration.notification_preferences = data.get('notification_preferences')
    
    # Registration source
    registration.registration_source = data.get('registration_source', 'admin_portal')
    registration.registration_method = data.get('registration_method', 'admin_registration')
    
    # Device and session information
    registration.device_id = data.get('device_id')
    registration.ip_address = request.remote_addr
    registration.user_agent = request.headers.get('User-Agent')
    registration.location_data = data.get('location_data')
    
    # Update verification level based on checks
    registration.update_verification_level()
    
    # Set initial status
    registration.status = data.get('status', 'pending')
    
    # Add audit event
    registration.add_audit_event('registration_created', 'Voter registration created')
    
    set_audit_fields(registration, is_create=True)
    
    db.session.add(registration)
    db.session.flush()
    return safe_commit((jsonify({
        'message': 'Voter registration created successfully',
        'registration_id': registration.registration_id,
        'id': registration.id
    }), 201), 'Failed to create voter registration')

@voter_registrations_bp.route('/<int:registration_id>', methods=['GET'])
@require_permission('VoterRegistrations', 'view')
def get_voter_registration(registration_id):
    """Get detailed voter registration information"""
    company_id = get_current_company_id()
    registration = VoterRegistration.query.join(Voter).outerjoin(User).join(Election).filter(
        VoterRegistration.id == registration_id,
        VoterRegistration.company_id == company_id,
        VoterRegistration.status != 'deleted',
        Voter.status != STATUS_INACTIVE,
        Election.status != str(STATUS_INACTIVE)
    ).first_or_404()
    
    return jsonify({
        'id': registration.id,
        'registration_id': registration.registration_id,
        'voter_id': registration.voter_id,
        'voter_name': registration.voter.display_name,
        'voter_email': registration.voter.display_email,
        'voter_phone': registration.voter.phone_number,
        'voter_verification_level': registration.voter.verification_level,
        'election_id': registration.election_id,
        'election_title': registration.election.title,
        'election_status': registration.election.status,
        'status': registration.status,
        'registration_type': registration.registration_type,
        'registered_at': registration.registered_at.isoformat(),
        'approved_at': registration.approved_at.isoformat() if registration.approved_at else None,
        'rejected_at': registration.rejected_at.isoformat() if registration.rejected_at else None,
        'expires_at': registration.expires_at.isoformat() if registration.expires_at else None,
        'processed_by': registration.processed_by,
        'approval_notes': registration.approval_notes,
        'rejection_reason': registration.rejection_reason,
        'verification_level_met': registration.verification_level_met,
        'required_verification_level': registration.required_verification_level,
        'verification_completion_percentage': registration.verification_completion_percentage,
        'is_eligible': registration.is_eligible_to_vote,
        'eligibility_verified': registration.eligibility_verified,
        'identity_verified': registration.identity_verified,
        'address_verified': registration.address_verified,
        'age_verified': registration.age_verified,
        'registered_address': registration.registered_address,
        'jurisdiction': registration.jurisdiction,
        'precinct': registration.precinct,
        'district': registration.district,
        'eligible_ballot_types': registration.eligible_ballot_types,
        'ballot_restrictions': registration.ballot_restrictions,
        'special_accommodations': registration.special_accommodations,
        'preferred_language': registration.preferred_language,
        'accessibility_needs': registration.accessibility_needs,
        'notification_preferences': registration.notification_preferences,
        'registration_source': registration.registration_source,
        'registration_method': registration.registration_method,
        'device_id': registration.device_id,
        'ip_address': registration.ip_address,
        'location_data': registration.location_data,
        'documents_submitted': registration.documents_submitted,
        'verification_documents': registration.verification_documents,
        'is_first_time_voter': registration.is_first_time_voter,
        'fraud_check_score': registration.fraud_check_score,
        'risk_assessment': registration.risk_assessment,
        'missing_requirements': registration.get_missing_requirements(),
        'audit_trail': registration.audit_trail,
        'created_at': registration.created_at.isoformat() if registration.created_at else None,
        'updated_at': registration.updated_at.isoformat() if registration.updated_at else None
    })

@voter_registrations_bp.route('/<int:registration_id>', methods=['PUT'])
@require_permission('VoterRegistrations', 'update')
def update_voter_registration(registration_id):
    """Update voter registration information"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    registration = VoterRegistration.query.filter_by(id=registration_id, company_id=company_id).filter(VoterRegistration.status != 'deleted').first_or_404()
    data = request.get_json()
    
    if 'voter_id' in data or 'election_id' in data:
        return jsonify({'error': 'voter_id and election_id cannot be changed after registration'}), 400
    
    # Update verification status
    if 'eligibility_verified' in data:
        registration.eligibility_verified = data['eligibility_verified']
    if 'identity_verified' in data:
        registration.identity_verified = data['identity_verified']
    if 'address_verified' in data:
        registration.address_verified = data['address_verified']
    if 'age_verified' in data:
        registration.age_verified = data['age_verified']
    
    # Update geographic information
    if 'registered_address' in data:
        registration.registered_address = data['registered_address']
    if 'jurisdiction' in data:
        registration.jurisdiction = data['jurisdiction']
    if 'precinct' in data:
        registration.precinct = data['precinct']
    if 'district' in data:
        registration.district = data['district']
    
    # Update preferences and accommodations
    if 'preferred_language' in data:
        registration.preferred_language = data['preferred_language']
    if 'accessibility_needs' in data:
        registration.accessibility_needs = data['accessibility_needs']
    if 'special_accommodations' in data:
        registration.special_accommodations = data['special_accommodations']
    if 'notification_preferences' in data:
        registration.notification_preferences = data['notification_preferences']
    
    # Update documents
    if 'documents_submitted' in data:
        registration.documents_submitted = data['documents_submitted']
    if 'verification_documents' in data:
        registration.verification_documents = data['verification_documents']
    
    # Update verification level based on changes
    registration.update_verification_level()
    
    # Add audit event
    registration.add_audit_event('registration_updated', 'Voter registration updated')
    
    set_audit_fields(registration, is_create=False)
    
    return safe_commit((jsonify({'message': 'Voter registration updated successfully'}), 200), 'Failed to update voter registration')

@voter_registrations_bp.route('/<int:registration_id>/approve', methods=['POST'])
@require_permission('VoterRegistrations', 'update')
@audit_action('approve_voter_registration', module='VoterRegistrations', description='Approved voter registration')
def approve_voter_registration(registration_id):
    """Approve a voter registration"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    registration = VoterRegistration.query.filter_by(id=registration_id, company_id=company_id).filter(VoterRegistration.status != 'deleted').first_or_404()
    data = request.get_json()
    
    # Validate registration can be approved
    if registration.status != 'pending':
        return jsonify({'error': 'Only pending registrations can be approved'}), 400
    
    # Check if minimum verification requirements are met
    if registration.verification_level_met not in ['standard', 'full']:
        return jsonify({'error': 'Minimum verification requirements not met'}), 400
    
    notes = data.get('notes') if data else None
    
    registration.approve_registration(current_user.id if current_user else None, notes)
    
    # Update election registered voter count
    election = Election.query.get(registration.election_id)
    if election:
        election.total_registered_voters = VoterRegistration.query.filter_by(
            election_id=registration.election_id,
            status='approved'
        ).count()
    
    return safe_commit((jsonify({'message': 'Voter registration approved successfully'}), 200), 'Failed to approve voter registration')

@voter_registrations_bp.route('/<int:registration_id>/reject', methods=['POST'])
@require_permission('VoterRegistrations', 'update')
@audit_action('reject_voter_registration', module='VoterRegistrations', description='Rejected voter registration')
def reject_voter_registration(registration_id):
    """Reject a voter registration"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    registration = VoterRegistration.query.filter_by(id=registration_id, company_id=company_id).filter(VoterRegistration.status != 'deleted').first_or_404()
    data = request.get_json()
    
    # Validate registration can be rejected
    if registration.status not in ['pending', 'approved']:
        return jsonify({'error': 'Only pending or approved registrations can be rejected'}), 400
    
    if not data or not data.get('reason'):
        return jsonify({'error': 'Rejection reason is required'}), 400
    
    reason = data['reason']
    
    registration.reject_registration(current_user.id if current_user else None, reason)
    
    # Update election registered voter count
    election = Election.query.get(registration.election_id)
    if election:
        election.total_registered_voters = VoterRegistration.query.filter_by(
            election_id=registration.election_id,
            status='approved'
        ).count()
    
    return safe_commit((jsonify({'message': 'Voter registration rejected successfully'}), 200), 'Failed to reject voter registration')

@voter_registrations_bp.route('/bulk-approve', methods=['POST'])
@require_permission('VoterRegistrations', 'update')
@audit_action('bulk_approve_registrations', module='VoterRegistrations', description='Bulk approved voter registrations')
def bulk_approve_registrations():
    """Bulk approve voter registrations"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('registration_ids'):
        return jsonify({'error': 'registration_ids array is required'}), 400
    
    registration_ids = data['registration_ids']
    notes = data.get('notes')
    
    registrations = VoterRegistration.query.filter(
        VoterRegistration.id.in_(registration_ids),
        VoterRegistration.company_id == company_id,
        VoterRegistration.status == 'pending'
    ).all()
    
    approved_count = 0
    for registration in registrations:
        # Check verification requirements
        if registration.verification_level_met in ['standard', 'full']:
            registration.approve_registration(current_user.id if current_user else None, notes)
            approved_count += 1
    
    # Update election registered voter counts
    election_ids_needed = list(set(r.election_id for r in registrations))
    elections_map = {e.id: e for e in Election.query.filter(Election.id.in_(election_ids_needed)).all()}
    
    for election_id in election_ids_needed:
        election = elections_map.get(election_id)
        if election:
            election.total_registered_voters = VoterRegistration.query.filter_by(
                election_id=election_id,
                status='approved'
            ).count()
    
    return safe_commit((jsonify({
        'message': f'Bulk approval completed',
        'approved_count': approved_count,
        'total_requested': len(registration_ids)
    }), 200), 'Failed to bulk approve registrations')

@voter_registrations_bp.route('/stats', methods=['GET'])
@require_permission('VoterRegistrations', 'view')
def get_voter_registration_stats():
    """Get voter registration statistics for the company"""
    company_id = get_current_company_id()
    
    total_registrations = VoterRegistration.query.filter_by(company_id=company_id).count()
    approved_registrations = VoterRegistration.query.filter_by(company_id=company_id, status='approved').count()
    pending_registrations = VoterRegistration.query.filter_by(company_id=company_id, status='pending').count()
    rejected_registrations = VoterRegistration.query.filter_by(company_id=company_id, status='rejected').count()
    
    # Registration types
    registration_types = db.session.query(
        VoterRegistration.registration_type,
        db.func.count(VoterRegistration.id).label('count')
    ).filter_by(company_id=company_id).group_by(VoterRegistration.registration_type).all()
    
    # Verification levels
    verification_levels = db.session.query(
        VoterRegistration.verification_level_met,
        db.func.count(VoterRegistration.id).label('count')
    ).filter_by(company_id=company_id).group_by(VoterRegistration.verification_level_met).all()
    
    # Registration statuses
    registration_statuses = db.session.query(
        VoterRegistration.status,
        db.func.count(VoterRegistration.id).label('count')
    ).filter_by(company_id=company_id).group_by(VoterRegistration.status).all()
    
    return jsonify({
        'total_registrations': total_registrations,
        'approved_registrations': approved_registrations,
        'pending_registrations': pending_registrations,
        'rejected_registrations': rejected_registrations,
        'approval_rate': (approved_registrations / total_registrations * 100) if total_registrations > 0 else 0,
        'registration_types': {rtype: count for rtype, count in registration_types},
        'verification_levels': {level: count for level, count in verification_levels},
        'registration_statuses': {status: count for status, count in registration_statuses}
    })
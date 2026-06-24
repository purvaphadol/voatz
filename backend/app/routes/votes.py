from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.vote import Vote
from app.models.voter import Voter
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.voter_registration import VoterRegistration
from app.utils import get_current_company_id, require_permission, get_current_user
from sqlalchemy import or_, and_
from datetime import datetime, timezone
import secrets
import string
import json
import logging

from app.utils.validators import parse_pagination
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action

logger = logging.getLogger(__name__)

votes_bp = Blueprint('votes', __name__)

@votes_bp.route('/', methods=['GET'])
@require_permission('Votes', 'view')
def list_votes():
    """List all votes with filtering and pagination"""
    company_id = get_current_company_id()
    search = request.args.get('search')
    election_id = request.args.get('election_id')
    ballot_id = request.args.get('ballot_id')
    voter_id = request.args.get('voter_id')
    vote_status = request.args.get('vote_status')
    vote_method = request.args.get('vote_method')
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    query = Vote.query.join(Voter).join(Election).join(Ballot).filter(Vote.company_id == company_id)
    
    if search:
        query = query.filter(or_(
            Vote.vote_id.ilike(f'%{search}%'),
            Vote.tracking_code.ilike(f'%{search}%'),
            Voter.voter_id.ilike(f'%{search}%')
        ))
    
    if election_id:
        query = query.filter(Vote.election_id == election_id)
    
    if ballot_id:
        query = query.filter(Vote.ballot_id == ballot_id)
    
    if voter_id:
        query = query.filter(Vote.voter_id == voter_id)
    
    if vote_status:
        query = query.filter(Vote.vote_status == vote_status)
    
    if vote_method:
        query = query.filter(Vote.vote_method == vote_method)

    pagination = query.order_by(Vote.vote_cast_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
    votes = pagination.items
    
    base = Vote.query.filter_by(company_id=company_id)
    summary = {
        'total_votes': pagination.total,
        'verified_votes': base.filter_by(vote_status='verified').count(),
        'counted_votes': base.filter_by(is_counted=True).count(),
        'pending_votes': base.filter_by(processing_status='pending').count()
    }
    
    return jsonify({
        'data': [{
            'id': v.id,
            'vote_id': v.vote_id,
            'tracking_code': v.tracking_code,
            'voter_id': v.voter_id,
            'voter_name': v.voter.display_name,
            'election_id': v.election_id,
            'election_title': v.election.title,
            'ballot_id': v.ballot_id,
            'ballot_title': v.ballot.title,
            'vote_cast_time': v.vote_cast_time.isoformat(),
            'vote_status': v.vote_status,
            'processing_status': v.processing_status,
            'vote_method': v.vote_method,
            'vote_type': v.vote_type,
            'is_counted': v.is_counted,
            'is_verified': v.is_verified,
            'verification_level': v.verification_level,
            'biometric_verified': v.biometric_verified,
            'device_verified': v.device_verified,
            'identity_verified': v.identity_verified,
            'created_at': v.created_at.isoformat() if v.created_at else None
        } for v in votes],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': summary
    })

@votes_bp.route('/', methods=['POST'])
@require_permission('Votes', 'create')
@audit_action('cast_vote', module='Votes')
def cast_vote():
    """Cast a vote (for testing or admin purposes)"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()

    if not data or not data.get('voter_id') or not data.get('ballot_id') or not data.get('vote_data'):
        return jsonify({'error': 'voter_id, ballot_id, and vote_data are required'}), 400

    try:
        ballot_id = int(data['ballot_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'ballot_id must be a valid integer'}), 400

    # voter_id can be either the string voter_id field or the integer id field
    voter_id = data['voter_id']

    if isinstance(voter_id, str):
        voter = Voter.query.filter_by(voter_id=voter_id, company_id=company_id).first()
    else:
        voter = Voter.query.filter_by(id=voter_id, company_id=company_id).first()

    if not voter:
        return jsonify({'error': 'Voter not found'}), 404

    # Validate ballot exists and belongs to company
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first()
    if not ballot:
        return jsonify({'error': 'Ballot not found'}), 404

    if not ballot.is_active:
        return jsonify({'error': 'Ballot is not available'}), 400
    if not ballot.is_published:
        return jsonify({'error': 'Ballot is not published'}), 400

    # Check if voter has already voted for this ballot
    existing_vote = Vote.query.filter_by(voter_id=voter.id, ballot_id=ballot_id).first()
    if existing_vote:
        return jsonify({'error': 'Voter has already voted for this ballot'}), 400

    # Check if election is active
    if not ballot.election.is_active:
        return jsonify({'error': 'Election is not active'}), 400

    # Check if voter is registered for this election
    registration = VoterRegistration.query.filter_by(
        voter_id=voter.id,
        election_id=ballot.election_id,
        status='approved'
    ).first()
    if not registration:
        return jsonify({'error': 'Voter is not registered for this election'}), 400

    # Enforce ballot jurisdiction restriction
    if ballot.jurisdiction_restriction:
        if not voter.jurisdiction or voter.jurisdiction.strip().lower() != ballot.jurisdiction_restriction.strip().lower():
            return jsonify({
                'error': f"This ballot is restricted to voters in '{ballot.jurisdiction_restriction}'"
            }), 403

    # Enforce ballot voter-type restriction (comma-separated list e.g. "standard,overseas")
    if ballot.voter_type_restriction:
        allowed_types = {t.strip().lower() for t in ballot.voter_type_restriction.split(',') if t.strip()}
        if allowed_types and (voter.voter_type or '').strip().lower() not in allowed_types:
            return jsonify({
                'error': f"This ballot is restricted to voter types: {ballot.voter_type_restriction}"
            }), 403

    # Generate unique vote ID and tracking code
    vote_id = generate_vote_id()
    while Vote.query.filter_by(vote_id=vote_id).first():
        vote_id = generate_vote_id()

    # Create vote
    vote = Vote()
    vote.company_id = company_id
    vote.election_id = ballot.election_id
    vote.ballot_id = ballot_id
    vote.voter_id = voter.id
    vote.vote_id = vote_id
    vote.vote_data = data['vote_data']
    vote.vote_method = data.get('vote_method', 'admin')
    vote.vote_type = data.get('vote_type', 'regular')
    vote.is_test_vote = data.get('is_test_vote', False)

    # Set timestamps FIRST (needed for hash generation)
    vote.vote_start_time = datetime.fromisoformat(data['vote_start_time'].replace('Z', '+00:00')) if data.get('vote_start_time') else None
    vote.vote_cast_time = datetime.now(timezone.utc)

    # Set verification status
    vote.biometric_verified = data.get('biometric_verified', False)
    vote.device_verified = data.get('device_verified', False)
    vote.identity_verified = data.get('identity_verified', False)
    vote.two_factor_verified = data.get('two_factor_verified', False)

    # Set device and session info
    vote.device_id = data.get('device_id')
    vote.device_fingerprint = data.get('device_fingerprint')
    vote.app_version = data.get('app_version')
    vote.operating_system = data.get('operating_system')
    vote.ip_address = request.remote_addr
    vote.user_agent = request.headers.get('User-Agent')
    vote.location_data = data.get('location_data')
    vote.timezone = data.get('timezone')

    # Generate tracking code and hashes
    vote.generate_tracking_code()
    vote.generate_vote_hash()
    vote.generate_verification_hash()

    # Explicitly set ballot relationship for validation
    vote.ballot = ballot
    is_valid, error_message = vote.validate_vote_data()
    if not is_valid:
        return jsonify({'error': error_message}), 400

    # Set initial status
    vote.vote_status = 'cast'
    vote.processing_status = 'pending'
    vote.is_counted = False
    vote.is_auditable = True

    vote.add_audit_event('vote_cast', 'Vote was cast', {
        'method': vote.vote_method,
        'selections': len(vote.get_selected_candidates()),
        'write_ins': len(vote.get_write_in_candidates())
    })

    set_audit_fields(vote, is_create=True)

    db.session.add(vote)
    db.session.flush()

    return safe_commit(
        (jsonify({
            'message': 'Vote cast successfully',
            'vote_id': vote.vote_id,
            'tracking_code': vote.tracking_code
        }), 201),
        'Failed to cast vote'
    )

@votes_bp.route('/<int:vote_id>', methods=['GET'])
@require_permission('Votes', 'view')
def get_vote(vote_id):
    """Get detailed vote information"""
    company_id = get_current_company_id()
    vote = Vote.query.join(Voter).join(Election).join(Ballot).filter(
        Vote.id == vote_id,
        Vote.company_id == company_id
    ).first_or_404()
    
    # Get selected candidates
    selected_candidates = []
    for candidate_id in vote.get_selected_candidates():
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            selected_candidates.append({
                'id': candidate.id,
                'name': candidate.name,
                'party': candidate.party,
                'party_abbreviation': candidate.party_abbreviation
            })
    
    return jsonify({
        'id': vote.id,
        'vote_id': vote.vote_id,
        'tracking_code': vote.tracking_code,
        'voter_id': vote.voter_id,
        'voter_name': vote.voter.display_name,
        'election_id': vote.election_id,
        'election_title': vote.election.title,
        'ballot_id': vote.ballot_id,
        'ballot_title': vote.ballot.title,
        'vote_cast_time': vote.vote_cast_time.isoformat(),
        'vote_start_time': vote.vote_start_time.isoformat() if vote.vote_start_time else None,
        'vote_processing_time': vote.vote_processing_time.isoformat() if vote.vote_processing_time else None,
        'vote_status': vote.vote_status,
        'processing_status': vote.processing_status,
        'vote_method': vote.vote_method,
        'vote_type': vote.vote_type,
        'is_test_vote': vote.is_test_vote,
        'is_counted': vote.is_counted,
        'is_verified': vote.is_verified,
        'verification_level': vote.verification_level,
        'biometric_verified': vote.biometric_verified,
        'device_verified': vote.device_verified,
        'identity_verified': vote.identity_verified,
        'two_factor_verified': vote.two_factor_verified,
        'device_id': vote.device_id,
        'app_version': vote.app_version,
        'operating_system': vote.operating_system,
        'ip_address': vote.ip_address,
        'location_data': vote.location_data,
        'timezone': vote.timezone,
        'vote_hash': vote.vote_hash,
        'verification_hash': vote.verification_hash,
        'selected_candidates': selected_candidates,
        'write_in_candidates': vote.get_write_in_candidates(),
        'audit_trail': vote.audit_trail,
        'error_count': vote.error_count,
        'error_messages': vote.error_messages,
        'created_at': vote.created_at.isoformat() if vote.created_at else None,
        'updated_at': vote.updated_at.isoformat() if vote.updated_at else None
    })

@votes_bp.route('/<int:vote_id>/verify', methods=['POST'])
@require_permission('Votes', 'update')
@audit_action('verify_vote', module='Votes')
def verify_vote(vote_id):
    """Verify a vote (admin function)"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    vote = Vote.query.filter_by(id=vote_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    verification_type = data.get('verification_type')  # biometric, device, identity, all
    
    if verification_type == 'biometric':
        vote.biometric_verified = True
        vote.add_audit_event('biometric_verified', 'Biometric verification completed')
    elif verification_type == 'device':
        vote.device_verified = True
        vote.add_audit_event('device_verified', 'Device verification completed')
    elif verification_type == 'identity':
        vote.identity_verified = True
        vote.add_audit_event('identity_verified', 'Identity verification completed')
    elif verification_type == 'all':
        vote.biometric_verified = True
        vote.device_verified = True
        vote.identity_verified = True
        vote.add_audit_event('full_verification', 'All verification types completed')
    
    # Update vote status if fully verified
    is_fully_verified = (vote.biometric_verified and 
                         vote.device_verified and 
                         vote.identity_verified)
    if is_fully_verified:
        vote.vote_status = 'verified'
        vote.processing_status = 'processed'
        vote.vote_processing_time = datetime.now(timezone.utc)
        vote.add_audit_event('vote_verified', 'Vote fully verified and processed')
    
    set_audit_fields(vote, is_create=False)
    
    return safe_commit(
        (jsonify({'message': f'Vote {verification_type} verification updated successfully'}), 200),
        'Failed to verify vote'
    )

@votes_bp.route('/<int:vote_id>/count', methods=['POST'])
@require_permission('Votes', 'update')
@audit_action('count_vote', module='Votes')
def count_vote(vote_id):
    """Count a vote (include in final tally)"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    vote = Vote.query.filter_by(id=vote_id, company_id=company_id).first_or_404()
    
    # Only count verified votes
    if not vote.is_verified:
        return jsonify({'error': 'Vote must be verified before counting'}), 400
    
    # Don't count twice
    if vote.is_counted:
        return jsonify({'error': 'Vote is already counted'}), 400
    
    vote.is_counted = True
    vote.vote_status = 'counted'
    vote.processing_status = 'processed'
    vote.vote_processing_time = datetime.now(timezone.utc)
    
    # Update candidate vote counts
    for candidate_id in vote.get_selected_candidates():
        candidate = db.session.get(Candidate, candidate_id)
        if candidate:
            candidate.total_votes_received += 1
    
    # Update ballot vote count
    ballot = db.session.get(Ballot, vote.ballot_id)
    if ballot:
        ballot.total_votes_cast += 1
    
    # Update election vote count
    election = db.session.get(Election, vote.election_id)
    if election:
        election.total_votes_cast += 1
    
    vote.add_audit_event('vote_counted', 'Vote included in final tally')
    
    set_audit_fields(vote, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Vote counted successfully'}), 200),
        'Failed to count vote'
    )

@votes_bp.route('/<int:vote_id>/flag', methods=['POST'])
@require_permission('Votes', 'update')
@audit_action('flag_vote', module='Votes')
def flag_vote(vote_id):
    """Flag a vote for review"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    vote = Vote.query.filter_by(id=vote_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    reason = data.get('reason', 'Manual flag')
    
    vote.vote_status = 'flagged'
    vote.processing_status = 'auditing'
    
    # Add warning flag
    if not vote.warning_flags:
        vote.warning_flags = []
    
    vote.warning_flags.append({
        'flag_type': 'manual',
        'reason': reason,
        'flagged_by': current_user.id if current_user else None,
        'flagged_at': datetime.now(timezone.utc).isoformat()
    })
    
    vote.add_audit_event('vote_flagged', f'Vote flagged for review: {reason}')
    
    set_audit_fields(vote, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Vote flagged successfully'}), 200),
        'Failed to flag vote'
    )

@votes_bp.route('/tracking/<tracking_code>', methods=['GET'])
def track_vote(tracking_code):
    """Track a vote using tracking code (public endpoint)"""
    vote = Vote.query.filter_by(tracking_code=tracking_code).first_or_404()
    
    # Return limited public information
    return jsonify({
        'tracking_code': vote.tracking_code,
        'election_title': vote.election.title,
        'ballot_title': vote.ballot.title,
        'vote_cast_time': vote.vote_cast_time.isoformat(),
        'vote_status': vote.vote_status,
        'is_counted': vote.is_counted,
        'is_verified': vote.is_verified,
        'verification_level': vote.verification_level,
        'receipt_generated': vote.receipt_generated,
        'receipt_code': vote.receipt_code if vote.receipt_generated else None
    })

@votes_bp.route('/stats', methods=['GET'])
@require_permission('Votes', 'view')
def get_vote_stats():
    """Get vote statistics for the company"""
    company_id = get_current_company_id()
    
    total_votes = Vote.query.filter_by(company_id=company_id).count()
    verified_votes = Vote.query.filter_by(company_id=company_id, vote_status='verified').count()
    counted_votes = Vote.query.filter_by(company_id=company_id, is_counted=True).count()
    flagged_votes = Vote.query.filter_by(company_id=company_id, vote_status='flagged').count()
    
    # Vote methods
    vote_methods = db.session.query(
        Vote.vote_method,
        db.func.count(Vote.id).label('count')
    ).filter_by(company_id=company_id).group_by(Vote.vote_method).all()
    
    # Vote statuses
    vote_statuses = db.session.query(
        Vote.vote_status,
        db.func.count(Vote.id).label('count')
    ).filter_by(company_id=company_id).group_by(Vote.vote_status).all()
    
    # Verification counts (using actual DB columns instead of property)
    biometric_verified_count = Vote.query.filter_by(company_id=company_id, biometric_verified=True).count()
    device_verified_count = Vote.query.filter_by(company_id=company_id, device_verified=True).count()
    identity_verified_count = Vote.query.filter_by(company_id=company_id, identity_verified=True).count()
    two_factor_verified_count = Vote.query.filter_by(company_id=company_id, two_factor_verified=True).count()
    
    return jsonify({
        'total_votes': total_votes,
        'verified_votes': verified_votes,
        'counted_votes': counted_votes,
        'flagged_votes': flagged_votes,
        'pending_votes': total_votes - verified_votes - flagged_votes,
        'verification_rate': (verified_votes / total_votes * 100) if total_votes > 0 else 0,
        'vote_methods': {method: count for method, count in vote_methods},
        'vote_statuses': {status: count for status, count in vote_statuses},
        'verification_types': {
            'biometric_verified': biometric_verified_count,
            'device_verified': device_verified_count,
            'identity_verified': identity_verified_count,
            'two_factor_verified': two_factor_verified_count
        }
    })

@votes_bp.route('/bulk-verify', methods=['POST'])
@require_permission('Votes', 'update')
@audit_action('bulk_verify_votes', module='Votes')
def bulk_verify_votes():
    """Bulk verify votes"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('vote_ids'):
        return jsonify({'error': 'vote_ids array is required'}), 400
    
    vote_ids = data['vote_ids']
    verification_type = data.get('verification_type', 'all')
    
    votes = Vote.query.filter(Vote.id.in_(vote_ids), Vote.company_id == company_id).all()
    
    updated_count = 0
    for vote in votes:
        if verification_type in ['biometric', 'all']:
            vote.biometric_verified = True
        if verification_type in ['device', 'all']:
            vote.device_verified = True
        if verification_type in ['identity', 'all']:
            vote.identity_verified = True
        
        is_fully_verified = (vote.biometric_verified and 
                             vote.device_verified and 
                             vote.identity_verified)
        if is_fully_verified:
            vote.vote_status = 'verified'
            vote.processing_status = 'processed'
            vote.vote_processing_time = datetime.now(timezone.utc)
        
        vote.add_audit_event('bulk_verified', f'Bulk {verification_type} verification')
        set_audit_fields(vote, is_create=False)
        updated_count += 1
    
    return safe_commit(
        (jsonify({
            'message': f'Bulk verification completed',
            'updated_count': updated_count,
            'total_requested': len(vote_ids)
        }), 200),
        'Failed to bulk verify votes'
    )

@votes_bp.route('/history', methods=['GET'])
@jwt_required()
def get_user_vote_history():
    """Get voting history for the current user"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    company_id = current_user.company_id
    
    # Find the voter profile for this user
    voter = Voter.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if not voter:
        return jsonify({'error': 'Voter profile not found'}), 404
    
    # Get pagination parameters
    page, per_page, error = parse_pagination(request)
    if error:
        return error
        
    election_id = request.args.get('election_id')
    
    # Build query for user's votes
    query = Vote.query.join(Election).join(Ballot).filter(
        Vote.voter_id == voter.id,
        Vote.company_id == company_id
    )
    
    # Filter by election if specified
    if election_id:
        query = query.filter(Vote.election_id == election_id)
    
    # Order by most recent first
    pagination = query.order_by(Vote.vote_cast_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    votes = pagination.items
    
    voter_base = Vote.query.filter_by(voter_id=voter.id, company_id=company_id)
    summary = {
        'total_votes_cast': pagination.total,
        'verified_votes': voter_base.filter_by(vote_status='verified').count(),
        'counted_votes': voter_base.filter_by(is_counted=True).count(),
        'pending_votes': voter_base.filter_by(processing_status='pending').count(),
        'elections_participated': db.session.query(db.func.count(db.distinct(Vote.election_id))).filter_by(voter_id=voter.id, company_id=company_id).scalar()
    }
    
    # Return user's voting history (without sensitive vote data)
    return jsonify({
        'data': [{
            'id': v.id,
            'vote_id': v.vote_id,
            'tracking_code': v.tracking_code,
            'election_id': v.election_id,
            'election_title': v.election.title,
            'election_type': v.election.election_type,
            'ballot_id': v.ballot_id,
            'ballot_title': v.ballot.title,
            'position_title': v.ballot.position_title,
            'vote_cast_time': v.vote_cast_time.isoformat(),
            'vote_status': v.vote_status,
            'processing_status': v.processing_status,
            'vote_method': v.vote_method,
            'vote_type': v.vote_type,
            'is_counted': v.is_counted,
            'is_verified': v.is_verified,
            'verification_level': v.verification_level,
            'biometric_verified': v.biometric_verified,
            'device_verified': v.device_verified,
            'identity_verified': v.identity_verified,
            'receipt_generated': v.receipt_generated,
            'receipt_code': v.receipt_code if v.receipt_generated else None,
            'created_at': v.created_at.isoformat() if v.created_at else None
        } for v in votes],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'voter_info': {
            'voter_id': voter.voter_id,
            'verification_level': voter.verification_level,
            'is_verified': voter.is_verified
        },
        'summary': summary
    })

def generate_vote_id():
    """Generate a unique vote ID"""
    alphabet = string.ascii_uppercase + string.digits
    return 'VOTE-' + ''.join(secrets.choice(alphabet) for _ in range(12)) 
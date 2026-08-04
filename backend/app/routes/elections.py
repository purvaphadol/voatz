from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.election import Election
from app.models.company import Company
from app.models.ballot import Ballot
from app.models.voter_registration import VoterRegistration
from app.models.vote import Vote
from app.utils import get_current_company_id, require_permission, get_current_user, is_administrator
from app.utils.validators import parse_pagination, validate_election_input
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from app.utils.query_helpers import get_active_elections_query, get_election_registrations_query
from sqlalchemy import or_, and_
from datetime import datetime, timedelta, timezone
import secrets
import string

elections_bp = Blueprint('elections', __name__)

def _safe_prop(obj, prop, default=None):
    """Safely access a model property that may raise due to tz-naive/aware mismatch."""
    try:
        return getattr(obj, prop)
    except TypeError:
        return default

@elections_bp.route('/', methods=['GET'])
@require_permission('Elections', 'view')
def list_elections():
    """List all elections with filtering and pagination"""
    search = request.args.get('search')
    election_type = request.args.get('election_type')
    status = request.args.get('status')
    is_active = request.args.get('is_active')
    show_cancelled = request.args.get('show_cancelled')
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        if req_company_id:
            if show_cancelled == 'true':
                query = Election.query.filter(Election.company_id == req_company_id)
            else:
                query = get_active_elections_query(req_company_id)
            base = get_active_elections_query(req_company_id)
        else:
            if show_cancelled == 'true':
                query = Election.query
            else:
                query = Election.query.filter(Election.status != 'cancelled')
            base = Election.query.filter(Election.status != 'cancelled')
    else:
        company_id = get_current_company_id()
        if show_cancelled == 'true':
            query = Election.query.filter(Election.company_id == company_id)
        else:
            query = get_active_elections_query(company_id)
        base = get_active_elections_query(company_id)
    
    if search:
        query = query.filter(or_(
            Election.title.ilike(f'%{search}%'),
            Election.description.ilike(f'%{search}%'),
            Election.election_code.ilike(f'%{search}%')
        ))
    
    if election_type:
        query = query.filter(Election.election_type == election_type)
    
    if status:
        # Handle mobile app's 'scheduled' status filter
        if status == 'scheduled':
            # Map 'scheduled' to draft and published elections (upcoming)
            query = query.filter(Election.status.in_(['draft', 'published']))
        else:
            query = query.filter(Election.status == status)
    
    if is_active is not None:
        now = datetime.now(timezone.utc)
        if is_active.lower() == 'true':
            query = query.filter(and_(
                Election.start_date <= now,
                Election.end_date >= now,
                Election.status == 'active'
            ))
        else:
            query = query.filter(or_(
                Election.start_date > now,
                Election.end_date < now,
                Election.status != 'active'
            ))

    pagination = query.order_by(Election.start_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    elections = pagination.items

    # Full dataset counts using base query
    now = datetime.now(timezone.utc)
    summary = {
        'total_elections': pagination.total,
        'active_elections': base.filter_by(status='active').count(),
        'draft_elections': base.filter_by(status='draft').count(),
        'completed_elections': base.filter_by(status='completed').count(),
        'upcoming_elections': base.filter(Election.start_date > now).count()
    }
    
    return jsonify({
        'data': [{
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'election_code': e.election_code,
            'election_type': e.election_type,
            'election_category': e.election_category,
            'start_date': e.start_date.isoformat(),
            'end_date': e.end_date.isoformat(),
            'registration_deadline': e.registration_deadline.isoformat() if e.registration_deadline else None,
            'status': e.status,
            'is_public': e.is_public,
            'is_test_election': e.is_test_election,
            'total_registered_voters': e.total_registered_voters,
            'total_votes_cast': e.total_votes_cast,
            'turnout_percentage': e.turnout_percentage,
            'results_published': e.results_published,
            'voting_window_status': _safe_prop(e, 'voting_window_status', 'unknown'),
            'is_active': _safe_prop(e, 'is_active', False),
            'created_at': e.created_at.isoformat() if e.created_at else None,
            'updated_at': e.updated_at.isoformat() if e.updated_at else None
        } for e in elections],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': summary
    })

@elections_bp.route('/', methods=['POST'])
@require_permission('Elections', 'create')
@audit_action('create_election', module='Elections')
def create_election():
    """Create a new election"""
    data = request.get_json() or {}
    if is_administrator():
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id is required for platform Administrators'}), 400
    else:
        company_id = get_current_company_id()
    current_user = get_current_user()
    
    cleaned_data, err = validate_election_input(data, is_create=True)
    if err:
        return err

    if not data.get('election_type'):
        return jsonify({'error': 'election_type is required'}), 400

    start_date = cleaned_data['start_date']
    end_date = cleaned_data['end_date']
    
    # Generate unique election code
    election_code = generate_election_code()
    while Election.query.filter_by(election_code=election_code, company_id=company_id).first():
        election_code = generate_election_code()
    
    # Create election
    election = Election()
    election.company_id = company_id
    election.title = data['title']
    election.description = data.get('description', '')
    election.election_code = election_code
    election.election_type = data['election_type']
    election.election_category = data.get('election_category')
    election.start_date = start_date
    election.end_date = end_date
    
    # Optional fields
    if data.get('registration_deadline'):
        election.registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
    
    if data.get('early_voting_start'):
        election.early_voting_start = datetime.fromisoformat(data['early_voting_start'].replace('Z', '+00:00'))
    
    if data.get('early_voting_end'):
        election.early_voting_end = datetime.fromisoformat(data['early_voting_end'].replace('Z', '+00:00'))
    
    # Configuration
    election.allow_early_voting = data.get('allow_early_voting', False)
    election.require_biometric = data.get('require_biometric', True)
    election.require_photo_id = data.get('require_photo_id', True)
    election.allow_overseas_voting = data.get('allow_overseas_voting', False)
    election.allow_military_voting = data.get('allow_military_voting', False)
    election.max_votes_per_voter = data.get('max_votes_per_voter', 1)
    election.allow_vote_changes = data.get('allow_vote_changes', False)
    election.require_all_ballots = data.get('require_all_ballots', False)
    election.jurisdiction = data.get('jurisdiction')
    election.geographic_scope = data.get('geographic_scope')
    election.eligible_voter_types = data.get('eligible_voter_types', 'standard')
    election.is_public = data.get('is_public', True)
    election.is_test_election = data.get('is_test_election', False)
    election.audit_enabled = data.get('audit_enabled', True)
    election.paper_trail_required = data.get('paper_trail_required', True)
    
    set_audit_fields(election, is_create=True)
    
    db.session.add(election)
    db.session.flush()
    return safe_commit(
        (jsonify({
            'message': 'Election created successfully',
            'election_id': election.id,
            'election_code': election.election_code
        }), 201),
        'Failed to create election'
    )

@elections_bp.route('/<int:election_id>', methods=['GET'])
@require_permission('Elections', 'view')
def get_election(election_id):
    """Get detailed election information"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    
    # Get related statistics
    ballot_count = Ballot.query.filter_by(election_id=election_id).count()
    registration_count = VoterRegistration.query.filter_by(election_id=election_id).count()
    vote_count = Vote.query.filter_by(election_id=election_id).count()
    
    return jsonify({
        'id': election.id,
        'title': election.title,
        'description': election.description,
        'election_code': election.election_code,
        'election_type': election.election_type,
        'election_category': election.election_category,
        'start_date': election.start_date.isoformat(),
        'end_date': election.end_date.isoformat(),
        'registration_deadline': election.registration_deadline.isoformat() if election.registration_deadline else None,
        'early_voting_start': election.early_voting_start.isoformat() if election.early_voting_start else None,
        'early_voting_end': election.early_voting_end.isoformat() if election.early_voting_end else None,
        'allow_early_voting': election.allow_early_voting,
        'require_biometric': election.require_biometric,
        'require_photo_id': election.require_photo_id,
        'allow_overseas_voting': election.allow_overseas_voting,
        'allow_military_voting': election.allow_military_voting,
        'max_votes_per_voter': election.max_votes_per_voter,
        'allow_vote_changes': election.allow_vote_changes,
        'require_all_ballots': election.require_all_ballots,
        'jurisdiction': election.jurisdiction,
        'geographic_scope': election.geographic_scope,
        'eligible_voter_types': election.eligible_voter_types,
        'status': election.status,
        'is_public': election.is_public,
        'is_test_election': election.is_test_election,
        'results_published': election.results_published,
        'results_published_at': election.results_published_at.isoformat() if election.results_published_at else None,
        'total_registered_voters': election.total_registered_voters,
        'total_votes_cast': election.total_votes_cast,
        'turnout_percentage': election.turnout_percentage,
        'audit_enabled': election.audit_enabled,
        'paper_trail_required': election.paper_trail_required,
        'voting_window_status': _safe_prop(election, 'voting_window_status', 'unknown'),
        'is_active': _safe_prop(election, 'is_active', False),
        'is_early_voting_active': _safe_prop(election, 'is_early_voting_active', False),
        'statistics': {
            'ballot_count': ballot_count,
            'registration_count': registration_count,
            'vote_count': vote_count
        },
        'created_at': election.created_at.isoformat() if election.created_at else None,
        'updated_at': election.updated_at.isoformat() if election.updated_at else None
    })

@elections_bp.route('/<int:election_id>', methods=['PUT'])
@require_permission('Elections', 'update')
@audit_action('update_election', module='Elections')
def update_election(election_id):
    """Update election information"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    current_user = get_current_user()
    data = request.get_json() or {}
    cleaned_data, err = validate_election_input(data, is_create=False)
    if err:
        return err

    # Only block date changes on active elections
    if election.status == 'active':
        if any(k in data for k in ['start_date', 'end_date', 'registration_deadline']):
            return jsonify({'error': 'Cannot modify election dates while election is active'}), 400
    
    # Update basic fields
    if data.get('title'):
        election.title = data['title']
    if data.get('description'):
        election.description = data['description']
    if data.get('election_type'):
        election.election_type = data['election_type']
    if data.get('election_category'):
        election.election_category = data['election_category']
    
    # Update dates
    if data.get('start_date'):
        election.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
    if data.get('end_date'):
        election.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
    if data.get('registration_deadline'):
        election.registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
    if data.get('early_voting_start'):
        election.early_voting_start = datetime.fromisoformat(data['early_voting_start'].replace('Z', '+00:00'))
    if data.get('early_voting_end'):
        election.early_voting_end = datetime.fromisoformat(data['early_voting_end'].replace('Z', '+00:00'))
    
    # Update configuration
    if 'allow_early_voting' in data:
        election.allow_early_voting = data['allow_early_voting']
    if 'require_biometric' in data:
        election.require_biometric = data['require_biometric']
    if 'require_photo_id' in data:
        election.require_photo_id = data['require_photo_id']
    if 'allow_overseas_voting' in data:
        election.allow_overseas_voting = data['allow_overseas_voting']
    if 'allow_military_voting' in data:
        election.allow_military_voting = data['allow_military_voting']
    if 'max_votes_per_voter' in data:
        election.max_votes_per_voter = data['max_votes_per_voter']
    if 'allow_vote_changes' in data:
        election.allow_vote_changes = data['allow_vote_changes']
    if 'require_all_ballots' in data:
        election.require_all_ballots = data['require_all_ballots']
    if 'jurisdiction' in data:
        election.jurisdiction = data['jurisdiction']
    if 'geographic_scope' in data:
        election.geographic_scope = data['geographic_scope']
    if 'eligible_voter_types' in data:
        election.eligible_voter_types = data['eligible_voter_types']
    if 'is_public' in data:
        election.is_public = data['is_public']
    if 'audit_enabled' in data:
        election.audit_enabled = data['audit_enabled']
    if 'paper_trail_required' in data:
        election.paper_trail_required = data['paper_trail_required']
    
    # Update status
    if data.get('status'):
        election.status = data['status']
    
    set_audit_fields(election, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Election updated successfully'}), 200),
        'Failed to update election'
    )

@elections_bp.route('/<int:election_id>', methods=['DELETE'])
@require_permission('Elections', 'delete')
@audit_action('delete_election', module='Elections')
def delete_election(election_id):
    """Delete election (soft delete)"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    
    # Don't allow deletion of active elections
    if election.status == 'active':
        return jsonify({'error': 'Cannot delete active elections'}), 400
    
    # Check if there are votes cast
    vote_count = Vote.query.filter_by(election_id=election_id).count()
    if vote_count > 0:
        return jsonify({'error': 'Cannot delete elections with votes already cast'}), 400
    
    # Soft delete by updating status
    election.status = 'cancelled'
    set_audit_fields(election, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Election deleted successfully'}), 200),
        'Failed to delete election'
    )

@elections_bp.route('/<int:election_id>/activate', methods=['POST'])
@require_permission('Elections', 'update')
@audit_action('activate_election', module='Elections')
def activate_election(election_id):
    """Activate an election for voting"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    current_user = get_current_user()
    
    # Validate election can be activated
    if election.status != 'draft':
        return jsonify({'error': 'Only draft elections can be activated'}), 400
    
    # Check if election has ballots
    ballot_count = Ballot.query.filter_by(election_id=election_id, is_active=True).count()
    if ballot_count == 0:
        return jsonify({'error': 'Election must have at least one active ballot'}), 400
    
    # Check dates
    now = datetime.now(timezone.utc)
    if election.start_date <= now and election.end_date <= now:
        return jsonify({'error': 'Election dates are in the past'}), 400
    
    election.status = 'active'
    set_audit_fields(election, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Election activated successfully'}), 200),
        'Failed to activate election'
    )

@elections_bp.route('/<int:election_id>/publish-results', methods=['POST'])
@require_permission('Elections', 'update')
@audit_action('publish_results', module='Elections')
def publish_results(election_id):
    """Publish election results"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    current_user = get_current_user()
    
    # Validate election can have results published
    if election.status not in ['completed', 'active']:
        return jsonify({'error': 'Only completed or active elections can have results published'}), 400
    
    # Check if voting period has ended (unless election status is already completed)
    end_dt = election.end_date.replace(tzinfo=timezone.utc) if election.end_date and election.end_date.tzinfo is None else election.end_date
    if election.status != 'completed' and end_dt and end_dt > datetime.now(timezone.utc):
        return jsonify({'error': 'Cannot publish results before voting period ends'}), 400
    
    # Auto-tally uncounted votes before publishing
    from app.routes.votes import tally_election_votes
    tally_election_votes(election_id)
    
    election.results_published = True
    election.results_published_at = datetime.now(timezone.utc)
    election.status = 'completed'
    set_audit_fields(election, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Election results published successfully'}), 200),
        'Failed to publish election results'
    )

@elections_bp.route('/<int:election_id>/tally', methods=['POST'])
@require_permission('Elections', 'update')
def tally_election(election_id):
    """Tally votes for an election"""
    from app.routes.votes import tally_election_votes
    return tally_election_votes(election_id)

@elections_bp.route('/<int:election_id>/change-status', methods=['POST'])
@require_permission('Elections', 'update')
@audit_action('change_election_status', module='Elections')
def change_election_status(election_id):
    """Change election status"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    new_status = data['status']
    valid_statuses = ['draft', 'active', 'completed', 'cancelled']
    
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    # Business logic validation
    if new_status == 'active':
        # Check if election has ballots
        ballot_count = Ballot.query.filter_by(election_id=election_id, is_active=True).count()
        if ballot_count == 0:
            return jsonify({'error': 'Election must have at least one active ballot to activate'}), 400
    
    # Allow status change (this bypasses the normal update restrictions)
    election.status = new_status
    set_audit_fields(election, is_create=False)
    
    return safe_commit(
        (jsonify({'message': f'Election status changed to {new_status} successfully'}), 200),
        'Failed to change election status'
    )

@elections_bp.route('/<int:election_id>/ballots', methods=['GET'])
@require_permission('Elections', 'view')
def get_election_ballots(election_id):
    """Get all ballots for an election"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    
    ballots = Ballot.query.filter_by(election_id=election_id).order_by(Ballot.order_index).all()
    
    return jsonify({
        'ballots': [{
            'id': b.id,
            'title': b.title,
            'ballot_code': b.ballot_code,
            'ballot_type': b.ballot_type,
            'position_title': b.position_title,
            'order_index': b.order_index,
            'is_active': b.is_active,
            'is_published': b.is_published,
            'total_votes_cast': b.total_votes_cast,
            'candidate_count': len(b.candidates)
        } for b in ballots]
    })

@elections_bp.route('/<int:election_id>/registrations', methods=['GET'])
@require_permission('Elections', 'view')
def get_election_registrations(election_id):
    """Get voter registrations for an election"""
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first_or_404()
        company_id = election.company_id
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first_or_404()
    
    page, per_page, error = parse_pagination(request)
    if error:
        return error
    status = request.args.get('status')
    
    query = get_election_registrations_query(election_id, company_id)
    
    if status:
        query = query.filter(VoterRegistration.status == status)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    registrations = pagination.items
    
    return jsonify({
        'data': [{
            'id': r.id,
            'registration_id': r.registration_id,
            'voter_id': r.voter_id,
            'voter_name': r.voter.display_name,
            'status': r.status,
            'registration_type': r.registration_type,
            'registered_at': r.registered_at.isoformat(),
            'is_eligible': r.is_eligible_to_vote,
            'verification_level': r.verification_level_met
        } for r in registrations],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })

@elections_bp.route('/stats', methods=['GET'])
@require_permission('Elections', 'view')
def get_election_stats():
    """Get election statistics for the company"""
    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        if req_company_id:
            filter_kwargs = {'company_id': req_company_id}
            comp_filter = (Election.company_id == req_company_id)
        else:
            filter_kwargs = {}
            comp_filter = True
    else:
        company_id = get_current_company_id()
        filter_kwargs = {'company_id': company_id}
        comp_filter = (Election.company_id == company_id)
    
    total_elections = Election.query.filter_by(**filter_kwargs).count()
    active_elections = Election.query.filter_by(status='active', **filter_kwargs).count()
    
    # Upcoming and completed counts
    now = datetime.now(timezone.utc)
    upcoming = Election.query.filter(
        comp_filter,
        Election.start_date > now,
        Election.status != 'cancelled'
    ).count()
    completed = Election.query.filter_by(status='completed', **filter_kwargs).count()
    
    # Election types
    election_types = db.session.query(
        Election.election_type,
        db.func.count(Election.id).label('count')
    ).filter(comp_filter).group_by(Election.election_type).all()
    
    # Elections by status
    election_statuses = db.session.query(
        Election.status,
        db.func.count(Election.id).label('count')
    ).filter(comp_filter).group_by(Election.status).all()
    
    return jsonify({
        'total_elections': total_elections,
        'active_elections': active_elections,
        'upcoming_elections': upcoming,
        'completed_elections': completed,
        'election_types': {etype: count for etype, count in election_types},
        'election_statuses': {status: count for status, count in election_statuses}
    })

def generate_election_code():
    """Generate a unique election code"""
    alphabet = string.ascii_uppercase + string.digits
    return 'E' + ''.join(secrets.choice(alphabet) for _ in range(8)) 
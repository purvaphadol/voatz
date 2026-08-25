from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.candidate import Candidate
from app.models.vote import Vote
from app.utils import get_current_company_id, require_permission, get_current_user, is_administrator, check_user_permission
from app.utils.validators import parse_pagination, validate_ballot_input
from app.utils.query_helpers import get_active_ballots_query
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from app.utils.cascade import count_dependents, count_reactivatable_dependents, cascade_set_inactive, cascade_reactivate
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED
from sqlalchemy import or_
from datetime import datetime, timezone
import secrets
import string


ballots_bp = Blueprint('ballots', __name__)

@ballots_bp.route('/<int:ballot_id>/status_dependents', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot_status_dependents(ballot_id):
    """Retrieve dependent counts for status transitions (Inactive or Reactivate)."""
    if is_administrator():
        ballot = Ballot.query.filter(Ballot.id == ballot_id, Ballot.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter(Ballot.id == ballot_id, Ballot.company_id == company_id, Ballot.status != STATUS_DEACTIVATED).first_or_404()

    if ballot.status == STATUS_ACTIVE:
        result = count_dependents('Ballot', ballot_id)
        return jsonify({'current_status': STATUS_ACTIVE, 'target_status': STATUS_INACTIVE, 'dependents': result})
    else:
        result = count_reactivatable_dependents('Ballot', ballot_id)
        return jsonify({'current_status': STATUS_INACTIVE, 'target_status': STATUS_ACTIVE, 'dependents': result})


@ballots_bp.route('/', methods=['GET'])
@require_permission('Ballots', 'view')
def list_ballots():
    """List all ballots with filtering and pagination"""
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
    
    if is_administrator():
        req_company_id = request.args.get('company_id', type=int)
        query = Ballot.query.join(Election)
        if req_company_id:
            query = query.filter(Ballot.company_id == req_company_id)
    else:
        company_id = get_current_company_id()
        query = Ballot.query.filter(Ballot.company_id == company_id).join(Election)

    query = query.filter(Ballot.status.in_(allowed), Ballot.status != STATUS_DEACTIVATED)

    search = request.args.get('search')
    election_id = request.args.get('election_id')
    ballot_type = request.args.get('ballot_type')
    is_published = request.args.get('is_published')
    page, per_page, error = parse_pagination(request)
    if error:
        return error
    
    if search:
        query = query.filter(or_(
            Ballot.title.ilike(f'%{search}%'),
            Ballot.description.ilike(f'%{search}%'),
            Ballot.ballot_code.ilike(f'%{search}%'),
            Ballot.position_title.ilike(f'%{search}%')
        ))
    
    if election_id:
        query = query.filter(Ballot.election_id == election_id)
    
    if ballot_type:
        query = query.filter(Ballot.ballot_type == ballot_type)
    
    if is_published is not None:
        query = query.filter(Ballot.is_published == (is_published.lower() == 'true'))

    pagination = query.order_by(Ballot.election_id, Ballot.order_index).paginate(page=page, per_page=per_page, error_out=False)
    ballots = pagination.items
    
    out_ballots = []
    has_admin = is_administrator()
    has_results_perm = check_user_permission('Votes', 'view_unpublished_results')
    for b in ballots:
        res_pub = bool(b.election.results_published) if b.election else False
        can_view_results = res_pub or has_admin or has_results_perm
        out_ballots.append({
            'id': b.id,
            'title': b.title,
            'description': b.description,
            'ballot_code': b.ballot_code,
            'ballot_type': b.ballot_type,
            'position_title': b.position_title,
            'election_id': b.election_id,
            'election_title': b.election.title if b.election else None,
            'order_index': b.order_index,
            'min_selections': b.min_selections,
            'max_selections': b.max_selections,
            'allow_write_in': b.allow_write_in,
            'require_selection': b.require_selection,
            'display_format': b.display_format,
            'randomize_candidates': b.randomize_candidates,
            'instructions': b.instructions,
            'question_text': b.question_text,
            'jurisdiction_restriction': b.jurisdiction_restriction,
            'voter_type_restriction': b.voter_type_restriction,
            'is_active': b.status == STATUS_ACTIVE,
            'status': b.status,
            'is_published': b.is_published,
            'is_test_ballot': b.is_test_ballot,
            'results_published': res_pub,
            'total_votes_cast': b.total_votes_cast if can_view_results else None,
            'total_eligible_voters': b.total_eligible_voters,
            'candidate_count': len(b.candidates),
            'selection_rules_text': b.get_selection_rules_text(),
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'updated_at': b.updated_at.isoformat() if b.updated_at else None
        })

    return jsonify({
        'data': out_ballots,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': {
            'total_ballots': pagination.total,
            'active_ballots': sum(1 for b in ballots if b.status == STATUS_ACTIVE),
            'published_ballots': sum(1 for b in ballots if b.is_published),
            'draft_ballots': sum(1 for b in ballots if not b.is_published)
        }
    })

@ballots_bp.route('/', methods=['POST'])
@require_permission('Ballots', 'create')
@audit_action('create_ballot', module='Ballots')
def create_ballot():
    """Create a new ballot"""
    current_user = get_current_user()
    data = request.get_json() or {}
    cleaned_data, err = validate_ballot_input(data, is_create=True)
    if err:
        return err
    
    try:
        election_id = int(data['election_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'election_id must be a valid integer'}), 400
    
    # Validate election exists and belongs to company
    if is_administrator():
        election = Election.query.filter_by(id=election_id).first()
    else:
        company_id = get_current_company_id()
        election = Election.query.filter_by(id=election_id, company_id=company_id).first()

    if not election:
        return jsonify({'error': 'Election not found'}), 404

    company_id = election.company_id
    
    # Don't allow ballot creation for active, completed, or cancelled elections
    if election.status in ['active', 'cancelled', 'completed']:
        return jsonify({'error': 'Cannot create ballots for active, completed, or cancelled elections'}), 400
    
    # Check for inactive collision (409 Conflict)
    existing_inactive = Ballot.query.filter(
        Ballot.election_id == election_id,
        Ballot.title == data['title'],
        Ballot.status == STATUS_INACTIVE
    ).first()
    if existing_inactive:
        return jsonify({
            'error': 'A ballot with this title already exists in this election but is currently Inactive.',
            'existing_id': existing_inactive.id,
            'can_reactivate': True
        }), 409

    # Generate unique ballot code
    ballot_code = generate_ballot_code()
    while Ballot.query.filter_by(ballot_code=ballot_code, election_id=election_id).first():
        ballot_code = generate_ballot_code()
    
    # Create ballot
    ballot = Ballot()
    ballot.company_id = company_id
    ballot.election_id = election_id
    ballot.title = data['title']
    ballot.description = data.get('description', '')
    ballot.ballot_code = ballot_code
    ballot.ballot_type = data['ballot_type']
    ballot.position_title = data.get('position_title')
    
    # Voting rules
    ballot.min_selections = data.get('min_selections', 0)
    ballot.max_selections = data.get('max_selections', 1)
    ballot.allow_write_in = data.get('allow_write_in', False)
    ballot.require_selection = data.get('require_selection', True)
    
    # Display settings
    ballot.order_index = data.get('order_index', 0)
    ballot.display_format = data.get('display_format', 'list')
    ballot.randomize_candidates = data.get('randomize_candidates', False)
    ballot.instructions = data.get('instructions')
    ballot.question_text = data.get('question_text')
    
    # Restrictions
    ballot.jurisdiction_restriction = data.get('jurisdiction_restriction')
    ballot.voter_type_restriction = data.get('voter_type_restriction')
    
    # Status
    ballot.status = data.get('status', STATUS_ACTIVE)
    ballot.is_active = (ballot.status == STATUS_ACTIVE)
    ballot.is_published = data.get('is_published', False)
    ballot.is_test_ballot = data.get('is_test_ballot', False)
    
    set_audit_fields(ballot, is_create=True)
    
    db.session.add(ballot)
    db.session.flush()
    return safe_commit(
        (jsonify({
            'message': 'Ballot created successfully',
            'ballot_id': ballot.id,
            'ballot_code': ballot.ballot_code
        }), 201),
        'Failed to create ballot'
    )

@ballots_bp.route('/<int:ballot_id>', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot(ballot_id):
    """Get detailed ballot information"""
    if is_administrator():
        ballot = Ballot.query.join(Election).filter(
            Ballot.id == ballot_id,
            Ballot.status != STATUS_DEACTIVATED
        ).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.join(Election).filter(
            Ballot.id == ballot_id,
            Ballot.company_id == company_id,
            Ballot.status != STATUS_DEACTIVATED
        ).first_or_404()
    
    # Get candidates
    candidates = Candidate.query.filter_by(ballot_id=ballot_id).filter(Candidate.status != STATUS_DEACTIVATED).order_by(Candidate.order_index).all()
    
    # Get vote count
    vote_count = Vote.query.filter_by(ballot_id=ballot_id).count()

    c_election = ballot.election if ballot else None
    res_pub = bool(c_election.results_published) if c_election else False
    can_view_results = res_pub or is_administrator() or check_user_permission('Votes', 'view_unpublished_results')
    
    return jsonify({
        'id': ballot.id,
        'title': ballot.title,
        'description': ballot.description,
        'ballot_code': ballot.ballot_code,
        'ballot_type': ballot.ballot_type,
        'position_title': ballot.position_title,
        'election_id': ballot.election_id,
        'election_title': ballot.election.title,
        'election_status': ballot.election.status,
        'order_index': ballot.order_index,
        'min_selections': ballot.min_selections,
        'max_selections': ballot.max_selections,
        'allow_write_in': ballot.allow_write_in,
        'require_selection': ballot.require_selection,
        'display_format': ballot.display_format,
        'randomize_candidates': ballot.randomize_candidates,
        'instructions': ballot.instructions,
        'question_text': ballot.question_text,
        'jurisdiction_restriction': ballot.jurisdiction_restriction,
        'voter_type_restriction': ballot.voter_type_restriction,
        'is_active': ballot.status == STATUS_ACTIVE,
        'status': ballot.status,
        'is_published': ballot.is_published,
        'is_test_ballot': ballot.is_test_ballot,
        'total_votes_cast': ballot.total_votes_cast if can_view_results else None,
        'total_eligible_voters': ballot.total_eligible_voters,
        'selection_rules_text': ballot.get_selection_rules_text(),
        'results_published': res_pub,
        'candidates': [{
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'image_url': c.image_url,
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.status == STATUS_ACTIVE,
            'status': c.status,
            'results_published': res_pub,
            'total_votes_received': c.total_votes_received if can_view_results else None,
            'vote_percentage': c.vote_percentage if can_view_results else None
        } for c in candidates],
        'statistics': {
            'candidate_count': len(candidates),
            'vote_count': vote_count if can_view_results else None,
            'active_candidates': sum(1 for c in candidates if c.status == STATUS_ACTIVE)
        },
        'created_at': ballot.created_at.isoformat() if ballot.created_at else None,
        'updated_at': ballot.updated_at.isoformat() if ballot.updated_at else None
    })

@ballots_bp.route('/<int:ballot_id>', methods=['PUT'])
@require_permission('Ballots', 'update')
@audit_action('update_ballot', module='Ballots')
def update_ballot(ballot_id):
    """Update ballot information"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id).filter(Ballot.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).filter(Ballot.status != STATUS_DEACTIVATED).first_or_404()
    current_user = get_current_user()
    data = request.get_json()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot modify ballots for active elections'}), 400
    
    # Update basic fields
    if data.get('title'):
        ballot.title = data['title']
    if data.get('description'):
        ballot.description = data['description']
    if data.get('ballot_type'):
        ballot.ballot_type = data['ballot_type']
    if data.get('position_title'):
        ballot.position_title = data['position_title']
    
    # Update voting rules
    if 'min_selections' in data:
        ballot.min_selections = data['min_selections']
    if 'max_selections' in data:
        ballot.max_selections = data['max_selections']
    if 'allow_write_in' in data:
        ballot.allow_write_in = data['allow_write_in']
    if 'require_selection' in data:
        ballot.require_selection = data['require_selection']
    
    # Update display settings
    if 'order_index' in data:
        ballot.order_index = data['order_index']
    if 'display_format' in data:
        ballot.display_format = data['display_format']
    if 'randomize_candidates' in data:
        ballot.randomize_candidates = data['randomize_candidates']
    if 'instructions' in data:
        ballot.instructions = data['instructions']
    if 'question_text' in data:
        ballot.question_text = data['question_text']
    
    # Update restrictions
    if 'jurisdiction_restriction' in data:
        ballot.jurisdiction_restriction = data['jurisdiction_restriction']
    if 'voter_type_restriction' in data:
        ballot.voter_type_restriction = data['voter_type_restriction']
    
    # Handle status transition and cascade
    new_status = data.get('status')
    if new_status is None and 'is_active' in data:
        new_status = STATUS_ACTIVE if data['is_active'] else STATUS_INACTIVE

    if new_status is not None and new_status != ballot.status:
        old_status = ballot.status
        ballot.status = new_status
        ballot.is_active = (new_status == STATUS_ACTIVE)
        if old_status == STATUS_ACTIVE and new_status == STATUS_INACTIVE:
            cascade_set_inactive('Ballot', ballot.id)
        elif old_status == STATUS_INACTIVE and new_status == STATUS_ACTIVE:
            cascade_reactivate('Ballot', ballot.id)

    if 'is_published' in data:
        ballot.is_published = data['is_published']
    
    set_audit_fields(ballot, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Ballot updated successfully'}), 200),
        'Failed to update ballot'
    )

@ballots_bp.route('/<int:ballot_id>', methods=['DELETE'])
@require_permission('Ballots', 'delete')
@audit_action('delete_ballot', module='Ballots')
def delete_ballot(ballot_id):
    """Delete ballot (soft delete)"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id).filter(Ballot.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).filter(Ballot.status != STATUS_DEACTIVATED).first_or_404()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot delete ballots for active elections'}), 400
    
    # Check if there are votes cast
    vote_count = Vote.query.filter_by(ballot_id=ballot_id).count()
    if vote_count > 0:
        return jsonify({'error': 'Cannot delete ballots with votes already cast'}), 400

    force = request.args.get('force', 'false').lower() == 'true'

    from app.models.candidate import Candidate
    active_candidates = Candidate.query.filter_by(ballot_id=ballot_id).filter(Candidate.status != STATUS_DEACTIVATED).count()

    if active_candidates > 0 and not force:
        user_friendly_error = f"Cannot delete ballot: It currently has {active_candidates} active candidate(s). Please remove or deactivate these candidates first."
        return jsonify({
            'error': user_friendly_error,
            'can_force': True,
            'active_dependencies': {
                'candidates': active_candidates
            },
            'message': 'Are you sure you want to delete this ballot (and deactivate all related candidate assignments)?'
        }), 400

    import time
    ts = int(time.time())

    # Deactivate active candidates on this ballot
    if active_candidates > 0:
        candidates = Candidate.query.filter_by(ballot_id=ballot_id).filter(Candidate.status != STATUS_DEACTIVATED).all()
        for c in candidates:
            c.status = STATUS_DEACTIVATED
            if "_deleted_" not in c.name:
                c.name = f"{c.name}_deleted_{c.id}_{ts}"
            set_audit_fields(c, is_create=False)

    # Soft delete by updating status
    ballot.status = STATUS_DEACTIVATED
    ballot.is_active = False
    if "_deleted_" not in ballot.title:
        ballot.title = f"{ballot.title}_deleted_{ballot.id}_{ts}"
    if ballot.ballot_code and "_deleted_" not in ballot.ballot_code:
        ballot.ballot_code = f"{ballot.ballot_code}_deleted_{ballot.id}_{ts}"
    set_audit_fields(ballot, is_create=False)

    return safe_commit(
        (jsonify({'message': 'Ballot deleted successfully'}), 200),
        'Failed to delete ballot'
    )

@ballots_bp.route('/<int:ballot_id>/publish', methods=['POST'])
@require_permission('Ballots', 'update')
@audit_action('publish_ballot', module='Ballots')
def publish_ballot(ballot_id):
    """Publish a ballot"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id, is_active=True).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id, is_active=True).first_or_404()
    current_user = get_current_user()
    
    # Validate ballot can be published
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot publish ballots for active elections'}), 400
    
    # Check if ballot has candidates
    candidate_count = Candidate.query.filter_by(ballot_id=ballot_id, is_active=True).count()
    if candidate_count == 0:
        return jsonify({'error': 'Ballot must have at least one active candidate'}), 400
    
    ballot.is_published = True
    set_audit_fields(ballot, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Ballot published successfully'}), 200),
        'Failed to publish ballot'
    )

@ballots_bp.route('/<int:ballot_id>/unpublish', methods=['POST'])
@require_permission('Ballots', 'update')
@audit_action('unpublish_ballot', module='Ballots')
def unpublish_ballot(ballot_id):
    """Unpublish a ballot"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id, is_active=True).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id, is_active=True).first_or_404()
    current_user = get_current_user()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot unpublish ballots for active elections'}), 400
    
    ballot.is_published = False
    set_audit_fields(ballot, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Ballot unpublished successfully'}), 200),
        'Failed to unpublish ballot'
    )

@ballots_bp.route('/<int:ballot_id>/candidates', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot_candidates(ballot_id):
    """Get all candidates for a ballot"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id, is_active=True).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id, is_active=True).first_or_404()
    
    candidates = Candidate.query.filter_by(ballot_id=ballot_id, is_active=True).order_by(Candidate.order_index).all()
    
    c_election = ballot.election if ballot else None
    res_pub = bool(c_election.results_published) if c_election else False
    can_view_results = res_pub or is_administrator() or check_user_permission('Votes', 'view_unpublished_results')

    return jsonify({
        'ballot_id': ballot_id,
        'ballot_title': ballot.title,
        'results_published': res_pub,
        'candidates': [{
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'description': c.description,
            'image_url': c.image_url,
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.is_active,
            'is_qualified': c.is_qualified,
            'results_published': res_pub,
            'total_votes_received': c.total_votes_received if can_view_results else None,
            'vote_percentage': c.vote_percentage if can_view_results else None,
            'full_display_name': c.full_display_name
        } for c in candidates]
    })

@ballots_bp.route('/<int:ballot_id>/reorder', methods=['POST'])
@require_permission('Ballots', 'update')
def reorder_ballot_candidates(ballot_id):
    """Reorder candidates in a ballot"""
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id, is_active=True).first_or_404()
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id, is_active=True).first_or_404()
    current_user = get_current_user()
    data = request.get_json()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot reorder candidates for active elections'}), 400
    
    if not data or not data.get('candidate_order'):
        return jsonify({'error': 'candidate_order array is required'}), 400
    
    # Update candidate order
    for index, candidate_id in enumerate(data['candidate_order']):
        candidate = Candidate.query.filter_by(id=candidate_id, ballot_id=ballot_id).first()
        if candidate:
            candidate.order_index = index
            set_audit_fields(candidate, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Candidates reordered successfully'}), 200),
        'Failed to reorder candidates'
    )

@ballots_bp.route('/<int:ballot_id>/duplicate', methods=['POST'])
@require_permission('Ballots', 'create')
@audit_action('duplicate_ballot', module='Ballots')
def duplicate_ballot(ballot_id):
    """Duplicate a ballot"""
    if is_administrator():
        original_ballot = Ballot.query.filter_by(id=ballot_id, is_active=True).first_or_404()
        company_id = original_ballot.company_id
    else:
        company_id = get_current_company_id()
        original_ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id, is_active=True).first_or_404()
    current_user = get_current_user()
    data = request.get_json()
    
    # Create new ballot
    new_ballot = Ballot()
    new_ballot.company_id = company_id
    new_ballot.election_id = data.get('election_id', original_ballot.election_id)
    new_ballot.title = data.get('title', f"{original_ballot.title} (Copy)")
    new_ballot.description = original_ballot.description
    new_ballot.ballot_code = generate_ballot_code()
    new_ballot.ballot_type = original_ballot.ballot_type
    new_ballot.position_title = original_ballot.position_title
    new_ballot.min_selections = original_ballot.min_selections
    new_ballot.max_selections = original_ballot.max_selections
    new_ballot.allow_write_in = original_ballot.allow_write_in
    new_ballot.require_selection = original_ballot.require_selection
    new_ballot.order_index = original_ballot.order_index
    new_ballot.display_format = original_ballot.display_format
    new_ballot.randomize_candidates = original_ballot.randomize_candidates
    new_ballot.instructions = original_ballot.instructions
    new_ballot.question_text = original_ballot.question_text
    new_ballot.jurisdiction_restriction = original_ballot.jurisdiction_restriction
    new_ballot.voter_type_restriction = original_ballot.voter_type_restriction
    new_ballot.is_active = True
    new_ballot.is_published = False
    new_ballot.is_test_ballot = original_ballot.is_test_ballot
    set_audit_fields(new_ballot, is_create=True)
    
    db.session.add(new_ballot)
    db.session.flush()
    
    # Duplicate candidates if requested
    if data.get('include_candidates', False):
        original_candidates = Candidate.query.filter_by(ballot_id=ballot_id).all()
        for original_candidate in original_candidates:
            new_candidate = Candidate()
            new_candidate.ballot_id = new_ballot.id
            new_candidate.company_id = company_id
            new_candidate.name = original_candidate.name
            from app.routes.candidates import generate_candidate_code
            new_candidate.candidate_code = generate_candidate_code()
            new_candidate.party = original_candidate.party
            new_candidate.party_abbreviation = original_candidate.party_abbreviation
            new_candidate.title = original_candidate.title
            new_candidate.description = original_candidate.description
            new_candidate.order_index = original_candidate.order_index
            new_candidate.is_write_in = original_candidate.is_write_in
            new_candidate.is_incumbent = original_candidate.is_incumbent
            new_candidate.is_active = True
            new_candidate.is_qualified = True
            set_audit_fields(new_candidate, is_create=True)
            db.session.add(new_candidate)
    
    return safe_commit(
        (jsonify({
            'message': 'Ballot duplicated successfully',
            'ballot_id': new_ballot.id,
            'ballot_code': new_ballot.ballot_code
        }), 201),
        'Failed to duplicate ballot'
    )

@ballots_bp.route('/stats', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot_stats():
    """Get ballot statistics for the company"""
    if is_administrator():
        total_ballots = Ballot.query.count()
        active_ballots = Ballot.query.filter_by(is_active=True).count()
        published_ballots = Ballot.query.filter_by(is_published=True).count()
        ballot_types = db.session.query(
            Ballot.ballot_type,
            db.func.count(Ballot.id).label('count')
        ).group_by(Ballot.ballot_type).all()
    else:
        company_id = get_current_company_id()
        total_ballots = Ballot.query.filter_by(company_id=company_id).count()
        active_ballots = Ballot.query.filter_by(company_id=company_id, is_active=True).count()
        published_ballots = Ballot.query.filter_by(company_id=company_id, is_published=True).count()
        ballot_types = db.session.query(
            Ballot.ballot_type,
            db.func.count(Ballot.id).label('count')
        ).filter_by(company_id=company_id).group_by(Ballot.ballot_type).all()
    
    return jsonify({
        'total_ballots': total_ballots,
        'active_ballots': active_ballots,
        'published_ballots': published_ballots,
        'draft_ballots': total_ballots - published_ballots,
        'ballot_types': {btype: count for btype, count in ballot_types}
    })

def generate_ballot_code():
    """Generate a unique ballot code"""
    alphabet = string.ascii_uppercase + string.digits
    return 'B' + ''.join(secrets.choice(alphabet) for _ in range(8)) 
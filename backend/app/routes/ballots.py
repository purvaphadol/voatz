from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.candidate import Candidate
from app.models.vote import Vote
from app.utils import get_current_company_id, require_permission, get_current_user
from sqlalchemy import or_
from datetime import datetime
import secrets
import string

ballots_bp = Blueprint('ballots', __name__)

@ballots_bp.route('/', methods=['GET'])
@require_permission('Ballots', 'view')
def list_ballots():
    """List all ballots with filtering and pagination"""
    company_id = get_current_company_id()
    search = request.args.get('search')
    election_id = request.args.get('election_id')
    ballot_type = request.args.get('ballot_type')
    is_active = request.args.get('is_active')
    is_published = request.args.get('is_published')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    query = Ballot.query.join(Election).filter(Ballot.company_id == company_id)
    
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
    
    if is_active is not None:
        query = query.filter(Ballot.is_active == (is_active.lower() == 'true'))
    
    if is_published is not None:
        query = query.filter(Ballot.is_published == (is_published.lower() == 'true'))

    pagination = query.order_by(Ballot.election_id, Ballot.order_index).paginate(page=page, per_page=per_page, error_out=False)
    ballots = pagination.items
    
    return jsonify({
        'data': [{
            'id': b.id,
            'title': b.title,
            'description': b.description,
            'ballot_code': b.ballot_code,
            'ballot_type': b.ballot_type,
            'position_title': b.position_title,
            'election_id': b.election_id,
            'election_title': b.election.title,
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
            'is_active': b.is_active,
            'is_published': b.is_published,
            'is_test_ballot': b.is_test_ballot,
            'total_votes_cast': b.total_votes_cast,
            'total_eligible_voters': b.total_eligible_voters,
            'candidate_count': len(b.candidates),
            'selection_rules_text': b.get_selection_rules_text(),
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'updated_at': b.updated_at.isoformat() if b.updated_at else None
        } for b in ballots],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': {
            'total_ballots': pagination.total,
            'active_ballots': sum(1 for b in ballots if b.is_active),
            'published_ballots': sum(1 for b in ballots if b.is_published),
            'draft_ballots': sum(1 for b in ballots if not b.is_published)
        }
    })

@ballots_bp.route('/', methods=['POST'])
@require_permission('Ballots', 'create')
def create_ballot():
    """Create a new ballot"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('election_id') or not data.get('ballot_type'):
        return jsonify({'error': 'Title, election_id, and ballot_type are required'}), 400
    
    # Validate election exists and belongs to company
    election = Election.query.filter_by(id=data['election_id'], company_id=company_id).first()
    if not election:
        return jsonify({'error': 'Election not found'}), 404
    
    # Don't allow ballot creation for active elections
    if election.status == 'active':
        return jsonify({'error': 'Cannot create ballots for active elections'}), 400
    
    # Generate unique ballot code
    ballot_code = generate_ballot_code()
    while Ballot.query.filter_by(ballot_code=ballot_code, election_id=data['election_id']).first():
        ballot_code = generate_ballot_code()
    
    # Create ballot
    ballot = Ballot()
    ballot.company_id = company_id
    ballot.election_id = data['election_id']
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
    ballot.is_active = data.get('is_active', True)
    ballot.is_published = data.get('is_published', False)
    ballot.is_test_ballot = data.get('is_test_ballot', False)
    
    ballot.created_by = current_user.id if current_user else None
    
    db.session.add(ballot)
    db.session.commit()
    
    return jsonify({
        'message': 'Ballot created successfully',
        'ballot_id': ballot.id,
        'ballot_code': ballot.ballot_code
    }), 201

@ballots_bp.route('/<int:ballot_id>', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot(ballot_id):
    """Get detailed ballot information"""
    company_id = get_current_company_id()
    ballot = Ballot.query.join(Election).filter(
        Ballot.id == ballot_id,
        Ballot.company_id == company_id
    ).first_or_404()
    
    # Get candidates
    candidates = Candidate.query.filter_by(ballot_id=ballot_id).order_by(Candidate.order_index).all()
    
    # Get vote count
    vote_count = Vote.query.filter_by(ballot_id=ballot_id).count()
    
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
        'is_active': ballot.is_active,
        'is_published': ballot.is_published,
        'is_test_ballot': ballot.is_test_ballot,
        'total_votes_cast': ballot.total_votes_cast,
        'total_eligible_voters': ballot.total_eligible_voters,
        'selection_rules_text': ballot.get_selection_rules_text(),
        'candidates': [{
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'image_url': c.image_url,  # Added candidate image support
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.is_active,
            'total_votes_received': c.total_votes_received,
            'vote_percentage': c.vote_percentage
        } for c in candidates],
        'statistics': {
            'candidate_count': len(candidates),
            'vote_count': vote_count,
            'active_candidates': sum(1 for c in candidates if c.is_active)
        },
        'created_at': ballot.created_at.isoformat() if ballot.created_at else None,
        'updated_at': ballot.updated_at.isoformat() if ballot.updated_at else None
    })

@ballots_bp.route('/<int:ballot_id>', methods=['PUT'])
@require_permission('Ballots', 'update')
def update_ballot(ballot_id):
    """Update ballot information"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
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
    
    # Update status
    if 'is_active' in data:
        ballot.is_active = data['is_active']
    if 'is_published' in data:
        ballot.is_published = data['is_published']
    
    ballot.updated_by = current_user.id if current_user else None
    ballot.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Ballot updated successfully'}), 200

@ballots_bp.route('/<int:ballot_id>', methods=['DELETE'])
@require_permission('Ballots', 'delete')
def delete_ballot(ballot_id):
    """Delete ballot (soft delete)"""
    company_id = get_current_company_id()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot delete ballots for active elections'}), 400
    
    # Check if there are votes cast
    vote_count = Vote.query.filter_by(ballot_id=ballot_id).count()
    if vote_count > 0:
        return jsonify({'error': 'Cannot delete ballots with votes already cast'}), 400
    
    # Soft delete by updating status
    ballot.is_active = False
    ballot.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Ballot deleted successfully'}), 200

@ballots_bp.route('/<int:ballot_id>/publish', methods=['POST'])
@require_permission('Ballots', 'update')
def publish_ballot(ballot_id):
    """Publish a ballot"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
    
    # Validate ballot can be published
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot publish ballots for active elections'}), 400
    
    # Check if ballot has candidates
    candidate_count = Candidate.query.filter_by(ballot_id=ballot_id, is_active=True).count()
    if candidate_count == 0:
        return jsonify({'error': 'Ballot must have at least one active candidate'}), 400
    
    ballot.is_published = True
    ballot.updated_by = current_user.id if current_user else None
    ballot.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Ballot published successfully'}), 200

@ballots_bp.route('/<int:ballot_id>/unpublish', methods=['POST'])
@require_permission('Ballots', 'update')
def unpublish_ballot(ballot_id):
    """Unpublish a ballot"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
    
    # Check if election is active
    if ballot.election.status == 'active':
        return jsonify({'error': 'Cannot unpublish ballots for active elections'}), 400
    
    ballot.is_published = False
    ballot.updated_by = current_user.id if current_user else None
    ballot.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Ballot unpublished successfully'}), 200

@ballots_bp.route('/<int:ballot_id>/candidates', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot_candidates(ballot_id):
    """Get all candidates for a ballot"""
    company_id = get_current_company_id()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
    
    candidates = Candidate.query.filter_by(ballot_id=ballot_id).order_by(Candidate.order_index).all()
    
    return jsonify({
        'ballot_id': ballot_id,
        'ballot_title': ballot.title,
        'candidates': [{
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'description': c.description,
            'image_url': c.image_url,  # Added candidate image support
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.is_active,
            'is_qualified': c.is_qualified,
            'total_votes_received': c.total_votes_received,
            'vote_percentage': c.vote_percentage,
            'full_display_name': c.full_display_name
        } for c in candidates]
    })

@ballots_bp.route('/<int:ballot_id>/reorder', methods=['POST'])
@require_permission('Ballots', 'update')
def reorder_ballot_candidates(ballot_id):
    """Reorder candidates in a ballot"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
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
            candidate.updated_by = current_user.id if current_user else None
            candidate.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Candidates reordered successfully'}), 200

@ballots_bp.route('/<int:ballot_id>/duplicate', methods=['POST'])
@require_permission('Ballots', 'create')
def duplicate_ballot(ballot_id):
    """Duplicate a ballot"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    original_ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first_or_404()
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
    new_ballot.created_by = current_user.id if current_user else None
    
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
            new_candidate.candidate_code = f"{original_candidate.candidate_code}_COPY"
            new_candidate.party = original_candidate.party
            new_candidate.party_abbreviation = original_candidate.party_abbreviation
            new_candidate.title = original_candidate.title
            new_candidate.description = original_candidate.description
            new_candidate.order_index = original_candidate.order_index
            new_candidate.is_write_in = original_candidate.is_write_in
            new_candidate.is_incumbent = original_candidate.is_incumbent
            new_candidate.is_active = True
            new_candidate.is_qualified = True
            new_candidate.created_by = current_user.id if current_user else None
            db.session.add(new_candidate)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Ballot duplicated successfully',
        'ballot_id': new_ballot.id,
        'ballot_code': new_ballot.ballot_code
    }), 201

@ballots_bp.route('/stats', methods=['GET'])
@require_permission('Ballots', 'view')
def get_ballot_stats():
    """Get ballot statistics for the company"""
    company_id = get_current_company_id()
    
    total_ballots = Ballot.query.filter_by(company_id=company_id).count()
    active_ballots = Ballot.query.filter_by(company_id=company_id, is_active=True).count()
    published_ballots = Ballot.query.filter_by(company_id=company_id, is_published=True).count()
    
    # Ballot types
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
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from app import db
from app.models.candidate import Candidate
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.vote import Vote
from app.utils import get_current_company_id, require_permission, get_current_user
from sqlalchemy import or_
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import secrets
import string
import logging
import os

from app.utils.validators import parse_pagination
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from app.utils.query_helpers import get_active_candidates_query
from app.utils.constants import STATUS_INACTIVE

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
UPLOAD_SUBFOLDER = 'uploads/candidates'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set up logging for this module
logger = logging.getLogger(__name__)

candidates_bp = Blueprint('candidates', __name__)

@candidates_bp.route('/', methods=['GET'])
@require_permission('Candidates', 'view')
def list_candidates():
    """List all candidates with filtering and pagination"""
    company_id = get_current_company_id()
    search = request.args.get('search')
    ballot_id = request.args.get('ballot_id')
    election_id = request.args.get('election_id')
    party = request.args.get('party')
    is_active = request.args.get('is_active')
    is_incumbent = request.args.get('is_incumbent')
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    query = get_active_candidates_query(company_id).join(Ballot).join(Election)
    
    if search:
        query = query.filter(or_(
            Candidate.name.ilike(f'%{search}%'),
            Candidate.candidate_code.ilike(f'%{search}%'),
            Candidate.party.ilike(f'%{search}%'),
            Candidate.title.ilike(f'%{search}%')
        ))
    
    if ballot_id:
        query = query.filter(Candidate.ballot_id == ballot_id)
    
    if election_id:
        query = query.filter(Ballot.election_id == election_id)
    
    if party:
        query = query.filter(Candidate.party.ilike(f'%{party}%'))
    
    if is_active is not None:
        query = query.filter(Candidate.is_active == (is_active.lower() == 'true'))
    
    if is_incumbent is not None:
        query = query.filter(Candidate.is_incumbent == (is_incumbent.lower() == 'true'))

    pagination = query.order_by(Candidate.ballot_id, Candidate.order_index).paginate(page=page, per_page=per_page, error_out=False)
    candidates = pagination.items
    
    base = get_active_candidates_query(company_id)
    summary = {
        'total_candidates': pagination.total,
        'active_candidates': pagination.total,
        'incumbent_candidates': base.filter_by(is_incumbent=True).count(),
        'withdrawn_candidates': Candidate.query.filter_by(company_id=company_id, is_withdrawn=True).count()
    }
    
    return jsonify({
        'data': [{
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'image_url': c.image_url,  # ADDED: Include image URL in list response
            'ballot_id': c.ballot_id,
            'ballot_title': c.ballot.title,
            'election_id': c.ballot.election_id,
            'election_title': c.ballot.election.title,
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.is_active,
            'is_qualified': c.is_qualified,
            'is_withdrawn': c.is_withdrawn,
            'total_votes_received': c.total_votes_received,
            'vote_percentage': c.vote_percentage,
            'rank_position': c.rank_position,
            'full_display_name': c.full_display_name,
            'party_display': c.party_display,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None
        } for c in candidates],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'summary': summary
    })

@candidates_bp.route('/', methods=['POST'])
@require_permission('Candidates', 'create')
@audit_action('create_candidate', module='Candidates')
def create_candidate():
    """Create a new candidate"""
    company_id = get_current_company_id()
    current_user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('ballot_id'):
        return jsonify({'error': 'name and ballot_id are required'}), 400
    
    try:
        ballot_id = int(data['ballot_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'ballot_id must be a valid integer'}), 400
    
    # Validate ballot exists and belongs to company
    ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first()
    if not ballot:
        return jsonify({'error': 'Ballot not found'}), 404
    
    # Don't allow candidate creation for active, completed, or cancelled elections
    if ballot.election.status in ['active', 'cancelled', 'completed']:
        return jsonify({'error': 'Cannot create candidates for active, completed, or cancelled elections'}), 400
    
    # Generate unique candidate code
    candidate_code = generate_candidate_code()
    while Candidate.query.filter_by(candidate_code=candidate_code, ballot_id=ballot_id).first():
        candidate_code = generate_candidate_code()
    
    # Create candidate
    candidate = Candidate()
    candidate.company_id = company_id
    candidate.ballot_id = ballot_id
    candidate.name = data['name']
    candidate.candidate_code = candidate_code
    candidate.party = data.get('party')
    candidate.party_abbreviation = data.get('party_abbreviation')
    candidate.title = data.get('title')
    candidate.description = data.get('description')
    candidate.biography = data.get('biography')
    candidate.platform_summary = data.get('platform_summary')
    
    # Media and presentation
    candidate.image_url = data.get('image_url')
    candidate.profile_image_path = data.get('profile_image_path')
    candidate.campaign_website = data.get('campaign_website')
    candidate.social_media_links = data.get('social_media_links')
    candidate.display_name = data.get('display_name')
    
    # Position and status
    candidate.order_index = data.get('order_index', 0)
    candidate.is_write_in = data.get('is_write_in', False)
    candidate.is_incumbent = data.get('is_incumbent', False)
    candidate.is_endorsed = data.get('is_endorsed', False)
    candidate.is_active = data.get('is_active', True)
    candidate.is_qualified = data.get('is_qualified', True)
    
    # Contact information
    candidate.email = data.get('email')
    candidate.phone = data.get('phone')
    candidate.address = data.get('address')
    
    # Background information
    candidate.age = data.get('age')
    candidate.years_in_office = data.get('years_in_office')
    candidate.education = data.get('education')
    candidate.occupation = data.get('occupation')
    
    # Campaign information
    candidate.campaign_finance_id = data.get('campaign_finance_id')
    candidate.endorsements = data.get('endorsements')
    candidate.key_issues = data.get('key_issues')
    
    set_audit_fields(candidate, is_create=True)
    
    db.session.add(candidate)
    db.session.flush()
    
    return safe_commit(
        (jsonify({
            'message': 'Candidate created successfully',
            'candidate_id': candidate.id,
            'candidate_code': candidate.candidate_code
        }), 201),
        'Failed to create candidate'
    )

@candidates_bp.route('/<int:candidate_id>', methods=['GET'])
@require_permission('Candidates', 'view')
def get_candidate(candidate_id):
    """Get detailed candidate information"""
    company_id = get_current_company_id()
    candidate = Candidate.query.join(Ballot).join(Election).filter(
        Candidate.id == candidate_id,
        Candidate.company_id == company_id,
        Candidate.is_active == True
    ).first_or_404()
    
    return jsonify({
        'id': candidate.id,
        'name': candidate.name,
        'candidate_code': candidate.candidate_code,
        'party': candidate.party,
        'party_abbreviation': candidate.party_abbreviation,
        'title': candidate.title,
        'description': candidate.description,
        'biography': candidate.biography,
        'platform_summary': candidate.platform_summary,
        'ballot_id': candidate.ballot_id,
        'ballot_title': candidate.ballot.title,
        'election_id': candidate.ballot.election_id,
        'election_title': candidate.ballot.election.title,
        'election_status': candidate.ballot.election.status,
        'image_url': candidate.image_url,
        'profile_image_path': candidate.profile_image_path,
        'campaign_website': candidate.campaign_website,
        'social_media_links': candidate.social_media_links,
        'order_index': candidate.order_index,
        'display_name': candidate.display_name,
        'is_write_in': candidate.is_write_in,
        'is_incumbent': candidate.is_incumbent,
        'is_endorsed': candidate.is_endorsed,
        'email': candidate.email,
        'phone': candidate.phone,
        'address': candidate.address,
        'age': candidate.age,
        'years_in_office': candidate.years_in_office,
        'education': candidate.education,
        'occupation': candidate.occupation,
        'campaign_finance_id': candidate.campaign_finance_id,
        'endorsements': candidate.endorsements,
        'key_issues': candidate.key_issues,
        'is_active': candidate.is_active,
        'is_qualified': candidate.is_qualified,
        'is_withdrawn': candidate.is_withdrawn,
        'withdrawal_date': candidate.withdrawal_date.isoformat() if candidate.withdrawal_date else None,
        'withdrawal_reason': candidate.withdrawal_reason,
        'total_votes_received': candidate.total_votes_received,
        'vote_percentage': candidate.vote_percentage,
        'rank_position': candidate.rank_position,
        'full_display_name': candidate.full_display_name,
        'party_display': candidate.party_display,
        'is_special_option': candidate.is_special_option,
        'vote_summary': candidate.get_vote_summary(),
        'created_at': candidate.created_at.isoformat() if candidate.created_at else None,
        'updated_at': candidate.updated_at.isoformat() if candidate.updated_at else None
    })

@candidates_bp.route('/<int:candidate_id>', methods=['PUT'])
@require_permission('Candidates', 'update')
@audit_action('update_candidate', module='Candidates')
def update_candidate(candidate_id):
    """Update candidate information"""
    company_id = get_current_company_id()
    
    candidate = Candidate.query.filter_by(id=candidate_id, company_id=company_id, is_active=True).first_or_404()
    
    data = request.get_json()
    
    # Check if election is active
    if candidate.ballot.election.status == 'active':
        return jsonify({'error': 'Cannot modify candidates for active elections'}), 400
    
    # Update basic information
    if data.get('name'):
        candidate.name = data['name']
    if data.get('party'):
        candidate.party = data['party']
    if data.get('party_abbreviation'):
        candidate.party_abbreviation = data['party_abbreviation']
    if data.get('title'):
        candidate.title = data['title']
    if data.get('description'):
        candidate.description = data['description']
    if data.get('biography'):
        candidate.biography = data['biography']
    if data.get('platform_summary'):
        candidate.platform_summary = data['platform_summary']
    
    # Update media and presentation
    if data.get('image_url'):
        candidate.image_url = data['image_url']
    if data.get('profile_image_path'):
        candidate.profile_image_path = data['profile_image_path']
    if data.get('campaign_website'):
        candidate.campaign_website = data['campaign_website']
    if data.get('social_media_links'):
        candidate.social_media_links = data['social_media_links']
    if data.get('display_name'):
        candidate.display_name = data['display_name']
    
    # Update position and status
    if 'order_index' in data:
        candidate.order_index = data['order_index']
    if 'is_incumbent' in data:
        candidate.is_incumbent = data['is_incumbent']
    if 'is_endorsed' in data:
        candidate.is_endorsed = data['is_endorsed']
    if 'is_active' in data:
        candidate.is_active = data['is_active']
    if 'is_qualified' in data:
        candidate.is_qualified = data['is_qualified']
    
    # Update contact information
    if data.get('email'):
        candidate.email = data['email']
    if data.get('phone'):
        candidate.phone = data['phone']
    if data.get('address'):
        candidate.address = data['address']
    
    # Update background information
    if data.get('age'):
        candidate.age = data['age']
    if data.get('years_in_office'):
        candidate.years_in_office = data['years_in_office']
    if data.get('education'):
        candidate.education = data['education']
    if data.get('occupation'):
        candidate.occupation = data['occupation']
    
    # Update campaign information
    if data.get('campaign_finance_id'):
        candidate.campaign_finance_id = data['campaign_finance_id']
    if data.get('endorsements'):
        candidate.endorsements = data['endorsements']
    if data.get('key_issues'):
        candidate.key_issues = data['key_issues']
    
    set_audit_fields(candidate, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Candidate updated successfully'}), 200),
        'Failed to update candidate'
    )

@candidates_bp.route('/<int:candidate_id>', methods=['DELETE'])
@require_permission('Candidates', 'delete')
@audit_action('delete_candidate', module='Candidates')
def delete_candidate(candidate_id):
    """Delete candidate (soft delete)"""
    company_id = get_current_company_id()
    candidate = Candidate.query.filter_by(id=candidate_id, company_id=company_id, is_active=True).first_or_404()
    
    # Check if election is active
    if candidate.ballot.election.status == 'active':
        return jsonify({'error': 'Cannot delete candidates for active elections'}), 400
    
    # Check if there are votes for this candidate
    vote_count = Vote.query.filter(
        Vote.ballot_id == candidate.ballot_id,
        db.cast(Vote.vote_data, db.String).contains(f'"{candidate.id}"')
    ).count()
    
    if vote_count > 0:
        return jsonify({'error': 'Cannot delete candidates with votes already cast'}), 400
    
    # Soft delete by updating status
    candidate.is_active = False
    set_audit_fields(candidate, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Candidate deleted successfully'}), 200),
        'Failed to delete candidate'
    )

@candidates_bp.route('/<int:candidate_id>/withdraw', methods=['POST'])
@require_permission('Candidates', 'update')
@audit_action('withdraw_candidate', module='Candidates')
def withdraw_candidate(candidate_id):
    """Withdraw a candidate from the election"""
    company_id = get_current_company_id()
    candidate = Candidate.query.filter_by(id=candidate_id, company_id=company_id, is_active=True).first_or_404()
    data = request.get_json()
    
    # Check if election is active
    if candidate.ballot.election.status == 'active':
        return jsonify({'error': 'Cannot withdraw candidates from active elections'}), 400
    
    reason = 'Candidate withdrawal'
    if data:
        reason = data.get('withdrawal_reason') or data.get('reason', 'Candidate withdrawal')
    
    candidate.is_withdrawn = True
    candidate.withdrawal_date = datetime.now(timezone.utc)
    candidate.withdrawal_reason = reason
    candidate.is_active = False
    set_audit_fields(candidate, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Candidate withdrawn successfully'}), 200),
        'Failed to withdraw candidate'
    )

@candidates_bp.route('/<int:candidate_id>/reinstate', methods=['POST'])
@require_permission('Candidates', 'update')
@audit_action('reinstate_candidate', module='Candidates')
def reinstate_candidate(candidate_id):
    """Reinstate a withdrawn candidate"""
    company_id = get_current_company_id()
    candidate = Candidate.query.filter_by(id=candidate_id, company_id=company_id, is_withdrawn=True).first_or_404()
    
    # Check if election is active
    if candidate.ballot.election.status == 'active':
        return jsonify({'error': 'Cannot reinstate candidates for active elections'}), 400
    
    if not candidate.is_withdrawn:
        return jsonify({'error': 'Candidate is not withdrawn'}), 400
    
    candidate.is_withdrawn = False
    candidate.withdrawal_date = None
    candidate.withdrawal_reason = None
    candidate.is_active = True
    set_audit_fields(candidate, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Candidate reinstated successfully'}), 200),
        'Failed to reinstate candidate'
    )

@candidates_bp.route('/stats', methods=['GET'])
@require_permission('Candidates', 'view')
def get_candidate_stats():
    """Get candidate statistics for the company"""
    company_id = get_current_company_id()
    
    total_candidates = Candidate.query.filter_by(company_id=company_id).count()
    active_candidates = Candidate.query.filter_by(company_id=company_id, is_active=True).count()
    incumbent_candidates = Candidate.query.filter_by(company_id=company_id, is_incumbent=True).count()
    withdrawn_candidates = Candidate.query.filter_by(company_id=company_id, is_withdrawn=True).count()
    
    # Party distribution
    party_distribution = db.session.query(
        Candidate.party,
        db.func.count(Candidate.id).label('count')
    ).filter_by(company_id=company_id).group_by(Candidate.party).all()
    
    return jsonify({
        'total_candidates': total_candidates,
        'active_candidates': active_candidates,
        'incumbent_candidates': incumbent_candidates,
        'withdrawn_candidates': withdrawn_candidates,
        'party_distribution': {party or 'Independent': count for party, count in party_distribution}
    })

@candidates_bp.route('/upload-image', methods=['POST'])
@require_permission('Candidates', 'create')
def upload_candidate_image():
    """Upload a candidate profile image. Returns a URL to store on the candidate record."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided. Use field name "image".'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, WEBP, or GIF.'}), 400

    # Check file size (max 5 MB)
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    if file_length > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 400

    # Generate a unique filename to prevent collisions
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = secrets.token_hex(16) + '.' + ext
    safe_name = secure_filename(unique_name)

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'candidates')
    os.makedirs(upload_dir, exist_ok=True)

    file.save(os.path.join(upload_dir, safe_name))

    # Build the public URL
    image_url = f'/static/uploads/candidates/{safe_name}'

    return jsonify({
        'message': 'Image uploaded successfully',
        'image_url': image_url,
        'filename': safe_name
    }), 201


@candidates_bp.route('/images/<filename>', methods=['GET'])
def serve_candidate_image(filename):
    """Serve a candidate image (fallback route)"""
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'candidates')
    return send_from_directory(upload_dir, filename)


def generate_candidate_code():
    """Generate a unique candidate code"""
    alphabet = string.ascii_uppercase + string.digits
    return 'C' + ''.join(secrets.choice(alphabet) for _ in range(8))
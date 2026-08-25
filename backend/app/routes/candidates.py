from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from app import db
from app.models.candidate import Candidate
from app.models.ballot import Ballot
from app.models.election import Election
from app.models.vote import Vote
from app.utils import get_current_company_id, require_permission, get_current_user, is_administrator, check_user_permission
from sqlalchemy import or_
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import secrets
import string
import logging
import os

from app.utils.validators import parse_pagination, validate_candidate_input
from app.utils.db_utils import safe_commit
from app.utils.audit import set_audit_fields, audit_action
from app.utils.query_helpers import get_active_candidates_query
from app.utils.cascade import count_dependents, count_reactivatable_dependents, cascade_set_inactive, cascade_reactivate
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE, STATUS_DEACTIVATED

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
UPLOAD_SUBFOLDER = 'uploads/candidates'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set up logging for this module
logger = logging.getLogger(__name__)

candidates_bp = Blueprint('candidates', __name__)

@candidates_bp.route('/<int:candidate_id>/status_dependents', methods=['GET'])
@require_permission('Candidates', 'view')
def get_candidate_status_dependents(candidate_id):
    """Retrieve dependent counts for status transitions (Inactive or Reactivate)."""
    company_id = get_current_company_id()
    candidate = Candidate.query.filter(
        Candidate.id == candidate_id,
        Candidate.company_id == company_id,
        Candidate.status != STATUS_DEACTIVATED
    ).first_or_404()

    if candidate.status == STATUS_ACTIVE:
        result = count_dependents('Candidate', candidate_id)
        return jsonify({'current_status': STATUS_ACTIVE, 'target_status': STATUS_INACTIVE, 'dependents': result})
    else:
        result = count_reactivatable_dependents('Candidate', candidate_id)
        return jsonify({'current_status': STATUS_INACTIVE, 'target_status': STATUS_ACTIVE, 'dependents': result})


@candidates_bp.route('/', methods=['GET'])
@require_permission('Candidates', 'view')
def list_candidates():
    """List all candidates with filtering and pagination"""
    company_id = get_current_company_id()
    search = request.args.get('search')
    ballot_id = request.args.get('ballot_id')
    election_id = request.args.get('election_id')
    party = request.args.get('party')
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
    is_incumbent = request.args.get('is_incumbent')
    page, per_page, error = parse_pagination(request)
    if error:
        return error

    query = Candidate.query.filter(Candidate.company_id == company_id).join(Ballot).join(Election)
    query = query.filter(Candidate.status.in_(allowed), Candidate.status != STATUS_DEACTIVATED)

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
    
    if is_incumbent is not None:
        query = query.filter(Candidate.is_incumbent == (is_incumbent.lower() == 'true'))

    pagination = query.order_by(Candidate.ballot_id, Candidate.order_index).paginate(page=page, per_page=per_page, error_out=False)
    candidates = pagination.items
    
    summary = {
        'total_candidates': pagination.total,
        'active_candidates': sum(1 for c in candidates if c.status == STATUS_ACTIVE),
        'incumbent_candidates': sum(1 for c in candidates if c.is_incumbent),
        'withdrawn_candidates': sum(1 for c in candidates if c.is_withdrawn)
    }

    out_data = []
    has_admin = is_administrator()
    has_results_perm = check_user_permission('Votes', 'view_unpublished_results')
    for c in candidates:
        c_election = c.ballot.election if (c.ballot and c.ballot.election) else None
        res_pub = bool(c_election.results_published) if c_election else False
        can_view_results = res_pub or has_admin or has_results_perm
        out_data.append({
            'id': c.id,
            'name': c.name,
            'candidate_code': c.candidate_code,
            'party': c.party,
            'party_abbreviation': c.party_abbreviation,
            'title': c.title,
            'image_url': c.image_url,
            'ballot_id': c.ballot_id,
            'ballot_title': c.ballot.title if c.ballot else None,
            'election_id': c.ballot.election_id if c.ballot else None,
            'election_title': c.ballot.election.title if (c.ballot and c.ballot.election) else None,
            'order_index': c.order_index,
            'is_write_in': c.is_write_in,
            'is_incumbent': c.is_incumbent,
            'is_active': c.status == STATUS_ACTIVE,
            'status': c.status,
            'is_qualified': c.is_qualified,
            'is_withdrawn': c.is_withdrawn,
            'results_published': res_pub,
            'total_votes_received': c.total_votes_received if can_view_results else None,
            'vote_percentage': c.vote_percentage if can_view_results else None,
            'rank_position': c.rank_position if can_view_results else None,
            'full_display_name': c.full_display_name,
            'party_display': c.party_display,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None
        })
    
    return jsonify({
        'data': out_data,
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
    from app.utils import is_administrator
    data = request.get_json() or {}
    cleaned_data, err = validate_candidate_input(data, is_create=True)
    if err:
        return err
    
    try:
        ballot_id = int(data['ballot_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'ballot_id must be a valid integer'}), 400
    
    # Validate ballot exists
    if is_administrator():
        ballot = Ballot.query.filter_by(id=ballot_id).first()
        company_id = ballot.company_id if ballot else None
    else:
        company_id = get_current_company_id()
        ballot = Ballot.query.filter_by(id=ballot_id, company_id=company_id).first()
    if not ballot:
        return jsonify({'error': 'Ballot not found'}), 404
    
    # Don't allow candidate creation for active, completed, or cancelled elections
    if ballot.election.status in ['active', 'cancelled', 'completed']:
        return jsonify({'error': 'Cannot create candidates for active, completed, or cancelled elections'}), 400
    
    # Check for inactive collision (409 Conflict)
    existing_inactive = Candidate.query.filter(
        Candidate.ballot_id == ballot_id,
        Candidate.name == data['name'],
        Candidate.status == STATUS_INACTIVE
    ).first()
    if existing_inactive:
        return jsonify({
            'error': 'A candidate with this name already exists on this ballot but is currently Inactive.',
            'existing_id': existing_inactive.id,
            'can_reactivate': True
        }), 409

    # Generate unique candidate code
    candidate_code = generate_candidate_code()
    while Candidate.query.filter_by(candidate_code=candidate_code, ballot_id=ballot_id).first():
        candidate_code = generate_candidate_code()
    
    # Helper: convert empty strings to None (prevents PostgreSQL integer
    # column errors when the frontend sends '' for unfilled optional fields).
    def _str_or_none(val):
        """Return None for falsy/whitespace-only strings, otherwise stripped str."""
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    def _int_or_none(val):
        """Safely coerce to int; return None for empty/invalid values."""
        if val is None or val == '':
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # Create candidate
    candidate = Candidate()
    candidate.company_id = company_id
    candidate.ballot_id = ballot_id
    candidate.name = data['name']
    candidate.candidate_code = candidate_code
    candidate.party = _str_or_none(data.get('party'))
    candidate.party_abbreviation = _str_or_none(data.get('party_abbreviation'))
    candidate.title = _str_or_none(data.get('title'))
    candidate.description = _str_or_none(data.get('description'))
    candidate.biography = _str_or_none(data.get('biography'))
    candidate.platform_summary = _str_or_none(data.get('platform_summary'))
    
    # Media and presentation
    candidate.image_url = _str_or_none(data.get('image_url'))
    candidate.profile_image_path = _str_or_none(data.get('profile_image_path'))
    candidate.campaign_website = _str_or_none(data.get('campaign_website'))
    candidate.social_media_links = data.get('social_media_links') or None
    candidate.display_name = _str_or_none(data.get('display_name'))
    
    # Position and status
    candidate.order_index = _int_or_none(data.get('order_index')) or 0
    candidate.is_write_in = data.get('is_write_in', False)
    candidate.is_incumbent = data.get('is_incumbent', False)
    candidate.is_endorsed = data.get('is_endorsed', False)
    candidate.status = data.get('status', STATUS_ACTIVE)
    candidate.is_active = (candidate.status == STATUS_ACTIVE)
    candidate.is_qualified = data.get('is_qualified', True)
    
    # Contact information
    candidate.email = _str_or_none(data.get('email'))
    candidate.phone = _str_or_none(data.get('phone'))
    candidate.address = _str_or_none(data.get('address'))
    
    # Background information
    candidate.age = _int_or_none(data.get('age'))
    candidate.years_in_office = _int_or_none(data.get('years_in_office'))
    candidate.education = _str_or_none(data.get('education'))
    candidate.occupation = _str_or_none(data.get('occupation'))
    
    # Campaign information
    candidate.campaign_finance_id = _str_or_none(data.get('campaign_finance_id'))
    candidate.endorsements = _str_or_none(data.get('endorsements'))
    candidate.key_issues = data.get('key_issues') or None
    
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
        Candidate.status != STATUS_DEACTIVATED
    ).first_or_404()

    c_election = candidate.ballot.election if (candidate.ballot and candidate.ballot.election) else None
    res_pub = bool(c_election.results_published) if c_election else False
    can_view_results = res_pub or is_administrator() or check_user_permission('Votes', 'view_unpublished_results')
    
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
        'is_active': candidate.status == STATUS_ACTIVE,
        'status': candidate.status,
        'is_qualified': candidate.is_qualified,
        'is_withdrawn': candidate.is_withdrawn,
        'withdrawal_date': candidate.withdrawal_date.isoformat() if candidate.withdrawal_date else None,
        'withdrawal_reason': candidate.withdrawal_reason,
        'results_published': res_pub,
        'total_votes_received': candidate.total_votes_received if can_view_results else None,
        'vote_percentage': candidate.vote_percentage if can_view_results else None,
        'rank_position': candidate.rank_position if can_view_results else None,
        'full_display_name': candidate.full_display_name,
        'party_display': candidate.party_display,
        'is_special_option': candidate.is_special_option,
        'vote_summary': candidate.get_vote_summary() if can_view_results else None,
        'created_at': candidate.created_at.isoformat() if candidate.created_at else None,
        'updated_at': candidate.updated_at.isoformat() if candidate.updated_at else None
    })

@candidates_bp.route('/<int:candidate_id>', methods=['PUT'])
@require_permission('Candidates', 'update')
@audit_action('update_candidate', module='Candidates')
def update_candidate(candidate_id):
    """Update candidate information"""
    from app.utils import is_administrator
    if is_administrator():
        candidate = Candidate.query.filter(Candidate.id == candidate_id, Candidate.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        candidate = Candidate.query.filter(Candidate.id == candidate_id, Candidate.company_id == company_id, Candidate.status != STATUS_DEACTIVATED).first_or_404()
    
    data = request.get_json()
    cleaned_data, err = validate_candidate_input(data, is_create=False)
    if err:
        return err
    if candidate.ballot.election.status == 'active':
        return jsonify({'error': 'Cannot modify candidates for active elections'}), 400
    
    # Helper: convert empty strings to None (prevents PostgreSQL integer
    # column errors when the frontend sends '' for unfilled optional fields).
    def _str_or_none(val):
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    def _int_or_none(val):
        if val is None or val == '':
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # Update basic information
    if 'name' in data and data.get('name'):
        candidate.name = data['name']
    if 'party' in data:
        candidate.party = _str_or_none(data['party'])
    if 'party_abbreviation' in data:
        candidate.party_abbreviation = _str_or_none(data['party_abbreviation'])
    if 'title' in data:
        candidate.title = _str_or_none(data['title'])
    if 'description' in data:
        candidate.description = _str_or_none(data['description'])
    if 'biography' in data:
        candidate.biography = _str_or_none(data['biography'])
    if 'platform_summary' in data:
        candidate.platform_summary = _str_or_none(data['platform_summary'])
    
    # Update media and presentation
    if 'image_url' in data:
        candidate.image_url = _str_or_none(data['image_url'])
    if 'profile_image_path' in data:
        candidate.profile_image_path = _str_or_none(data['profile_image_path'])
    if 'campaign_website' in data:
        candidate.campaign_website = _str_or_none(data['campaign_website'])
    if 'social_media_links' in data:
        candidate.social_media_links = data['social_media_links'] or None
    if 'display_name' in data:
        candidate.display_name = _str_or_none(data['display_name'])
    
    # Update position and status
    if 'order_index' in data:
        candidate.order_index = _int_or_none(data['order_index']) or 0
    if 'is_incumbent' in data:
        candidate.is_incumbent = data['is_incumbent']
    if 'is_endorsed' in data:
        candidate.is_endorsed = data['is_endorsed']

    # Handle status transition and cascade
    new_status = data.get('status')
    if new_status is None and 'is_active' in data:
        new_status = STATUS_ACTIVE if data['is_active'] else STATUS_INACTIVE

    if new_status is not None and new_status != candidate.status:
        old_status = candidate.status
        candidate.status = new_status
        candidate.is_active = (new_status == STATUS_ACTIVE)
        if old_status == STATUS_ACTIVE and new_status == STATUS_INACTIVE:
            cascade_set_inactive('Candidate', candidate.id)
        elif old_status == STATUS_INACTIVE and new_status == STATUS_ACTIVE:
            cascade_reactivate('Candidate', candidate.id)

    if 'is_qualified' in data:
        candidate.is_qualified = data['is_qualified']
    
    # Update contact information
    if 'email' in data:
        candidate.email = _str_or_none(data['email'])
    if 'phone' in data:
        candidate.phone = _str_or_none(data['phone'])
    if 'address' in data:
        candidate.address = _str_or_none(data['address'])
    
    # Update background information
    if 'age' in data:
        candidate.age = _int_or_none(data['age'])
    if 'years_in_office' in data:
        candidate.years_in_office = _int_or_none(data['years_in_office'])
    if 'education' in data:
        candidate.education = _str_or_none(data['education'])
    if 'occupation' in data:
        candidate.occupation = _str_or_none(data['occupation'])
    
    # Update campaign information
    if 'campaign_finance_id' in data:
        candidate.campaign_finance_id = _str_or_none(data['campaign_finance_id'])
    if 'endorsements' in data:
        candidate.endorsements = _str_or_none(data['endorsements'])
    if 'key_issues' in data:
        candidate.key_issues = data['key_issues'] or None
    
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
    from app.utils import is_administrator
    if is_administrator():
        candidate = Candidate.query.filter(Candidate.id == candidate_id, Candidate.status != STATUS_DEACTIVATED).first_or_404()
    else:
        company_id = get_current_company_id()
        candidate = Candidate.query.filter(Candidate.id == candidate_id, Candidate.company_id == company_id, Candidate.status != STATUS_DEACTIVATED).first_or_404()
    
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
    
    import time
    ts = int(time.time())

    # Soft delete by updating status
    candidate.status = STATUS_DEACTIVATED
    candidate.is_active = False
    if candidate.name and "_deleted_" not in candidate.name:
        candidate.name = f"{candidate.name}_deleted_{candidate.id}_{ts}"
    if candidate.candidate_code and "_deleted_" not in candidate.candidate_code:
        candidate.candidate_code = f"{candidate.candidate_code}_deleted_{candidate.id}_{ts}"
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
    data = request.get_json(silent=True)
    
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
    candidate = Candidate.query.filter(
        Candidate.id == candidate_id,
        Candidate.company_id == company_id,
        or_(Candidate.is_active == True, Candidate.is_withdrawn == True)
    ).first_or_404()
    
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
from flask import Blueprint, request, jsonify
from app import db
from app.models.company import Company
from app.models.user import User
from app.utils import (
    require_permission, get_current_company_id,
    is_administrator, require_same_company_or_administrator,
)
from app.utils.db_utils import safe_commit
from app.utils.audit import audit_action, set_audit_fields
from app.utils.validators import parse_pagination, validate_company_input
from app.utils.constants import STATUS_INACTIVE, STATUS_ACTIVE
from app.utils.query_helpers import get_active_companies_query

companies_bp = Blueprint('companies', __name__)

def _serialize_company(c):
    return {
        'id': c.id,
        'company_name': c.company_name,
        'description': c.description or '',
        'email': c.email or '',
        'phone': c.phone or '',
        'website': c.website or '',
        'address': c.address or '',
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        'status': c.status
    }

@companies_bp.route('/', methods=['GET'])
@require_permission('Companies', 'view')
def list_companies():
    """List companies visible to the current user.

    Platform Administrators see every active company (with pagination and
    search).  All other users see only their own company.
    """
    if is_administrator():
        query = get_active_companies_query()
        search = request.args.get('search', '').strip()
        if search:
            query = query.filter(Company.company_name.ilike(f'%{search}%'))
            
        query = query.order_by(Company.updated_at.desc(), Company.created_at.desc())
        
        page, per_page, error = parse_pagination(request)
        if error:
            return error
            
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'data': [_serialize_company(c) for c in paginated.items],
            'total': paginated.total,
            'page': paginated.page,
            'pages': paginated.pages
        })
    else:
        company_id = get_current_company_id()
        company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
            
        return jsonify({
            'data': [_serialize_company(company)],
            'total': 1,
            'page': 1,
            'pages': 1
        })

@companies_bp.route('/', methods=['POST'])
@require_permission('Companies', 'create')
@audit_action('create_company', module='Companies', description='Created a company')
def create_company():
    """Create a new company.  Platform Administrators only."""
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can create companies'}), 403
        
    data = request.get_json()
    cleaned_data, error = validate_company_input(data, is_create=True)
    if error:
        return error[0], error[1]
        
    # Case-insensitive duplicate check
    existing = Company.query.filter(
        Company.company_name.ilike(cleaned_data['company_name']),
        Company.status != STATUS_INACTIVE
    ).first()
    
    if existing:
        return jsonify({'error': 'Company name already exists'}), 400
        
    company = Company()
    for key, value in cleaned_data.items():
        setattr(company, key, value)
        
    set_audit_fields(company, is_create=True)
    db.session.add(company)
    
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Company name already exists'}), 400
        
    return safe_commit(
        (jsonify({'message': 'Company created', 'company_id': company.id}), 201),
        'Internal server error during company creation'
    )

@companies_bp.route('/<int:company_id>', methods=['GET'])
@require_permission('Companies', 'view')
def get_company(company_id):
    """Retrieve a single company.

    Users may only view their own company unless they are a platform
    Administrator.
    """
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    return jsonify(_serialize_company(company))

@companies_bp.route('/<int:company_id>', methods=['PUT'])
@require_permission('Companies', 'update')
@audit_action('update_company', module='Companies', description='Updated a company', get_target_id=lambda *a, **kw: kw.get('company_id'))
def update_company(company_id):
    """Update company details.

    Users may only update their own company unless they are a platform
    Administrator.
    """
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    data = request.get_json()
    cleaned_data, error = validate_company_input(data, is_create=False)
    if error:
        return error[0], error[1]
        
    if 'company_name' in cleaned_data:
        existing = Company.query.filter(
            Company.company_name.ilike(cleaned_data['company_name']),
            Company.status != STATUS_INACTIVE,
            Company.id != company_id
        ).first()
        if existing:
            return jsonify({'error': 'Company name already exists'}), 400
            
    for key, value in cleaned_data.items():
        setattr(company, key, value)
        
    set_audit_fields(company, is_create=False)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Company name already exists'}), 400
        
    return safe_commit(
        (jsonify({'message': 'Company updated'}), 200),
        'Internal server error during company update'
    )

@companies_bp.route('/<int:company_id>', methods=['DELETE'])
@require_permission('Companies', 'delete')
@audit_action('delete_company', module='Companies', description='Deleted a company', get_target_id=lambda *a, **kw: kw.get('company_id'))
def delete_company(company_id):
    """Soft-delete a company.  Platform Administrators only.

    Defense-in-depth: even after the Administrator check, we explicitly
    verify the caller's own company matches the target unless the caller
    is an Administrator (prevents bugs in future permission changes from
    silently widening the blast radius).
    """
    if not is_administrator():
        return jsonify({'error': 'Forbidden: Only platform Administrators can delete companies'}), 403

    # Defense-in-depth: non-administrators must target their own company
    # (already blocked above, but kept as an explicit second gate).
    denied = require_same_company_or_administrator(company_id)
    if denied:
        return denied
        
    company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    active_users = User.query.filter(
        User.company_id == company_id,
        User.status != STATUS_INACTIVE
    ).count()
    
    if active_users > 0:
        return jsonify({'error': f'Cannot delete company. There are {active_users} active users associated with this company.'}), 400
        
    company.status = STATUS_INACTIVE
    set_audit_fields(company, is_create=False)
    
    return safe_commit(
        (jsonify({'message': 'Company deleted'}), 200),
        'Internal server error during company deletion'
    )

from flask import Blueprint, request, jsonify
from app import db
from app.models.company import Company
from app.models.user import User
from app.utils import require_permission, get_current_company_id, is_current_user_super_admin
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
    is_super = is_current_user_super_admin()
    if is_super:
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
    if not is_current_user_super_admin():
        return jsonify({'error': 'Forbidden: Only Super Admins can create companies'}), 403
        
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
    is_super = is_current_user_super_admin()
    if not is_super and company_id != get_current_company_id():
        return jsonify({'error': 'Forbidden'}), 403
        
    company = Company.query.filter_by(id=company_id).filter(Company.status != STATUS_INACTIVE).first()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    return jsonify(_serialize_company(company))

@companies_bp.route('/<int:company_id>', methods=['PUT'])
@require_permission('Companies', 'update')
@audit_action('update_company', module='Companies', description='Updated a company', get_target_id=lambda *a, **kw: kw.get('company_id'))
def update_company(company_id):
    is_super = is_current_user_super_admin()
    if not is_super and company_id != get_current_company_id():
        return jsonify({'error': 'Forbidden'}), 403
        
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
    if not is_current_user_super_admin():
        return jsonify({'error': 'Forbidden: Only Super Admins can delete companies'}), 403
        
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

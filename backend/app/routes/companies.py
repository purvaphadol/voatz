from flask import Blueprint, request, jsonify
from app import db
from app.models.company import Company

companies_bp = Blueprint('companies', __name__)

@companies_bp.route('/', methods=['GET'])
def list_companies():
    companies = Company.query.all()
    
    # Build company data with all available fields
    company_data = []
    for c in companies:
        company_info = {
            'id': c.id, 
            'company_name': c.company_name,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None,
            'status': c.status if hasattr(c, 'status') else 1
        }
        # Add additional fields if the model has them
        if hasattr(c, 'email') and c.email:
            company_info['email'] = c.email
        if hasattr(c, 'phone') and c.phone:
            company_info['phone'] = c.phone
        if hasattr(c, 'website') and c.website:
            company_info['website'] = c.website
        if hasattr(c, 'address') and c.address:
            company_info['address'] = c.address
        company_data.append(company_info)
    
    return jsonify({
        'data': company_data,
        'total': len(company_data),
        'page': 1,
        'pages': 1
    })

@companies_bp.route('/', methods=['POST'])
def create_company():
    data = request.get_json()
    company = Company()
    company.company_name = data['company_name']
    db.session.add(company)
    db.session.commit()
    return jsonify({'message': 'Company created'}), 201

@companies_bp.route('/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    company = Company.query.get_or_404(company_id)
    data = request.get_json()
    company.company_name = data.get('company_name', company.company_name)
    db.session.commit()
    return jsonify({'message': 'Company updated'}), 200

@companies_bp.route('/<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    return jsonify({'message': 'Company deleted'}), 200

from flask import Blueprint, request, jsonify
from app import db
from app.models.department import Department
from app.models.company import Company
from app.utils import get_current_company_id, require_company_context

departments_bp = Blueprint('departments', __name__)

@departments_bp.route('/', methods=['GET'])
@require_company_context
def list_departments():
    company_id = get_current_company_id()
    departments = Department.query.join(Company).filter(Department.company_id == company_id).all()
    
    # Build department data with description if available
    dept_data = []
    for d in departments:
        dept_info = {
            'id': d.id, 
            'department_name': d.department_name,
            'company_id': d.company_id,
            'company_name': d.company.company_name,
            'created_at': d.created_at.isoformat() if d.created_at else None,
            'updated_at': d.updated_at.isoformat() if d.updated_at else None,
            'status': d.status if hasattr(d, 'status') else 1
        }
        # Add description if the model has it
        if hasattr(d, 'description') and d.description:
            dept_info['description'] = d.description
        dept_data.append(dept_info)
    
    return jsonify({
        'data': dept_data,
        'total': len(dept_data),
        'page': 1,
        'pages': 1
    })

@departments_bp.route('/', methods=['POST'])
@require_company_context
def create_department():
    company_id = get_current_company_id()
    data = request.get_json()
    
    if not data or not data.get('department_name'):
        return jsonify({'error': 'Department name is required'}), 400
    
    # Check if department name already exists within the company
    if Department.query.filter_by(department_name=data['department_name'], company_id=company_id).first():
        return jsonify({'error': 'Department name already exists in this company'}), 400
    
    department = Department()
    department.department_name = data['department_name']
    department.company_id = company_id
    db.session.add(department)
    db.session.commit()
    return jsonify({'message': 'Department created', 'department_id': department.id}), 201

@departments_bp.route('/<int:department_id>', methods=['GET'])
@require_company_context
def get_department(department_id):
    company_id = get_current_company_id()
    department = Department.query.join(Company).filter(
        Department.id == department_id, 
        Department.company_id == company_id
    ).first_or_404()
    return jsonify({
        'id': department.id,
        'department_name': department.department_name,
        'company_id': department.company_id,
        'company_name': department.company.company_name,
        'created_at': department.created_at.isoformat() if department.created_at else None,
        'updated_at': department.updated_at.isoformat() if department.updated_at else None,
        'status': department.status if hasattr(department, 'status') else 1
    })

@departments_bp.route('/<int:department_id>', methods=['PUT'])
@require_company_context
def update_department(department_id):
    company_id = get_current_company_id()
    department = Department.query.filter_by(id=department_id, company_id=company_id).first_or_404()
    data = request.get_json()
    
    if data.get('department_name'):
        # Check if department name already exists within the company (excluding current department)
        existing_dept = Department.query.filter_by(
            department_name=data['department_name'], 
            company_id=company_id
        ).first()
        if existing_dept and existing_dept.id != department_id:
            return jsonify({'error': 'Department name already exists in this company'}), 400
        
        department.department_name = data['department_name']
    
    db.session.commit()
    return jsonify({'message': 'Department updated'}), 200

@departments_bp.route('/<int:department_id>', methods=['DELETE'])
@require_company_context
def delete_department(department_id):
    company_id = get_current_company_id()
    department = Department.query.filter_by(id=department_id, company_id=company_id).first_or_404()
    db.session.delete(department)
    db.session.commit()
    return jsonify({'message': 'Department deleted'}), 200

from flask import jsonify
import re
from app.models.department import Department
from app.utils.constants import (
    STATUS_INACTIVE, 
    DEFAULT_PAGE, 
    DEFAULT_PER_PAGE, 
    MAX_PER_PAGE, 
    MIN_PASSWORD_LENGTH
)

def safe_get_json(request):
    try:
        data = request.get_json()
        if data is None:
            data = request.form.to_dict() if request.form else None
        if isinstance(data, str):
            return None, (jsonify({'error': 'Invalid JSON format in request'}), 400)
        return data, None
    except Exception as e:
        return None, (jsonify({'error': f'Request parsing error: {str(e)}'}), 400)

def sanitize_string(value):
    if value is None:
        return None
    return str(value).strip()

def validate_email(email):
    email = sanitize_string(email)
    if not email:
        return None, (jsonify({'error': 'Email cannot be empty'}), 400)
    email = email.lower()
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return None, (jsonify({'error': 'Invalid email address format'}), 400)
    return email, None

def validate_password(password):
    if not password:
        return (jsonify({'error': 'Password is required'}), 400)
        
    password = str(password).strip()
    if not password:
        return (jsonify({'error': 'Password cannot be entirely whitespace'}), 400)
        
    if len(password) < MIN_PASSWORD_LENGTH:
        return (jsonify({'error': f'Password must be at least {MIN_PASSWORD_LENGTH} characters long'}), 400)
        
    if not any(char.isalpha() for char in password):
        return (jsonify({'error': 'Password must contain at least one letter'}), 400)
        
    if not any(char.isdigit() for char in password):
        return (jsonify({'error': 'Password must contain at least one number'}), 400)
        
    return None

def validate_department(dept_id, company_id):
    if not dept_id:
        return None, None
    try:
        dept_id = int(dept_id)
    except ValueError:
        return None, (jsonify({'error': 'Invalid department ID format'}), 400)
        
    dept = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    if not dept:
        return None, (jsonify({'error': 'Invalid department'}), 400)
    if getattr(dept, 'status', 1) == STATUS_INACTIVE:
        return None, (jsonify({'error': 'Department is inactive'}), 400)
    return dept_id, None

def validate_user_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
        
    if is_create and (not data.get('name') or not data.get('email') or not data.get('password')):
        return None, (jsonify({'error': 'Name, email, and password are required'}), 400)
        
    cleaned_data = {}
    
    if 'name' in data and data['name'] is not None:
        name = sanitize_string(data['name'])
        if not name:
            return None, (jsonify({'error': 'Name cannot be empty'}), 400)
        cleaned_data['name'] = name
        
    if 'email' in data and data['email'] is not None:
        email, error = validate_email(data['email'])
        if error:
            return None, error
        cleaned_data['email'] = email
        
    return cleaned_data, None

def parse_pagination(request):
    try:
        page = int(request.args.get('page', DEFAULT_PAGE))
        if page < 1:
            page = DEFAULT_PAGE
    except ValueError:
        return None, None, (jsonify({'error': 'Invalid page parameter'}), 400)
        
    try:
        per_page = int(request.args.get('per_page', DEFAULT_PER_PAGE))
        if per_page < 1:
            per_page = DEFAULT_PER_PAGE
        if per_page > MAX_PER_PAGE:
            per_page = MAX_PER_PAGE
    except ValueError:
        return None, None, (jsonify({'error': 'Invalid per_page parameter'}), 400)
        
    return page, per_page, None


def validate_role_name(role_name):
    """Sanitize and validate a role name. Returns (cleaned_name, error_tuple_or_None)."""
    if role_name is None:
        return None, (jsonify({'error': 'Role name is required'}), 400)
    name = str(role_name).strip()
    if not name:
        return None, (jsonify({'error': 'Role name cannot be empty'}), 400)
    if len(name) > 100:
        return None, (jsonify({'error': 'Role name cannot exceed 100 characters'}), 400)
    return name, None


def validate_role_input(data, is_create=False):
    """Validate role create/update payload. Returns (cleaned_data, error_tuple_or_None)."""
    if not data:
        return None, (jsonify({'error': 'Request data is required'}), 400)
    cleaned = {}
    if is_create:
        if not data.get('department_id'):
            return None, (jsonify({'error': 'department_id is required'}), 400)
        role_name, err = validate_role_name(data.get('role_name'))
        if err:
            return None, err
        cleaned['role_name'] = role_name
    else:
        if data.get('role_name') is not None:
            role_name, err = validate_role_name(data.get('role_name'))
            if err:
                return None, err
            cleaned['role_name'] = role_name
    if 'description' in data:
        cleaned['description'] = str(data['description']).strip() if data['description'] else ''
    if 'department_id' in data and data['department_id']:
        try:
            cleaned['department_id'] = int(data['department_id'])
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid department_id format'}), 400)
    return cleaned, None


def validate_department_active(department):
    """Check a Department object is active. Returns error_tuple or None."""
    from app.utils.constants import STATUS_INACTIVE
    if not department:
        return (jsonify({'error': 'Invalid department for this company'}), 400)
    if getattr(department, 'status', 1) == STATUS_INACTIVE:
        return (jsonify({'error': 'Department is inactive'}), 400)
    return None

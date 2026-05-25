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
    name = str(role_name).strip().title()
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


def validate_department_name(name):
    """Sanitize and validate a department name.
    Returns (cleaned_name, error_tuple_or_None)."""
    if name is None:
        return None, (jsonify({'error': 'Department name is required'}), 400)
    cleaned = str(name).strip().title()
    if not cleaned:
        return None, (jsonify({'error': 'Department name cannot be empty'}), 400)
    if len(cleaned) > 100:
        return None, (jsonify({'error': 'Department name cannot exceed 100 characters'}), 400)
    return cleaned, None


def validate_department_input(data, is_create=False):
    """Validate department create/update payload.
    Returns (cleaned_data, error_tuple_or_None)."""
    if not data:
        return None, (jsonify({'error': 'Request data is required'}), 400)
    cleaned = {}
    if is_create:
        name, err = validate_department_name(data.get('department_name'))
        if err:
            return None, err
        cleaned['department_name'] = name
    else:
        if data.get('department_name') is not None:
            name, err = validate_department_name(data.get('department_name'))
            if err:
                return None, err
            cleaned['department_name'] = name
    if 'description' in data:
        cleaned['description'] = str(data['description']).strip() \
            if data['description'] else ''
    return cleaned, None


def validate_company_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
        
    cleaned = {}
    
    # Handle company_name
    if is_create and not data.get('company_name'):
        return None, (jsonify({'error': 'Company name is required'}), 400)
        
    if 'company_name' in data and data['company_name'] is not None:
        name = str(data['company_name']).strip().title()
        if not name:
            return None, (jsonify({'error': 'Company name cannot be empty'}), 400)
        if len(name) > 100:
            return None, (jsonify({'error': 'Company name cannot exceed 100 characters'}), 400)
        cleaned['company_name'] = name
    elif is_create:
        return None, (jsonify({'error': 'Company name cannot be empty'}), 400)
        
    # Handle email
    if 'email' in data:
        email = data['email']
        if email and str(email).strip():
            valid_email, err = validate_email(email)
            if err:
                return None, err
            cleaned['email'] = valid_email
        else:
            cleaned['email'] = None

    # Handle phone
    if 'phone' in data:
        phone = data['phone']
        if phone and str(phone).strip():
            phone_val = str(phone).strip()
            if len(phone_val) > 20:
                return None, (jsonify({'error': 'Phone cannot exceed 20 characters'}), 400)
            cleaned['phone'] = phone_val
        else:
            cleaned['phone'] = None

    # Handle website
    if 'website' in data:
        website = data['website']
        if website and str(website).strip():
            website_val = str(website).strip()
            if len(website_val) > 200:
                return None, (jsonify({'error': 'Website cannot exceed 200 characters'}), 400)
            cleaned['website'] = website_val
        else:
            cleaned['website'] = None

    # Handle description
    if 'description' in data:
        desc = data['description']
        if desc and str(desc).strip():
            cleaned['description'] = str(desc).strip()
        else:
            cleaned['description'] = None

    # Handle address
    if 'address' in data:
        addr = data['address']
        if addr and str(addr).strip():
            cleaned['address'] = str(addr).strip()
        else:
            cleaned['address'] = None

    return cleaned, None


def validate_module_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
        
    cleaned = {}
    
    if is_create:
        if not data.get('module_name') or not str(data['module_name']).strip():
            return None, (jsonify({'error': 'Module name is required'}), 400)
            
    if 'module_name' in data and data['module_name'] is not None:
        name = str(data['module_name']).strip()
        if not name and is_create:
            return None, (jsonify({'error': 'Module name cannot be empty'}), 400)
        elif name:
            name = name.title()
            if len(name) > 100:
                return None, (jsonify({'error': 'Module name cannot exceed 100 characters'}), 400)
            cleaned['module_name'] = name

    if 'route_name' in data:
        if data['route_name'] and str(data['route_name']).strip():
            route = str(data['route_name']).strip().lower()
            if len(route) > 100:
                return None, (jsonify({'error': 'Route name cannot exceed 100 characters'}), 400)
            cleaned['route_name'] = route
        else:
            cleaned['route_name'] = None
            
    if 'description' in data:
        if data['description'] and str(data['description']).strip():
            cleaned['description'] = str(data['description']).strip()
        else:
            cleaned['description'] = None
            
    if 'icon' in data:
        if data['icon'] and str(data['icon']).strip():
            icon = str(data['icon']).strip()
            if len(icon) > 100:
                return None, (jsonify({'error': 'Icon cannot exceed 100 characters'}), 400)
            cleaned['icon'] = icon
        else:
            cleaned['icon'] = None
            
    if 'order_index' in data and data['order_index'] is not None:
        try:
            order_index = int(data['order_index'])
            if order_index < 0 or order_index > 999:
                return None, (jsonify({'error': 'Order index must be between 0 and 999'}), 400)
            cleaned['order_index'] = order_index
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid order_index format'}), 400)
            
    if 'status' in data and data['status'] is not None:
        try:
            status = int(data['status'])
            if status not in (0, 1, 9):
                return None, (jsonify({'error': 'Invalid status'}), 400)
            cleaned['status'] = status
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid status format'}), 400)
            
    return cleaned, None


def validate_module_action_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
        
    cleaned = {}
    
    if is_create:
        if not data.get('action_name') or not str(data['action_name']).strip():
            return None, (jsonify({'error': 'Action name is required'}), 400)
        if not data.get('action_url') or not str(data['action_url']).strip():
            return None, (jsonify({'error': 'Action URL is required'}), 400)
            
    if 'action_name' in data and data['action_name'] is not None:
        name = str(data['action_name']).strip()
        if not name:
            return None, (jsonify({'error': 'Action name cannot be empty'}), 400)
        name = name.lower()
        if len(name) > 100:
            return None, (jsonify({'error': 'Action name cannot exceed 100 characters'}), 400)
        cleaned['action_name'] = name
        
    if 'action_url' in data and data['action_url'] is not None:
        url = str(data['action_url']).strip()
        if not url:
            return None, (jsonify({'error': 'Action URL cannot be empty'}), 400)
        if len(url) > 255:
            return None, (jsonify({'error': 'Action URL cannot exceed 255 characters'}), 400)
        cleaned['action_url'] = url
        
    if 'status' in data and data['status'] is not None:
        try:
            status = int(data['status'])
            if status not in (0, 1, 9):
                return None, (jsonify({'error': 'Invalid status'}), 400)
            cleaned['status'] = status
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid status format'}), 400)
            
    return cleaned, None

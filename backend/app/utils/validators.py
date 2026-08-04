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
        name, err = validate_non_numeric_text(data['name'], 'Name', min_length=2, max_length=100, required=is_create)
        if err:
            return None, err
        cleaned_data['name'] = name
        
    if 'email' in data and data['email'] is not None:
        email, error = validate_email(data['email'])
        if error:
            return None, error
        cleaned_data['email'] = email
        
    return cleaned_data, None

def validate_voter_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
        
    cleaned_data = {}
    
    # phone_number validation
    if is_create and 'phone_number' not in data:
        return None, (jsonify({'error': 'phone_number is required'}), 400)
        
    if 'phone_number' in data:
        phone_val = data['phone_number']
        if phone_val is not None:
            phone_str = str(phone_val).strip()
            if is_create and not phone_str:
                return None, (jsonify({'error': 'phone_number is required'}), 400)
            if len(phone_str) > 20:
                return None, (jsonify({'error': 'phone_number cannot exceed 20 characters'}), 400)
            cleaned_data['phone_number'] = phone_str
        else:
            if is_create:
                return None, (jsonify({'error': 'phone_number is required'}), 400)
            cleaned_data['phone_number'] = None
            
    # date_of_birth validation
    if 'date_of_birth' in data:
        dob_val = data['date_of_birth']
        if dob_val and str(dob_val).strip():
            dob_str = str(dob_val).strip()
            from datetime import datetime
            try:
                parsed_dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                cleaned_data['date_of_birth'] = parsed_dob
            except (ValueError, TypeError):
                return None, (jsonify({'error': 'Invalid date_of_birth format, use YYYY-MM-DD'}), 400)
        else:
            cleaned_data['date_of_birth'] = None
            
    # voter_type validation
    if 'voter_type' in data:
        vt_val = data['voter_type']
        if vt_val is None or str(vt_val).strip() == '':
            cleaned_data['voter_type'] = 'standard'
        else:
            vt_str = str(vt_val).strip()
            if vt_str not in ['standard', 'overseas', 'military', 'disabled']:
                return None, (jsonify({'error': 'Invalid voter_type'}), 400)
            cleaned_data['voter_type'] = vt_str
            
    # name validation
    if 'name' in data:
        name_val = data['name']
        if name_val is not None:
            name_str = str(name_val).strip().title()
            if len(name_str) > 100:
                return None, (jsonify({'error': 'Name cannot exceed 100 characters'}), 400)
            cleaned_data['name'] = name_str
        else:
            cleaned_data['name'] = None
            
    # email validation
    if 'email' in data:
        email_val = data['email']
        if email_val and str(email_val).strip():
            cleaned_email, err = validate_email(email_val)
            if err:
                return None, err
            cleaned_data['email'] = cleaned_email
        else:
            cleaned_data['email'] = None
            
    # jurisdiction validation
    if 'jurisdiction' in data:
        jur_val = data['jurisdiction']
        if jur_val is not None:
            jur_str = str(jur_val).strip()
            if len(jur_str) > 100:
                return None, (jsonify({'error': 'Jurisdiction cannot exceed 100 characters'}), 400)
            cleaned_data['jurisdiction'] = jur_str
        else:
            cleaned_data['jurisdiction'] = None
            
    # registered_address validation
    if 'registered_address' in data:
        addr_val = data['registered_address']
        if addr_val is not None:
            cleaned_data['registered_address'] = str(addr_val).strip()
        else:
            cleaned_data['registered_address'] = None
            
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
    return validate_non_numeric_text(role_name, field_name="Role name", min_length=2, max_length=100, required=True)


def validate_role_input(data, is_create=False):
    """Validate role create/update payload. Returns (cleaned_data, error_tuple_or_None)."""
    if not data:
        return None, (jsonify({'error': 'Request data is required'}), 400)
    cleaned = {}
    if is_create:
        if not data.get('department_id') and not data.get('is_super_admin'):
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
    return validate_non_numeric_text(name, field_name="Department name", min_length=2, max_length=100, required=True)


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
        name, err = validate_non_numeric_text(data['company_name'], field_name="Company name", min_length=2, max_length=100, required=is_create)
        if err:
            return None, err
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
            phone_val, err = validate_phone_number(phone, field_name="Phone")
            if err:
                return None, err
            cleaned['phone'] = phone_val
        else:
            cleaned['phone'] = None

    # Handle website
    if 'website' in data:
        website = data['website']
        if website and str(website).strip():
            website_val, err = validate_url_format(website, field_name="Website")
            if err:
                return None, err
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
        name, err = validate_non_numeric_text(data['module_name'], field_name="Module name", min_length=2, max_length=100, required=is_create)
        if err:
            return None, err
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


def validate_non_numeric_text(text, field_name="Field", min_length=2, max_length=100, required=True):
    if text is None:
        if required:
            return None, (jsonify({'error': f'{field_name} is required'}), 400)
        return None, None
        
    val = str(text).strip()
    if not val:
        if required:
            return None, (jsonify({'error': f'{field_name} cannot be empty'}), 400)
        return None, None

    if len(val) < min_length:
        return None, (jsonify({'error': f'{field_name} must be at least {min_length} characters'}), 400)
        
    if len(val) > max_length:
        return None, (jsonify({'error': f'{field_name} cannot exceed {max_length} characters'}), 400)

    if val.isdigit():
        return None, (jsonify({'error': f'{field_name} cannot consist solely of numbers'}), 400)

    if not re.search(r'[a-zA-Z]', val):
        return None, (jsonify({'error': f'{field_name} must contain at least one letter'}), 400)

    return val, None


def validate_phone_number(phone, field_name="Phone number", required=False):
    if phone is None or str(phone).strip() == '':
        if required:
            return None, (jsonify({'error': f'{field_name} is required'}), 400)
        return None, None

    val = str(phone).strip()
    if len(val) < 7 or len(val) > 20:
        return None, (jsonify({'error': f'{field_name} must be between 7 and 20 characters'}), 400)

    phone_regex = r'^\+?[0-9\-\s\(\)]{7,20}$'
    if not re.match(phone_regex, val):
        return None, (jsonify({'error': f'Invalid {field_name.lower()} format'}), 400)

    return val, None


def validate_url_format(url, field_name="URL", required=False):
    if url is None or str(url).strip() == '':
        if required:
            return None, (jsonify({'error': f'{field_name} is required'}), 400)
        return None, None

    val = str(url).strip()
    if val.startswith('data:image/'):
        return val, None

    url_regex = r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$'
    if not re.match(url_regex, val, re.IGNORECASE):
        return None, (jsonify({'error': f'Invalid {field_name.lower()} format (must be valid HTTP/HTTPS URL)'}), 400)

    return val, None


def validate_date_range_iso(start_str, end_str):
    from datetime import datetime
    if not start_str or not end_str:
        return None, (jsonify({'error': 'Start date and end date are required'}), 400)

    try:
        start_date = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(str(end_str).replace('Z', '+00:00'))
    except Exception:
        return None, (jsonify({'error': 'Invalid date format (ISO 8601 expected)'}), 400)

    if end_date <= start_date:
        return None, (jsonify({'error': 'End date must be strictly after start date'}), 400)

    return (start_date, end_date), None


def validate_election_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
    cleaned = {}

    if is_create:
        if not data.get('title'):
            return None, (jsonify({'error': 'Title is required'}), 400)
        if not data.get('start_date') or not data.get('end_date'):
            return None, (jsonify({'error': 'Start date and end date are required'}), 400)

    if 'title' in data and data['title'] is not None:
        title, err = validate_non_numeric_text(data['title'], field_name="Title", min_length=3, max_length=150, required=is_create)
        if err:
            return None, err
        cleaned['title'] = title

    if 'start_date' in data and 'end_date' in data and data['start_date'] and data['end_date']:
        dates, err = validate_date_range_iso(data['start_date'], data['end_date'])
        if err:
            return None, err
        cleaned['start_date'] = dates[0]
        cleaned['end_date'] = dates[1]

    if 'description' in data:
        cleaned['description'] = str(data['description']).strip() if data['description'] else None

    return cleaned, None


def validate_ballot_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
    cleaned = {}

    if is_create:
        if not data.get('title'):
            return None, (jsonify({'error': 'Ballot title is required'}), 400)
        if not data.get('election_id'):
            return None, (jsonify({'error': 'election_id is required'}), 400)

    if 'title' in data and data['title'] is not None:
        title, err = validate_non_numeric_text(data['title'], field_name="Ballot title", min_length=3, max_length=200, required=is_create)
        if err:
            return None, err
        cleaned['title'] = title

    if 'ballot_type' in data and data['ballot_type'] is not None:
        b_type = str(data['ballot_type']).strip().lower()
        if b_type not in ['single_choice', 'multiple_choice', 'ranked_choice', 'approval']:
            return None, (jsonify({'error': 'Invalid ballot_type'}), 400)
        cleaned['ballot_type'] = b_type

    if 'min_selections' in data and 'max_selections' in data:
        try:
            min_sel = int(data['min_selections'])
            max_sel = int(data['max_selections'])
            if min_sel < 0:
                return None, (jsonify({'error': 'Minimum selections cannot be negative'}), 400)
            if max_sel < 1:
                return None, (jsonify({'error': 'Maximum selections must be at least 1'}), 400)
            if min_sel > max_sel:
                return None, (jsonify({'error': 'Minimum selections cannot exceed maximum selections'}), 400)
            cleaned['min_selections'] = min_sel
            cleaned['max_selections'] = max_sel
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid selection bounds format'}), 400)

    return cleaned, None


def validate_candidate_input(data, is_create=False):
    if not data:
        return None, (jsonify({'error': 'Data is required'}), 400)
    cleaned = {}

    if is_create:
        if not data.get('name'):
            return None, (jsonify({'error': 'Candidate name is required'}), 400)

    if 'name' in data and data['name'] is not None:
        name, err = validate_non_numeric_text(data['name'], field_name="Candidate name", min_length=2, max_length=100, required=is_create)
        if err:
            return None, err
        cleaned['name'] = name

    if 'email' in data and data['email']:
        email, err = validate_email(data['email'])
        if err:
            return None, err
        cleaned['email'] = email

    if 'phone' in data and data['phone']:
        phone, err = validate_phone_number(data['phone'], field_name="Phone")
        if err:
            return None, err
        cleaned['phone'] = phone

    if 'image_url' in data and data['image_url']:
        url, err = validate_url_format(data['image_url'], field_name="Image URL")
        if err:
            return None, err
        cleaned['image_url'] = url

    if 'age' in data and data['age']:
        try:
            age = int(data['age'])
            if age < 18 or age > 120:
                return None, (jsonify({'error': 'Candidate age must be between 18 and 120'}), 400)
            cleaned['age'] = age
        except (ValueError, TypeError):
            return None, (jsonify({'error': 'Invalid age format'}), 400)

    return cleaned, None



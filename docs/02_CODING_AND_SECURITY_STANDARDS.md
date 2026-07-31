# Coding, Architecture & Security Standards

## 1. Code Architecture & OOP Principles

All code in the project must follow clean Object-Oriented Programming (OOP) and DRY (Don't Repeat Yourself) principles:

- **Single Responsibility Principle**: Route handlers process HTTP requests/responses, models handle data persistence and properties, and validation logic resides strictly in utility modules.
- **Reusable Utility Functions**: Common operations (such as commit wrappers, datetime parsers, permission checks) must be implemented as clean, reusable functions in `app/utils/`.
- **Modular Blueprint Structure**: Backend routes must be split into feature-specific Flask Blueprints (`companies_bp`, `elections_bp`, `votes_bp`, etc.).

---

## 2. Centralized Input Validation Rules (`app/utils/validators.py`)

All input validation, sanitization, type checking, and boundary rules MUST be centralized inside `app/utils/validators.py`. Route handlers must NOT perform inline ad-hoc input validation.

### Standard Validation Functions Pattern:
```python
# Example pattern in app/utils/validators.py
def validate_election_input(data, is_create=True):
    cleaned_data = {}
    if is_create and not data.get('title'):
        return None, (jsonify({'error': 'Title is required'}), 400)
    # Perform type conversion, string stripping, sanitization...
    return cleaned_data, None
```

### Usage in Route Handlers:
```python
cleaned_data, error = validate_election_input(request.get_json(), is_create=True)
if error:
    return error
```

---

## 3. Indian Standard Time (IST - UTC+05:30) Standard

All date and time calculations must use **Indian Standard Time (IST)**:

```python
from datetime import datetime, timezone, timedelta

# IST Timezone Definition
IST = timezone(timedelta(hours=5, minutes=30))

def get_current_ist_time():
    return datetime.now(IST)

def ensure_ist(dt):
    """Converts naive or aware datetime to IST aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)
```

- When comparing database datetime fields against current timestamps, always wrap both in `ensure_ist()` to prevent `TypeError: can't compare offset-naive and offset-aware datetimes`.

---

## 4. Multi-Tenant Security & Isolation Standards

1. **Company Isolation**: All database queries for non-platform admin users MUST filter by `company_id = get_current_company_id()`.
2. **IDOR & Cross-Tenant Leakage Protection**:
   - Access attempts to resources belonging to another company must return `404 Not Found` (to avoid leaking resource existence) or `403 Forbidden`.
3. **Route Permission Decorator**:
   All protected endpoints MUST be decorated with `@require_permission(module_name, action_name)`:
   ```python
   @elections_bp.route('/', methods=['POST'])
   @require_permission('Elections', 'create')
   @audit_action('create_election', module='Elections')
   def create_election():
       ...
   ```
4. **Company Super Admin Privilege**:
   - Users with a role where `is_super_admin = True` automatically pass `check_user_permission` for any module provisioned for their company.
   - Company Super Admin roles cannot be deleted, edited, or self-deleted.

---

## 5. Database Transaction Safety (`safe_commit` & `flush`)

1. **Atomic Flush**: When creating dependent entities within a single request (e.g. creating a `Voter` and then registering them), call `db.session.flush()` after adding the first object to generate its primary key before querying or creating child records.
2. **`safe_commit` Wrapper**: All DB commit operations MUST use the `safe_commit` helper to catch database errors and perform automatic rollback on failure:
   ```python
   from app.utils.db_utils import safe_commit

   return safe_commit(
       (jsonify({'message': 'Resource created successfully', 'id': resource.id}), 201),
       'Failed to create resource due to internal database error'
   )
   ```

---

## 6. Audit Trail Logging (`@audit_action`)

- Major state changes (creating companies, updating roles, changing election status, casting votes, publishing results) MUST be annotated with `@audit_action(action_name, module=module_name)`.
- Audit logs capture `company_id`, `user_id`, `module_name`, `action_name`, `ip_address`, `user_agent`, and `timestamp` in IST.

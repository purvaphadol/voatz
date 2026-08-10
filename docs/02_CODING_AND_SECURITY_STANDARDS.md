# Coding & Security Standards

## 1. Core Coding Standards

### **Immutable Module Keys vs. Editable Display Names**
- **Rule**: Permission checks, route guards, and navigation items MUST evaluate immutable module codes (`module.code`), NEVER human-editable display names (`module.display_name`).
- **Backend Guard**: `@require_permission('modules', 'view')`
- **Frontend Guard**: `hasPermission('modules', 'view')`

### **3-Status Entity Lifecycle Standard**
All domain models MUST adhere to the standard 3-status entity lifecycle:

```python
from enum import IntEnum

class StatusEnum(IntEnum):
    INACTIVE = 0  # Temporarily disabled/paused by admin
    ACTIVE = 1    # Fully operational
    DELETED = 9   # Soft-deleted (excluded from active queries, retained for audit)
```

- **UI Toggle**: An `Active <-> Inactive` toggle switch switches status between `1` and `0`.
- **UI Delete**: The Delete button prompts for confirmation and sets status to `9`.

### **Protected System Roles & Permissions**
- Roles with `is_system = True` (e.g. `Company Super Admin`) cannot be edited or deleted by Company Super Admins.
- Backend API endpoints (`PUT /api/roles/<id>`, `DELETE /api/roles/<id>`) return `403 Forbidden` if a non-Platform Admin attempts to modify an `is_system` role.

---

## 2. API Response & Error Handling Standards

### **Standardized ApiResponse Format**
All Flask route handlers MUST return consistent JSON responses using the `ApiResponse` class:

```python
# Success Response (HTTP 200/201)
{
    "success": true,
    "message": "Operation completed successfully",
    "data": { ... }
}

# Error Response (HTTP 400/401/403/404/500)
{
    "success": false,
    "error": "Specific error message explaining the failure",
    "details": { ... }
}
```

### **Frontend Error Handling Rules**
- Catch blocks in React components MUST NOT swallow error details or replace them with generic `"Failed to load"` strings.
- Always extract and display `err.response?.data?.error` to provide actionable feedback to the user.

---

## 3. Database Scoping & OOP Reusability

- All tenant models inherit from `TenantScopedMixin`.
- Standard queries use `Model.query_tenant(current_user)` to ensure tenant isolation and soft-delete filtering in a single line.

```python
# Standard tenant-scoped query
users = User.query_tenant(current_user).all()
```

---

## 4. Security Standards

1. **Rate Limiting**: Login routes (`/api/auth/login`) MUST be protected by rate limiting (max 5 failed attempts per minute per IP).
2. **Password Security**: Passwords hashed using salted PBKDF2/Bcrypt.
3. **Deny-by-Default Authorization**: Access is denied unless an explicit role-permission or user-permission mapping exists.
4. **Audit Logging**: All write actions (Create, Update, Delete, Publish, Tally) MUST record an entry in `audit_logs` with IST timestamp, actor `user_id`, and `company_id`.

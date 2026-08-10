# Database Schema & Models Reference

## 1. Overview & Data Architecture

The Voatz database schema is built using PostgreSQL / SQLAlchemy. It features strict multi-tenant isolation, composite unique constraints, audit trail tracking, and soft-delete capabilities.

---

## 2. Core OOP Model Mixins

All database models inherit common behavior from core mixins defined in `app/models/base.py`:

```python
# app/models/base.py
from app import db
from enum import IntEnum

class StatusEnum(IntEnum):
    INACTIVE = 0
    ACTIVE = 1
    DELETED = 9

class TenantScopedMixin:
    """Base mixin providing company scoping and 3-status lifecycle."""
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.Integer, default=StatusEnum.ACTIVE, nullable=False)

    @classmethod
    def query_tenant(cls, current_user, include_inactive=False):
        """Unified query builder for multi-tenant and status scoping."""
        query = cls.query
        if not getattr(current_user, 'is_platform_admin', False):
            query = query.filter(cls.company_id == current_user.company_id)
            
        if not include_inactive:
            query = query.filter(cls.status == StatusEnum.ACTIVE)
        else:
            query = query.filter(cls.status != StatusEnum.DELETED)
            
        return query
```

---

## 3. Schema Definitions & Table Indexing

### **1. Companies (`companies`)**
* `id` (PK, Integer)
* `name` (String 150, Unique, Not Null)
* `code` (String 50, Unique, Not Null)
* `parent_id` (FK `companies.id`, Optional Parent Company for Hierarchies)
* `status` (Integer, Default 1)

### **2. Modules (`modules`)**
* `id` (PK, Integer)
* `code` (String 50, Unique, Immutable Permission Key)
* `display_name` (String 100, Human-Editable UI Label)
* `route_name` (String 100, Frontend Route Path)
* `status` (Integer, Default 1)

### **3. Company Modules (`company_modules`)**
* `id` (PK, Integer)
* `company_id` (FK `companies.id`, Cascade Delete)
* `module_id` (FK `modules.id`, Cascade Delete)
* **Constraints**: `UNIQUE (company_id, module_id)`

### **4. Roles (`roles`)**
* `id` (PK, Integer)
* `company_id` (FK `companies.id`, Cascade Delete, Nullable for System Roles)
* `department_id` (FK `departments.id`, Nullable for Organization-Level Roles)
* `name` (String 100, Not Null)
* `code` (String 100, Not Null)
* `is_system` (Boolean, Default False, True for Protected Roles like Company Super Admin)
* `status` (Integer, Default 1)
* **Constraints**: `UNIQUE (company_id, code)`

### **5. Role Permissions (`role_permissions`)**
* `id` (PK, Integer)
* `role_id` (FK `roles.id`, Cascade Delete)
* `module_id` (FK `modules.id`, Cascade Delete)
* `action` (String 50, Not Null)
* **Constraints**: `UNIQUE (role_id, module_id, action)`

### **6. User Roles (`user_roles`)**
* `id` (PK, Integer)
* `user_id` (FK `users.id`, Cascade Delete)
* `role_id` (FK `roles.id`, Cascade Delete)
* `company_id` (FK `companies.id`, Cascade Delete)
* **Constraints**: `UNIQUE (user_id, role_id, company_id)`

### **7. Elections (`elections`)**
* `id` (PK, Integer)
* `company_id` (FK `companies.id`, Nullable for Platform Shared Elections)
* `title` (String 200, Not Null)
* `election_code` (String 50, Not Null)
* `start_date` (DateTime IST, Not Null)
* `end_date` (DateTime IST, Not Null)
* `is_cross_company` (Boolean, Default False)
* `status` (Integer, Default 1)
* **Constraints**: `UNIQUE (company_id, election_code)`

### **8. Cross-Company Election Scopes (`election_company_scopes`)**
* `id` (PK, Integer)
* `election_id` (FK `elections.id`, Cascade Delete)
* `company_id` (FK `companies.id`, Cascade Delete)
* `status` (String 20, Default 'ACCEPTED') -- INVITED, ACCEPTED, DECLINED
* **Constraints**: `UNIQUE (election_id, company_id)`

---

## 4. Indexing Strategy for Performance & Safety

```sql
CREATE INDEX idx_user_roles_composite ON user_roles(user_id, company_id);
CREATE INDEX idx_role_perms_composite ON role_permissions(role_id, module_id);
CREATE INDEX idx_company_modules_composite ON company_modules(company_id, module_id);
CREATE INDEX idx_election_scopes_composite ON election_company_scopes(election_id, company_id);
```

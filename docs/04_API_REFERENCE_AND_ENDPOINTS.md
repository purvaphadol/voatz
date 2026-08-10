# API Reference & Endpoints Specification

## 1. Global API Standards

### **Response Envelope (`ApiResponse`)**
All API endpoints return JSON payloads wrapped in the standard `ApiResponse` envelope:

```json
// HTTP 200 / 201 - Success
{
  "success": true,
  "message": "Resource created successfully",
  "data": { ... }
}

// HTTP 400 / 401 / 403 / 404 / 500 - Error
{
  "success": false,
  "error": "Descriptive error message for client toast display",
  "details": { ... }
}
```

### **HTTP Status Codes**
* **`200 OK`**: Request succeeded.
* **`201 Created`**: Resource created successfully.
* **`400 Bad Request`**: Payload validation error.
* **`401 Unauthorized`**: Invalid or missing JWT token.
* **`403 Forbidden`**: Missing required permission or attempting to access an `is_system` protected role.
* **`404 Not Found`**: Resource does not exist or belongs to another tenant (`company_id` mismatch).
* **`500 Internal Server Error`**: Database or unhandled server error (details logged in server log, clean message sent to API client).

---

## 2. Core API Endpoints Reference

### **Authentication & System Admin**
* `POST /api/auth/login` — Login endpoint (protected by rate limiting).
* `GET /api/auth/me` — Returns logged-in user profile, company, and permissions object.
* `POST /api/companies` — Onboard new company (Platform Admin only).

### **Departments & Hierarchy**
* `GET /api/departments` — List departments (`Model.query_tenant()`).
* `POST /api/departments` — Create department.
* `PUT /api/departments/<id>` — Edit department.
* `DELETE /api/departments/<id>` — Soft-delete department (Scenario 1: direct soft-delete; Scenario 2: active dependency force confirm).

### **Roles & Permissions Management**
* `GET /api/roles` — List company roles.
* `POST /api/roles` — Create custom role.
* `PUT /api/roles/<id>` — Update role permissions. *Note: Rejects with 403 if target role has `is_system = True` unless called by Platform Admin.*
* `DELETE /api/roles/<id>` — Soft-delete role (*rejection logic applies for `is_system` roles*).

### **Elections & Voting Engine**
* `GET /api/elections` — List elections for current tenant & cross-company scope mappings.
* `POST /api/elections` — Create election draft.
* `POST /api/elections/<id>/scopes` — Map participating companies for cross-tenant elections (Platform Admin / Host Admin).
* `POST /api/votes/submit` — Submit encrypted vote receipt.
* `GET /api/votes/receipt/<id>` — Fetch vote cryptographic receipt.

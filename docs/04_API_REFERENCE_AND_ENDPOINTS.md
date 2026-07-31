# Complete API Reference & Endpoint Specification

All backend endpoints require JSON payloads and return JSON responses. Protected endpoints require a valid JWT token passed via the `Authorization: Bearer <token>` HTTP header.

---

## 1. Authentication & Menu Endpoints

| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Unified login for Platform Admins, Company Super Admins, and Staff |
| `POST` | `/api/auth/reset-password` | Public / Token | Resets password using OTP or verification token |
| `GET` | `/api/users/me/sidebar` | Authenticated | Retrieves persona-specific dynamic sidebar menu items |
| `GET` | `/api/users/me/permissions` | Authenticated | Returns current user's granted permissions map |

---

## 2. Platform Administration Endpoints (SaaS Level)

| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/companies/` | Platform Admin | List all tenant companies |
| `POST` | `/api/companies/` | Platform Admin | Create a new tenant company |
| `GET` | `/api/companies/<id>` | Platform Admin | Get company details |
| `PUT` | `/api/companies/<id>` | Platform Admin | Update company status/metadata |
| `DELETE` | `/api/companies/<id>` | Platform Admin | Soft-delete company |
| `POST` | `/api/modules/` | Platform Admin | Provision a module for a company |
| `POST` | `/api/module-actions/module/<mod_id>/actions` | Platform Admin | Provision an action for a module |

---

## 3. Tenant Administration Endpoints (Company Level)

### **3.1 Roles & Users**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/roles/` | `Roles.view` | List company roles |
| `POST` | `/api/roles/` | `Roles.create` | Create a role (`is_super_admin` flag optional) |
| `PUT` | `/api/roles/<id>` | `Roles.update` | Update role name/description |
| `DELETE` | `/api/roles/<id>` | `Roles.delete` | Delete role (Super Admin role protected) |
| `GET` | `/api/users/` | `Users.view` | List company users |
| `POST` | `/api/users/` | `Users.create` | Provision a new user account |
| `POST` | `/api/user-roles/user/<id>/roles` | `UserRoles.create` | Assign role to user |

### **3.2 Permission Management**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/permissions/role` | `Permissions.create` | Map role to module/action permission |
| `GET` | `/api/permissions/role/<role_id>` | `Permissions.view` | List permissions for a role |

---

## 4. Election Management Endpoints

| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/elections/` | `Elections.view` | List company elections |
| `POST` | `/api/elections/` | `Elections.create` | Create new election |
| `GET` | `/api/elections/<id>` | `Elections.view` | Get election details & vote stats |
| `PUT` | `/api/elections/<id>` | `Elections.update` | Update election metadata |
| `POST` | `/api/elections/<id>/change-status` | `Elections.update` | Change status (`draft`, `active`, `completed`) |
| `POST` | `/api/elections/<id>/tally` | `Elections.update` | Run automated vote tallying pipeline |
| `POST` | `/api/elections/<id>/publish-results` | `Elections.update` | Publish election results |

---

## 5. Ballots & Candidates Endpoints

### **5.1 Ballots**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/ballots/` | `Ballots.view` | List ballots for election |
| `POST` | `/api/ballots/` | `Ballots.create` | Create a ballot race |
| `PUT` | `/api/ballots/<id>` | `Ballots.update` | Publish/Activate/Update ballot |

### **5.2 Candidates**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/candidates/` | `Candidates.view` | List candidates |
| `POST` | `/api/candidates/` | `Candidates.create` | Add candidate to a ballot |
| `GET` | `/api/candidates/<id>` | `Candidates.view` | Get candidate stats & votes received |

---

## 6. Voters, Registrations & Vote Casting Endpoints

### **6.1 Voters & Registrations**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/voters/` | `Voters.view` | List company voters |
| `POST` | `/api/voters/` | `Voters.create` | Create a voter record |
| `GET` | `/api/voter-registrations/` | `VoterRegistrations.view` | List registrations |
| `POST` | `/api/voter-registrations/` | `VoterRegistrations.create` | Register voter for election |
| `POST` | `/api/voter-registrations/<id>/approve` | `VoterRegistrations.approve` | Approve voter registration |

### **6.2 Votes**
| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/votes/` | `Votes.create` | Cast a vote on a ballot |
| `GET` | `/api/votes/stats` | `Votes.view` | Get overall vote module statistics |

---

## 7. Audit Log Endpoints

| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/audit/` | `AuditLogs.view` | View company audit logs |
| `GET` | `/api/audit/user/<user_id>` | `AuditLogs.view` | View audit logs for a specific user |

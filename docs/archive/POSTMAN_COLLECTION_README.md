# Flask Multi-Tenant Access Control API - Postman Collection

This Postman collection contains all the API endpoints for the Flask Multi-Tenant Access Control System. The system provides comprehensive role-based access control, dynamic menu generation, and audit trail functionality.

## 📋 Collection Overview

The collection includes **45+ API endpoints** organized into 10 main categories:

1. **Authentication** - User login and JWT token management
2. **Health Check** - System health monitoring
3. **Companies** - Company management (multi-tenant support)
4. **Users** - User management with company-scoped operations
5. **Departments** - Department management
6. **Roles** - Role management with pagination
7. **Modules** - Module management
8. **User Roles** - User-role assignment management
9. **Permissions** - Permission management and role-based access
10. **Menu System** - Dynamic menu generation based on permissions
11. **Audit System** - Comprehensive audit trail and reporting

## 🚀 Quick Start

### 1. Import the Collection
- Download `postman_collection.json`
- Open Postman
- Click **Import** → **Upload Files** → Select the collection file
- The collection will be imported with all endpoints and variables

### 2. Set Up Environment Variables
The collection uses the following variables (automatically configured):

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `base_url` | `http://localhost:5000` | Flask API base URL |
| `user_email` | `admin@techcorp.com` | Default login email |
| `user_password` | `admin123` | Default login password |
| `jwt_token` | *(auto-set)* | JWT access token |
| `user_id` | *(auto-set)* | Current user ID |
| `company_id` | *(auto-set)* | Current company ID |

### 3. Start Testing
1. **Login First**: Use the "Authentication → Login" endpoint
2. **JWT Token Auto-Set**: The login response automatically sets your JWT token
3. **Test Other Endpoints**: All other endpoints will use the stored JWT token

## 🔐 Authentication Flow

### Login Process
```http
POST /api/auth/login
Content-Type: application/json

{
    "email": "admin@techcorp.com",
    "password": "admin123"
}
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "name": "Super Admin",
        "email": "admin@techcorp.com",
        "company_id": 1,
        "company_name": "TechCorp"
    }
}
```

The collection automatically extracts and stores:
- `jwt_token` for authentication
- `user_id` for user-specific operations
- `company_id` for multi-tenant operations

## 📁 API Endpoints Detail

### Authentication
- `POST /api/auth/login` - User authentication

### Companies
- `GET /api/companies/` - List all companies
- `POST /api/companies/` - Create new company
- `PUT /api/companies/{id}` - Update company
- `DELETE /api/companies/{id}` - Delete company

### Users (Company-Scoped)
- `GET /api/users/` - List users (with pagination & search)
- `POST /api/users/` - Create user
- `GET /api/users/{id}` - Get specific user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Departments (Company-Scoped)
- `GET /api/departments/` - List departments
- `POST /api/departments/` - Create department
- `GET /api/departments/{id}` - Get specific department
- `PUT /api/departments/{id}` - Update department
- `DELETE /api/departments/{id}` - Delete department

### Roles (Company-Scoped)
- `GET /api/roles/` - List roles (with pagination & search)
- `POST /api/roles/` - Create role
- `GET /api/roles/{id}` - Get specific role
- `PUT /api/roles/{id}` - Update role
- `DELETE /api/roles/{id}` - Delete role

### Modules (Company-Scoped)
- `GET /api/modules/` - List modules
- `POST /api/modules/` - Create module
- `GET /api/modules/{id}` - Get specific module
- `PUT /api/modules/{id}` - Update module
- `DELETE /api/modules/{id}` - Delete module

### User Roles Management
- `GET /api/user-roles/user/{user_id}/roles` - Get user's roles
- `POST /api/user-roles/user/{user_id}/roles` - Assign role to user
- `PUT /api/user-roles/user-role/{mapping_id}` - Update user role
- `DELETE /api/user-roles/user-role/{mapping_id}` - Remove role from user

### Permissions System
- `GET /api/permissions/user/{user_id}` - Get user permissions
- `GET /api/permissions/user/{user_id}/roles` - Get user role mappings
- `GET /api/permissions/modules` - Get modules with actions
- `POST /api/permissions/role` - Assign permission to role
- `POST /api/permissions/user` - Assign permission to user

### Menu System (Dynamic)
- `GET /api/menu/sidebar` - Get dynamic sidebar menu
- `GET /api/menu/permissions` - Get user permissions for frontend
- `GET /api/menu/navigation` - Get navigation items

### Audit System
- `GET /api/audit/logs` - Get audit logs (with filtering)
- `GET /api/audit/summary` - Get audit summary statistics
- `GET /api/audit/user/{user_id}` - Get user-specific audit logs
- `GET /api/audit/export` - Export audit logs as CSV
- `GET /api/audit/stats` - Get detailed audit statistics

## 🔍 Advanced Features

### Pagination Support
Many endpoints support pagination:
```
GET /api/users/?page=1&per_page=10&search=john
```

### Filtering & Search
Audit logs support comprehensive filtering:
```
GET /api/audit/logs?page=1&per_page=50&days=30&user_id=1&action=create&module=Users&success=true
```

### Multi-Tenant Isolation
All operations are automatically scoped to the user's company:
- Users can only see/manage data within their company
- JWT token contains company context
- All CRUD operations respect company boundaries

## 🛡️ Security Features

### JWT Authentication
- All protected endpoints require Bearer token
- Token automatically included via collection-level auth
- Auto-refresh on login

### Permission-Based Access
- Endpoints protected by `@require_permission` decorators
- Role-based and user-specific permissions
- Dynamic menu generation based on permissions

### Company Isolation
- Multi-tenant architecture
- Data isolation by `company_id`
- Company-scoped operations

## 📊 Sample Test Workflow

1. **Login**
   ```http
   POST /api/auth/login
   ```

2. **List Users**
   ```http
   GET /api/users/?page=1&per_page=5
   ```

3. **Create User**
   ```http
   POST /api/users/
   Body: {"name": "John Doe", "email": "john@example.com", "password": "secure123"}
   ```

4. **Assign Role to User**
   ```http
   POST /api/user-roles/user/2/roles
   Body: {"role_id": 1, "department_id": 1, "status": 1}
   ```

5. **Check User Permissions**
   ```http
   GET /api/permissions/user/2
   ```

6. **Get Dynamic Menu**
   ```http
   GET /api/menu/sidebar
   ```

7. **View Audit Logs**
   ```http
   GET /api/audit/logs?days=7
   ```

## 🏗️ System Architecture

### Multi-Tenant Design
- **Company Level**: Top-level tenant isolation
- **User Level**: Users belong to companies
- **Role Level**: Roles scoped to companies
- **Permission Level**: Permissions with role and user overrides

### Permission Hierarchy
1. **Role Permissions**: Base permissions from assigned roles
2. **User Overrides**: User-specific permission overrides
3. **Dynamic Resolution**: Real-time permission calculation

### Audit Trail
- **Comprehensive Logging**: All CRUD operations logged
- **Detailed Context**: User, action, module, success status
- **Filtering & Export**: Advanced filtering and CSV export
- **Statistics**: Usage analytics and failure tracking

## 🔧 Customization

### Environment Setup
Create a Postman environment with your specific values:
- `base_url`: Your Flask server URL
- `user_email`: Your test user email
- `user_password`: Your test user password

### Custom Variables
Add these variables for testing:
- `test_user_id`: ID of a test user
- `test_role_id`: ID of a test role
- `test_department_id`: ID of a test department

## 📈 Response Formats

### Success Response
```json
{
    "data": [...],
    "total": 100,
    "page": 1,
    "pages": 10
}
```

### Error Response
```json
{
    "error": "Email already exists in this company"
}
```

### Audit Log Response
```json
{
    "logs": [
        {
            "id": 1,
            "user": {"id": 1, "name": "Admin", "email": "admin@techcorp.com"},
            "action": "create",
            "module": "Users",
            "description": "Created user: John Doe",
            "success": true,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    ],
    "pagination": {...}
}
```

## 🚨 Important Notes

1. **Login First**: Always authenticate before testing other endpoints
2. **Company Scope**: All operations are company-scoped
3. **Permission Checks**: Some endpoints require specific permissions
4. **Data Isolation**: Users can only access their company's data
5. **JWT Expiry**: Tokens may expire; re-login if needed

## 🆘 Troubleshooting

### Common Issues

**401 Unauthorized**
- Ensure you've logged in first
- Check if JWT token is set correctly
- Token may have expired

**403 Forbidden**
- User doesn't have required permissions
- Check user's role assignments
- Verify permission configurations

**404 Not Found**
- Resource doesn't exist in user's company
- Check company_id context
- Verify resource IDs

**500 Internal Server Error**
- Check Flask server logs
- Verify database connection
- Check for missing migrations

## 🎯 Best Practices

1. **Always Login First**: Start each testing session with login
2. **Use Environment Variables**: Don't hardcode values in requests
3. **Test Permissions**: Verify role-based access controls
4. **Check Company Isolation**: Ensure multi-tenant data separation
5. **Monitor Audit Logs**: Use audit endpoints to track activities
6. **Test Error Cases**: Try invalid inputs to test error handling

---

## 📞 Support

For issues or questions about the API collection:
1. Check the Flask application logs
2. Verify database schema and migrations
3. Test with curl commands first
4. Check permission configurations

This collection provides comprehensive testing coverage for the entire Flask Multi-Tenant Access Control System with enterprise-grade features including role-based permissions, dynamic menus, and comprehensive audit trails. 
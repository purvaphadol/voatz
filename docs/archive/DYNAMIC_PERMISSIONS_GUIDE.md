 # Dynamic Module Actions & Permissions System

## Overview

The Flask Multi-Tenant Access Control System now supports **dynamic module actions** that automatically integrate with the permissions system. When you add custom actions to modules beyond the standard CRUD operations, they immediately become available in the permissions management interface.

## How It Works

### 1. **Dynamic Actions Creation**
- Navigate to **Modules** section in the frontend
- Click **"Manage Actions"** for any module
- Add custom actions with names like `export_data`, `import_users`, `generate_report`, etc.
- Actions are automatically created with proper company context

### 2. **Automatic Permissions Integration**
- Custom actions immediately appear in the **Permissions** section
- The permissions matrix dynamically shows all actions (CRUD + custom)
- Column headers are generated automatically from action names
- Action URLs are displayed for reference

### 3. **Role & User Permissions**
- **Role Permissions**: Grant/revoke access to custom actions for entire roles
- **User Permissions**: Override role permissions for specific users
- All changes are saved in real-time with proper validation

## Key Features

### ✅ **Fully Dynamic**
- No hardcoded action lists
- Actions appear immediately after creation
- Permissions matrix adapts automatically

### ✅ **Multi-Tenant Safe**
- All actions are company-scoped
- Users only see actions for their company's modules
- Complete data isolation

### ✅ **Hierarchical Structure**
- Company → Departments → Roles → Permissions
- Custom actions respect the same hierarchy
- Department-based role filtering

### ✅ **Real-Time Updates**
- Use the **"Refresh Data"** button to reload after adding actions
- Changes reflect immediately in the interface
- No need to restart the application

## Usage Examples

### Example 1: Adding Export Functionality
```
Module: Users
Custom Action: export_users
Action URL: /users/export
```
Result: "Export Users" column appears in permissions matrix

### Example 2: Adding Reporting Features
```
Module: Dashboard
Custom Action: generate_report
Action URL: /dashboard/reports
```
Result: "Generate Report" column appears in permissions matrix

### Example 3: Adding Bulk Operations
```
Module: Companies
Custom Action: bulk_update
Action URL: /companies/bulk
```
Result: "Bulk Update" column appears in permissions matrix

## API Integration

### Backend APIs
- **GET** `/api/module-actions/module/{id}/actions` - Get all actions for a module
- **POST** `/api/module-actions/module/{id}/actions` - Create new action
- **PUT** `/api/module-actions/action/{id}` - Update existing action
- **DELETE** `/api/module-actions/action/{id}` - Delete action (with usage validation)

### Permissions APIs
- **GET** `/api/permissions/module-actions` - Get all modules with actions
- **GET** `/api/permissions/role/{id}` - Get role permissions
- **POST** `/api/permissions/role/{id}` - Update role permissions
- **GET** `/api/permissions/user/{id}` - Get user permissions
- **POST** `/api/permissions/user/{id}` - Update user permissions

## Frontend Components

### Enhanced Permissions Matrix
- **Dynamic columns**: Actions are loaded from API, not hardcoded
- **Action details**: Shows action URLs as tooltips
- **Visual indicators**: Shows number of actions per module
- **Responsive design**: Handles varying numbers of columns

### Module Actions Management
- **Inline editing**: Add/edit/delete actions directly
- **Validation**: Prevents duplicate action names
- **Status management**: Enable/disable actions
- **Bulk operations**: Create multiple actions at once

## Permission Checking in Code

Use the same `hasPermission(module, action)` pattern for custom actions:

```javascript
// Check if user can export users
if (hasPermission('Users', 'export_users')) {
    // Show export button
}

// Check if user can generate reports
if (hasPermission('Dashboard', 'generate_report')) {
    // Show report generation feature
}
```

## Best Practices

### ✅ **Action Naming**
- Use descriptive names: `export_data`, `import_users`, `generate_report`
- Use underscores for multi-word actions
- Keep names consistent across modules

### ✅ **URL Patterns**
- Follow RESTful conventions: `/module/action`
- Use consistent patterns: `/users/export`, `/reports/generate`
- Include module context in URLs

### ✅ **Permission Management**
- Grant permissions at role level first
- Use user-level permissions for exceptions only
- Test permissions thoroughly before deployment

### ✅ **Security**
- Always validate permissions on backend APIs
- Use proper authentication for all endpoints
- Log permission changes for audit trails

## Troubleshooting

### Issue: Custom actions not appearing in permissions
**Solution**: Click the "Refresh Data" button in the permissions interface

### Issue: Permission changes not saving
**Solution**: Ensure user has proper permissions to update role/user permissions

### Issue: Actions showing for wrong company
**Solution**: Verify company context is properly set in user session

## Testing the System

1. **Login** to the application
2. **Navigate** to Modules section
3. **Add** a custom action to any module
4. **Go** to Permissions section
5. **Click** "Refresh Data" button
6. **Select** a department and role
7. **Verify** the custom action appears as a new column
8. **Grant/revoke** permissions and save
9. **Check** that permissions are properly saved

The system is now fully functional with dynamic module actions integrated into the permissions system! 🚀
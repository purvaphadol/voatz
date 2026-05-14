import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Alert,
  Card,
  CardContent,
  Grid,
  Chip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { usePermissions } from '../../contexts/PermissionContext';

const TestModule = () => {
  const { hasPermission, menu } = usePermissions();
  const location = useLocation();

  // Find which module points to this route
  const currentRoute = location.pathname.slice(1); // Remove leading slash
  const moduleInfo = menu.find(item => item.route === currentRoute);
  
  // Use the module name from the access control system, or fallback to 'Test'
  const moduleName = moduleInfo ? moduleInfo.module : 'Test';

  const canView = hasPermission(moduleName, 'view');
  const canCreate = hasPermission(moduleName, 'create');
  const canUpdate = hasPermission(moduleName, 'update');
  const canDelete = hasPermission(moduleName, 'delete');
  const canExport = hasPermission(moduleName, 'export');
  const canImport = hasPermission(moduleName, 'import');

  if (!canView) {
    return (
      <Box p={3}>
        <Alert severity="error">
          You don't have permission to view {moduleName} module.
        </Alert>
        <Typography variant="body2" sx={{ mt: 2 }}>
          Current route: {location.pathname}<br/>
          Detected module: {moduleName}<br/>
          Required permission: {moduleName}.view
        </Typography>
      </Box>
    );
  }

  const permissions = [
    { action: 'View', allowed: canView, description: `Can view ${moduleName} module data` },
    { action: 'Create', allowed: canCreate, description: 'Can create new records' },
    { action: 'Update', allowed: canUpdate, description: 'Can edit existing records' },
    { action: 'Delete', allowed: canDelete, description: 'Can delete records' },
    { action: 'Export', allowed: canExport, description: 'Can export data' },
    { action: 'Import', allowed: canImport, description: 'Can import data' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {moduleName}
      </Typography>

      <Alert severity="success" sx={{ mb: 3 }}>
        <Typography variant="body1">
          🎉 <strong>Success!</strong> {moduleName} module is working with dynamic routing!
        </Typography>
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">
                  Module Information
                </Typography>
              </Box>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                This component automatically detects which access control module points to this route
                and uses the correct permissions.
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                <strong>Module Name:</strong> {moduleName}<br/>
                <strong>Current Route:</strong> {location.pathname}<br/>
                <strong>Detected Route:</strong> {currentRoute}<br/>
                <strong>Component:</strong> TestModule (hardcoded)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Your Permissions
              </Typography>
              
              <Box>
                {permissions.map((perm) => (
                  <Box key={perm.action} display="flex" alignItems="center" mb={1}>
                    <Chip
                      icon={perm.allowed ? <CheckCircleIcon /> : undefined}
                      label={perm.action}
                      color={perm.allowed ? 'success' : 'default'}
                      variant={perm.allowed ? 'filled' : 'outlined'}
                      size="small"
                      sx={{ minWidth: 80, mr: 2 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {perm.description}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Next Steps
              </Typography>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                Now that TestModule is working, you can:
              </Typography>
              
              <ul>
                <li>
                  <Typography variant="body2">
                    <strong>Test Permission Changes:</strong> Go to Permissions → Role Permissions, 
                    remove the 'view' permission from TestModule, and see it disappear from the sidebar.
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>Add More Modules:</strong> Create additional modules in the Modules section 
                    and they will automatically appear here.
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>Create Custom Actions:</strong> Use the "Manage Actions" feature in Modules 
                    to add custom actions beyond the standard CRUD operations.
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>User-Specific Permissions:</strong> Grant specific permissions to individual 
                    users using the User Permissions tab.
                  </Typography>
                </li>
              </ul>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default TestModule; 
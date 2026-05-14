import React from 'react';
import { useParams } from 'react-router-dom';
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

const DynamicModule = () => {
  const { moduleName } = useParams();
  const { hasPermission, menu } = usePermissions();

  // Find the module info from the menu by route
  const moduleInfo = menu.find(item => item.route === moduleName);

  if (!moduleInfo) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Module with route "/{moduleName}" not found or you don't have permission to access it.
        </Alert>
        <Typography variant="body2" sx={{ mt: 2 }}>
          Available routes: {menu.map(m => `/${m.route}`).join(', ')}
        </Typography>
      </Box>
    );
  }

  // Use the actual module name for permission checks (not the route name)
  const actualModuleName = moduleInfo.module;
  
  const canView = hasPermission(actualModuleName, 'view');
  const canCreate = hasPermission(actualModuleName, 'create');
  const canUpdate = hasPermission(actualModuleName, 'update');
  const canDelete = hasPermission(actualModuleName, 'delete');
  const canExport = hasPermission(actualModuleName, 'export');
  const canImport = hasPermission(actualModuleName, 'import');

  if (!canView) {
    return (
      <Box p={3}>
        <Alert severity="error">
          You don't have permission to view {actualModuleName}.
        </Alert>
        <Typography variant="body2" sx={{ mt: 2 }}>
          Module: {actualModuleName}<br/>
          Route: /{moduleInfo.route}<br/>
          Required permission: {actualModuleName}.view
        </Typography>
      </Box>
    );
  }

  const permissions = [
    { action: 'View', allowed: canView, description: `Can view ${actualModuleName} data` },
    { action: 'Create', allowed: canCreate, description: 'Can create new records' },
    { action: 'Update', allowed: canUpdate, description: 'Can edit existing records' },
    { action: 'Delete', allowed: canDelete, description: 'Can delete records' },
    { action: 'Export', allowed: canExport, description: 'Can export data' },
    { action: 'Import', allowed: canImport, description: 'Can import data' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {actualModuleName}
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body1">
          🎯 <strong>Dynamic Module:</strong> This is a dynamically generated page for the "{actualModuleName}" module with custom route "/{moduleInfo.route}".
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
                This module was created dynamically through the access control system. 
                It appears here because you have the proper permissions.
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                <strong>Module Name:</strong> {actualModuleName}<br/>
                <strong>Custom Route:</strong> /{moduleInfo.route}<br/>
                <strong>URL:</strong> {window.location.origin}/{moduleInfo.route}<br/>
                <strong>Total Actions:</strong> {moduleInfo.actions?.length || 0}
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
                Available Actions
              </Typography>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                The following actions are available for this module:
              </Typography>
              
              <Box display="flex" flexWrap="wrap" gap={1}>
                {moduleInfo.actions?.map((action) => (
                  <Chip
                    key={action.name}
                    label={`${action.label} (${action.name})`}
                    color="primary"
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dynamic Routing Success!
              </Typography>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                This demonstrates the power of dynamic routing:
              </Typography>
              
              <ul>
                <li>
                  <Typography variant="body2">
                    <strong>Module Name:</strong> "{actualModuleName}" (used for permissions)
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>Custom Route:</strong> "/{moduleInfo.route}" (user-friendly URL)
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>Permission System:</strong> Uses module name "{actualModuleName}" for access control
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    <strong>Navigation:</strong> Sidebar shows "{actualModuleName}" but links to "/{moduleInfo.route}"
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

export default DynamicModule; 
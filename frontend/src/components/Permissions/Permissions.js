import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Grid,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Business as BusinessIcon,
} from '@mui/icons-material';
import { permissionsAPI, rolesAPI, usersAPI, departmentsAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';

const TabPanel = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`permissions-tabpanel-${index}`}
    aria-labelledby={`permissions-tab-${index}`}
    {...other}
  >
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const Permissions = () => {
  const { hasPermission, refreshPermissions, autoRefreshEnabled, toggleAutoRefresh } = usePermissions();
  const [tabValue, setTabValue] = useState(0);
  const [moduleActions, setModuleActions] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [allRoles, setAllRoles] = useState([]);
  const [filteredRoles, setFilteredRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedUser, setSelectedUser] = useState('');
  const [rolePermissions, setRolePermissions] = useState({});
  const [userPermissions, setUserPermissions] = useState({});
  const [permissionSources, setPermissionSources] = useState({});
  const [userOverrides, setUserOverrides] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Permissions', 'view');
  const canUpdate = hasPermission('Permissions', 'update');

  useEffect(() => {
    if (canView) {
      loadInitialData();
    }
  }, [canView]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [moduleActionsRes, departmentsRes, rolesRes, usersRes] = await Promise.allSettled([
        permissionsAPI.getModuleActions(),
        departmentsAPI.getAll(),
        rolesAPI.getAll(),
        usersAPI.getAll(),
      ]);

      if (moduleActionsRes.status === 'fulfilled') {
        setModuleActions(moduleActionsRes.value.data || []);
      }
      if (departmentsRes.status === 'fulfilled') {
        setDepartments(departmentsRes.value.data.data || []);
      }
      if (rolesRes.status === 'fulfilled') {
        const roles = rolesRes.value.data.data || [];
        setAllRoles(roles);
        setFilteredRoles(roles); // Initially show all roles
      }
      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.data.data || []);
      }
    } catch (error) {
      console.error('Error loading initial data:', error);
      setError('Failed to load permissions data');
    } finally {
      setLoading(false);
    }
  };

  const loadRolePermissions = async (roleId) => {
    try {
      setLoading(true);
      const response = await permissionsAPI.getRolePermissions(roleId);
      setRolePermissions(response.data.permissions || {});
    } catch (error) {
      console.error('Error loading role permissions:', error);
      setError('Failed to load role permissions');
    } finally {
      setLoading(false);
    }
  };

  const loadUserPermissions = async (userId) => {
    try {
      setLoading(true);
      // Use the new management API that shows all actions with their states
      const response = await permissionsAPI.getUserPermissionsForManagement(userId);
      setUserPermissions(response.data.permissions || {});
      
      // Store the sources information for display
      setPermissionSources(response.data.sources || {});
      
      // Reset user overrides when loading new user
      setUserOverrides({});
    } catch (error) {
      console.error('Error loading user permissions:', error);
      setError('Failed to load user permissions');
    } finally {
      setLoading(false);
    }
  };

  const handleDepartmentChange = (departmentId) => {
    setSelectedDepartment(departmentId);
    setSelectedRole(''); // Reset role selection when department changes
    setRolePermissions({}); // Clear role permissions
    
    if (departmentId) {
      // Filter roles by selected department
      const rolesInDepartment = allRoles.filter(role => role.department_id === departmentId);
      setFilteredRoles(rolesInDepartment);
    } else {
      // Show all roles if no department selected
      setFilteredRoles(allRoles);
    }
  };

  const handleRoleChange = (roleId) => {
    setSelectedRole(roleId);
    if (roleId) {
      loadRolePermissions(roleId);
    } else {
      setRolePermissions({});
    }
  };

  const handleUserChange = (userId) => {
    setSelectedUser(userId);
    if (userId) {
      loadUserPermissions(userId);
    } else {
      setUserPermissions({});
      setPermissionSources({});
    }
  };

  const handleRolePermissionChange = (moduleId, actionId, checked) => {
    const moduleKey = String(moduleId);
    const actionKey = String(actionId);
    setRolePermissions(prev => ({
      ...prev,
      [moduleKey]: {
        ...prev[moduleKey],
        [actionKey]: checked
      }
    }));
  };

  const handleUserPermissionChange = (moduleId, actionId, checked) => {
    const moduleKey = String(moduleId);
    const actionKey = String(actionId);
    
    // Get the current effective permission and source
    const currentPermission = userPermissions[moduleKey] && userPermissions[moduleKey][actionKey] === true;
    const currentSource = permissionSources[moduleKey] && permissionSources[moduleKey][actionKey];
    
    // Update the display permissions
    setUserPermissions(prev => ({
      ...prev,
      [moduleKey]: {
        ...prev[moduleKey],
        [actionKey]: checked
      }
    }));
    
    // Track user-specific overrides
    if (currentSource === 'role') {
      // User is changing a role permission - create an override
      if (checked !== true) { // Role permission is true, user wants false -> DENY override
        setUserOverrides(prev => ({
          ...prev,
          [moduleKey]: {
            ...prev[moduleKey],
            [actionKey]: false
          }
        }));
      } else {
        // User wants to keep role permission as-is, remove any existing override
        setUserOverrides(prev => {
          const newOverrides = { ...prev };
          if (newOverrides[moduleKey]) {
            delete newOverrides[moduleKey][actionKey];
            if (Object.keys(newOverrides[moduleKey]).length === 0) {
              delete newOverrides[moduleKey];
            }
          }
          return newOverrides;
        });
      }
    } else if (currentSource === 'user-override') {
      // User is changing an existing override
      if (checked) {
        // User wants to grant permission -> ALLOW override
        setUserOverrides(prev => ({
          ...prev,
          [moduleKey]: {
            ...prev[moduleKey],
            [actionKey]: true
          }
        }));
      } else {
        // User wants to deny permission -> DENY override
        setUserOverrides(prev => ({
          ...prev,
          [moduleKey]: {
            ...prev[moduleKey],
            [actionKey]: false
          }
        }));
      }
    } else if (currentSource === 'none') {
      // User is adding permission where none existed -> ALLOW override
      if (checked) {
        setUserOverrides(prev => ({
          ...prev,
          [moduleKey]: {
            ...prev[moduleKey],
            [actionKey]: true
          }
        }));
      } else {
        // User unchecked a 'none' permission, remove any override
        setUserOverrides(prev => {
          const newOverrides = { ...prev };
          if (newOverrides[moduleKey]) {
            delete newOverrides[moduleKey][actionKey];
            if (Object.keys(newOverrides[moduleKey]).length === 0) {
              delete newOverrides[moduleKey];
            }
          }
          return newOverrides;
        });
      }
    }
  };

  const saveRolePermissions = async () => {
    if (!selectedRole) return;

    try {
      setLoading(true);
      await permissionsAPI.updateRolePermissions(selectedRole, rolePermissions);
      setSuccess('Role permissions updated successfully');
      
      // Refresh permissions context to update sidebar and permission checks
      await refreshPermissions();
    } catch (error) {
      setError('Failed to update role permissions');
    } finally {
      setLoading(false);
    }
  };

  const saveUserPermissions = async () => {
    if (!selectedUser) return;

    try {
      setLoading(true);
      // Send only the user-specific overrides, not the complete permissions
      await permissionsAPI.updateUserPermissions(selectedUser, userOverrides);
      setSuccess('User permissions updated successfully');
      
      // Reload user permissions to get the updated state
      await loadUserPermissions(selectedUser);
      
      // Refresh permissions context to update sidebar and permission checks
      await refreshPermissions();
    } catch (error) {
      setError('Failed to update user permissions');
    } finally {
      setLoading(false);
    }
  };

  const getPermissionStatus = (permissions, moduleId, actionId) => {
    // Convert IDs to strings since API returns string keys
    const moduleKey = String(moduleId);
    const actionKey = String(actionId);
    const hasPermission = permissions[moduleKey] && permissions[moduleKey][actionKey] === true;
    return hasPermission;
  };

  const PermissionMatrix = ({ permissions, onPermissionChange, type, sources }) => {
    // Get all unique actions across all modules for table headers
    const allActions = [...new Set(
      moduleActions.flatMap(module => 
        module.actions ? module.actions.map(action => action.action_name) : []
      )
    )].sort();

    const getPermissionSource = (moduleId, actionId) => {
      if (!sources) return null;
      const moduleKey = String(moduleId);
      const actionKey = String(actionId);
      return sources[moduleKey] && sources[moduleKey][actionKey] ? sources[moduleKey][actionKey] : null;
    };

    const getSourceColor = (source) => {
      switch (source) {
        case 'role': return 'primary';
        case 'user-override': return 'secondary';
        case 'none': return 'default';
        default: return 'default';
      }
    };

    const getSourceLabel = (source) => {
      switch (source) {
        case 'role': return 'Role';
        case 'user-override': return 'User';
        case 'none': return 'None';
        default: return 'Unknown';
      }
    };

    return (
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Module</strong></TableCell>
              {allActions.map((actionName) => (
                <TableCell key={actionName} align="center">
                  <strong style={{ textTransform: 'capitalize' }}>
                    {actionName.replace(/_/g, ' ')}
                  </strong>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {moduleActions.map((module) => (
              <TableRow key={module.id}>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <SecurityIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {module.module_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {module.actions ? module.actions.length : 0} actions available
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                {allActions.map((actionName) => {
                  const moduleAction = module.actions && module.actions.find(a => a.action_name === actionName);
                  if (!moduleAction) {
                    return (
                      <TableCell key={actionName} align="center">
                        <Chip label="N/A" size="small" variant="outlined" />
                      </TableCell>
                    );
                  }

                  const hasPermission = getPermissionStatus(permissions, module.id, moduleAction.id);
                  const source = getPermissionSource(module.id, moduleAction.id);
                  const isUserOverride = source === 'user-override';
                  const isFromRole = source === 'role';

                  return (
                    <TableCell key={actionName} align="center">
                      <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                        <Checkbox
                          checked={hasPermission}
                          onChange={(e) => onPermissionChange(module.id, moduleAction.id, e.target.checked)}
                          disabled={!canUpdate}
                          color={isUserOverride ? "secondary" : "primary"}
                        />
                        
                        {/* Show permission source */}
                        {source && type === 'user' && (
                          <Chip 
                            label={getSourceLabel(source)} 
                            size="small" 
                            variant={isUserOverride ? "filled" : "outlined"}
                            color={getSourceColor(source)}
                            sx={{ fontSize: '0.7rem', height: '20px' }}
                          />
                        )}
                        
                        {/* Show action URL */}
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                          {moduleAction.action_url || 'N/A'}
                        </Typography>
                        
                        {/* Show explanation for user permissions */}
                        {type === 'user' && isFromRole && (
                          <Typography variant="caption" color="primary.main" sx={{ fontSize: '0.6rem', fontStyle: 'italic' }}>
                            From role
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  if (!canView) {
    return (
      <Box p={3}>
        <Alert severity="error">
          You don't have permission to view permissions.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">
          Permissions Management
        </Typography>
        
        <Box display="flex" gap={1} alignItems="center">
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadInitialData}
            disabled={loading}
          >
            Refresh Data
          </Button>
          
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<SecurityIcon />}
            onClick={refreshPermissions}
            disabled={loading}
          >
            Refresh Permissions
          </Button>

          <FormControlLabel
            control={
              <Switch
                checked={autoRefreshEnabled}
                onChange={toggleAutoRefresh}
                color="primary"
              />
            }
            label="Auto-refresh (2min)"
            sx={{ ml: 2 }}
          />
        </Box>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2">
          <strong>Dynamic Actions:</strong> Custom actions added to modules will automatically appear here. 
          Use the refresh button above to reload if you've just added new actions.
        </Typography>
      </Alert>

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab icon={<GroupIcon />} label="Role Permissions" />
          <Tab icon={<PersonIcon />} label="User Permissions" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Select Department & Role
                  </Typography>
                  
                  {/* Department Selection */}
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Department</InputLabel>
                    <Select
                      value={selectedDepartment}
                      onChange={(e) => handleDepartmentChange(e.target.value)}
                      label="Department"
                    >
                      <MenuItem value="">
                        <em>All Departments</em>
                      </MenuItem>
                      {departments.map((dept) => (
                        <MenuItem key={dept.id} value={dept.id}>
                          {dept.department_name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  {/* Role Selection */}
                  <FormControl fullWidth>
                    <InputLabel>Role</InputLabel>
                    <Select
                      value={selectedRole}
                      onChange={(e) => handleRoleChange(e.target.value)}
                      label="Role"
                      disabled={!selectedDepartment}
                    >
                      <MenuItem value="">
                        <em>Select a role</em>
                      </MenuItem>
                      {filteredRoles.map((role) => (
                        <MenuItem key={role.id} value={role.id}>
                          <Box display="flex" alignItems="center">
                            <GroupIcon sx={{ mr: 1, fontSize: 'small' }} />
                            {role.role_name}
                            <Chip 
                              label={role.department_name} 
                              size="small" 
                              variant="outlined" 
                              sx={{ ml: 1 }} 
                            />
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  {!selectedDepartment && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                      Please select a department first to see available roles.
                    </Alert>
                  )}
                  
                  {selectedRole && (
                    <Box sx={{ mt: 2 }}>
                      <Button
                        variant="contained"
                        startIcon={<SaveIcon />}
                        onClick={saveRolePermissions}
                        disabled={!canUpdate || loading}
                        fullWidth
                      >
                        Save Permissions
                      </Button>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={8}>
              {selectedRole ? (
                <Box>
                  {/* Role Information Header */}
                  <Paper sx={{ p: 2, mb: 2, backgroundColor: 'primary.light', color: 'primary.contrastText' }}>
                    <Typography variant="h6" gutterBottom>
                      Managing Permissions for:
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Chip 
                        icon={<SecurityIcon />}
                        label={`Department: ${departments.find(d => d.id === selectedDepartment)?.department_name || 'N/A'}`}
                        variant="filled"
                        color="secondary"
                      />
                      <Chip 
                        icon={<GroupIcon />}
                        label={`Role: ${filteredRoles.find(r => r.id === selectedRole)?.role_name || 'N/A'}`}
                        variant="filled"
                        color="secondary"
                      />
                    </Box>
                  </Paper>
                  
                  <PermissionMatrix
                    permissions={rolePermissions}
                    onPermissionChange={handleRolePermissionChange}
                    type="role"
                    sources={null}
                  />
                </Box>
              ) : (
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    {!selectedDepartment 
                      ? 'Select a department first, then choose a role to manage its permissions'
                      : 'Select a role to manage its permissions'
                    }
                  </Typography>
                </Paper>
              )}
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Select User
                  </Typography>
                  <FormControl fullWidth>
                    <InputLabel>User</InputLabel>
                    <Select
                      value={selectedUser}
                      onChange={(e) => handleUserChange(e.target.value)}
                      label="User"
                    >
                      <MenuItem value="">
                        <em>Select a user</em>
                      </MenuItem>
                      {users.map((user) => (
                        <MenuItem key={user.id} value={user.id}>
                          <Box display="flex" alignItems="center">
                            <PersonIcon sx={{ mr: 1, fontSize: 'small' }} />
                            {user.name}
                            <Chip 
                              label={user.email} 
                              size="small" 
                              variant="outlined" 
                              sx={{ ml: 1 }} 
                            />
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  {selectedUser && (
                    <Box sx={{ mt: 2 }}>
                      <Alert severity="info" sx={{ mb: 2 }}>
                        <Typography variant="body2">
                          <strong>User Permission Management:</strong><br/>
                          • <strong>Role</strong> permissions are inherited from the user's assigned roles<br/>
                          • <strong>User</strong> permissions are direct overrides for this specific user<br/>
                          • Checking a box creates a user-specific permission override<br/>
                          • Unchecking removes the user-specific override (reverts to role-based)
                        </Typography>
                      </Alert>
                      
                      <Button
                        variant="contained"
                        startIcon={<SaveIcon />}
                        onClick={saveUserPermissions}
                        disabled={!canUpdate || loading}
                        fullWidth
                      >
                        Save User Permissions
                      </Button>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={8}>
              {selectedUser ? (
                <Box>
                  {/* User Information Header */}
                  <Paper sx={{ p: 2, mb: 2, backgroundColor: 'secondary.light', color: 'secondary.contrastText' }}>
                    <Typography variant="h6" gutterBottom>
                      Managing User-Specific Permissions for:
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Chip 
                        icon={<PersonIcon />}
                        label={`User: ${users.find(u => u.id === selectedUser)?.name || 'N/A'}`}
                        variant="filled"
                        color="primary"
                      />
                      <Chip 
                        icon={<BusinessIcon />}
                        label={`Email: ${users.find(u => u.id === selectedUser)?.email || 'N/A'}`}
                        variant="filled"
                        color="primary"
                      />
                    </Box>
                  </Paper>
                  
                  {/* Show pending user overrides */}
                  {Object.keys(userOverrides).length > 0 && (
                    <Paper sx={{ p: 2, mb: 2, backgroundColor: 'warning.light' }}>
                      <Typography variant="h6" gutterBottom>
                        Pending User Overrides ({Object.keys(userOverrides).reduce((count, moduleId) => count + Object.keys(userOverrides[moduleId]).length, 0)})
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        These changes will be applied when you click "Save User Permissions":
                      </Typography>
                      {Object.entries(userOverrides).map(([moduleId, actions]) =>
                        Object.entries(actions).map(([actionId, granted]) => {
                          const module = moduleActions.find(m => m.id === parseInt(moduleId));
                          const action = module?.actions?.find(a => a.id === parseInt(actionId));
                          return (
                            <Chip
                              key={`${moduleId}-${actionId}`}
                              label={`${module?.module_name || `Module ${moduleId}`} → ${action?.action_name || `Action ${actionId}`}: ${granted ? 'ALLOW' : 'DENY'}`}
                              color={granted ? 'success' : 'error'}
                              size="small"
                              sx={{ mr: 1, mb: 1 }}
                            />
                          );
                        })
                      )}
                    </Paper>
                  )}
                  
                  <PermissionMatrix
                    permissions={userPermissions}
                    onPermissionChange={handleUserPermissionChange}
                    type="user"
                    sources={permissionSources}
                  />
                </Box>
              ) : (
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    Select a user to manage their specific permissions
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    User-specific permissions override role-based permissions
                  </Typography>
                </Paper>
              )}
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default Permissions; 
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
  TextField,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Business as BusinessIcon,
} from '@mui/icons-material';
import { permissionsAPI, rolesAPI, usersAPI, departmentsAPI, companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';

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
  const { user: currentUser } = useAuth();
  const { hasPermission, refreshPermissions, autoRefreshEnabled, toggleAutoRefresh } = usePermissions();
  const [tabValue, setTabValue] = useState(0);
  const [moduleActions, setModuleActions] = useState([]);
  
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);

  // Selection states
  const [selectedCompany, setSelectedCompany] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedUser, setSelectedUser] = useState('');

  // Scoped lists
  const [filteredDepartments, setFilteredDepartments] = useState([]);
  const [filteredRoles, setFilteredRoles] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);

  const [rolePermissions, setRolePermissions] = useState({});
  const [userPermissions, setUserPermissions] = useState({});
  const [permissionSources, setPermissionSources] = useState({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isPlatformAdmin = currentUser?.is_administrator;
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
      const initialCompanyId = !isPlatformAdmin && currentUser?.company_id ? currentUser.company_id : '';
      if (initialCompanyId) {
        setSelectedCompany(initialCompanyId);
      }

      const promises = [
        permissionsAPI.getModuleActions(),
        departmentsAPI.getAll(),
        rolesAPI.getAll(),
        usersAPI.getAll(),
      ];

      if (isPlatformAdmin) {
        promises.push(companiesAPI.getAll());
      }

      const results = await Promise.allSettled(promises);

      if (results[0].status === 'fulfilled') setModuleActions(results[0].value.data || []);
      
      const allDepts = results[1].status === 'fulfilled' ? (results[1].value.data.data || []) : [];
      const allRolesList = results[2].status === 'fulfilled' ? (results[2].value.data.data || []) : [];
      const allUsersList = results[3].status === 'fulfilled' ? (results[3].value.data.data || []) : [];

      setDepartments(allDepts);
      setRoles(allRolesList);
      setUsers(allUsersList);

      if (isPlatformAdmin && results[4]?.status === 'fulfilled') {
        setCompanies(results[4].value.data.data || []);
      }

      // Initial scoping if company is set
      const compTarget = initialCompanyId || '';
      if (compTarget) {
        setFilteredDepartments(allDepts.filter(d => d.company_id === Number(compTarget)));
        setFilteredUsers(allUsersList.filter(u => u.company_id === Number(compTarget)));
        setFilteredRoles(allRolesList.filter(r => r.company_id === Number(compTarget)));
      } else {
        setFilteredDepartments(allDepts);
        setFilteredUsers(allUsersList);
        setFilteredRoles(allRolesList);
      }
    } catch (error) {
      console.error('Error loading initial data:', error);
      setError('Failed to load permissions data');
    } finally {
      setLoading(false);
    }
  };

  const handleCompanyChange = (companyId) => {
    setSelectedCompany(companyId);
    setSelectedDepartment('');
    setSelectedRole('');
    setSelectedUser('');
    setRolePermissions({});
    setUserPermissions({});

    if (!companyId) {
      setFilteredDepartments(departments);
      setFilteredRoles([]);
      setFilteredUsers(users);
      return;
    }

    const cIdNum = Number(companyId);
    const matchedDepts = departments.filter(d => d.company_id === cIdNum);
    const matchedUsers = users.filter(u => u.company_id === cIdNum);
    const matchedRoles = roles.filter(r => r.company_id === cIdNum);

    setFilteredDepartments(matchedDepts);
    setFilteredUsers(matchedUsers);
    setFilteredRoles(matchedRoles);
  };

  const handleDepartmentChange = (departmentId) => {
    setSelectedDepartment(departmentId);
    setSelectedRole('');
    setRolePermissions({});
    
    const cIdNum = Number(selectedCompany || currentUser?.company_id);
    if (departmentId) {
      const dIdNum = Number(departmentId);
      const rolesInDepartment = roles.filter(role => 
        (cIdNum ? role.company_id === cIdNum : true) && role.department_id === dIdNum
      );
      setFilteredRoles(rolesInDepartment);
    } else {
      const companyRoles = roles.filter(role => 
        cIdNum ? role.company_id === cIdNum : true
      );
      setFilteredRoles(companyRoles);
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
      const response = await permissionsAPI.getUserPermissionsForManagement(userId);
      setUserPermissions(response.data.permissions || {});
      setPermissionSources(response.data.sources || {});
    } catch (error) {
      console.error('Error loading user permissions:', error);
      setError('Failed to load user permissions');
    } finally {
      setLoading(false);
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
    setUserPermissions(prev => ({
      ...prev,
      [moduleKey]: {
        ...prev[moduleKey],
        [actionKey]: checked
      }
    }));
  };

  const saveRolePermissions = async () => {
    if (!selectedRole) return;

    try {
      setLoading(true);
      await permissionsAPI.updateRolePermissions(selectedRole, rolePermissions);
      setSuccess('Role permissions updated successfully');
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
      await permissionsAPI.updateUserPermissions(selectedUser, userPermissions);
      setSuccess('User permissions updated successfully');
      await loadUserPermissions(selectedUser);
      await refreshPermissions();
    } catch (error) {
      setError('Failed to update user permissions');
    } finally {
      setLoading(false);
    }
  };

  const getPermissionStatus = (permissions, moduleId, actionId) => {
    const moduleKey = String(moduleId);
    const actionKey = String(actionId);
    return permissions[moduleKey] && permissions[moduleKey][actionKey] === true;
  };

  const PermissionMatrix = ({ permissions, onPermissionChange, type, sources }) => {
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
        default: return 'default';
      }
    };

    const getSourceLabel = (source) => {
      switch (source) {
        case 'role': return 'Role';
        case 'user-override': return 'User';
        default: return 'None';
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
                        
                        {source && type === 'user' && (
                          <Chip 
                            label={getSourceLabel(source)} 
                            size="small" 
                            variant={isUserOverride ? "filled" : "outlined"}
                            color={getSourceColor(source)}
                            sx={{ fontSize: '0.7rem', height: '20px' }}
                          />
                        )}
                        
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                          {moduleAction.action_url || 'N/A'}
                        </Typography>
                        
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

        {/* Tab 1: Role Permissions */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Select Company, Department & Role
                  </Typography>
                  
                  {/* 1. Company Selection FIRST */}
                  {isPlatformAdmin ? (
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>Company</InputLabel>
                      <Select
                        value={selectedCompany}
                        onChange={(e) => handleCompanyChange(e.target.value)}
                        label="Company"
                      >
                        <MenuItem value="">
                          <em>Select Company</em>
                        </MenuItem>
                        {companies.map((c) => (
                          <MenuItem key={c.id} value={c.id}>
                            {c.company_name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : (
                    <TextField
                      fullWidth
                      label="Company"
                      value={currentUser?.company_name || 'Your Company'}
                      disabled
                      sx={{ mb: 2 }}
                    />
                  )}

                  {/* 2. Department Selection SECOND (Optional filter) */}
                  <FormControl fullWidth sx={{ mb: 2 }} disabled={!selectedCompany}>
                    <InputLabel>Department (Optional Filter)</InputLabel>
                    <Select
                      value={selectedDepartment}
                      onChange={(e) => handleDepartmentChange(e.target.value)}
                      label="Department (Optional Filter)"
                    >
                      <MenuItem value="">
                        <em>{selectedCompany ? 'All Departments (Show All Roles)' : 'Select Company First'}</em>
                      </MenuItem>
                      {filteredDepartments.map((dept) => (
                        <MenuItem key={dept.id} value={dept.id}>
                          {dept.department_name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  {/* 3. Role Selection THIRD */}
                  <FormControl fullWidth disabled={!selectedCompany}>
                    <InputLabel>Role</InputLabel>
                    <Select
                      value={selectedRole}
                      onChange={(e) => handleRoleChange(e.target.value)}
                      label="Role"
                    >
                      <MenuItem value="">
                        <em>{selectedCompany ? 'Select Role' : 'Select Company First'}</em>
                      </MenuItem>
                      {filteredRoles.map((role) => (
                        <MenuItem key={role.id} value={role.id}>
                          <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
                            <Box display="flex" alignItems="center">
                              <GroupIcon sx={{ mr: 1, fontSize: 'small' }} />
                              {role.role_name}
                            </Box>
                            <Chip 
                              label={role.department_name || (role.department_id ? (departments.find(d => d.id === role.department_id)?.department_name || 'N/A') : 'Company-Wide')} 
                              size="small" 
                              variant="outlined" 
                              color={role.department_name || role.department_id ? "default" : "secondary"}
                              sx={{ ml: 1 }} 
                            />
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  {!selectedCompany && isPlatformAdmin && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                      Please select a company first to see available roles and departments.
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
                  <Paper sx={{ p: 2, mb: 2, backgroundColor: 'primary.light', color: 'primary.contrastText' }}>
                    <Typography variant="h6" gutterBottom>
                      Managing Permissions for:
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Chip 
                        icon={<BusinessIcon />}
                        label={`Company: ${companies.find(c => c.id === Number(selectedCompany))?.company_name || currentUser?.company_name || 'N/A'}`}
                        variant="filled"
                        color="secondary"
                      />
                      <Chip 
                        icon={<SecurityIcon />}
                        label={`Department: ${filteredRoles.find(r => r.id === Number(selectedRole))?.department_name || (filteredRoles.find(r => r.id === Number(selectedRole))?.department_id ? (departments.find(d => d.id === filteredRoles.find(r => r.id === Number(selectedRole))?.department_id)?.department_name || 'N/A') : 'Company-Wide')}`}
                        variant="filled"
                        color="secondary"
                      />
                      <Chip 
                        icon={<GroupIcon />}
                        label={`Role: ${filteredRoles.find(r => r.id === Number(selectedRole))?.role_name || 'N/A'}`}
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
                    {!selectedCompany && isPlatformAdmin
                      ? 'Select a company first to proceed'
                      : 'Select a role to manage its permissions'}
                  </Typography>
                </Paper>
              )}
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 2: User Permissions */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Select Company & User
                  </Typography>

                  {/* 1. Company Selection FIRST */}
                  {isPlatformAdmin ? (
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>Company</InputLabel>
                      <Select
                        value={selectedCompany}
                        onChange={(e) => handleCompanyChange(e.target.value)}
                        label="Company"
                      >
                        <MenuItem value="">
                          <em>Select Company</em>
                        </MenuItem>
                        {companies.map((c) => (
                          <MenuItem key={c.id} value={c.id}>
                            {c.company_name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : (
                    <TextField
                      fullWidth
                      label="Company"
                      value={currentUser?.company_name || 'Your Company'}
                      disabled
                      sx={{ mb: 2 }}
                    />
                  )}

                  {/* 2. User Selection SECOND */}
                  <FormControl fullWidth disabled={!selectedCompany}>
                    <InputLabel>User</InputLabel>
                    <Select
                      value={selectedUser}
                      onChange={(e) => handleUserChange(e.target.value)}
                      label="User"
                    >
                      <MenuItem value="">
                        <em>{selectedCompany ? 'Select User' : 'Select Company First'}</em>
                      </MenuItem>
                      {filteredUsers.map((u) => (
                        <MenuItem key={u.id} value={u.id}>
                          <Box display="flex" alignItems="center">
                            <PersonIcon sx={{ mr: 1, fontSize: 'small' }} />
                            {u.name}
                            <Chip 
                              label={u.email} 
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
                          • Checking a box creates a user-specific permission override
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
                  <Paper sx={{ p: 2, mb: 2, backgroundColor: 'secondary.light', color: 'secondary.contrastText' }}>
                    <Typography variant="h6" gutterBottom>
                      Managing User-Specific Permissions for:
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Chip 
                        icon={<PersonIcon />}
                        label={`User: ${users.find(u => u.id === Number(selectedUser))?.name || 'N/A'}`}
                        variant="filled"
                        color="primary"
                      />
                      <Chip 
                        icon={<BusinessIcon />}
                        label={`Email: ${users.find(u => u.id === Number(selectedUser))?.email || 'N/A'}`}
                        variant="filled"
                        color="primary"
                      />
                    </Box>
                  </Paper>
                  
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
                    {!selectedCompany && isPlatformAdmin
                      ? 'Select a company first to see users'
                      : 'Select a user to manage their specific permissions'}
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
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material';
import {
  DataGrid,
  GridActionsCellItem,
  GridToolbarContainer,
  GridToolbarExport,
  GridToolbarFilterButton,
  GridToolbarColumnsButton,
} from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Person as PersonIcon,
  Security as SecurityIcon,
  Business as BusinessIcon,
  Assignment as AssignmentIcon,
} from '@mui/icons-material';
import { userRolesAPI, usersAPI, rolesAPI, departmentsAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Assign Role
      </Button>
    )}
  </GridToolbarContainer>
);

const UserRoles = () => {
  const { hasPermission, refreshPermissions } = usePermissions();
  const [userRoles, setUserRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState('');
  const [userRolesList, setUserRolesList] = useState([]);
  const [formData, setFormData] = useState({
    user_id: '',
    role_id: '',
    department_id: '',
  });
  const [filteredRoles, setFilteredRoles] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const canView = hasPermission('UserRoles', 'view');
  const canCreate = hasPermission('UserRoles', 'create');
  const canDelete = hasPermission('UserRoles', 'delete');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    loadData();
  }, [debouncedSearch, filterDepartment]);

  const loadData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (filterDepartment) params.department_id = filterDepartment;

      const [userRolesRes, usersRes, rolesRes, departmentsRes] = await Promise.allSettled([
        userRolesAPI.getAll(params),
        usersAPI.getAll(),
        rolesAPI.getAll(),
        departmentsAPI.getAll(),
      ]);

      if (userRolesRes.status === 'fulfilled') {
        setUserRoles(userRolesRes.value.data.data || []);
      }
      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.data.data || []);
      }
      if (rolesRes.status === 'fulfilled') {
        setRoles(rolesRes.value.data.data || []);
      }
      if (departmentsRes.status === 'fulfilled') {
        setDepartments(departmentsRes.value.data.data || []);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      setError('Failed to load user roles data');
    } finally {
      setLoading(false);
    }
  };

  const loadUserRoles = async (userId) => {
    try {
      const response = await userRolesAPI.getUserRoles(userId);
      setUserRolesList(response.data || []);
    } catch (error) {
      console.error('Error loading user roles:', error);
      setUserRolesList([]);
    }
  };

  const loadRolesByDepartment = async (departmentId) => {
    try {
      if (!departmentId) {
        setFilteredRoles([]);
        return;
      }
      const response = await rolesAPI.getAll({ department_id: departmentId });
      setFilteredRoles(response.data.data || []);
    } catch (error) {
      console.error('Error loading roles by department:', error);
      setFilteredRoles([]);
    }
  };

  const handleAdd = () => {
    setFormData({
      user_id: '',
      role_id: '',
      department_id: '',
    });
    setFilteredRoles([]);
    setDialogOpen(true);
  };

  const handleUserSelect = (userId) => {
    setSelectedUser(userId);
    if (userId) {
      loadUserRoles(userId);
    } else {
      setUserRolesList([]);
    }
  };

  const handleDepartmentChange = (departmentId) => {
    setFormData({ 
      ...formData, 
      department_id: departmentId,
      role_id: '' // Clear role selection when department changes
    });
    loadRolesByDepartment(departmentId);
  };

  const handleAssignRole = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.user_id || !formData.role_id) {
      setError('User and Role are required');
      return;
    }

    try {
      await userRolesAPI.assign(formData);
      setSuccess('Role assigned successfully');
      setDialogOpen(false);
      loadData();
      if (selectedUser) {
        loadUserRoles(selectedUser);
      }
      
      // Refresh permissions since role assignments affect user permissions
      await refreshPermissions();
    } catch (error) {
      setError((error.response && error.response.data && error.response.data.error) || 'Failed to assign role');
    }
  };

  const handleUnassignRole = async (mappingId) => {
    if (window.confirm('Are you sure you want to unassign this role?')) {
      try {
        await userRolesAPI.unassign(mappingId);
        setSuccess('Role unassigned successfully');
        loadData();
        if (selectedUser) {
          loadUserRoles(selectedUser);
        }
        
        // Refresh permissions since role unassignments affect user permissions
        await refreshPermissions();
      } catch (error) {
        setError(
          (error.response && error.response.data && error.response.data.error)
          || 'Failed to unassign role'
        );
      }
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setError('');
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.name : 'Unknown';
  };

  const getRoleName = (roleId) => {
    const role = roles.find(r => r.id === roleId);
    return role ? role.role_name : 'Unknown';
  };

  const getDepartmentName = (departmentId) => {
    const department = departments.find(d => d.id === departmentId);
    return department ? department.department_name : 'N/A';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'user_id',
      headerName: 'User',
      width: 200,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          <PersonIcon sx={{ mr: 1, color: 'primary.main' }} />
          {getUserName(params.value)}
        </Box>
      ),
    },
    {
      field: 'role_id',
      headerName: 'Role',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={getRoleName(params.value)}
          size="small"
          variant="outlined"
          icon={<SecurityIcon />}
        />
      ),
    },
    {
      field: 'department_id',
      headerName: 'Department',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={params.row.department_name || getDepartmentName(params.value)}
          size="small"
          variant="outlined"
          icon={<BusinessIcon />}
        />
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value === 1 ? 'Active' : 'Inactive'}
          color={params.value === 1 ? 'success' : 'error'}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => {
        const actions = [];
        
        if (canDelete) {
          actions.push(
            <GridActionsCellItem
              icon={<DeleteIcon />}
              label="Unassign"
              onClick={() => handleUnassignRole(params.row.id)}
            />
          );
        }
        
        return actions;
      },
    },
  ];



  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        User Roles Management
      </Typography>
      
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

      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          label="Search by name"
          placeholder="Search by user name..."
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Filter by Department</InputLabel>
          <Select
            value={filterDepartment}
            label="Filter by Department"
            onChange={(e) => setFilterDepartment(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            {departments.map(d => (
              <MenuItem key={d.id} value={d.id}>{d.department_name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ height: 600, width: '100%' }}>
            <DataGrid
              rows={userRoles}
              columns={columns}
              loading={loading}
              pageSize={10}
              rowsPerPageOptions={[5, 10, 25]}
              disableSelectionOnClick
              components={{
                Toolbar: () => <CustomToolbar onAdd={handleAdd} hasCreatePermission={canCreate} />
              }}
            />
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                User Role Details
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Select User</InputLabel>
                <Select
                  value={selectedUser}
                  onChange={(e) => handleUserSelect(e.target.value)}
                  label="Select User"
                >
                  <MenuItem value="">
                    <em>Select a user</em>
                  </MenuItem>
                  {users.map((user) => (
                    <MenuItem key={user.id} value={user.id}>
                      {user.name} ({user.email})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {selectedUser && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Assigned Roles:
                  </Typography>
                  {userRolesList.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No roles assigned
                    </Typography>
                  ) : (
                    <List dense>
                      {userRolesList.map((roleAssignment, index) => (
                        <ListItem key={index}>
                          <ListItemText
                            primary={
                              <Box display="flex" alignItems="center">
                                <SecurityIcon sx={{ mr: 1, fontSize: 16 }} />
                                {roleAssignment.role_name}
                              </Box>
                            }
                            secondary={`Dept: ${roleAssignment.department_name || 'N/A'}`}
                          />
                          {canDelete && (
                            <ListItemSecondaryAction>
                              <IconButton
                                edge="end"
                                size="small"
                                onClick={() => handleUnassignRole(roleAssignment.id)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </ListItemSecondaryAction>
                          )}
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Paper>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <AssignmentIcon sx={{ mr: 1 }} />
            Assign Role to User
          </Box>
        </DialogTitle>
        <form onSubmit={handleAssignRole}>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>User</InputLabel>
              <Select
                value={formData.user_id}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                label="User"
                required
              >
                <MenuItem value="">
                  <em>Select User</em>
                </MenuItem>
                {users.map((user) => (
                  <MenuItem key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Department</InputLabel>
              <Select
                value={formData.department_id}
                onChange={(e) => handleDepartmentChange(e.target.value)}
                label="Department"
                required
              >
                <MenuItem value="">
                  <em>Select Department</em>
                </MenuItem>
                {departments.map((department) => (
                  <MenuItem key={department.id} value={department.id}>
                    {department.department_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={formData.role_id}
                onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
                label="Role"
                required
                disabled={!formData.department_id}
              >
                <MenuItem value="">
                  <em>{formData.department_id ? 'Select Role' : 'Select Department First'}</em>
                </MenuItem>
                {filteredRoles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.role_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancel</Button>
            <Button type="submit" variant="contained">
              Assign Role
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default UserRoles; 
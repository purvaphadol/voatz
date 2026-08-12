import React, { useState, useEffect, useRef } from 'react';
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
import { userRolesAPI, usersAPI, rolesAPI, departmentsAPI, companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';
import { showConfirmDialog } from '../../utils/swal';
import { capitalizeError } from '../../utils/validators';
import SearchableSelect from '../Common/SearchableSelect';

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
  const { user: currentUser } = useAuth();
  const { hasPermission, refreshPermissions } = usePermissions();
  const [userRoles, setUserRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState('');
  const [userRolesList, setUserRolesList] = useState([]);
  
  // Filter bar states
  const [filterCompany, setFilterCompany] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Form modal states
  const [formData, setFormData] = useState({
    company_id: '',
    user_id: '',
    department_id: '',
    role_id: '',
  });
  
  const [formDepartments, setFormDepartments] = useState([]);
  const [formRoles, setFormRoles] = useState([]);
  const [formUsers, setFormUsers] = useState([]);

  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const dialogContentRef = useRef(null);

  useEffect(() => {
    if (formError && dialogContentRef.current) {
      dialogContentRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [formError]);

  const isPlatformAdmin = currentUser?.is_administrator;
  const canView = hasPermission('UserRoles', 'view');
  const canCreate = hasPermission('UserRoles', 'create');
  const canDelete = hasPermission('UserRoles', 'delete');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    loadData();
  }, [debouncedSearch, filterCompany, filterDepartment]);

  const loadData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (filterCompany) params.company_id = filterCompany;
      if (filterDepartment) params.department_id = filterDepartment;

      const promises = [
        userRolesAPI.getAll(params),
        usersAPI.getAll(filterCompany ? { company_id: filterCompany } : {}),
        rolesAPI.getAll(filterCompany ? { company_id: filterCompany } : {}),
        departmentsAPI.getAll(filterCompany ? { company_id: filterCompany } : {}),
      ];

      if (isPlatformAdmin) {
        promises.push(companiesAPI.getAll());
      }

      const results = await Promise.allSettled(promises);

      if (results[0].status === 'fulfilled') setUserRoles(results[0].value.data.data || []);
      if (results[1].status === 'fulfilled') setUsers(results[1].value.data.data || []);
      if (results[2].status === 'fulfilled') setRoles(results[2].value.data.data || []);
      if (results[3].status === 'fulfilled') setDepartments(results[3].value.data.data || []);
      if (isPlatformAdmin && results[4]?.status === 'fulfilled') {
        setCompanies(results[4].value.data.data || []);
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

  const handleFilterCompanyChange = (companyId) => {
    setFilterCompany(companyId);
    setFilterDepartment(''); // Reset department filter when company changes
    setSelectedUser('');
    setUserRolesList([]);
  };

  const handleAdd = () => {
    const initialCompanyId = !isPlatformAdmin && currentUser?.company_id ? currentUser.company_id : '';
    setFormError('');
    setFormData({
      company_id: initialCompanyId,
      user_id: '',
      department_id: '',
      role_id: '',
    });
    setFormDepartments([]);
    setFormRoles([]);
    setFormUsers([]);
    setDialogOpen(true);

    if (initialCompanyId) {
      loadFormDepartmentsAndUsers(initialCompanyId);
    }
  };

  const loadFormDepartmentsAndUsers = async (companyId) => {
    try {
      if (!companyId) {
        setFormDepartments([]);
        setFormUsers([]);
        setFormRoles([]);
        return;
      }
      const [deptRes, userRes, roleRes] = await Promise.all([
        departmentsAPI.getAll({ company_id: companyId }),
        usersAPI.getAll({ company_id: companyId }),
        rolesAPI.getAll({ company_id: companyId }),
      ]);
      setFormDepartments(deptRes.data.data || []);
      setFormUsers(userRes.data.data || []);
      setFormRoles(roleRes.data.data || []);
    } catch (err) {
      console.error('Error loading form departments/users/roles:', err);
      setFormDepartments([]);
      setFormUsers([]);
      setFormRoles([]);
    }
  };

  const handleFormCompanyChange = (companyId) => {
    setFormData({
      ...formData,
      company_id: companyId,
      user_id: '',
      department_id: '',
      role_id: '',
    });
    setFormRoles([]);
    loadFormDepartmentsAndUsers(companyId);
  };

  const handleFormDepartmentChange = async (departmentId) => {
    setFormData({ 
      ...formData, 
      department_id: departmentId,
      role_id: '' // Clear role selection when department changes
    });

    try {
      const params = { company_id: formData.company_id };
      if (departmentId) {
        params.department_id = departmentId;
      }
      const response = await rolesAPI.getAll(params);
      setFormRoles(response.data.data || []);
    } catch (error) {
      console.error('Error loading roles by department:', error);
      setFormRoles([]);
    }
  };

  const handleUserSelect = (userId) => {
    setSelectedUser(userId);
    if (userId) {
      loadUserRoles(userId);
    } else {
      setUserRolesList([]);
    }
  };

  const handleAssignRole = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    if (!formData.user_id || !formData.role_id) {
      setFormError(capitalizeError('User and Role are required'));
      return;
    }

    try {
      await userRolesAPI.assign({
        user_id: formData.user_id,
        role_id: formData.role_id,
        company_id: formData.company_id,
        department_id: formData.department_id,
      });
      setSuccess('Role assigned successfully');
      setDialogOpen(false);
      loadData();
      if (selectedUser) {
        loadUserRoles(selectedUser);
      }
      
      await refreshPermissions();
    } catch (error) {
      setFormError(capitalizeError((error.response && error.response.data && error.response.data.error) || 'Failed to assign role'));
    }
  };

  const handleUnassignRole = async (mappingId) => {
    const confirmed = await showConfirmDialog({
      title: 'Unassign Role?',
      text: 'Are you sure you want to unassign this role from the user?',
      icon: 'warning',
      confirmButtonText: 'Yes, unassign',
      confirmButtonColor: '#d32f2f',
    });
    if (confirmed) {
      try {
        await userRolesAPI.unassign(mappingId);
        setSuccess('Role unassigned successfully');
        loadData();
        if (selectedUser) {
          loadUserRoles(selectedUser);
        }
        
        await refreshPermissions();
      } catch (error) {
        setError(
          capitalizeError(
            (error.response && error.response.data && error.response.data.error)
            || 'Failed to unassign role'
          )
        );
      }
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
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

  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.id === companyId);
    return company ? company.company_name : 'N/A';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'company_name',
      headerName: 'Company',
      width: 170,
      renderCell: (params) => (
        <Chip
          label={params.value || params.row.company_name || getCompanyName(params.row.company_id)}
          size="small"
          variant="outlined"
          color="primary"
          icon={<BusinessIcon />}
        />
      ),
    },
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

      {/* Filter Bar */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          label="Search by name"
          placeholder="Search by user name..."
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          sx={{ minWidth: 200 }}
        />

        {isPlatformAdmin && (
          <SearchableSelect
            options={companies}
            getOptionLabel={(c) => c.company_name}
            getOptionValue={(c) => c.id}
            value={filterCompany}
            onChange={(e) => handleFilterCompanyChange(e.target.value)}
            label="Filter by Company"
            allOptionLabel="All Companies"
            allOptionValue=""
            sx={{ minWidth: 200, maxWidth: 300 }}
          />
        )}

        <SearchableSelect
          options={departments}
          getOptionLabel={(d) => d.department_name}
          getOptionValue={(d) => d.id}
          value={filterDepartment}
          onChange={(e) => setFilterDepartment(e.target.value)}
          label="Filter by Department"
          allOptionLabel="All Departments"
          allOptionValue=""
          sx={{ minWidth: 200, maxWidth: 300 }}
        />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ height: 600, width: '100%' }}>
            <DataGrid
              rows={userRoles}
              columns={columns}
              loading={loading}
              initialState={{
                pagination: {
                  paginationModel: { pageSize: 10 },
                },
              }}
              pageSizeOptions={[5, 10, 25, 50]}
              disableRowSelectionOnClick
              slots={{
                toolbar: () => <CustomToolbar onAdd={handleAdd} hasCreatePermission={canCreate} />
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
              
              <Box sx={{ mb: 2 }}>
                <SearchableSelect
                  options={users}
                  getOptionLabel={(u) => `${u.name} (${u.email})`}
                  getOptionValue={(u) => u.id}
                  value={selectedUser}
                  onChange={(e) => handleUserSelect(e.target.value)}
                  label="Select User"
                  placeholder={isPlatformAdmin && !filterCompany ? 'Select Company Filter First' : 'Select User'}
                  disabled={isPlatformAdmin && !filterCompany}
                />
              </Box>

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
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            
            {/* 1. Company Field FIRST */}
            {isPlatformAdmin ? (
              <Box sx={{ mb: 2 }}>
                <SearchableSelect
                  options={companies}
                  getOptionLabel={(c) => c.company_name}
                  getOptionValue={(c) => c.id}
                  value={formData.company_id || ''}
                  onChange={(e) => handleFormCompanyChange(e.target.value)}
                  label="Company *"
                  placeholder="Select Company"
                  margin="dense"
                />
              </Box>
            ) : (
              <TextField
                fullWidth
                margin="dense"
                label="Company"
                value={currentUser?.company_name || 'Your Company'}
                disabled
                sx={{ mb: 2 }}
              />
            )}

            {/* 2. User Field (Scoped to selected Company) */}
            <Box sx={{ mb: 2 }}>
              <SearchableSelect
                options={formUsers}
                getOptionLabel={(u) => `${u.name} (${u.email})`}
                getOptionValue={(u) => u.id}
                value={formData.user_id || ''}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                label="User *"
                margin="dense"
                placeholder={formData.company_id ? 'Select User' : 'Select Company First'}
                disabled={!formData.company_id}
              />
            </Box>

            {/* 3. Department Field (Optional for Company-Wide Roles) */}
            <Box sx={{ mb: 2 }}>
              <SearchableSelect
                options={formDepartments}
                getOptionLabel={(d) => d.department_name}
                getOptionValue={(d) => d.id}
                value={formData.department_id || ''}
                onChange={(e) => handleFormDepartmentChange(e.target.value)}
                label="Department (Optional)"
                margin="dense"
                allOptionLabel="None (Company-Wide Role)"
                allOptionValue=""
                disabled={!formData.company_id}
              />
            </Box>

            {/* 4. Role Field (Scoped to selected Company / Department) */}
            <Box sx={{ mb: 2 }}>
              <SearchableSelect
                options={formRoles}
                getOptionLabel={(r) => `${r.role_name} ${r.department_name ? `(${r.department_name})` : '(Company-Wide)'}`}
                getOptionValue={(r) => r.id}
                value={formData.role_id || ''}
                onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
                label="Role *"
                margin="dense"
                placeholder={formData.company_id ? 'Select Role' : 'Select Company First'}
                disabled={!formData.company_id}
              />
            </Box>
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
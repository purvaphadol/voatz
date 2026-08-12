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
  CircularProgress,
  FormControlLabel,
  Switch,
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
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { usersAPI, departmentsAPI, companiesAPI, handleApiError } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';
import { showSuccessAlert, showErrorAlert, showConfirmDialog } from '../../utils/swal';
import { validateNonNumericText, validateEmail, validatePhone, capitalizeError } from '../../utils/validators';
import { useDeleteWithDependencies } from '../../hooks/useDeleteWithDependencies';
import SearchableSelect from '../Common/SearchableSelect';

const CustomToolbar = ({ onAdd, hasCreatePermission, showInactive, setShowInactive }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add User
      </Button>
    )}
    <FormControlLabel
      control={
        <Switch
          checked={showInactive}
          onChange={(e) => setShowInactive(e.target.checked)}
          color="warning"
          size="small"
        />
      }
      label={<Typography variant="body2">Show Inactive</Typography>}
      sx={{ ml: 'auto' }}
    />
  </GridToolbarContainer>
);

const Users = () => {
  const { hasPermission } = usePermissions();
  const { user } = useAuth();
  
  const isPlatformAdmin = user?.is_administrator === true;
  const isCompanySuperAdmin = user?.roles?.some(
    r => r.role_name?.toLowerCase() === 'super admin'
  ) || false;

  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    department_id: '',
    company_id: '',
    status: 1,
  });
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const dialogContentRef = useRef(null);

  useEffect(() => {
    if (formError && dialogContentRef.current) {
      dialogContentRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [formError]);
  
  // Pagination & Search
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [totalRows, setTotalRows] = useState(0);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Filters
  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState('');
  const [selectedDepartmentFilter, setSelectedDepartmentFilter] = useState('');

  const canView = hasPermission('Users', 'view');
  const canCreate = hasPermission('Users', 'create');
  const canUpdate = hasPermission('Users', 'update');
  const canDelete = hasPermission('Users', 'delete');

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, selectedCompanyFilter, selectedDepartmentFilter, showInactive]);

  useEffect(() => {
    loadUsers();
  }, [page, pageSize, debouncedSearch, selectedCompanyFilter, selectedDepartmentFilter, showInactive]);

  useEffect(() => {
    if (isPlatformAdmin) {
      loadCompanies();
    }
    loadDepartments(isPlatformAdmin ? selectedCompanyFilter : undefined);
  }, [isPlatformAdmin, selectedCompanyFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1, // backend is 1-indexed
        per_page: pageSize,
        search: debouncedSearch || undefined,
      };
      if (selectedDepartmentFilter) params.department_id = selectedDepartmentFilter;
      if (isPlatformAdmin && selectedCompanyFilter) params.company_id = selectedCompanyFilter;
      if (showInactive) params.show_inactive = 'true';

      const response = await usersAPI.getAll(params);
      setUsers(response.data.data || []);
      setTotalRows(response.data.total || 0);
    } catch (error) {
      console.error('Error loading users:', error);
      setError(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const loadDepartments = async (companyId) => {
    try {
      const params = companyId ? { company_id: companyId } : {};
      const response = await departmentsAPI.getAll(params);
      setDepartments((response.data.data || []).filter(d => d.status === 1));
    } catch (error) {
      console.error('Error loading departments:', error);
    }
  };

  const loadCompanies = async () => {
    try {
      const response = await companiesAPI.getAll();
      setCompanies((response.data.data || []).filter(c => c.status === 1));
    } catch (error) {
      console.error('Error loading companies:', error);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingUser(null);
    setViewMode(false);
  };

  const handleAdd = () => {
    setEditingUser(null);
    setViewMode(false);
    setFormError('');
    setFormData({
      name: '',
      email: '',
      password: '',
      department_id: '',
      company_id: '',
      status: 1,
    });
    setDialogOpen(true);
  };

  const handleEdit = (user) => {
    if (!user || !user.id) {
      showErrorAlert('Invalid user record. Please refresh the page and try again.');
      return;
    }
    setEditingUser(user);
    setViewMode(false);
    setFormError('');
    const compId = user.company_id || '';
    setFormData({
      name: user.name,
      email: user.email,
      password: '',
      company_id: compId,
      department_id: user.department_id || '',
      status: user.status ?? 1,
    });
    if (isPlatformAdmin && compId) {
      loadDepartments(compId);
    }
    setDialogOpen(true);
  };

  const handleView = (userRecord) => {
    if (!userRecord || !userRecord.id) return;
    setEditingUser(userRecord);
    setViewMode(true);
    setFormError('');
    const compId = userRecord.company_id || '';
    setFormData({
      name: userRecord.name,
      email: userRecord.email,
      password: '',
      company_id: compId,
      department_id: userRecord.department_id || '',
      status: userRecord.status ?? 1,
    });
    if (isPlatformAdmin && compId) {
      loadDepartments(compId);
    }
    setDialogOpen(true);
  };

  const handleDelete = useDeleteWithDependencies({
    deleteApi: usersAPI.delete,
    itemLabel: 'this user',
    successMsg: 'User deleted successfully',
    forceSuccessMsg: 'User and active roles/voter records force-deleted successfully',
    forceConfirmMessage: 'Are you sure you want to delete this user (and all related role mapping and voter profile data)?',
    onSuccess: loadUsers,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const cleanedData = {
      ...formData,
      name: formData.name.trim(),
      email: formData.email.trim().toLowerCase(),
    };

    if (isPlatformAdmin && !editingUser && !formData.company_id) {
      setFormError(capitalizeError('Please select a company'));
      return;
    }

    const nameErr = validateNonNumericText(cleanedData.name, 'Full Name', 2, 100);
    if (nameErr) {
      setFormError(capitalizeError(nameErr));
      return;
    }

    const emailErr = validateEmail(cleanedData.email);
    if (emailErr) {
      setFormError(capitalizeError(emailErr));
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanedData.email)) {
      setFormError(capitalizeError('Invalid email address format'));
      return;
    }
    
    if (!editingUser && !cleanedData.password) {
      setFormError(capitalizeError('Password is required'));
      return;
    }
    
    if (cleanedData.password) {
      if (cleanedData.password.length < 8) {
        setFormError(capitalizeError('Password must be at least 8 characters long'));
        return;
      }
      if (!/[a-zA-Z]/.test(cleanedData.password)) {
        setFormError(capitalizeError('Password must contain at least one letter'));
        return;
      }
      if (!/[0-9]/.test(cleanedData.password)) {
        setFormError(capitalizeError('Password must contain at least one number'));
        return;
      }
    }

    try {
      setIsSubmitting(true);
      
      const payload = { ...cleanedData };
      if (!isPlatformAdmin || editingUser) {
        delete payload.company_id;
      }
      
      if (editingUser) {
        if (editingUser.status !== formData.status) {
          if (formData.status === 0) {
            try {
              const depRes = await usersAPI.getStatusDependents(editingUser.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Set User Inactive?',
                  text: `Setting this user inactive will also pause ${depCount} user role mappings and voter registrations to Inactive. Do you wish to proceed?`,
                  confirmButtonText: 'Yes, set inactive',
                  confirmButtonColor: '#ed6c02',
                });
                if (!confirmed) {
                  setIsSubmitting(false);
                  return;
                }
              }
            } catch (err) {
              console.warn('Could not inspect status dependents:', err);
            }
          } else if (formData.status === 1) {
            try {
              const depRes = await usersAPI.getStatusDependents(editingUser.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Reactivate User?',
                  text: `Reactivating this user will reactivate child records paused with them. Do you wish to proceed?`,
                  confirmButtonText: 'Yes, reactivate',
                  confirmButtonColor: '#2e7d32',
                });
                if (!confirmed) {
                  setIsSubmitting(false);
                  return;
                }
              }
            } catch (err) {
              console.warn('Could not inspect status dependents:', err);
            }
          }
        }
        payload.status = formData.status;
        await usersAPI.update(editingUser.id, payload);
        setDialogOpen(false);
        await showSuccessAlert('User updated successfully');
      } else {
        await usersAPI.create(payload);
        setDialogOpen(false);
        await showSuccessAlert('User created successfully');
      }
      loadUsers();
    } catch (error) {
      if (error.response && error.response.status === 409 && error.response.data?.can_reactivate) {
        const existingId = error.response.data.existing_id;
        const reactivateConfirmed = await showConfirmDialog({
          title: 'Inactive User Found',
          text: error.response.data.error || 'An inactive user with this email already exists. Would you like to reactivate them?',
          confirmButtonText: 'Reactivate User',
          confirmButtonColor: '#2e7d32',
        });
        if (reactivateConfirmed && existingId) {
          try {
            await usersAPI.update(existingId, { status: 1 });
            setDialogOpen(false);
            await showSuccessAlert('User reactivated successfully');
            loadUsers();
            return;
          } catch (reactivateErr) {
            setFormError(capitalizeError(reactivateErr.response?.data?.error || 'Failed to reactivate user'));
            return;
          }
        }
      }
      setFormError(capitalizeError(handleApiError(error)));
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDepartmentName = (departmentId) => {
    const dept = departments.find(d => d.id === departmentId);
    return dept ? dept.department_name : 'N/A';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'email', headerName: 'Email', width: 250 },
    {
      field: 'company_name',
      headerName: 'Company',
      width: 180,
      renderCell: (params) => (
        <Chip 
          label={params.value || 'N/A'}
          variant="outlined"
          size="small"
          color="primary"
        />
      ),
    },
    {
      field: 'department_id',
      headerName: 'Department',
      width: 170,
      renderCell: (params) => (
        <Chip
          label={params.row.department_name || getDepartmentName(params.value)}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value === 1 ? 'Active' : params.value === 0 ? 'Inactive' : 'Deactivated'}
          color={params.value === 1 ? 'success' : params.value === 0 ? 'warning' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        const date = new Date(params.value);
        return isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString();
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 150,
      getActions: (params) => {
        const actions = [];
        
        if (canView) {
          actions.push(
            <GridActionsCellItem
              icon={<ViewIcon />}
              label="View"
              onClick={() => handleView(params.row)}
            />
          );
        }

        if (canUpdate) {
          actions.push(
            <GridActionsCellItem
              icon={<EditIcon />}
              label="Edit"
              onClick={() => handleEdit(params.row)}
            />
          );
        }
        
        if (canDelete) {
          actions.push(
            <GridActionsCellItem
              icon={<DeleteIcon />}
              label="Delete"
              onClick={() => handleDelete(params.row.id)}
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
        Users Management
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
      
      {/* Search and Filters Bar: Company First, Department Second */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          label="Search Users"
          variant="outlined"
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by name or email..."
          sx={{ minWidth: 220 }}
        />

        {isPlatformAdmin && (
          <SearchableSelect
            options={companies}
            getOptionLabel={(comp) => comp.company_name}
            getOptionValue={(comp) => comp.id}
            value={selectedCompanyFilter}
            onChange={(e) => {
              const compId = e.target.value;
              setSelectedCompanyFilter(compId);
              setSelectedDepartmentFilter('');
              loadDepartments(compId);
            }}
            label="Filter by Company"
            allOptionLabel="All Companies"
            allOptionValue=""
            sx={{ minWidth: 200, maxWidth: 300 }}
          />
        )}

        <SearchableSelect
          options={departments}
          getOptionLabel={(dept) => dept.department_name}
          getOptionValue={(dept) => dept.id}
          value={selectedDepartmentFilter}
          onChange={(e) => setSelectedDepartmentFilter(e.target.value)}
          label="Filter by Department"
          allOptionLabel="All Departments"
          allOptionValue=""
          sx={{ minWidth: 200, maxWidth: 300 }}
        />
      </Box>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={users}
          columns={columns}
          paginationMode="server"
          rowCount={totalRows}
          paginationModel={{ page, pageSize }}
          onPaginationModelChange={(model) => {
            setPage(model.page);
            setPageSize(model.pageSize);
          }}
          pageSizeOptions={[5, 10, 25, 50, 100]}
          disableRowSelectionOnClick
          loading={loading}
          slots={{
            toolbar: () => (
              <CustomToolbar
                onAdd={handleAdd}
                hasCreatePermission={canCreate}
                showInactive={showInactive}
                setShowInactive={setShowInactive}
              />
            ),
          }}
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {viewMode ? 'View User' : editingUser ? 'Edit User' : 'Add New User'}
          </DialogTitle>
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}

            <TextField
              autoFocus
              margin="dense"
              label="Name"
              type="text"
              fullWidth
              variant="outlined"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Email"
              type="email"
              fullWidth
              variant="outlined"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
            />
            {!viewMode && (
              <TextField
                margin="dense"
                label={editingUser ? "New Password (leave blank to keep current)" : "Password"}
                type="password"
                fullWidth
                variant="outlined"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required={!editingUser}
                sx={{ mb: 2 }}
              />
            )}

            {/* 1. Company Field */}
            {!editingUser ? (
              isPlatformAdmin ? (
                <Box sx={{ mb: 2 }}>
                  <SearchableSelect
                    options={companies}
                    getOptionLabel={(comp) => comp.company_name}
                    getOptionValue={(comp) => comp.id}
                    value={formData.company_id || ''}
                    onChange={(e) => {
                      const selectedCompanyId = e.target.value;
                      setFormData({ ...formData, company_id: selectedCompanyId, department_id: '' });
                      if (selectedCompanyId) {
                        loadDepartments(selectedCompanyId);
                      }
                    }}
                    label="Company *"
                    placeholder="Select Company"
                    margin="dense"
                    disabled={viewMode}
                  />
                </Box>
              ) : (
                <TextField
                  margin="dense"
                  label="Company"
                  fullWidth
                  variant="outlined"
                  value={
                    user?.company_name ||
                    companies.find(c => c.id === user?.company_id)?.company_name ||
                    (departments.length > 0 ? departments[0]?.company_name : '') ||
                    'Your Company'
                  }
                  disabled
                  helperText={!viewMode ? "Users are automatically assigned to your company." : ""}
                  sx={{ mb: 2 }}
                />
              )
            ) : (
              <TextField
                margin="dense"
                label="Company"
                fullWidth
                variant="outlined"
                value={editingUser.company_name || 'N/A'}
                disabled
                helperText={!viewMode ? "Company cannot be modified after creation." : ""}
                sx={{ mb: 2 }}
              />
            )}

            {/* 2. Department Field */}
            <Box sx={{ mb: 2 }}>
              <SearchableSelect
                options={departments}
                getOptionLabel={(dept) => dept.department_name}
                getOptionValue={(dept) => dept.id}
                value={formData.department_id || ''}
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                label="Department"
                margin="dense"
                placeholder={isPlatformAdmin && !formData.company_id && !editingUser ? 'Select Company First' : 'Select Department'}
                disabled={viewMode || (isPlatformAdmin && !formData.company_id && !editingUser)}
              />
            </Box>

            {/* 3. Status Field LAST */}
            {(editingUser || viewMode) && (
              <Box sx={{ mb: 2 }}>
                <SearchableSelect
                  options={[
                    { id: 1, name: 'Active' },
                    { id: 0, name: 'Inactive' }
                  ]}
                  getOptionLabel={(opt) => opt.name}
                  getOptionValue={(opt) => opt.id}
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: Number(e.target.value) })}
                  label="Status"
                  margin="dense"
                  disabled={viewMode}
                />
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog} disabled={isSubmitting}>
              {viewMode ? 'Close' : 'Cancel'}
            </Button>
            {!viewMode && (
              <Button type="submit" variant="contained" disabled={isSubmitting}>
                {isSubmitting ? <CircularProgress size={24} /> : (editingUser ? 'Update' : 'Create')}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};


export default Users; 
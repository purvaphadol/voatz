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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
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
  Business as BusinessIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { rolesAPI, departmentsAPI, companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';
import { showSuccessAlert, showErrorAlert, showConfirmDialog } from '../../utils/swal';
import { validateNonNumericText, capitalizeError } from '../../utils/validators';
import { useDeleteWithDependencies } from '../../hooks/useDeleteWithDependencies';
import SearchableSelect from '../Common/SearchableSelect';

const CustomToolbar = ({ onAdd, hasCreatePermission, showInactive, setShowInactive }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Role
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

const Roles = () => {
  const { hasPermission } = usePermissions();
  const { user } = useAuth();

  const isPlatformAdmin = user?.is_administrator === true;

  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [showInactive, setShowInactive] = useState(false);

  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState('');
  const [selectedDepartmentFilter, setSelectedDepartmentFilter] = useState('');

  const [formData, setFormData] = useState({
    role_name: '',
    description: '',
    company_id: '',
    department_id: '',
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

  const canView = hasPermission('Roles', 'view') || hasPermission('Settings', 'view');
  const canCreate = hasPermission('Roles', 'create') || hasPermission('Settings', 'create');
  const canUpdate = hasPermission('Roles', 'update') || hasPermission('Settings', 'update');
  const canDelete = hasPermission('Roles', 'delete') || hasPermission('Settings', 'delete');

  useEffect(() => {
    if (canView) {
      if (isPlatformAdmin) {
        loadCompanies();
      }
      loadDepartments(isPlatformAdmin ? selectedCompanyFilter : undefined);
    }
  }, [canView, isPlatformAdmin, selectedCompanyFilter]);

  useEffect(() => {
    if (canView) {
      loadRoles();
    }
  }, [canView, selectedCompanyFilter, selectedDepartmentFilter, showInactive]);

  const loadRoles = async () => {
    try {
      setLoading(true);
      const params = {};
      if (selectedDepartmentFilter) params.department_id = selectedDepartmentFilter;
      if (isPlatformAdmin && selectedCompanyFilter) params.company_id = selectedCompanyFilter;
      if (showInactive) params.show_inactive = 'true';
      const response = await rolesAPI.getAll(params);
      setRoles(response.data.data || []);
    } catch (error) {
      console.error('Error loading roles:', error);
      setError('Failed to load roles');
    } finally {
      setLoading(false);
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

  const loadDepartments = async (companyId) => {
    try {
      const params = companyId ? { company_id: companyId } : {};
      const response = await departmentsAPI.getAll(params);
      setDepartments((response.data.data || []).filter(d => d.status === 1));
    } catch (error) {
      console.error('Error loading departments:', error);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingRole(null);
    setViewMode(false);
  };

  const handleAdd = () => {
    setEditingRole(null);
    setViewMode(false);
    setFormError('');
    setFormData({
      role_name: '',
      description: '',
      company_id: '',
      department_id: '',
      status: 1,
    });
    setDialogOpen(true);
  };

  const handleEdit = (role) => {
    setEditingRole(role);
    setViewMode(false);
    setFormError('');
    const roleCompId = role.company_id || '';
    setFormData({
      role_name: role.role_name,
      description: role.description || '',
      company_id: roleCompId,
      department_id: role.department_id || '',
      status: role.status ?? 1,
    });
    if (isPlatformAdmin && roleCompId) {
      loadDepartments(roleCompId);
    }
    setDialogOpen(true);
  };

  const handleView = (role) => {
    if (!role || !role.id) return;
    setEditingRole(role);
    setViewMode(true);
    setFormError('');
    const roleCompId = role.company_id || '';
    setFormData({
      role_name: role.role_name,
      description: role.description || '',
      company_id: roleCompId,
      department_id: role.department_id || '',
      status: role.status ?? 1,
    });
    if (isPlatformAdmin && roleCompId) {
      loadDepartments(roleCompId);
    }
    setDialogOpen(true);
  };

  const handleDelete = useDeleteWithDependencies({
    deleteApi: rolesAPI.delete,
    itemLabel: 'this role',
    successMsg: 'Role deleted successfully',
    forceSuccessMsg: 'Role and user role mappings force-deleted successfully',
    forceConfirmMessage: 'Are you sure you want to delete this role (and all related user role mapping data)?',
    onSuccess: loadRoles,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const nameErr = validateNonNumericText(formData.role_name, 'Role name', 2, 100);
    if (nameErr) {
      setFormError(capitalizeError(nameErr));
      return;
    }

    try {
      setIsSubmitting(true);
      if (editingRole && editingRole.status !== formData.status) {
        if (formData.status === 0) {
          try {
            const depRes = await rolesAPI.getStatusDependents(editingRole.id);
            const depCount = depRes.data?.data?.total_count || 0;
            if (depCount > 0) {
              const confirmed = await showConfirmDialog({
                title: 'Set Role Inactive?',
                text: `Setting this role inactive will pause ${depCount} user role mappings to Inactive. Do you wish to proceed?`,
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
            const depRes = await rolesAPI.getStatusDependents(editingRole.id);
            const depCount = depRes.data?.data?.total_count || 0;
            if (depCount > 0) {
              const confirmed = await showConfirmDialog({
                title: 'Reactivate Role?',
                text: `Reactivating this role will reactivate associated user role mappings paused with it. Do you wish to proceed?`,
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

      const payload = {
        role_name: formData.role_name,
        description: formData.description,
        department_id: formData.department_id || null,
        status: formData.status,
      };
      if (isPlatformAdmin && formData.company_id) {
        payload.company_id = formData.company_id;
      }

      if (editingRole) {
        await rolesAPI.update(editingRole.id, payload);
        setDialogOpen(false);
        await showSuccessAlert('Role updated successfully');
      } else {
        await rolesAPI.create(payload);
        setDialogOpen(false);
        await showSuccessAlert('Role created successfully');
      }
      loadRoles();
    } catch (error) {
      if (error.response && error.response.status === 409 && error.response.data?.can_reactivate) {
        const existingId = error.response.data.existing_id;
        const reactivateConfirmed = await showConfirmDialog({
          title: 'Inactive Role Found',
          text: error.response.data.error || 'An inactive role with this name already exists. Would you like to reactivate it?',
          confirmButtonText: 'Reactivate Role',
          confirmButtonColor: '#2e7d32',
        });
        if (reactivateConfirmed && existingId) {
          try {
            await rolesAPI.update(existingId, { status: 1 });
            setDialogOpen(false);
            await showSuccessAlert('Role reactivated successfully');
            loadRoles();
            return;
          } catch (reactivateErr) {
            setFormError(capitalizeError(reactivateErr.response?.data?.error || 'Failed to reactivate role'));
            return;
          }
        }
      }
      setFormError(capitalizeError((error.response && error.response.data && error.response.data.error) || 'Operation failed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'role_name', headerName: 'Role Name', width: 200 },
    {
      field: 'company_name',
      headerName: 'Company',
      width: 180,
      renderCell: (params) => (
        <Chip
          icon={<BusinessIcon />}
          label={params.value || 'N/A'}
          variant="outlined"
          size="small"
          color="primary"
        />
      ),
    },
    { 
      field: 'department_name', 
      headerName: 'Department', 
      width: 180,
      renderCell: (params) => (
        <Chip 
          label={params.value || 'N/A'}
          variant="outlined"
          size="small"
        />
      ),
    },
    { field: 'description', headerName: 'Description', width: 220 },
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
      width: 130,
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

  if (!canView) {
    return (
      <Box>
        <Alert severity="error">
          You don't have permission to view roles.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Roles Management
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

      {/* Filters Bar: Company First, Department Second */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
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
          rows={roles}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 10 },
            },
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          disableRowSelectionOnClick
          loading={loading}
          slots={{
            toolbar: CustomToolbar,
          }}
          slotProps={{
            toolbar: {
              onAdd: handleAdd,
              hasCreatePermission: canCreate,
              showInactive: showInactive,
              setShowInactive: setShowInactive,
            },
          }}
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {viewMode ? 'View Role' : editingRole ? 'Edit Role' : 'Add New Role'}
          </DialogTitle>
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}

            <TextField
              autoFocus
              margin="dense"
              label="Role Name"
              type="text"
              fullWidth
              variant="outlined"
              value={formData.role_name}
              onChange={(e) => setFormData({ ...formData, role_name: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
            />
            
            {/* 1. Company Field FIRST */}
            {!editingRole ? (
              isPlatformAdmin ? (
                <Box sx={{ mb: 2 }}>
                  <SearchableSelect
                    options={companies}
                    getOptionLabel={(comp) => comp.company_name}
                    getOptionValue={(comp) => comp.id}
                    value={formData.company_id || ''}
                    onChange={(e) => {
                      const selectedCompId = e.target.value;
                      setFormData({ ...formData, company_id: selectedCompId, department_id: '' });
                      if (selectedCompId) {
                        loadDepartments(selectedCompId);
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
                    'Your Company'
                  }
                  disabled
                  helperText={!viewMode ? "Roles are automatically assigned to your company." : ""}
                  sx={{ mb: 2 }}
                />
              )
            ) : (
              <TextField
                margin="dense"
                label="Company"
                fullWidth
                variant="outlined"
                value={editingRole.company_name || 'N/A'}
                disabled
                helperText={!viewMode ? "Company cannot be modified after creation." : ""}
                sx={{ mb: 2 }}
              />
            )}

            {/* 2. Department Field SECOND (Dynamic dependent dropdown - Optional) */}
            <Box sx={{ mb: 2 }}>
              <SearchableSelect
                options={departments}
                getOptionLabel={(dept) => dept.department_name}
                getOptionValue={(dept) => dept.id}
                value={formData.department_id || ''}
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                label="Department (Optional)"
                margin="dense"
                allOptionLabel="None (Company-wide / No Department)"
                allOptionValue=""
                disabled={viewMode || (isPlatformAdmin && !formData.company_id && !editingRole)}
              />
            </Box>
            
            <TextField
              margin="dense"
              label="Description"
              type="text"
              fullWidth
              variant="outlined"
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            {/* Status select for edit / view mode */}
            {(editingRole || viewMode) && (
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
                {isSubmitting ? 'Saving...' : editingRole ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Roles; 
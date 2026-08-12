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
  Business as BusinessIcon,
} from '@mui/icons-material';
import { departmentsAPI, companiesAPI } from '../../services/api';
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
        Add Department
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

const Departments = () => {
  const { hasPermission } = usePermissions();
  const { user } = useAuth();
  
  const isPlatformAdmin = user?.is_administrator === true;

  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [formData, setFormData] = useState({
    department_name: '',
    description: '',
    company_id: '',
    status: 1,
  });
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterCompany, setFilterCompany] = useState('');

  const dialogContentRef = useRef(null);

  useEffect(() => {
    if (formError && dialogContentRef.current) {
      dialogContentRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [formError]);

  const canView = hasPermission('Departments', 'view');
  const canCreate = hasPermission('Departments', 'create');
  const canUpdate = hasPermission('Departments', 'update');
  const canDelete = hasPermission('Departments', 'delete');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (canView) {
      loadCompanies();
    }
  }, [canView]);

  useEffect(() => {
    if (canView) {
      loadDepartments();
    }
  }, [canView, debouncedSearch, filterCompany, showInactive]);

  const loadDepartments = async () => {
    try {
      setLoading(true);
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (isPlatformAdmin && filterCompany) params.company_id = filterCompany;
      if (showInactive) params.show_inactive = 'true';
      const response = await departmentsAPI.getAll(params);
      setDepartments(response.data.data || []);
    } catch (error) {
      console.error('Error loading departments:', error);
      setError('Failed to load departments');
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

  const handleAdd = () => {
    setEditingDepartment(null);
    setViewMode(false);
    setFormError('');
    setFormData({
      department_name: '',
      description: '',
      company_id: '',
      status: 1,
    });
    setDialogOpen(true);
  };

  const handleEdit = (department) => {
    setEditingDepartment(department);
    setViewMode(false);
    setFormError('');
    setFormData({
      department_name: department.department_name,
      company_id: department.company_id || '',
      description: department.description || '',
      status: department.status ?? 1,
    });
    setDialogOpen(true);
  };

  const handleView = (department) => {
    setEditingDepartment(department);
    setViewMode(true);
    setFormError('');
    setFormData({
      department_name: department.department_name,
      company_id: department.company_id || '',
      description: department.description || '',
      status: department.status ?? 1,
    });
    setDialogOpen(true);
  };

  const handleDelete = useDeleteWithDependencies({
    deleteApi: departmentsAPI.delete,
    itemLabel: 'this department',
    successMsg: 'Department deleted successfully',
    forceSuccessMsg: 'Department deleted successfully. Assigned users were unassigned and department roles deactivated.',
    forceConfirmMessage: 'Are you sure you want to delete this department? Assigned users will be unassigned from this department, and department roles will be deactivated.',
    onSuccess: loadDepartments,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const nameErr = validateNonNumericText(formData.department_name, 'Department name', 2, 100);
    if (nameErr) {
      setFormError(capitalizeError(nameErr));
      return;
    }

    try {
      setIsSubmitting(true);
      if (editingDepartment) {
        // Status cascade transition check
        if (editingDepartment.status !== formData.status) {
          if (formData.status === 0) {
            try {
              const depRes = await departmentsAPI.getStatusDependents(editingDepartment.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Set Department Inactive?',
                  text: `Setting this department inactive will also set ${depCount} related active roles and users to Inactive. Do you wish to proceed?`,
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
              const depRes = await departmentsAPI.getStatusDependents(editingDepartment.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Reactivate Department?',
                  text: `Reactivating this department will also reactivate child records that were paused with it. Do you wish to proceed?`,
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

        const updatePayload = {
          department_name: formData.department_name,
          description: formData.description,
          status: formData.status,
        };
        if (isPlatformAdmin && formData.company_id) {
          updatePayload.company_id = formData.company_id;
        }
        await departmentsAPI.update(editingDepartment.id, updatePayload);
        setDialogOpen(false);
        await showSuccessAlert('Department updated successfully');
      } else {
        const createPayload = {
          department_name: formData.department_name,
          description: formData.description,
          status: formData.status,
        };
        if (isPlatformAdmin && formData.company_id) {
          createPayload.company_id = formData.company_id;
        }
        await departmentsAPI.create(createPayload);
        setDialogOpen(false);
        await showSuccessAlert('Department created successfully');
      }
      loadDepartments();
    } catch (error) {
      if (error.response && error.response.status === 409 && error.response.data?.can_reactivate) {
        const existingId = error.response.data.existing_id;
        const reactivateConfirmed = await showConfirmDialog({
          title: 'Inactive Department Found',
          text: error.response.data.error || 'An inactive department with this name already exists. Would you like to reactivate it?',
          confirmButtonText: 'Reactivate Department',
          confirmButtonColor: '#2e7d32',
        });
        if (reactivateConfirmed && existingId) {
          try {
            await departmentsAPI.update(existingId, { status: 1 });
            setDialogOpen(false);
            await showSuccessAlert('Department reactivated successfully');
            loadDepartments();
            return;
          } catch (reactivateErr) {
            setFormError(capitalizeError(reactivateErr.response?.data?.error || 'Failed to reactivate department'));
            return;
          }
        }
      }
      setFormError(capitalizeError((error.response && error.response.data && error.response.data.error) || 'Operation failed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingDepartment(null);
    setViewMode(false);
  };

  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.id === companyId);
    return company ? company.company_name : 'N/A';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'department_name', headerName: 'Department Name', width: 200 },
    {
      field: 'company_id',
      headerName: 'Company',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={getCompanyName(params.value)}
          size="small"
          variant="outlined"
          icon={<BusinessIcon />}
        />
      ),
    },
    { field: 'description', headerName: 'Description', width: 250 },
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

  if (!canView) {
    return (
      <Box p={3}>
        <Alert severity="error">
          You don't have permission to view departments.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Departments Management
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

      <Box sx={{ mb: 2 }}>
        <TextField
          label="Search departments"
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by department name..."
          sx={{ minWidth: 250 }}
        />
      </Box>

      {isPlatformAdmin && (
        <Box sx={{ mb: 2 }}>
          <SearchableSelect
            options={companies}
            getOptionLabel={(c) => c.company_name}
            getOptionValue={(c) => c.id}
            value={filterCompany}
            onChange={(e) => setFilterCompany(e.target.value)}
            label="Filter by Company"
            allOptionLabel="All Companies"
            allOptionValue=""
            sx={{ minWidth: 200, maxWidth: 300 }}
          />
        </Box>
      )}

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={departments}
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
        <DialogTitle>
          {viewMode ? 'View Department' : editingDepartment ? 'Edit Department' : 'Add New Department'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            
            <TextField
              autoFocus
              margin="dense"
              label="Department Name"
              fullWidth
              variant="outlined"
              value={formData.department_name}
              onChange={(e) => setFormData({ ...formData, department_name: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            {/* Company field — dropdown for Platform Admin, non-editable pre-selected box for Company Staff */}
            {!editingDepartment && !viewMode && (
              isPlatformAdmin ? (
                <Box sx={{ mb: 2 }}>
                  <SearchableSelect
                    options={companies}
                    getOptionLabel={(c) => c.company_name}
                    getOptionValue={(c) => c.id}
                    value={formData.company_id || ''}
                    onChange={(e) => setFormData({ ...formData, company_id: e.target.value })}
                    label="Company *"
                    placeholder="Select Company"
                    margin="dense"
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
                  helperText="Departments are automatically assigned to your company."
                  sx={{ mb: 2 }}
                />
              )
            )}

            {/* Edit/View mode — always show company as non-editable */}
            {(editingDepartment || viewMode) && (
              <TextField
                margin="dense"
                label="Company"
                fullWidth
                variant="outlined"
                value={
                  getCompanyName(formData.company_id) ||
                  editingDepartment?.company_name ||
                  'N/A'
                }
                disabled
                helperText={!viewMode ? "Company cannot be modified after creation." : ""}
                sx={{ mb: 2 }}
              />
            )}

            <TextField
              margin="dense"
              label="Description"
              fullWidth
              variant="outlined"
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            {/* Status Select Field */}
            {(editingDepartment || viewMode) && (
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
            <Button onClick={handleCloseDialog}>
              {viewMode ? 'Close' : 'Cancel'}
            </Button>
            {!viewMode && (
              <Button type="submit" variant="contained" disabled={isSubmitting}>
                {isSubmitting
                  ? 'Saving...'
                  : editingDepartment ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Departments;
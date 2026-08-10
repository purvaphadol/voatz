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
import { showSuccessAlert, showErrorAlert } from '../../utils/swal';
import { validateNonNumericText, capitalizeError } from '../../utils/validators';
import { useDeleteWithDependencies } from '../../hooks/useDeleteWithDependencies';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Department
      </Button>
    )}
  </GridToolbarContainer>
);

const Departments = () => {
  const { hasPermission } = usePermissions();
  const { user } = useAuth();
  
  const isPlatformAdmin = user?.is_administrator === true;
  const isCompanySuperAdmin = user?.roles?.some(
    r => r.role_name?.toLowerCase() === 'super admin'
  ) || false;

  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [formData, setFormData] = useState({
    department_name: '',
    description: '',
    company_id: '',
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
  }, [canView, debouncedSearch, filterCompany]);

  const loadDepartments = async () => {
    try {
      setLoading(true);
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (isPlatformAdmin && filterCompany) params.company_id = filterCompany;
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
        await departmentsAPI.update(editingDepartment.id, {
          department_name: formData.department_name,
          description: formData.description,
        });
        setSuccess('Department updated successfully');
      } else {
        const createPayload = {
          department_name: formData.department_name,
          description: formData.description,
        };
        if (isPlatformAdmin && formData.company_id) {
          createPayload.company_id = formData.company_id;
        }
        await departmentsAPI.create(createPayload);
        setSuccess('Department created successfully');
      }
      setDialogOpen(false);
      loadDepartments();
    } catch (error) {
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
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Company</InputLabel>
            <Select
              value={filterCompany}
              label="Filter by Company"
              onChange={(e) => setFilterCompany(e.target.value)}
            >
              <MenuItem value="">All Companies</MenuItem>
              {companies.map(c => (
                <MenuItem key={c.id} value={c.id}>
                  {c.company_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={departments}
          columns={columns}
          loading={loading}
          pageSize={10}
          rowsPerPageOptions={[5, 10, 25]}
          disableSelectionOnClick
          components={{
            Toolbar: () => <CustomToolbar onAdd={handleAdd} hasCreatePermission={canCreate} />,
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
                <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
                  <InputLabel id="dept-company-select-label">Company *</InputLabel>
                  <Select
                    labelId="dept-company-select-label"
                    value={formData.company_id || ''}
                    onChange={(e) => setFormData({
                      ...formData, company_id: e.target.value
                    })}
                    label="Company *"
                    required
                  >
                    <MenuItem value="" disabled hidden>
                      Select Company
                    </MenuItem>
                    {companies.map(c => (
                      <MenuItem key={c.id} value={c.id}>
                        {c.company_name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
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
            />
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
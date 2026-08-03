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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
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
} from '@mui/icons-material';
import { rolesAPI, departmentsAPI, companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Role
      </Button>
    )}
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

  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState('');
  const [selectedDepartmentFilter, setSelectedDepartmentFilter] = useState('');

  const [formData, setFormData] = useState({
    role_name: '',
    description: '',
    company_id: '',
    department_id: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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
  }, [canView, selectedCompanyFilter, selectedDepartmentFilter]);

  const loadRoles = async () => {
    try {
      setLoading(true);
      const params = {};
      if (selectedDepartmentFilter) params.department_id = selectedDepartmentFilter;
      if (isPlatformAdmin && selectedCompanyFilter) params.company_id = selectedCompanyFilter;
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
      setDepartments(response.data.data || []);
    } catch (error) {
      console.error('Error loading departments:', error);
    }
  };

  const handleAdd = () => {
    setEditingRole(null);
    setFormData({
      role_name: '',
      description: '',
      company_id: '',
      department_id: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (role) => {
    setEditingRole(role);
    const roleCompId = role.company_id || '';
    setFormData({
      role_name: role.role_name,
      description: role.description || '',
      company_id: roleCompId,
      department_id: role.department_id || '',
    });
    if (isPlatformAdmin && roleCompId) {
      loadDepartments(roleCompId);
    }
    setDialogOpen(true);
  };

  const handleDelete = async (roleId) => {
    if (window.confirm('Are you sure you want to delete this role?')) {
      try {
        await rolesAPI.delete(roleId);
        setSuccess('Role deleted successfully');
        loadRoles();
      } catch (error) {
        setError(
          (error.response && error.response.data && error.response.data.error)
          || 'Failed to delete role'
        );
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (isPlatformAdmin && !editingRole && !formData.company_id) {
      setError('Please select a company');
      return;
    }

    if (!formData.department_id) {
      setError('Please select a department');
      return;
    }

    try {
      const payload = {
        role_name: formData.role_name,
        description: formData.description,
        department_id: formData.department_id,
      };
      if (isPlatformAdmin && formData.company_id) {
        payload.company_id = formData.company_id;
      }

      if (editingRole) {
        await rolesAPI.update(editingRole.id, payload);
        setSuccess('Role updated successfully');
      } else {
        await rolesAPI.create(payload);
        setSuccess('Role created successfully');
      }
      setDialogOpen(false);
      loadRoles();
    } catch (error) {
      setError((error.response && error.response.data && error.response.data.error) || 'Operation failed');
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
      width: 130,
      getActions: (params) => {
        const actions = [];
        
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
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Company</InputLabel>
            <Select
              value={selectedCompanyFilter}
              label="Filter by Company"
              onChange={(e) => {
                const compId = e.target.value;
                setSelectedCompanyFilter(compId);
                setSelectedDepartmentFilter('');
                loadDepartments(compId);
              }}
            >
              <MenuItem value="">All Companies</MenuItem>
              {companies.map((comp) => (
                <MenuItem key={comp.id} value={comp.id}>
                  {comp.company_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Department</InputLabel>
          <Select
            value={selectedDepartmentFilter}
            label="Filter by Department"
            onChange={(e) => setSelectedDepartmentFilter(e.target.value)}
          >
            <MenuItem value="">All Departments</MenuItem>
            {departments.map((dept) => (
              <MenuItem key={dept.id} value={dept.id}>
                {dept.department_name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={roles}
          columns={columns}
          pageSize={10}
          rowsPerPageOptions={[5, 10, 25]}
          disableSelectionOnClick
          loading={loading}
          components={{
            Toolbar: CustomToolbar,
          }}
          componentsProps={{
            toolbar: {
              onAdd: handleAdd,
              hasCreatePermission: canCreate,
            },
          }}
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {editingRole ? 'Edit Role' : 'Add New Role'}
          </DialogTitle>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

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
              sx={{ mb: 2 }}
            />
            
            {/* 1. Company Field FIRST */}
            {!editingRole ? (
              isPlatformAdmin ? (
                <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
                  <InputLabel>Company *</InputLabel>
                  <Select
                    value={formData.company_id}
                    label="Company *"
                    onChange={(e) => {
                      const selectedCompId = e.target.value;
                      setFormData({ ...formData, company_id: selectedCompId, department_id: '' });
                      if (selectedCompId) {
                        loadDepartments(selectedCompId);
                      }
                    }}
                    required
                  >
                    <MenuItem value="">
                      <em>Select Company</em>
                    </MenuItem>
                    {companies.map((comp) => (
                      <MenuItem key={comp.id} value={comp.id}>
                        {comp.company_name}
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
                    'Your Company'
                  }
                  disabled
                  helperText="Roles are automatically assigned to your company."
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
                helperText="Company cannot be modified after creation."
                sx={{ mb: 2 }}
              />
            )}

            {/* 2. Department Field SECOND (Dynamic dependent dropdown) */}
            <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
              <InputLabel>Department *</InputLabel>
              <Select
                value={formData.department_id}
                label="Department *"
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                required
                disabled={isPlatformAdmin && !formData.company_id && !editingRole}
              >
                <MenuItem value="">
                  <em>{isPlatformAdmin && !formData.company_id && !editingRole ? 'Select Company First' : 'Select Department'}</em>
                </MenuItem>
                {departments.map((dept) => (
                  <MenuItem key={dept.id} value={dept.id}>
                    {dept.department_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
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
              sx={{ mb: 2 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {editingRole ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Roles; 
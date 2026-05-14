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
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [formData, setFormData] = useState({
    department_name: '',
    company_id: '',
    description: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Departments', 'view');
  const canCreate = hasPermission('Departments', 'create');
  const canUpdate = hasPermission('Departments', 'update');
  const canDelete = hasPermission('Departments', 'delete');

  useEffect(() => {
    if (canView) {
      loadDepartments();
      loadCompanies();
    }
  }, [canView]);

  const loadDepartments = async () => {
    try {
      setLoading(true);
      const response = await departmentsAPI.getAll();
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
      setCompanies(response.data.data || []);
    } catch (error) {
      console.error('Error loading companies:', error);
    }
  };

  const handleAdd = () => {
    setEditingDepartment(null);
    setViewMode(false);
    setFormData({
      department_name: '',
      company_id: '',
      description: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (department) => {
    setEditingDepartment(department);
    setViewMode(false);
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
    setFormData({
      department_name: department.department_name,
      company_id: department.company_id || '',
      description: department.description || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (departmentId) => {
    if (window.confirm('Are you sure you want to delete this department?')) {
      try {
        await departmentsAPI.delete(departmentId);
        setSuccess('Department deleted successfully');
        loadDepartments();
      } catch (error) {
        setError('Failed to delete department');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.department_name.trim()) {
      setError('Department name is required');
      return;
    }

    try {
      if (editingDepartment) {
        await departmentsAPI.update(editingDepartment.id, formData);
        setSuccess('Department updated successfully');
      } else {
        await departmentsAPI.create(formData);
        setSuccess('Department created successfully');
      }
      setDialogOpen(false);
      loadDepartments();
    } catch (error) {
      setError((error.response && error.response.data && error.response.data.error) || 'Operation failed');
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setError('');
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

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={departments}
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

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {viewMode ? 'View Department' : editingDepartment ? 'Edit Department' : 'Add New Department'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            
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

            <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
              <InputLabel>Company</InputLabel>
              <Select
                value={formData.company_id}
                onChange={(e) => setFormData({ ...formData, company_id: e.target.value })}
                label="Company"
                disabled={viewMode}
              >
                <MenuItem value="">
                  <em>Select Company</em>
                </MenuItem>
                {companies.map((company) => (
                  <MenuItem key={company.id} value={company.id}>
                    {company.company_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

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
              <Button type="submit" variant="contained">
                {editingDepartment ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Departments; 
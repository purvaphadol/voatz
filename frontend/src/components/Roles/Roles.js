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
import { rolesAPI, departmentsAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';

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
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [formData, setFormData] = useState({
    role_name: '',
    description: '',
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
      loadDepartments();
    }
  }, [canView]);

  useEffect(() => {
    if (canView) {
      loadRoles();
    }
  }, [canView, selectedDepartment]);

  const loadRoles = async () => {
    try {
      setLoading(true);
      const params = selectedDepartment ? { department_id: selectedDepartment } : {};
      const response = await rolesAPI.getAll(params);
      setRoles(response.data.data || []);
    } catch (error) {
      console.error('Error loading roles:', error);
      setError('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  const loadDepartments = async () => {
    try {
      const response = await departmentsAPI.getAll();
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
      department_id: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (role) => {
    setEditingRole(role);
    setFormData({
      role_name: role.role_name,
      description: role.description || '',
      department_id: role.department_id || '',
    });
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

    try {
      if (editingRole) {
        await rolesAPI.update(editingRole.id, formData);
        setSuccess('Role updated successfully');
      } else {
        await rolesAPI.create(formData);
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
    { field: 'description', headerName: 'Description', width: 250 },
    { 
      field: 'department_name', 
      headerName: 'Department', 
      width: 200,
      renderCell: (params) => (
        <Chip 
          icon={<BusinessIcon />}
          label={params.value}
          variant="outlined"
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

      {/* Department Filter */}
      <Box sx={{ mb: 2 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Department</InputLabel>
          <Select
            value={selectedDepartment}
            label="Filter by Department"
            onChange={(e) => {
              setSelectedDepartment(e.target.value);
            }}
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
          checkboxSelection
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
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Department *</InputLabel>
              <Select
                value={formData.department_id}
                label="Department *"
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                required
              >
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
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
  CircularProgress,
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
} from '@mui/icons-material';
import { usersAPI, departmentsAPI, companiesAPI, handleApiError } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { useAuth } from '../../contexts/AuthContext';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd} sx={{ ml: 2 }}>
        Add User
      </Button>
    )}
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
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    department_id: '',
    company_id: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
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

  useEffect(() => {
    loadUsers();
  }, [page, pageSize, debouncedSearch, selectedCompanyFilter, selectedDepartmentFilter]);

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
      setDepartments(response.data.data || []);
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

  const handleAdd = () => {
    setEditingUser(null);
    setFormData({
      name: '',
      email: '',
      password: '',
      department_id: '',
      company_id: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    const compId = user.company_id || '';
    setFormData({
      name: user.name,
      email: user.email,
      password: '',
      company_id: compId,
      department_id: user.department_id || '',
    });
    if (isPlatformAdmin && compId) {
      loadDepartments(compId);
    }
    setDialogOpen(true);
  };

  const handleDelete = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await usersAPI.delete(userId);
        setSuccess('User deleted successfully');
        loadUsers();
      } catch (error) {
        setError(handleApiError(error));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const cleanedData = {
      ...formData,
      name: formData.name.trim(),
      email: formData.email.trim().toLowerCase(),
    };

    if (isPlatformAdmin && !editingUser && !formData.company_id) {
      setError('Please select a company');
      return;
    }

    if (!cleanedData.name || !cleanedData.email) {
      setError('Name and email cannot be empty');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanedData.email)) {
      setError('Invalid email address format');
      return;
    }
    
    if (!editingUser && !cleanedData.password) {
      setError('Password is required');
      return;
    }
    
    if (cleanedData.password) {
      if (cleanedData.password.length < 8) {
        setError('Password must be at least 8 characters long');
        return;
      }
      if (!/[a-zA-Z]/.test(cleanedData.password)) {
        setError('Password must contain at least one letter');
        return;
      }
      if (!/[0-9]/.test(cleanedData.password)) {
        setError('Password must contain at least one number');
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
        await usersAPI.update(editingUser.id, payload);
        setSuccess('User updated successfully');
      } else {
        await usersAPI.create(payload);
        setSuccess('User created successfully');
      }
      setDialogOpen(false);
      loadUsers();
    } catch (error) {
      setError(handleApiError(error));
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
      width: 180,
      renderCell: (params) => (
        <Chip
          label={params.row.department_name || getDepartmentName(params.value)}
          size="small"
          variant="outlined"
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
          <TextField
            label="Filter by Company"
            select
            size="small"
            value={selectedCompanyFilter}
            onChange={(e) => {
              const compId = e.target.value;
              setSelectedCompanyFilter(compId);
              setSelectedDepartmentFilter('');
              loadDepartments(compId);
            }}
            SelectProps={{ native: true }}
            sx={{ minWidth: 200 }}
          >
            <option value="">All Companies</option>
            {companies.map((comp) => (
              <option key={comp.id} value={comp.id}>
                {comp.company_name}
              </option>
            ))}
          </TextField>
        )}

        <TextField
          label="Filter by Department"
          select
          size="small"
          value={selectedDepartmentFilter}
          onChange={(e) => setSelectedDepartmentFilter(e.target.value)}
          SelectProps={{ native: true }}
          sx={{ minWidth: 200 }}
        >
          <option value="">All Departments</option>
          {departments.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.department_name}
            </option>
          ))}
        </TextField>
      </Box>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={users}
          columns={columns}
          paginationMode="server"
          rowCount={totalRows}
          page={page}
          onPageChange={(newPage) => setPage(newPage)}
          pageSize={pageSize}
          onPageSizeChange={(newPageSize) => setPageSize(newPageSize)}
          rowsPerPageOptions={[5, 10, 25, 50, 100]}
          disableSelectionOnClick
          loading={loading}
          components={{
            Toolbar: () => <CustomToolbar onAdd={handleAdd} hasCreatePermission={canCreate} />
          }}
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {editingUser ? 'Edit User' : 'Add New User'}
          </DialogTitle>
          <DialogContent>
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
              sx={{ mb: 2 }}
            />
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

            {/* 1. Company Field FIRST */}
            {!editingUser ? (
              isPlatformAdmin ? (
                <TextField
                  margin="dense"
                  label="Company *"
                  select
                  fullWidth
                  variant="outlined"
                  value={formData.company_id}
                  onChange={(e) => {
                    const selectedCompanyId = e.target.value;
                    setFormData({ ...formData, company_id: selectedCompanyId, department_id: '' });
                    if (selectedCompanyId) {
                      loadDepartments(selectedCompanyId);
                    }
                  }}
                  SelectProps={{
                    native: true,
                  }}
                  sx={{ mb: 2 }}
                >
                  <option value="">Select Company</option>
                  {companies.map((comp) => (
                    <option key={comp.id} value={comp.id}>
                      {comp.company_name}
                    </option>
                  ))}
                </TextField>
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
                  helperText="Users are automatically assigned to your company."
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
                helperText="Company cannot be modified after creation."
                sx={{ mb: 2 }}
              />
            )}

            {/* 2. Department Field SECOND (Dynamic dependent dropdown) */}
            <TextField
              margin="dense"
              label="Department"
              select
              fullWidth
              variant="outlined"
              value={formData.department_id}
              onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
              disabled={isPlatformAdmin && !formData.company_id && !editingUser}
              SelectProps={{
                native: true,
              }}
              sx={{ mb: 2 }}
            >
              <option value="">
                {isPlatformAdmin && !formData.company_id && !editingUser ? 'Select Company First' : 'Select Department'}
              </option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.department_name}
                </option>
              ))}
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)} disabled={isSubmitting}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? <CircularProgress size={24} /> : (editingUser ? 'Update' : 'Create')}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};


export default Users; 
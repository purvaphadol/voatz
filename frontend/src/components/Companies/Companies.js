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
import { companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { showDeleteConfirm, showSuccessAlert, showErrorAlert } from '../../utils/swal';
import { validateNonNumericText, validateEmail, validatePhone, validateUrl, capitalizeError } from '../../utils/validators';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Company
      </Button>
    )}
  </GridToolbarContainer>
);

const Companies = () => {
  const { hasPermission } = usePermissions();
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [formData, setFormData] = useState({
    company_name: '',
    address: '',
    phone: '',
    email: '',
    website: '',
    description: '',
  });
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Companies', 'view');
  const canCreate = hasPermission('Companies', 'create');
  const canUpdate = hasPermission('Companies', 'update');
  const canDelete = hasPermission('Companies', 'delete');

  useEffect(() => {
    if (canView) {
      loadCompanies();
    }
  }, [canView]);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const response = await companiesAPI.getAll();
      setCompanies(response.data.data || []);
    } catch (error) {
      console.error('Error loading companies:', error);
      setError('Failed to load companies');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingCompany(null);
    setViewMode(false);
    setFormError('');
    setFormData({
      company_name: '',
      address: '',
      phone: '',
      email: '',
      website: '',
      description: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (company) => {
    setEditingCompany(company);
    setViewMode(false);
    setFormError('');
    setFormData({
      company_name: company.company_name,
      address: company.address || '',
      phone: company.phone || '',
      email: company.email || '',
      website: company.website || '',
      description: company.description || '',
    });
    setDialogOpen(true);
  };

  const handleView = (company) => {
    setEditingCompany(company);
    setViewMode(true);
    setFormError('');
    setFormData({
      company_name: company.company_name,
      address: company.address || '',
      phone: company.phone || '',
      email: company.email || '',
      website: company.website || '',
      description: company.description || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (companyId) => {
    const confirmed = await showDeleteConfirm('this company (and all related user data)');
    if (confirmed) {
      try {
        await companiesAPI.delete(companyId);
        await showSuccessAlert('Company deleted successfully');
        loadCompanies();
      } catch (error) {
        const errMsg = (error.response && error.response.data && error.response.data.error) || 'Failed to delete company';
        showErrorAlert(capitalizeError(errMsg));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const nameErr = validateNonNumericText(formData.company_name, 'Company name', 2, 100);
    if (nameErr) {
      setFormError(capitalizeError(nameErr));
      return;
    }

    if (formData.email) {
      const emailErr = validateEmail(formData.email);
      if (emailErr) {
        setFormError(capitalizeError(emailErr));
        return;
      }
    }

    if (formData.phone) {
      const phoneErr = validatePhone(formData.phone);
      if (phoneErr) {
        setFormError(capitalizeError(phoneErr));
        return;
      }
    }

    if (formData.website) {
      const urlErr = validateUrl(formData.website);
      if (urlErr) {
        setFormError(capitalizeError(urlErr));
        return;
      }
    }

    try {
      if (editingCompany) {
        await companiesAPI.update(editingCompany.id, formData);
        setDialogOpen(false);
        loadCompanies();
        await showSuccessAlert('Company updated successfully');
      } else {
        await companiesAPI.create(formData);
        setDialogOpen(false);
        loadCompanies();
        await showSuccessAlert('Company created successfully');
      }
    } catch (error) {
      const errMsg = (error.response && error.response.data && error.response.data.error) || 'Operation failed';
      setFormError(capitalizeError(errMsg));
      showErrorAlert(capitalizeError(errMsg));
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingCompany(null);
    setViewMode(false);
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'company_name',
      headerName: 'Company Name',
      width: 200,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          <BusinessIcon sx={{ mr: 1, color: 'primary.main' }} />
          {params.value}
        </Box>
      ),
    },
    { field: 'email', headerName: 'Email', width: 200 },
    { field: 'phone', headerName: 'Phone', width: 150 },
    { field: 'website', headerName: 'Website', width: 200 },
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
          You don't have permission to view companies.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Companies Management
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
          rows={companies}
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

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {viewMode ? 'View Company' : editingCompany ? 'Edit Company' : 'Add New Company'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}

            <TextField
              autoFocus
              margin="dense"
              label="Company Name"
              fullWidth
              variant="outlined"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            <TextField
              margin="dense"
              label="Email"
              fullWidth
              variant="outlined"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            <TextField
              margin="dense"
              label="Phone"
              fullWidth
              variant="outlined"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            <TextField
              margin="dense"
              label="Website"
              fullWidth
              variant="outlined"
              value={formData.website}
              onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

            <TextField
              margin="dense"
              label="Address"
              fullWidth
              variant="outlined"
              multiline
              rows={2}
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
            />

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
                {editingCompany ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Companies; 
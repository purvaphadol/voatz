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
import { companiesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';
import { showSuccessAlert, showErrorAlert, showConfirmDialog } from '../../utils/swal';
import { validateNonNumericText, validateEmail, validatePhone, validateUrl, capitalizeError } from '../../utils/validators';
import { useDeleteWithDependencies } from '../../hooks/useDeleteWithDependencies';
import SearchableSelect from '../Common/SearchableSelect';

const CustomToolbar = ({ onAdd, hasCreatePermission, showInactive, setShowInactive }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Company
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

const Companies = () => {
  const { hasPermission } = usePermissions();
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [viewMode, setViewMode] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [formData, setFormData] = useState({
    company_name: '',
    address: '',
    phone: '',
    email: '',
    website: '',
    description: '',
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

  const canView = hasPermission('Companies', 'view');
  const canCreate = hasPermission('Companies', 'create');
  const canUpdate = hasPermission('Companies', 'update');
  const canDelete = hasPermission('Companies', 'delete');

  useEffect(() => {
    if (canView) {
      loadCompanies();
    }
  }, [canView, showInactive]);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const params = {};
      if (showInactive) params.show_inactive = 'true';
      const response = await companiesAPI.getAll(params);
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
      status: 1,
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
      status: company.status ?? 1,
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
      status: company.status ?? 1,
    });
    setDialogOpen(true);
  };

  const handleDelete = useDeleteWithDependencies({
    deleteApi: companiesAPI.delete,
    itemLabel: 'this company',
    successMsg: 'Company deleted successfully',
    forceSuccessMsg: 'Company and all related data force-deleted successfully',
    forceConfirmMessage: 'Are you sure you want to delete this company (and all related user, department, role, election, and voter data)?',
    onSuccess: loadCompanies,
  });

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
      setIsSubmitting(true);
      if (editingCompany) {
        // Status transition cascade warning
        if (editingCompany.status !== formData.status) {
          if (formData.status === 0) {
            try {
              const depRes = await companiesAPI.getStatusDependents(editingCompany.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Set Company Inactive?',
                  text: `Setting this company inactive will cascade-pause ${depCount} related departments, roles, users, elections, ballots, and candidates to Inactive. Do you wish to proceed?`,
                  confirmButtonText: 'Yes, set inactive',
                  confirmButtonColor: '#ed6c02',
                });
                if (!confirmed) {
                  setIsSubmitting(false);
                  return;
                }
              }
            } catch (err) {
              console.warn('Could not check status dependents:', err);
            }
          } else if (formData.status === 1) {
            try {
              const depRes = await companiesAPI.getStatusDependents(editingCompany.id);
              const depCount = depRes.data?.data?.total_count || 0;
              if (depCount > 0) {
                const confirmed = await showConfirmDialog({
                  title: 'Reactivate Company?',
                  text: `Reactivating this company will reactivate linked child entities that were paused with it. Do you wish to proceed?`,
                  confirmButtonText: 'Yes, reactivate',
                  confirmButtonColor: '#2e7d32',
                });
                if (!confirmed) {
                  setIsSubmitting(false);
                  return;
                }
              }
            } catch (err) {
              console.warn('Could not check status dependents:', err);
            }
          }
        }

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
      if (error.response && error.response.status === 409 && error.response.data?.can_reactivate) {
        const existingId = error.response.data.existing_id;
        const reactivateConfirmed = await showConfirmDialog({
          title: 'Inactive Company Found',
          text: error.response.data.error || 'An inactive company with this name already exists. Would you like to reactivate it?',
          confirmButtonText: 'Reactivate Company',
          confirmButtonColor: '#2e7d32',
        });
        if (reactivateConfirmed && existingId) {
          try {
            await companiesAPI.update(existingId, { status: 1 });
            setDialogOpen(false);
            await showSuccessAlert('Company reactivated successfully');
            loadCompanies();
            return;
          } catch (reactivateErr) {
            setFormError(capitalizeError(reactivateErr.response?.data?.error || 'Failed to reactivate company'));
            return;
          }
        }
      }
      const errMsg = (error.response && error.response.data && error.response.data.error) || 'Operation failed';
      setFormError(capitalizeError(errMsg));
      showErrorAlert(capitalizeError(errMsg));
    } finally {
      setIsSubmitting(false);
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
    { field: 'website', headerName: 'Website', width: 180 },
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
      width: 130,
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

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {viewMode ? 'View Company' : editingCompany ? 'Edit Company' : 'Add New Company'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent ref={dialogContentRef}>
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
              sx={{ mb: 2 }}
            />

            {(editingCompany || viewMode) && (
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
                {isSubmitting ? 'Saving...' : editingCompany ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default Companies; 
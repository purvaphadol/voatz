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
  Switch,
  FormControlLabel,
  IconButton,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
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
  AccountTree as ModuleIcon,
  Settings as SettingsIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as ActionIcon,
  Restore as RestoreIcon,
} from '@mui/icons-material';
import { modulesAPI, moduleActionsAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Add Module
      </Button>
    )}
  </GridToolbarContainer>
);

const Modules = () => {
  const { hasPermission } = usePermissions();
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionsDialogOpen, setActionsDialogOpen] = useState(false);
  const [editingModule, setEditingModule] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);
  const [moduleActions, setModuleActions] = useState([]);
  const [viewMode, setViewMode] = useState(false);
  const [formData, setFormData] = useState({
    module_name: '',
    route_name: '',
    description: '',
    icon: '',
    status: 1,
    order_index: 0,
  });
  const [actionFormData, setActionFormData] = useState({
    action_name: '',
    action_url: '',
    status: true,
  });
  const [editingAction, setEditingAction] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Modules', 'view');
  const canCreate = hasPermission('Modules', 'create');
  const canUpdate = hasPermission('Modules', 'update');
  const canDelete = hasPermission('Modules', 'delete');

  useEffect(() => {
    if (canView) {
      loadModules();
    }
  }, [canView]);

  const loadModules = async () => {
    try {
      setLoading(true);
      const response = await modulesAPI.getAll({ per_page: 200 });
      setModules(response.data.data || []);
    } catch (error) {
      console.error('Error loading modules:', error);
      setError('Failed to load modules');
    } finally {
      setLoading(false);
    }
  };

  const loadModuleActions = async (moduleId) => {
    try {
      const response = await moduleActionsAPI.getModuleActions(moduleId);
      setModuleActions(response.data.data || []);
    } catch (error) {
      console.error('Error loading module actions:', error);
      setError('Failed to load module actions');
    }
  };

  const handleAdd = () => {
    setEditingModule(null);
    setViewMode(false);
    setFormData({
      module_name: '',
      route_name: '',
      description: '',
      icon: '',
      status: 1,
      order_index: 0,
    });
    setDialogOpen(true);
  };

  const handleEdit = (module) => {
    setEditingModule(module);
    setViewMode(false);
    setFormData({
      module_name: module.module_name,
      route_name: module.route_name || '',
      description: module.description || '',
      icon: module.icon || '',
      status: module.status,
      order_index: module.order_index || 0,
    });
    setDialogOpen(true);
  };

  const handleView = (module) => {
    setEditingModule(module);
    setViewMode(true);
    setFormData({
      module_name: module.module_name,
      route_name: module.route_name || '',
      description: module.description || '',
      icon: module.icon || '',
      status: module.status,
      order_index: module.order_index || 0,
    });
    setDialogOpen(true);
  };

  const handleManageActions = (module) => {
    setSelectedModule(module);
    loadModuleActions(module.id);
    setActionsDialogOpen(true);
  };

  const handleDelete = async (moduleId) => {
    if (window.confirm('Are you sure you want to delete this module? This will affect all related permissions.')) {
      try {
        await modulesAPI.delete(moduleId);
        setSuccess('Module deleted successfully');
        loadModules();
      } catch (error) {
        setError(error.response?.data?.error || 'Failed to delete module');
      }
    }
  };

  const handleReactivate = async (moduleId) => {
    try {
      await modulesAPI.updateStatus(moduleId, { status: 1 });
      setSuccess('Module reactivated successfully');
      loadModules();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to reactivate module');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.module_name.trim()) {
      setError('Module name is required');
      return;
    }

    try {
      if (editingModule) {
        const updateData = {};
        if (formData.module_name !== editingModule.module_name) updateData.module_name = formData.module_name;
        if (formData.route_name !== (editingModule.route_name || '')) updateData.route_name = formData.route_name;
        if (formData.description !== (editingModule.description || '')) updateData.description = formData.description;
        if (formData.icon !== (editingModule.icon || '')) updateData.icon = formData.icon;
        if (formData.order_index !== (editingModule.order_index || 0)) updateData.order_index = formData.order_index;
        if (formData.status !== editingModule.status) updateData.status = formData.status;

        await modulesAPI.update(editingModule.id, updateData);
        setSuccess('Module updated successfully');
      } else {
        const submitData = {
          ...formData
        };
        const response = await modulesAPI.create(submitData);
        setSuccess('Module created successfully');
        
        // If module was created successfully, optionally create default actions
        if (response.data && response.data.module_id) {
          try {
            await moduleActionsAPI.createBulkActions(response.data.module_id, [
              { action_name: 'view', action_url: '/view' },
              { action_name: 'create', action_url: '/create' },
              { action_name: 'update', action_url: '/update' },
              { action_name: 'delete', action_url: '/delete' },
            ]);
          } catch (actionError) {
            console.warn('Failed to create default actions:', actionError);
          }
        }
      }
      setDialogOpen(false);
      loadModules();
    } catch (error) {
      setError((error.response && error.response.data && error.response.data.error) || 'Operation failed');
    }
  };

  const handleActionSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!actionFormData.action_name.trim() || !actionFormData.action_url.trim()) {
      setError('Action name and URL are required');
      return;
    }

    try {
      if (editingAction) {
        await moduleActionsAPI.updateAction(editingAction.id, {
          action_name: actionFormData.action_name,
          action_url: actionFormData.action_url,
          status: actionFormData.status ? 1 : 0,
        });
        setSuccess('Action updated successfully');
      } else {
        await moduleActionsAPI.createAction(selectedModule.id, {
          action_name: actionFormData.action_name,
          action_url: actionFormData.action_url,
          status: actionFormData.status ? 1 : 0,
        });
        setSuccess('Action created successfully');
      }
      
      setActionFormData({ action_name: '', action_url: '', status: true });
      setEditingAction(null);
      loadModuleActions(selectedModule.id);
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save action');
    }
  };

  const handleEditAction = (action) => {
    setEditingAction(action);
    setActionFormData({
      action_name: action.action_name,
      action_url: action.action_url,
      status: action.status === 1,
    });
  };

  const handleDeleteAction = async (actionId) => {
    if (window.confirm('Are you sure you want to delete this action? This may affect permissions.')) {
      try {
        await moduleActionsAPI.deleteAction(actionId);
        setSuccess('Action deleted successfully');
        loadModuleActions(selectedModule.id);
      } catch (error) {
        setError(error.response?.data?.error || 'Failed to delete action');
      }
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setError('');
    setEditingModule(null);
    setViewMode(false);
  };

  const handleCloseActionsDialog = () => {
    setActionsDialogOpen(false);
    setSelectedModule(null);
    setModuleActions([]);
    setActionFormData({ action_name: '', action_url: '', status: true });
    setEditingAction(null);
    setError('');
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'module_name',
      headerName: 'Module Name',
      width: 200,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          <ModuleIcon sx={{ mr: 1, color: 'primary.main' }} />
          {params.value}
        </Box>
      ),
    },
    {
      field: 'display_route',
      headerName: 'Route',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={`/${params.value}`}
          size="small"
          color="primary"
          variant="outlined"
        />
      ),
    },
    { 
      field: 'order_index', 
      headerName: 'Order', 
      width: 80,
      renderCell: (params) => (
        <Chip
          label={params.value || 0}
          size="small"
          color="secondary"
          variant="outlined"
        />
      ),
    },
    { field: 'description', headerName: 'Description', width: 250 },
    { field: 'icon', headerName: 'Icon', width: 100 },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const status = params.value;
        if (status === 1) return <Chip label="Active" color="success" size="small" />;
        if (status === 9) return <Chip label="Inactive" color="warning" size="small" />;
        return <Chip label="Deleted" color="error" size="small" />;
      },
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
      width: 200,
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
          
          actions.push(
            <GridActionsCellItem
              icon={<SettingsIcon />}
              label="Manage Actions"
              onClick={() => handleManageActions(params.row)}
            />
          );

          if (params.row.status === 9) {
            actions.push(
              <GridActionsCellItem
                icon={<RestoreIcon />}
                label="Reactivate"
                onClick={() => handleReactivate(params.row.id)}
              />
            );
          }
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
          You don't have permission to view modules.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Modules Management
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
          rows={modules}
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

      {/* Module Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {viewMode ? 'View Module' : editingModule ? 'Edit Module' : 'Add New Module'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            
            <TextField
              autoFocus
              margin="dense"
              label="Module Name"
              fullWidth
              variant="outlined"
              value={formData.module_name}
              onChange={(e) => setFormData({ ...formData, module_name: e.target.value })}
              required
              disabled={viewMode}
              sx={{ mb: 2 }}
              helperText="Enter a unique module name (e.g., Users, Roles, Settings)"
            />

            <TextField
              margin="dense"
              label="Route Name (Optional)"
              fullWidth
              variant="outlined"
              value={formData.route_name}
              onChange={(e) => setFormData({ ...formData, route_name: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
              helperText="Custom route name (e.g., 'testing' for /testing). Leave empty to use module name."
            />

            <TextField
              margin="dense"
              label="Icon"
              fullWidth
              variant="outlined"
              value={formData.icon}
              onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
              disabled={viewMode}
              sx={{ mb: 2 }}
              helperText="Icon name for UI display (e.g., users, settings, dashboard)"
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
              helperText="Brief description of what this module manages"
            />

            <TextField
              margin="dense"
              label="Order Index"
              type="number"
              fullWidth
              variant="outlined"
              value={formData.order_index}
              onChange={(e) => setFormData({ ...formData, order_index: parseInt(e.target.value) || 0 })}
              disabled={viewMode}
              sx={{ mb: 2 }}
              helperText="Order for sidebar display (lower numbers appear first)"
              inputProps={{ min: 0, max: 999 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={formData.status === 1}
                  onChange={(e) => setFormData({ ...formData, status: e.target.checked ? 1 : 9 })}
                  disabled={viewMode}
                />
              }
              label="Active Status"
              sx={{ mt: 1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>
              {viewMode ? 'Close' : 'Cancel'}
            </Button>
            {!viewMode && (
              <Button type="submit" variant="contained">
                {editingModule ? 'Update' : 'Create'}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>

      {/* Module Actions Management Dialog */}
      <Dialog 
        open={actionsDialogOpen} 
        onClose={handleCloseActionsDialog} 
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <SettingsIcon sx={{ mr: 1 }} />
            Manage Actions for "{selectedModule?.module_name}"
          </Box>
        </DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
          
          <Grid container spacing={3}>
            {/* Add/Edit Action Form */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {editingAction ? 'Edit Action' : 'Add New Action'}
                  </Typography>
                  
                  <form onSubmit={handleActionSubmit}>
                    <TextField
                      margin="dense"
                      label="Action Name"
                      fullWidth
                      variant="outlined"
                      value={actionFormData.action_name}
                      onChange={(e) => setActionFormData({ 
                        ...actionFormData, 
                        action_name: e.target.value 
                      })}
                      required
                      sx={{ mb: 2 }}
                      helperText="e.g., view, create, update, delete, export, import"
                    />
                    
                    <TextField
                      margin="dense"
                      label="Action URL"
                      fullWidth
                      variant="outlined"
                      value={actionFormData.action_url}
                      onChange={(e) => setActionFormData({ 
                        ...actionFormData, 
                        action_url: e.target.value 
                      })}
                      required
                      sx={{ mb: 2 }}
                      helperText="e.g., /view, /create, /export"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={actionFormData.status}
                          onChange={(e) => setActionFormData({ 
                            ...actionFormData, 
                            status: e.target.checked 
                          })}
                        />
                      }
                      label="Active"
                      sx={{ mb: 2 }}
                    />
                    
                    <Box>
                      <Button 
                        type="submit" 
                        variant="contained" 
                        startIcon={<AddIcon />}
                        sx={{ mr: 1 }}
                      >
                        {editingAction ? 'Update' : 'Add'} Action
                      </Button>
                      
                      {editingAction && (
                        <Button 
                          onClick={() => {
                            setEditingAction(null);
                            setActionFormData({ action_name: '', action_url: '', status: true });
                          }}
                        >
                          Cancel
                        </Button>
                      )}
                    </Box>
                  </form>
                </CardContent>
              </Card>
            </Grid>
            
            {/* Existing Actions List */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Current Actions ({moduleActions.length})
                  </Typography>
                  
                  {moduleActions.length === 0 ? (
                    <Typography color="text.secondary">
                      No actions defined for this module
                    </Typography>
                  ) : (
                    <List dense>
                      {moduleActions.map((action, index) => (
                        <React.Fragment key={action.id}>
                          <ListItem>
                            <ListItemText
                              primary={
                                <Box display="flex" alignItems="center">
                                  <ActionIcon sx={{ mr: 1, fontSize: 16 }} />
                                  {action.action_name}
                                  <Chip
                                    label={action.status === 1 ? 'Active' : 'Inactive'}
                                    size="small"
                                    color={action.status === 1 ? 'success' : 'default'}
                                    sx={{ ml: 1 }}
                                  />
                                </Box>
                              }
                              secondary={`URL: ${action.action_url}`}
                            />
                            <ListItemSecondaryAction>
                              <IconButton
                                edge="end"
                                size="small"
                                onClick={() => handleEditAction(action)}
                                sx={{ mr: 1 }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                edge="end"
                                size="small"
                                onClick={() => handleDeleteAction(action.id)}
                                color="error"
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </ListItemSecondaryAction>
                          </ListItem>
                          {index < moduleActions.length - 1 && <Divider />}
                        </React.Fragment>
                      ))}
                    </List>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseActionsDialog}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Modules; 
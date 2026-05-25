import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  Chip,
  Grid,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
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
  History as HistoryIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Person as PersonIcon,
  Computer as ComputerIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { auditAPI, usersAPI, modulesAPI } from '../../services/api';
import { usePermissions } from '../../contexts/PermissionContext';

const CustomToolbar = ({ onFilter, onExport }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    <Button startIcon={<FilterIcon />} onClick={onFilter}>
      Advanced Filter
    </Button>
    <Button startIcon={<DownloadIcon />} onClick={onExport}>
      Export Logs
    </Button>
  </GridToolbarContainer>
);

const AuditLogs = () => {
  const { hasPermission } = usePermissions();
  const [auditLogs, setAuditLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
  });
  const [filters, setFilters] = useState({
    user_id: '',
    action: '',
    module: '',
    success: '',
    start_date: '',
    end_date: '',
    ip_address: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modules, setModules] = useState([]);

  const canView = hasPermission('AuditLogs', 'view');

  useEffect(() => {
    if (canView) {
      loadAuditLogs();
      loadUsers();
      loadModules();
    }
  }, [canView, pagination.page, pagination.per_page]);

  const loadModules = async () => {
    try {
      const response = await modulesAPI.getAll();
      setModules(response.data.data || []);
    } catch (error) {
      console.error('Error loading modules:', error);
    }
  };

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        ...filters,
      };
      
      // Remove empty filters
      Object.keys(params).forEach(key => {
        if (params[key] === '') {
          delete params[key];
        }
      });

      const response = await auditAPI.getLogs(params);
      setAuditLogs(response.data.logs || []);
      setPagination(prev => ({
        ...prev,
        total: response.data.total || 0,
      }));
    } catch (error) {
      console.error('Error loading audit logs:', error);
      setError('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await usersAPI.getAll();
      setUsers(response.data.data || []);
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  const handleFilterApply = () => {
    setPagination(prev => ({ ...prev, page: 1 }));
    loadAuditLogs();
    setFilterDialogOpen(false);
  };

  const handleFilterReset = () => {
    setFilters({
      user_id: '',
      action: '',
      module: '',
      success: '',
      start_date: '',
      end_date: '',
      ip_address: '',
    });
    setPagination(prev => ({ ...prev, page: 1 }));
    loadAuditLogs();
  };

  const handleView = (log) => {
    setSelectedLog(log);
    setViewDialogOpen(true);
  };

  const handleExport = async () => {
    try {
      const params = { ...filters, export: true };
      const response = await auditAPI.exportLogs(params);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit_logs_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      setSuccess('Audit logs exported successfully');
    } catch (error) {
      setError('Failed to export audit logs');
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.name : 'Unknown User';
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return isNaN(date.getTime()) ? 'N/A' : date.toLocaleString();
  };

  const getActionColor = (action) => {
    const actionColors = {
      create: 'success',
      update: 'warning',
      delete: 'error',
      view: 'info',
      login: 'primary',
      logout: 'secondary',
    };
    return actionColors[action.toLowerCase()] || 'default';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'timestamp',
      headerName: 'Timestamp',
      width: 180,
      renderCell: (params) => formatTimestamp(params.value),
    },
    {
      field: 'user_id',
      headerName: 'User',
      width: 150,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          <PersonIcon sx={{ mr: 1, fontSize: 16 }} />
          {getUserName(params.value)}
        </Box>
      ),
    },
    {
      field: 'action',
      headerName: 'Action',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={getActionColor(params.value)}
        />
      ),
    },
    {
      field: 'module',
      headerName: 'Module',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          variant="outlined"
        />
      ),
    },
    { field: 'description', headerName: 'Description', width: 250 },
    {
      field: 'success',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          {params.value ? (
            <SuccessIcon sx={{ color: 'success.main', mr: 1, fontSize: 16 }} />
          ) : (
            <ErrorIcon sx={{ color: 'error.main', mr: 1, fontSize: 16 }} />
          )}
          {params.value ? 'Success' : 'Failed'}
        </Box>
      ),
    },
    {
      field: 'ip_address',
      headerName: 'IP Address',
      width: 120,
      renderCell: (params) => (
        <Box display="flex" alignItems="center">
          <ComputerIcon sx={{ mr: 1, fontSize: 16 }} />
          {params.value}
        </Box>
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<ViewIcon />}
          label="View Details"
          onClick={() => handleView(params.row)}
        />,
      ],
    },
  ];

  if (!canView) {
    return (
      <Box p={3}>
        <Alert severity="error">
          You don't have permission to view audit logs.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Audit Logs
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
          rows={auditLogs}
          columns={columns}
          loading={loading}
          paginationMode="server"
          page={pagination.page - 1}
          pageSize={pagination.per_page}
          rowCount={pagination.total}
          rowsPerPageOptions={[10, 25, 50]}
          onPageChange={(newPage) => setPagination(prev => ({ ...prev, page: newPage + 1 }))}
          onPageSizeChange={(newPageSize) => setPagination(prev => ({ ...prev, per_page: newPageSize }))}
          disableSelectionOnClick
          components={{
            Toolbar: () => (
              <CustomToolbar
                onFilter={() => setFilterDialogOpen(true)}
                onExport={handleExport}
              />
            ),
          }}
        />
      </Paper>

      {/* Filter Dialog */}
      <Dialog open={filterDialogOpen} onClose={() => setFilterDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <FilterIcon sx={{ mr: 1 }} />
            Advanced Filters
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>User</InputLabel>
                <Select
                  value={filters.user_id}
                  onChange={(e) => setFilters({ ...filters, user_id: e.target.value })}
                  label="User"
                >
                  <MenuItem value="">All Users</MenuItem>
                  {users.map((user) => (
                    <MenuItem key={user.id} value={user.id}>
                      {user.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Action</InputLabel>
                <Select
                  value={filters.action}
                  onChange={(e) => setFilters({ ...filters, action: e.target.value })}
                  label="Action"
                >
                  <MenuItem value="">All Actions</MenuItem>
                  <MenuItem value="create">Create</MenuItem>
                  <MenuItem value="update">Update</MenuItem>
                  <MenuItem value="delete">Delete</MenuItem>
                  <MenuItem value="view">View</MenuItem>
                  <MenuItem value="login">Login</MenuItem>
                  <MenuItem value="logout">Logout</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Module</InputLabel>
                <Select
                  value={filters.module}
                  onChange={(e) => setFilters({ ...filters, module: e.target.value })}
                  label="Module"
                >
                  <MenuItem value="">All Modules</MenuItem>
                  {modules.map(m => <MenuItem key={m.id} value={m.module_name}>{m.module_name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.success}
                  onChange={(e) => setFilters({ ...filters, success: e.target.value })}
                  label="Status"
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="true">Success</MenuItem>
                  <MenuItem value="false">Failed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Start Date"
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="End Date"
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="IP Address"
                value={filters.ip_address}
                onChange={(e) => setFilters({ ...filters, ip_address: e.target.value })}
                placeholder="e.g., 192.168.1.1"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleFilterReset}>Reset</Button>
          <Button onClick={() => setFilterDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleFilterApply} variant="contained">Apply Filters</Button>
        </DialogActions>
      </Dialog>

      {/* View Details Dialog */}
      <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <HistoryIcon sx={{ mr: 1 }} />
            Audit Log Details
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedLog && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>Basic Information</Typography>
                      <Typography><strong>ID:</strong> {selectedLog.id}</Typography>
                      <Typography><strong>User:</strong> {getUserName(selectedLog.user_id)}</Typography>
                      <Typography><strong>Action:</strong> {selectedLog.action}</Typography>
                      <Typography><strong>Module:</strong> {selectedLog.module}</Typography>
                      <Typography><strong>Status:</strong> {selectedLog.success ? 'Success' : 'Failed'}</Typography>
                      <Typography><strong>Timestamp:</strong> {formatTimestamp(selectedLog.timestamp)}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>Technical Details</Typography>
                      <Typography><strong>IP Address:</strong> {selectedLog.ip_address}</Typography>
                      <Typography><strong>Method:</strong> {selectedLog.method || 'N/A'}</Typography>
                      <Typography><strong>Endpoint:</strong> {selectedLog.endpoint || 'N/A'}</Typography>
                      <Typography><strong>User Agent:</strong> {selectedLog.user_agent || 'N/A'}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>Description</Typography>
                      <Typography>{selectedLog.description}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                {selectedLog.metadata && (
                  <Grid item xs={12}>
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">Additional Metadata</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>
                          {JSON.stringify(selectedLog.metadata, null, 2)}
                        </pre>
                      </AccordionDetails>
                    </Accordion>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AuditLogs; 
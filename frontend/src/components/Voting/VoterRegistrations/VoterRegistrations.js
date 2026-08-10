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
  IconButton,
  Tooltip,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
  Avatar,
  Stack,
  Badge,
  Stepper,
  Step,
  StepLabel,
  LinearProgress,
  Tabs,
  Tab,
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
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  People as BulkApproveIcon,
  Assignment as AssignmentIcon,
  PersonAdd as RegistrationIcon,
  HowToReg as RegisterIcon,
  VerifiedUser as VerifiedIcon,
  Pending as PendingIcon,
  Error as RejectedIcon,
  AccessTime as ExpiredIcon,
  Warning as WarningIcon,
  Security as SecurityIcon,
  DocumentScanner as DocumentIcon,
  LocationOn as LocationIcon,
  Language as LanguageIcon,
  Accessibility as AccessibilityIcon,
  Speed as QuickProcessIcon,
  Analytics as AnalyticsIcon,
  Assessment as ComplianceIcon,
  Shield as FraudIcon,
  Timeline as HistoryIcon,
  Notifications as NotificationIcon,
  CloudUpload as ImportIcon,
  GetApp as ExportIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Groups as TotalIcon,
  CheckBox as ApprovedIcon,
} from '@mui/icons-material';
import { voterRegistrationsAPI, electionsAPI, votersAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import { useDeleteWithDependencies } from '../../../hooks/useDeleteWithDependencies';
import { showErrorAlert } from '../../../utils/swal';
import { capitalizeError } from '../../../utils/validators';

const CustomToolbar = ({ onAdd, onBulkApprove, onQuickProcess, onImportRegistrations, onExportReport, hasCreatePermission, hasUpdatePermission, selectedRows }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Tooltip title="Add new voter registration manually">
        <Button startIcon={<AddIcon />} onClick={onAdd}>
          Add Registration
        </Button>
      </Tooltip>
    )}
    {hasUpdatePermission && selectedRows.length > 0 && (
      <>
        <Tooltip title={`Bulk approve ${selectedRows.length} selected registrations`}>
      <Button 
        startIcon={<BulkApproveIcon />} 
        onClick={onBulkApprove}
        color="success"
      >
        Bulk Approve ({selectedRows.length})
      </Button>
        </Tooltip>
        <Tooltip title="Quick process selected registrations with automated verification">
          <Button 
            startIcon={<QuickProcessIcon />} 
            onClick={onQuickProcess}
            color="info"
          >
            Quick Process
          </Button>
        </Tooltip>
      </>
    )}
    <Tooltip title="Import voter registrations from CSV or external system">
      <Button startIcon={<ImportIcon />} onClick={onImportRegistrations}>
        Import
      </Button>
    </Tooltip>
    <Tooltip title="Export registration report with analytics and compliance data">
      <Button startIcon={<ExportIcon />} onClick={onExportReport}>
        Export Report
      </Button>
    </Tooltip>
  </GridToolbarContainer>
);

const VoterRegistrations = () => {
  const { hasPermission } = usePermissions();
  const [registrations, setRegistrations] = useState([]);
  const [elections, setElections] = useState([]);
  const [voters, setVoters] = useState([]);
  const [selectedRows, setSelectedRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [rejectionDialogOpen, setRejectionDialogOpen] = useState(false);
  const [bulkApprovalDialogOpen, setBulkApprovalDialogOpen] = useState(false);
  const [editingRegistration, setEditingRegistration] = useState(null);
  const [selectedRegistration, setSelectedRegistration] = useState(null);
  const [processingRegistration, setProcessingRegistration] = useState(null);
  const [stats, setStats] = useState({});
  const [quickProcessDialogOpen, setQuickProcessDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [verificationDialogOpen, setVerificationDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [formData, setFormData] = useState({
    voter_id: '',
    election_id: '',
    status: 'pending',
    notes: '',
    special_requirements: '',
    accessibility_needs: '',
    preferred_language: 'en',
    verification_documents: [],
  });
  const [approvalData, setApprovalData] = useState({
    approval_notes: '',
    special_instructions: '',
  });
  const [rejectionData, setRejectionData] = useState({
    rejection_reason: '',
    rejection_notes: '',
  });
  const [bulkApprovalData, setBulkApprovalData] = useState({
    approval_notes: '',
    notify_voters: true,
  });
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const dialogContentRef = useRef(null);

  useEffect(() => {
    if (formError && dialogContentRef.current) {
      dialogContentRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [formError]);

  const canView = hasPermission('VoterRegistrations', 'view');
  const canCreate = hasPermission('VoterRegistrations', 'create');
  const canUpdate = hasPermission('VoterRegistrations', 'update');
  const canDelete = hasPermission('VoterRegistrations', 'delete');

  useEffect(() => {
    if (canView) {
      loadRegistrations();
      loadElections();
      loadVoters();
      loadStats();
    }
  }, [canView]);

  const loadRegistrations = async () => {
    try {
      setLoading(true);
      const response = await voterRegistrationsAPI.getAll();
      setRegistrations(response.data.data || []);
    } catch (error) {
      console.error('Error loading registrations:', error);
      setError('Failed to load registrations');
    } finally {
      setLoading(false);
    }
  };

  const loadElections = async () => {
    try {
      const response = await electionsAPI.getAll();
      setElections(response.data.data || []);
    } catch (error) {
      console.error('Error loading elections:', error);
    }
  };

  const loadVoters = async () => {
    try {
      const response = await votersAPI.getAll();
      setVoters(response.data.data || []);
    } catch (error) {
      console.error('Error loading voters:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await voterRegistrationsAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const [importFile, setImportFile] = useState(null);
  const [importLoading, setImportLoading] = useState(false);

  const handleExportReport = async () => {
    try {
      const [regsRes, statsRes] = await Promise.all([
        voterRegistrationsAPI.getAll({ per_page: 1000 }),
        voterRegistrationsAPI.getStats(),
      ]);

      const report = {
        generated_at: new Date().toISOString(),
        report_type: 'voter_registration_report',
        summary: statsRes.data,
        registrations: regsRes.data.data,
      };

      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `voter_registrations_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setSuccess('Registration report downloaded successfully');
    } catch (err) {
      setError('Failed to export report: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleImportSubmit = async () => {
    if (!importFile) {
      setError('Please select a CSV or JSON file to import');
      return;
    }
    setImportLoading(true);
    try {
      const text = await importFile.text();
      let records = [];
      if (importFile.name.endsWith('.json')) {
        records = JSON.parse(text);
      } else {
        // Basic CSV parse: first row = headers
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',').map((h) => h.trim());
        records = lines.slice(1).map((line) => {
          const values = line.split(',');
          return headers.reduce((obj, key, i) => {
            obj[key] = (values[i] || '').trim();
            return obj;
          }, {});
        });
      }

      // Create each registration via the API
      let created = 0;
      let failed = 0;
      for (const record of records) {
        try {
          await voterRegistrationsAPI.create(record);
          created++;
        } catch {
          failed++;
        }
      }
      await loadRegistrations();
      setSuccess(`Import complete: ${created} created, ${failed} failed`);
      setImportDialogOpen(false);
      setImportFile(null);
    } catch (err) {
      setError('Failed to parse or import file: ' + err.message);
    } finally {
      setImportLoading(false);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingRegistration(null);
  };

  const handleAdd = () => {
    setEditingRegistration(null);
    setFormError('');
    setFormData({
      voter_id: '',
      election_id: '',
      status: 'pending',
      notes: '',
      special_requirements: '',
      accessibility_needs: '',
      preferred_language: 'en',
      verification_documents: [],
    });
    setDialogOpen(true);
  };

  const handleEdit = (registration) => {
    setEditingRegistration(registration);
    setFormError('');
    setFormData({
      voter_id: registration.voter_id || '',
      election_id: registration.election_id || '',
      status: registration.status || 'pending',
      notes: registration.notes || '',
      special_requirements: registration.special_requirements || '',
      accessibility_needs: registration.accessibility_needs || '',
      preferred_language: registration.preferred_language || 'en',
      verification_documents: registration.verification_documents || [],
    });
    setDialogOpen(true);
  };

  const handleView = async (registration) => {
    try {
      const response = await voterRegistrationsAPI.getById(registration.id);
      setSelectedRegistration(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError(capitalizeError('Failed to load registration details'));
    }
  };

  const handleDelete = useDeleteWithDependencies({
    deleteApi: voterRegistrationsAPI.delete,
    itemLabel: 'this registration',
    successMsg: 'Registration deleted successfully',
    forceSuccessMsg: 'Registration force-deleted successfully',
    forceConfirmMessage: 'Are you sure you want to force delete this registration?',
    onSuccess: () => { loadRegistrations(); loadStats(); },
  });

  const handleApprove = (registration) => {
    setProcessingRegistration(registration);
    setApprovalData({
      approval_notes: '',
      special_instructions: '',
    });
    setApprovalDialogOpen(true);
  };

  const handleReject = (registration) => {
    setProcessingRegistration(registration);
    setRejectionData({
      rejection_reason: '',
      rejection_notes: '',
    });
    setRejectionDialogOpen(true);
  };

  const handleBulkApprove = () => {
    setBulkApprovalData({
      approval_notes: '',
      notify_voters: true,
    });
    setBulkApprovalDialogOpen(true);
  };

  const handleConfirmApproval = async () => {
    try {
      await voterRegistrationsAPI.approve(processingRegistration.id, { notes: approvalData.approval_notes });
      setSuccess('Registration approved successfully');
      setApprovalDialogOpen(false);
      loadRegistrations();
      loadStats();
    } catch (error) {
      setError(capitalizeError('Failed to approve registration'));
    }
  };

  const handleConfirmRejection = async () => {
    try {
      await voterRegistrationsAPI.reject(processingRegistration.id, { reason: rejectionData.rejection_reason || rejectionData.rejection_notes });
      setSuccess('Registration rejected successfully');
      setRejectionDialogOpen(false);
      loadRegistrations();
      loadStats();
    } catch (error) {
      setError(capitalizeError('Failed to reject registration'));
    }
  };

  const handleConfirmBulkApproval = async () => {
    try {
      await voterRegistrationsAPI.bulkApprove({
        registration_ids: selectedRows,
        ...bulkApprovalData,
      });
      setSuccess(`${selectedRows.length} registrations approved successfully`);
      setBulkApprovalDialogOpen(false);
      setSelectedRows([]);
      loadRegistrations();
      loadStats();
    } catch (error) {
      setError(capitalizeError('Failed to bulk approve registrations'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    try {
      if (editingRegistration) {
        await voterRegistrationsAPI.update(editingRegistration.id, formData);
        setSuccess('Registration updated successfully');
      } else {
        await voterRegistrationsAPI.create(formData);
        setSuccess('Registration created successfully');
      }
      setDialogOpen(false);
      loadRegistrations();
      loadStats();
    } catch (error) {
      setFormError(capitalizeError((error.response?.data?.error) || 'Operation failed'));
    }
  };

  const getElectionName = (electionId) => {
    const election = elections.find(e => e.id === electionId);
    return election ? election.title : 'Unknown';
  };

  const getVoterName = (voterId) => {
    const voter = voters.find(v => v.id === voterId);
    return voter ? voter.name : 'Unknown';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved': return 'success';
      case 'rejected': return 'error';
      case 'pending': return 'warning';
      case 'under_review': return 'info';
      default: return 'default';
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'voter_id',
      headerName: 'Voter',
      width: 150,
      renderCell: (params) => (
        <Typography variant="body2">
          {getVoterName(params.value)}
        </Typography>
      ),
    },
    {
      field: 'election_id',
      headerName: 'Election',
      width: 200,
      renderCell: (params) => (
        <Typography variant="body2">
          {getElectionName(params.value)}
        </Typography>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const status = params.value || 'pending';
        let StatusIcon = PendingIcon;
        let tooltipText = 'Registration status';
        
        switch (status) {
          case 'approved':
            StatusIcon = ApproveIcon;
            tooltipText = 'Registration approved - voter is eligible to participate';
            break;
          case 'rejected':
            StatusIcon = RejectedIcon;
            tooltipText = 'Registration rejected - voter needs to reapply or fix issues';
            break;
          case 'pending':
            StatusIcon = PendingIcon;
            tooltipText = 'Registration pending review - awaiting administrator approval';
            break;
          case 'under_review':
            StatusIcon = SecurityIcon;
            tooltipText = 'Registration under detailed review - additional verification required';
            break;
          case 'expired':
            StatusIcon = ExpiredIcon;
            tooltipText = 'Registration expired - voter needs to re-register';
            break;
          default:
            StatusIcon = WarningIcon;
            tooltipText = 'Unknown registration status';
        }
        
        return (
          <Tooltip title={tooltipText}>
        <Chip
              label={status}
              color={getStatusColor(status)}
          size="small"
              icon={<StatusIcon />}
        />
          </Tooltip>
        );
      },
    },
    {
      field: 'preferred_language',
      headerName: 'Language',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value || 'en'}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'registered_at',
      headerName: 'Registered',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        return new Date(params.value).toLocaleDateString();
      },
    },
    {
      field: 'approved_at',
      headerName: 'Approved',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        return new Date(params.value).toLocaleDateString();
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
            <Tooltip title="View detailed registration information, verification status, and processing history" key="view">
            <GridActionsCellItem
              icon={<ViewIcon />}
              label="View Details"
              onClick={() => handleView(params.row)}
            />
            </Tooltip>
          );
        }
        
        if (canUpdate) {
          actions.push(
            <Tooltip title="Edit registration details, update voter information, and modify eligibility settings" key="edit">
            <GridActionsCellItem
              icon={<EditIcon />}
              label="Edit"
              onClick={() => handleEdit(params.row)}
            />
            </Tooltip>
          );
          
          if (params.row.status === 'pending') {
            actions.push(
              <Tooltip title="Approve this registration and grant voting eligibility to the voter" key="approve">
              <GridActionsCellItem
                icon={<ApproveIcon />}
                label="Approve"
                onClick={() => handleApprove(params.row)}
                  sx={{ color: 'success.main' }}
                />
              </Tooltip>,
              <Tooltip title="Reject this registration with reason and notify the voter" key="reject">
              <GridActionsCellItem
                icon={<RejectIcon />}
                label="Reject"
                onClick={() => handleReject(params.row)}
                  sx={{ color: 'error.main' }}
                />
              </Tooltip>
            );
          } else if (params.row.status === 'approved') {
            actions.push(
              <Tooltip title="View verification details and compliance status" key="verify">
                <GridActionsCellItem
                  icon={<VerifiedIcon />}
                  label="Verification"
                  onClick={() => setVerificationDialogOpen(true)}
                  sx={{ color: 'info.main' }}
              />
              </Tooltip>
            );
          }
        }
        
        if (canDelete) {
          actions.push(
            <Tooltip title="Permanently delete this registration (cannot be undone)" key="delete">
            <GridActionsCellItem
              icon={<DeleteIcon />}
              label="Delete"
              onClick={() => handleDelete(params.row.id)}
                sx={{ color: 'error.main' }}
            />
            </Tooltip>
          );
        }
        
        return actions;
      },
    },
  ];

  if (!canView) {
    return (
      <Alert severity="error">
        You don't have permission to view voter registrations.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48 }}>
          <RegistrationIcon />
        </Avatar>
        <Box>
      <Typography variant="h4" gutterBottom>
        Voter Registration Management
      </Typography>
          <Typography variant="body2" color="textSecondary">
            Manage voter registrations, verify eligibility, and process applications for election participation
          </Typography>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
              <Typography color="textSecondary" gutterBottom>
                Total Registrations
              </Typography>
              <Typography variant="h5">
                {stats.total_registrations || 0}
              </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                  <TotalIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
              <Typography color="textSecondary" gutterBottom>
                Pending Approval
              </Typography>
              <Typography variant="h5">
                {stats.pending_registrations || 0}
              </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'warning.main', width: 56, height: 56 }}>
                  <PendingIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
              <Typography color="textSecondary" gutterBottom>
                Approved
              </Typography>
              <Typography variant="h5">
                {stats.approved_registrations || 0}
              </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'success.main', width: 56, height: 56 }}>
                  <ApprovedIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
              <Typography color="textSecondary" gutterBottom>
                Approval Rate
              </Typography>
              <Typography variant="h5">
                {stats.approval_rate ? `${stats.approval_rate.toFixed(1)}%` : '0%'}
              </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'info.main', width: 56, height: 56 }}>
                  <AnalyticsIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

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
          rows={registrations}
          columns={columns}
          pageSize={25}
          rowsPerPageOptions={[25, 50, 100]}
          checkboxSelection
          disableSelectionOnClick
          loading={loading}
          onSelectionModelChange={(newSelection) => {
            setSelectedRows(newSelection);
          }}
          components={{
            Toolbar: () => (
              <CustomToolbar
                onAdd={handleAdd}
                onBulkApprove={handleBulkApprove}
                onQuickProcess={() => showErrorAlert('Quick Process functionality not implemented yet')}
                onImportRegistrations={() => setImportDialogOpen(true)}
                onExportReport={handleExportReport}
                hasCreatePermission={canCreate}
                hasUpdatePermission={canUpdate}
                selectedRows={selectedRows}
              />
            ),
          }}
        />
      </Paper>

      {/* Add/Edit Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingRegistration ? 'Edit Registration' : 'Add New Registration'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth required>
                  <InputLabel>Voter</InputLabel>
                  <Select
                    value={formData.voter_id}
                    onChange={(e) => setFormData({...formData, voter_id: e.target.value})}
                  >
                    {voters.map((voter) => (
                      <MenuItem key={voter.id} value={voter.id}>
                        {voter.name}{voter.email ? ` (${voter.email})` : ''}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth required>
                  <InputLabel>Election</InputLabel>
                  <Select
                    value={formData.election_id}
                    onChange={(e) => setFormData({...formData, election_id: e.target.value})}
                  >
                    {elections.map((election) => (
                      <MenuItem key={election.id} value={election.id}>
                        {election.title}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Registration Status</InputLabel>
                  <Select
                    value={formData.status}
                    onChange={(e) => setFormData({...formData, status: e.target.value})}
                  >
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="under_review">Under Review</MenuItem>
                    <MenuItem value="approved">Approved</MenuItem>
                    <MenuItem value="rejected">Rejected</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Preferred Language</InputLabel>
                  <Select
                    value={formData.preferred_language}
                    onChange={(e) => setFormData({...formData, preferred_language: e.target.value})}
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="es">Spanish</MenuItem>
                    <MenuItem value="fr">French</MenuItem>
                    <MenuItem value="de">German</MenuItem>
                    <MenuItem value="zh">Chinese</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Notes"
                  multiline
                  rows={3}
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Special Requirements"
                  multiline
                  rows={2}
                  value={formData.special_requirements}
                  onChange={(e) => setFormData({...formData, special_requirements: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Accessibility Needs"
                  multiline
                  rows={2}
                  value={formData.accessibility_needs}
                  onChange={(e) => setFormData({...formData, accessibility_needs: e.target.value})}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {editingRegistration ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Registration Details</DialogTitle>
        <DialogContent>
          {selectedRegistration && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Voter</Typography>
                <Typography variant="body1">{getVoterName(selectedRegistration.voter_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Election</Typography>
                <Typography variant="body1">{getElectionName(selectedRegistration.election_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Status</Typography>
                <Chip
                  label={selectedRegistration.status}
                  color={getStatusColor(selectedRegistration.status)}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Language</Typography>
                <Typography variant="body1">{selectedRegistration.preferred_language}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Registered At</Typography>
                <Typography variant="body1">
                  {selectedRegistration.registered_at ? new Date(selectedRegistration.registered_at).toLocaleString() : 'N/A'}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Approved At</Typography>
                <Typography variant="body1">
                  {selectedRegistration.approved_at ? new Date(selectedRegistration.approved_at).toLocaleString() : 'N/A'}
                </Typography>
              </Grid>
              
              {selectedRegistration.notes && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Notes</Typography>
                  <Typography variant="body1">{selectedRegistration.notes}</Typography>
                </Grid>
              )}
              
              {selectedRegistration.special_requirements && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Special Requirements</Typography>
                  <Typography variant="body1">{selectedRegistration.special_requirements}</Typography>
                </Grid>
              )}
              
              {selectedRegistration.accessibility_needs && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Accessibility Needs</Typography>
                  <Typography variant="body1">{selectedRegistration.accessibility_needs}</Typography>
                </Grid>
              )}
              
              {selectedRegistration.status === 'rejected' && (
                <>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" color="error">
                      Rejection Information
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Rejection Reason</Typography>
                    <Typography variant="body1">{selectedRegistration.rejection_reason || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2">Rejection Notes</Typography>
                    <Typography variant="body1">{selectedRegistration.rejection_notes || 'N/A'}</Typography>
                  </Grid>
                </>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Approval Dialog */}
      <Dialog
        open={approvalDialogOpen}
        onClose={() => setApprovalDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Approve Registration</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Approve registration for <strong>{processingRegistration && getVoterName(processingRegistration.voter_id)}</strong>?
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Approval Notes"
                multiline
                rows={3}
                value={approvalData.approval_notes}
                onChange={(e) => setApprovalData({...approvalData, approval_notes: e.target.value})}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Special Instructions"
                multiline
                rows={2}
                value={approvalData.special_instructions}
                onChange={(e) => setApprovalData({...approvalData, special_instructions: e.target.value})}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApprovalDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmApproval}
            variant="contained"
            color="success"
          >
            Approve
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rejection Dialog */}
      <Dialog
        open={rejectionDialogOpen}
        onClose={() => setRejectionDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Reject Registration</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Reject registration for <strong>{processingRegistration && getVoterName(processingRegistration.voter_id)}</strong>?
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Rejection Reason</InputLabel>
                <Select
                  value={rejectionData.rejection_reason}
                  onChange={(e) => setRejectionData({...rejectionData, rejection_reason: e.target.value})}
                >
                  <MenuItem value="incomplete_information">Incomplete Information</MenuItem>
                  <MenuItem value="invalid_documentation">Invalid Documentation</MenuItem>
                  <MenuItem value="eligibility_requirements">Eligibility Requirements Not Met</MenuItem>
                  <MenuItem value="duplicate_registration">Duplicate Registration</MenuItem>
                  <MenuItem value="other">Other</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Rejection Notes"
                multiline
                rows={3}
                value={rejectionData.rejection_notes}
                onChange={(e) => setRejectionData({...rejectionData, rejection_notes: e.target.value})}
                required
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectionDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmRejection}
            variant="contained"
            color="error"
          >
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Approval Dialog */}
      <Dialog
        open={bulkApprovalDialogOpen}
        onClose={() => setBulkApprovalDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Bulk Approve Registrations</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Approve <strong>{selectedRows.length}</strong> selected registrations?
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Approval Notes"
                multiline
                rows={3}
                value={bulkApprovalData.approval_notes}
                onChange={(e) => setBulkApprovalData({...bulkApprovalData, approval_notes: e.target.value})}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={bulkApprovalData.notify_voters}
                    onChange={(e) => setBulkApprovalData({...bulkApprovalData, notify_voters: e.target.checked})}
                  />
                }
                label="Send notification to voters"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkApprovalDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmBulkApproval}
            variant="contained"
            color="success"
          >
            Approve All
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Voter Registrations</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Upload a CSV or JSON file. CSV must have a header row with column names matching registration fields
            (voter_id, election_id, status, etc.).
          </Typography>
          <Box mt={2}>
            <Button variant="outlined" component="label" startIcon={<ImportIcon />} fullWidth>
              {importFile ? importFile.name : 'Choose CSV or JSON File'}
              <input
                type="file"
                accept=".csv,.json"
                hidden
                onChange={(e) => setImportFile(e.target.files[0] || null)}
              />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setImportDialogOpen(false); setImportFile(null); }}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleImportSubmit}
            disabled={!importFile || importLoading}
            startIcon={importLoading ? <CircularProgress size={16} /> : <ImportIcon />}
          >
            {importLoading ? 'Importing…' : 'Import'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default VoterRegistrations;
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
  IconButton,
  Tooltip,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  LinearProgress,
  Badge,
  Tab,
  Tabs,
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
  VerifiedUser as VerifyIcon,
  HowToVote as VoteIcon,
  AppRegistration as RegistrationIcon,
  Fingerprint as BiometricIcon,
  Security as SecurityIcon,
  Phone as PhoneIcon,
  Badge as IdentityIcon,
  Devices as DeviceIcon,
  Timeline as HistoryIcon,
  Settings as SettingsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon,
  VpnKey as PinIcon,
  ExpandMore as ExpandIcon,
  FaceRetouchingNatural as FaceIcon,
  TouchApp as TouchIcon,
} from '@mui/icons-material';
import { votersAPI, usersAPI, companiesAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import { useAuth } from '../../../contexts/AuthContext';
import { showDeleteConfirm } from '../../../utils/swal';
import { validateNonNumericText, validateEmail, validatePhone, capitalizeError } from '../../../utils/validators';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Tooltip title="Add new voter to the system">
        <Button startIcon={<AddIcon />} onClick={onAdd}>
          Add Voter
        </Button>
      </Tooltip>
    )}
  </GridToolbarContainer>
);

const Voters = () => {
  const { hasPermission } = usePermissions();
  const { user } = useAuth();

  const isPlatformAdmin = user?.is_administrator === true;

  const [voters, setVoters] = useState([]);
  const [users, setUsers] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [verificationDialogOpen, setVerificationDialogOpen] = useState(false);
  const [biometricDialogOpen, setBiometricDialogOpen] = useState(false);
  const [deviceDialogOpen, setDeviceDialogOpen] = useState(false);
  const [securityDialogOpen, setSecurityDialogOpen] = useState(false);
  const [editingVoter, setEditingVoter] = useState(null);
  const [selectedVoter, setSelectedVoter] = useState(null);
  const [verificationVoter, setVerificationVoter] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [stats, setStats] = useState({});
  const [formData, setFormData] = useState({
    company_id: '',
    user_id: '',
    name: '',
    email: '',
    password: '',
    phone_number: '',
    date_of_birth: '',
    registered_address: '',
    jurisdiction: '',
    voter_type: 'standard',
    two_factor_enabled: false,
    // Enhanced verification fields
    verification_level: 'none',
    is_verified: false,
    require_biometric: false,
    require_device_verification: true,
    // Device security fields
    max_registered_devices: 3,
    device_approval_required: true,
    // Security settings
    enable_security_pin: false,
    pin_required_for_voting: true,
    session_timeout_minutes: 30,
  });
  const [verificationData, setVerificationData] = useState({
    verification_type: 'identity',
    verification_method: 'manual',
    notes: '',
    document_verified: false,
    biometric_quality_score: 0.95,
    override_requirements: false,
  });
  const [biometricData, setBiometricData] = useState({
    enrollment_type: 'facial_recognition',
    quality_threshold: 0.85,
    enable_liveness_detection: true,
    require_multiple_angles: true,
    enrollment_status: 'pending',
  });
  const [deviceData, setDeviceData] = useState({
    registered_devices: [],
    pending_approvals: [],
    device_limit_reached: false,
    auto_approve_trusted: false,
  });
  const [securityData, setSecurityData] = useState({
    security_pin: '',
    confirm_pin: '',
    pin_strength: 'weak',
    enable_biometric_fallback: true,
    require_pin_change: false,
  });
  const [createLinked, setCreateLinked] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Voters', 'view');
  const canCreate = hasPermission('Voters', 'create');
  const canUpdate = hasPermission('Voters', 'update');
  const canDelete = hasPermission('Voters', 'delete');

  useEffect(() => {
    if (canView) {
      if (isPlatformAdmin) {
        loadCompanies();
      }
      loadVoters();
      loadUsers(isPlatformAdmin ? selectedCompanyFilter : undefined);
      loadStats();
    }
  }, [canView, isPlatformAdmin, selectedCompanyFilter]);

  const loadCompanies = async () => {
    try {
      const response = await companiesAPI.getAll();
      setCompanies((response.data.data || []).filter(c => c.status === 1));
    } catch (error) {
      console.error('Error loading companies:', error);
    }
  };

  const loadVoters = async () => {
    try {
      setLoading(true);
      const params = {};
      if (isPlatformAdmin && selectedCompanyFilter) params.company_id = selectedCompanyFilter;
      const response = await votersAPI.getAll(params);
      setVoters(response.data.data || []);
    } catch (error) {
      console.error('Error loading voters:', error);
      setError('Failed to load voters');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async (companyId) => {
    try {
      const params = companyId ? { company_id: companyId } : {};
      const response = await usersAPI.getAll(params);
      setUsers(response.data.data || []);
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  const loadStats = async () => {
    try {
      const params = {};
      if (isPlatformAdmin && selectedCompanyFilter) params.company_id = selectedCompanyFilter;
      const response = await votersAPI.getStats(params);
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  // Enhanced handler functions
  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingVoter(null);
  };

  const handleAdd = () => {
    setEditingVoter(null);
    setCreateLinked(false);
    setFormError('');
    setFormData({
      company_id: '',
      user_id: '',
      name: '',
      email: '',
      password: '',
      phone_number: '',
      date_of_birth: '',
      registered_address: '',
      jurisdiction: '',
      voter_type: 'standard',
      two_factor_enabled: false,
      // Enhanced verification fields
      verification_level: 'none',
      is_verified: false,
      require_biometric: false,
      require_device_verification: true,
      // Device security fields
      max_registered_devices: 3,
      device_approval_required: true,
      // Security settings
      enable_security_pin: false,
      pin_required_for_voting: true,
      session_timeout_minutes: 30,
    });
    setDialogOpen(true);
  };

  const handleEdit = (voter) => {
    setEditingVoter(voter);
    setCreateLinked(voter.user_id !== null);
    setFormError('');
    setFormData({
      company_id: voter.company_id || '',
      user_id: voter.user_id || '',
      name: voter.name || '',
      email: voter.email || '',
      password: '',
      phone_number: voter.phone_number || '',
      date_of_birth: voter.date_of_birth || '',
      registered_address: voter.registered_address || '',
      jurisdiction: voter.jurisdiction || '',
      voter_type: voter.voter_type || 'standard',
      two_factor_enabled: voter.two_factor_enabled || false,
      // Enhanced verification fields
      verification_level: voter.verification_level || 'none',
      is_verified: voter.is_verified || false,
      require_biometric: voter.require_biometric || false,
      require_device_verification: voter.require_device_verification || true,
      // Device security fields
      max_registered_devices: voter.max_registered_devices || 3,
      device_approval_required: voter.device_approval_required || true,
      // Security settings
      enable_security_pin: voter.enable_security_pin || false,
      pin_required_for_voting: voter.pin_required_for_voting || true,
      session_timeout_minutes: voter.session_timeout_minutes || 30,
    });
    setDialogOpen(true);
  };

  const handleView = async (voter) => {
    try {
      const response = await votersAPI.getById(voter.id);
      setSelectedVoter(response.data);
      setActiveTab(0);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError(capitalizeError('Failed to load voter details'));
    }
  };

  const handleDelete = async (voterId) => {
    const confirmed = await showDeleteConfirm('this voter');
    if (confirmed) {
      try {
        await votersAPI.delete(voterId);
        setSuccess('Voter deleted successfully');
        loadVoters();
        loadStats();
      } catch (error) {
        setError(capitalizeError('Failed to delete voter'));
      }
    }
  };

  // Enhanced verification management
  const handleVerificationManagement = (voter) => {
    setVerificationVoter(voter);
    setVerificationData({
      verification_type: 'identity',
      verification_method: 'manual',
      notes: '',
      document_verified: false,
      biometric_quality_score: 0.95,
      override_requirements: false,
    });
    setVerificationDialogOpen(true);
  };

  const handleBiometricEnrollment = (voter) => {
    setVerificationVoter(voter);
    setBiometricData({
      enrollment_type: 'facial_recognition',
      quality_threshold: 0.85,
      enable_liveness_detection: true,
      require_multiple_angles: true,
      enrollment_status: voter.biometric_verified_at ? 'completed' : 'pending',
    });
    setBiometricDialogOpen(true);
  };

  const handleDeviceManagement = (voter) => {
    setError('Device management will be available in a future update');
  };

  const handleSecuritySettings = (voter) => {
    setVerificationVoter(voter);
    setSecurityData({
      security_pin: '',
      confirm_pin: '',
      pin_strength: 'weak',
      enable_biometric_fallback: voter.enable_biometric_fallback || true,
      require_pin_change: voter.require_pin_change || false,
    });
    setSecurityDialogOpen(true);
  };

  const handleVerify = async (voterId, verificationType) => {
    try {
      await votersAPI.verify(voterId, { 
        verification_type: verificationType,
        ...verificationData 
      });
      setSuccess(`Voter ${verificationType} verification updated successfully`);
      loadVoters();
      setVerificationDialogOpen(false);
    } catch (error) {
      setError(capitalizeError(`Failed to update ${verificationType} verification`));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    if (formData.name) {
      const nameErr = validateNonNumericText(formData.name, 'Voter name', 2, 100);
      if (nameErr) {
        setFormError(capitalizeError(nameErr));
        return;
      }
    }

    if (formData.email) {
      const emailErr = validateEmail(formData.email);
      if (emailErr) {
        setFormError(capitalizeError(emailErr));
        return;
      }
    }

    if (formData.phone_number) {
      const phoneErr = validatePhone(formData.phone_number);
      if (phoneErr) {
        setFormError(capitalizeError(phoneErr));
        return;
      }
    }

    if (isPlatformAdmin && !editingVoter && !formData.company_id) {
      setFormError(capitalizeError('Please select a company'));
      return;
    }

    try {
      if (editingVoter) {
        await votersAPI.update(editingVoter.id, formData);
        setSuccess('Voter updated successfully');
      } else {
        await votersAPI.create(formData);
        setSuccess('Voter created successfully');
      }
      setDialogOpen(false);
      loadVoters();
      loadStats();
    } catch (error) {
      setFormError(capitalizeError((error.response?.data?.error) || 'Operation failed'));
    }
  };

  const getVerificationLevelColor = (level) => {
    switch (level) {
      case 'full': return 'success';
      case 'biometric': return 'success';
      case 'identity': return 'warning';
      case 'phone': return 'info';
      default: return 'default';
    }
  };

  const getVerificationIcon = (level) => {
    switch (level) {
      case 'full': return <BiometricIcon />;
      case 'biometric': return <FaceIcon />;
      case 'identity': return <IdentityIcon />;
      case 'phone': return <PhoneIcon />;
      default: return <WarningIcon />;
    }
  };

  const getVerificationProgress = (voter) => {
    if (!voter) return 0;
    let progress = 0;
    if (voter.is_verified) {
      progress = 100;
    } else {
      if (voter.phone_verified_at) progress += 25;
      if (voter.identity_verified_at) progress += 25;
      if (voter.biometric_verified_at) progress += 25;
      if (voter.security_pin_hash) progress += 25;
    }
    return progress;
  };

  const getPinStrength = (pin) => {
    if (!pin || pin.length < 4) return { level: 'weak', color: 'error' };
    if (pin.length < 6) return { level: 'medium', color: 'warning' };
    if (pin.length >= 6 && /[0-9]/.test(pin) && /[A-Za-z]/.test(pin)) {
      return { level: 'strong', color: 'success' };
    }
    return { level: 'medium', color: 'warning' };
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'voter_id', headerName: 'Voter ID', width: 150 },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'email', headerName: 'Email', width: 250 },
    { field: 'phone_number', headerName: 'Phone', width: 150 },
    {
      field: 'is_verified',
      headerName: 'Verified',
      width: 100,
      renderCell: (params) => (
        <Chip
          icon={params.value ? <CheckIcon /> : <WarningIcon />}
          label={params.value ? 'Yes' : 'No'}
          color={params.value ? 'success' : 'warning'}
          size="small"
        />
      ),
    },
    {
      field: 'verification_level',
      headerName: 'Level',
      width: 120,
      renderCell: (params) => {
        const level = params.value || 'none';
        return (
          <Tooltip title={`Verification Level: ${level}`}>
            <Chip
              icon={getVerificationIcon(level)}
              label={level}
              color={getVerificationLevelColor(level)}
              size="small"
              variant="outlined"
            />
          </Tooltip>
        );
      },
    },
    {
      field: 'voter_type',
      headerName: 'Type',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value || 'standard'}
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
        return new Date(params.value).toLocaleDateString();
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 350,
      getActions: (params) => {
        const actions = [];
        
        if (canView) {
          actions.push(
            <Tooltip title="View comprehensive voter details and verification status">
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
            <Tooltip title="Edit basic voter information and preferences">
              <GridActionsCellItem
                icon={<EditIcon />}
                label="Edit"
                onClick={() => handleEdit(params.row)}
              />
            </Tooltip>,
            <Tooltip title="Manage verification levels and identity verification">
              <GridActionsCellItem
                icon={<VerifyIcon />}
                label="Verification"
                onClick={() => handleVerificationManagement(params.row)}
              />
            </Tooltip>,
            <Tooltip title="Enroll and manage biometric authentication">
              <GridActionsCellItem
                icon={<BiometricIcon />}
                label="Biometric"
                onClick={() => handleBiometricEnrollment(params.row)}
              />
            </Tooltip>,
            <Tooltip title="Manage registered devices and device security">
              <GridActionsCellItem
                icon={<DeviceIcon />}
                label="Devices"
                onClick={() => handleDeviceManagement(params.row)}
              />
            </Tooltip>,
            <Tooltip title="Configure security PIN and authentication settings">
              <GridActionsCellItem
                icon={<SecurityIcon />}
                label="Security"
                onClick={() => handleSecuritySettings(params.row)}
              />
            </Tooltip>
          );
        }
        
        if (canDelete) {
          actions.push(
            <Tooltip title="Permanently delete this voter from the system">
              <GridActionsCellItem
                icon={<DeleteIcon />}
                label="Delete"
                onClick={() => handleDelete(params.row.id)}
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
        You don't have permission to view voters.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Voter Management
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Voters
              </Typography>
              <Typography variant="h5">
                {stats.total_voters || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Verified Voters
              </Typography>
              <Typography variant="h5">
                {stats.verified_voters || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Verification Rate
              </Typography>
              <Typography variant="h5">
                {stats.verification_rate ? `${stats.verification_rate.toFixed(1)}%` : '0%'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Unverified Voters
              </Typography>
              <Typography variant="h5">
                {stats.unverified_voters || 0}
              </Typography>
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

      {/* Platform Admin Filter Bar */}
      {isPlatformAdmin && (
        <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            label="Filter by Company"
            select
            size="small"
            value={selectedCompanyFilter}
            onChange={(e) => {
              const compId = e.target.value;
              setSelectedCompanyFilter(compId);
              loadUsers(compId);
            }}
            SelectProps={{ native: true }}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 220 }}
          >
            <option value="">All Companies</option>
            {companies.map((comp) => (
              <option key={comp.id} value={comp.id}>
                {comp.company_name}
              </option>
            ))}
          </TextField>
        </Box>
      )}

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={voters}
          columns={columns}
          pageSize={25}
          rowsPerPageOptions={[25, 50, 100]}
          checkboxSelection
          disableSelectionOnClick
          loading={loading}
          components={{
            Toolbar: () => <CustomToolbar onAdd={handleAdd} hasCreatePermission={canCreate} />,
          }}
        />
      </Paper>

      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingVoter ? 'Edit Voter' : 'Add New Voter'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            <Grid container spacing={2}>
              {/* Company Selection Field */}
              <Grid item xs={12} sm={6}>
                {!editingVoter ? (
                  isPlatformAdmin ? (
                    <TextField
                      fullWidth
                      label="Company *"
                      select
                      variant="outlined"
                      value={formData.company_id || ''}
                      onChange={(e) => {
                        const compId = e.target.value;
                        setFormData({ ...formData, company_id: compId, user_id: '' });
                        loadUsers(compId);
                      }}
                      SelectProps={{ native: true }}
                      InputLabelProps={{ shrink: true }}
                      required
                    >
                      <option value="" disabled hidden>Select Company</option>
                      {companies.map((comp) => (
                        <option key={comp.id} value={comp.id}>
                          {comp.company_name}
                        </option>
                      ))}
                    </TextField>
                  ) : (
                    <TextField
                      fullWidth
                      label="Company"
                      variant="outlined"
                      value={user?.company_name || 'Your Company'}
                      disabled
                      helperText="Voters are automatically assigned to your company."
                    />
                  )
                ) : (
                  <TextField
                    fullWidth
                    label="Company"
                    variant="outlined"
                    value={editingVoter.company_name || user?.company_name || 'N/A'}
                    disabled
                    helperText="Company cannot be modified after creation."
                  />
                )}
              </Grid>

              {!editingVoter && (
                <>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth>
                      <InputLabel id="voter-user-link-label">Link to Existing User</InputLabel>
                      <Select
                        labelId="voter-user-link-label"
                        label="Link to Existing User"
                        value={formData.user_id}
                        onChange={(e) => setFormData({...formData, user_id: e.target.value})}
                        disabled={isPlatformAdmin && !formData.company_id}
                      >
                        <MenuItem value="">Create New User (Unlinked)</MenuItem>
                        {users.map((u) => (
                          <MenuItem key={u.id} value={u.id}>
                            {u.name} ({u.email})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="textSecondary">
                      Leave blank to create a new user, or select an existing user to link
                    </Typography>
                  </Grid>
                </>
              )}
              
              {(!editingVoter && !formData.user_id) ? (
                <>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Full Name"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={createLinked}
                          onChange={(e) => {
                            setCreateLinked(e.target.checked);
                            if (!e.target.checked) {
                              setFormData({ ...formData, email: '', password: '' });
                            }
                          }}
                        />
                      }
                      label="Create Linked User Account (with login credentials)"
                    />
                    <Typography variant="caption" display="block" color="textSecondary" sx={{ mt: 0.5 }}>
                      Leave password empty to create a standalone voter (no system login). Fill password to create a linked user account.
                    </Typography>
                  </Grid>

                  {createLinked && (
                    <>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Email"
                          type="email"
                          value={formData.email}
                          onChange={(e) => setFormData({...formData, email: e.target.value})}
                          required
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Password"
                          type="password"
                          value={formData.password}
                          onChange={(e) => setFormData({...formData, password: e.target.value})}
                          required
                          helperText="Fill password to create a linked user account"
                        />
                      </Grid>
                    </>
                  )}
                </>
              ) : (editingVoter && !formData.user_id) ? (
                <>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Full Name"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                    />
                  </Grid>
                </>
              ) : null}
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Date of Birth"
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => setFormData({...formData, date_of_birth: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Registered Address"
                  multiline
                  rows={2}
                  value={formData.registered_address}
                  onChange={(e) => setFormData({...formData, registered_address: e.target.value})}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Jurisdiction"
                  value={formData.jurisdiction}
                  onChange={(e) => setFormData({...formData, jurisdiction: e.target.value})}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Voter Type</InputLabel>
                  <Select
                    value={formData.voter_type}
                    onChange={(e) => setFormData({...formData, voter_type: e.target.value})}
                  >
                    <MenuItem value="standard">Standard</MenuItem>
                    <MenuItem value="overseas">Overseas</MenuItem>
                    <MenuItem value="military">Military</MenuItem>
                    <MenuItem value="absentee">Absentee</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.two_factor_enabled}
                      onChange={(e) => setFormData({...formData, two_factor_enabled: e.target.checked})}
                    />
                  }
                  label="Enable Two-Factor Authentication"
                />
              </Grid>
              
              {/* Enhanced Verification Fields */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Verification Settings
                  </Typography>
                </Divider>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Required Verification Level</InputLabel>
                  <Select
                    value={formData.verification_level}
                    onChange={(e) => setFormData({...formData, verification_level: e.target.value})}
                  >
                    <MenuItem value="none">None</MenuItem>
                    <MenuItem value="phone">Phone Verification</MenuItem>
                    <MenuItem value="identity">Identity Verification</MenuItem>
                    <MenuItem value="biometric">Biometric Verification</MenuItem>
                    <MenuItem value="full">Full Verification</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_verified}
                      onChange={(e) => setFormData({...formData, is_verified: e.target.checked})}
                    />
                  }
                  label="Mark as Verified"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.require_biometric}
                      onChange={(e) => setFormData({...formData, require_biometric: e.target.checked})}
                    />
                  }
                  label="Require Biometric Verification"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.require_device_verification}
                      onChange={(e) => setFormData({...formData, require_device_verification: e.target.checked})}
                    />
                  }
                  label="Require Device Verification"
                />
              </Grid>
              
              {/* Device Security Fields */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Device Security Settings
                  </Typography>
                </Divider>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Max Registered Devices"
                  type="number"
                  value={formData.max_registered_devices}
                  onChange={(e) => setFormData({...formData, max_registered_devices: parseInt(e.target.value)})}
                  inputProps={{ min: 1, max: 10 }}
                  helperText="Maximum number of devices this voter can register"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.device_approval_required}
                      onChange={(e) => setFormData({...formData, device_approval_required: e.target.checked})}
                    />
                  }
                  label="Device Approval Required"
                />
              </Grid>
              
              {/* Security Settings */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Security & Authentication
                  </Typography>
                </Divider>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.enable_security_pin}
                      onChange={(e) => setFormData({...formData, enable_security_pin: e.target.checked})}
                    />
                  }
                  label="Enable Security PIN"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.pin_required_for_voting}
                      onChange={(e) => setFormData({...formData, pin_required_for_voting: e.target.checked})}
                    />
                  }
                  label="PIN Required for Voting"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Session Timeout (minutes)"
                  type="number"
                  value={formData.session_timeout_minutes}
                  onChange={(e) => setFormData({...formData, session_timeout_minutes: parseInt(e.target.value)})}
                  inputProps={{ min: 5, max: 480 }}
                  helperText="Automatic logout after inactivity"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {editingVoter ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Enhanced Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">
              Voter Details: {selectedVoter?.name}
            </Typography>
            <Chip
              icon={getVerificationIcon(selectedVoter?.verification_level)}
              label={`${selectedVoter?.verification_level || 'none'} verification`}
              color={getVerificationLevelColor(selectedVoter?.verification_level)}
              variant="outlined"
            />
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedVoter && (
            <Box sx={{ width: '100%' }}>
              <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
                <Tab label="Basic Information" icon={<ViewIcon />} />
                <Tab label="Verification Status" icon={<VerifyIcon />} />
                <Tab label="Device Security" icon={<DeviceIcon />} />
                <Tab label="Election History" icon={<HistoryIcon />} />
              </Tabs>
              
              {/* Basic Information Tab */}
              {activeTab === 0 && (
                <Grid container spacing={2} sx={{ mt: 2 }}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Voter ID</Typography>
                    <Typography variant="body1">{selectedVoter.voter_id}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Email</Typography>
                    <Typography variant="body1">{selectedVoter.email}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Phone Number</Typography>
                    <Typography variant="body1">{selectedVoter.phone_number}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Date of Birth</Typography>
                    <Typography variant="body1">
                      {selectedVoter.date_of_birth ? new Date(selectedVoter.date_of_birth).toLocaleDateString() : 'Not provided'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Voter Type</Typography>
                    <Chip label={selectedVoter.voter_type || 'standard'} size="small" />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Two-Factor Auth</Typography>
                    <Chip 
                      label={selectedVoter.two_factor_enabled ? 'Enabled' : 'Disabled'} 
                      color={selectedVoter.two_factor_enabled ? 'success' : 'default'}
                      size="small" 
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2">Registered Address</Typography>
                    <Typography variant="body1">{selectedVoter.registered_address || 'Not provided'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Jurisdiction</Typography>
                    <Typography variant="body1">{selectedVoter.jurisdiction || 'Not specified'}</Typography>
                  </Grid>
                </Grid>
              )}
              
              {/* Verification Status Tab */}
              {activeTab === 1 && (
                <Box sx={{ mt: 2 }}>
                  <Card>
                    <CardHeader 
                      title="Verification Status Overview"
                      subheader="Current verification level and requirements"
                    />
                    <CardContent>
                      <Grid container spacing={3}>
                        <Grid item xs={12} sm={6} md={3}>
                          <Card variant="outlined">
                            <CardContent sx={{ textAlign: 'center' }}>
                              <PhoneIcon color={selectedVoter.phone_verified_at ? 'success' : 'disabled'} sx={{ fontSize: 40 }} />
                              <Typography variant="h6">Phone</Typography>
                              <Typography variant="body2">
                                {selectedVoter.phone_verified_at ? 'Verified' : 'Not Verified'}
                              </Typography>
                              {selectedVoter.phone_verified_at && (
                                <Typography variant="caption" color="textSecondary">
                                  {new Date(selectedVoter.phone_verified_at).toLocaleDateString()}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                          <Card variant="outlined">
                            <CardContent sx={{ textAlign: 'center' }}>
                              <IdentityIcon color={selectedVoter.identity_verified_at ? 'success' : 'disabled'} sx={{ fontSize: 40 }} />
                              <Typography variant="h6">Identity</Typography>
                              <Typography variant="body2">
                                {selectedVoter.identity_verified_at ? 'Verified' : 'Not Verified'}
                              </Typography>
                              {selectedVoter.identity_verified_at && (
                                <Typography variant="caption" color="textSecondary">
                                  {new Date(selectedVoter.identity_verified_at).toLocaleDateString()}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                          <Card variant="outlined">
                            <CardContent sx={{ textAlign: 'center' }}>
                              <BiometricIcon color={selectedVoter.biometric_verified_at ? 'success' : 'disabled'} sx={{ fontSize: 40 }} />
                              <Typography variant="h6">Biometric</Typography>
                              <Typography variant="body2">
                                {selectedVoter.biometric_verified_at ? 'Enrolled' : 'Not Enrolled'}
                              </Typography>
                              {selectedVoter.biometric_verified_at && (
                                <Typography variant="caption" color="textSecondary">
                                  {new Date(selectedVoter.biometric_verified_at).toLocaleDateString()}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                          <Card variant="outlined">
                            <CardContent sx={{ textAlign: 'center' }}>
                              <SecurityIcon color={selectedVoter.security_pin_hash ? 'success' : 'disabled'} sx={{ fontSize: 40 }} />
                              <Typography variant="h6">Security PIN</Typography>
                              <Typography variant="body2">
                                {selectedVoter.security_pin_hash ? 'Set' : 'Not Set'}
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                      </Grid>
                      
                      <Box sx={{ mt: 3 }}>
                        <Typography variant="h6" gutterBottom>Verification Progress</Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Box sx={{ width: '100%', mr: 1 }}>
                            <LinearProgress 
                              variant="determinate" 
                              value={getVerificationProgress(selectedVoter)} 
                              color={selectedVoter.is_verified ? 'success' : 'primary'}
                            />
                          </Box>
                          <Box sx={{ minWidth: 35 }}>
                            <Typography variant="body2" color="textSecondary">
                              {`${Math.round(getVerificationProgress(selectedVoter))}%`}
                            </Typography>
                          </Box>
                        </Box>
                        <Typography variant="body2" color="textSecondary">
                          Complete verification requirements to enable voting
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* Device Security Tab */}
              {activeTab === 2 && (
                <Box sx={{ mt: 2 }}>
                  <Card>
                    <CardHeader 
                      title="Device Security"
                      subheader="Registered devices and security settings"
                    />
                    <CardContent>
                      <Typography variant="h6" gutterBottom>Registered Devices</Typography>
                      {selectedVoter.registered_device_id ? (
                        <List>
                          <ListItem>
                            <ListItemIcon>
                              <DeviceIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Primary Device"
                              secondary={`Device ID: ${selectedVoter.registered_device_id.substring(0, 16)}...`}
                            />
                            <ListItemSecondaryAction>
                              <Chip label="Active" color="success" size="small" />
                            </ListItemSecondaryAction>
                          </ListItem>
                        </List>
                      ) : (
                        <Alert severity="info">No devices registered</Alert>
                      )}
                      
                      <Divider sx={{ my: 2 }} />
                      
                      <Typography variant="h6" gutterBottom>Security Settings</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2">Device Verification</Typography>
                          <Typography variant="body2">
                            {selectedVoter.require_device_verification ? 'Required' : 'Optional'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2">Max Devices</Typography>
                          <Typography variant="body2">
                            {selectedVoter.max_registered_devices || 3} devices allowed
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* Election History Tab */}
              {activeTab === 3 && (
                <Box sx={{ mt: 2 }}>
                  <Card>
                    <CardHeader 
                      title="Election History"
                      subheader="Registration and voting history across elections"
                    />
                    <CardContent>
                      <Alert severity="info">
                        Election history will be displayed here when available
                      </Alert>
                    </CardContent>
                  </Card>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Verification Management Dialog */}
      <Dialog
        open={verificationDialogOpen}
        onClose={() => setVerificationDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <VerifyIcon />
            <Typography variant="h6">
              Verification Management: {verificationVoter?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Verification Type</InputLabel>
                <Select
                  value={verificationData.verification_type}
                  onChange={(e) => setVerificationData({...verificationData, verification_type: e.target.value})}
                >
                  <MenuItem value="phone">Phone Verification</MenuItem>
                  <MenuItem value="identity">Identity Verification</MenuItem>
                  <MenuItem value="biometric">Biometric Verification</MenuItem>
                  <MenuItem value="manual">Manual Override</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Verification Method</InputLabel>
                <Select
                  value={verificationData.verification_method}
                  onChange={(e) => setVerificationData({...verificationData, verification_method: e.target.value})}
                >
                  <MenuItem value="manual">Manual Review</MenuItem>
                  <MenuItem value="automated">Automated</MenuItem>
                  <MenuItem value="third_party">Third Party Service</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={verificationData.document_verified}
                    onChange={(e) => setVerificationData({...verificationData, document_verified: e.target.checked})}
                  />
                }
                label="Document Verified"
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Verification Notes"
                multiline
                rows={3}
                value={verificationData.notes}
                onChange={(e) => setVerificationData({...verificationData, notes: e.target.value})}
                placeholder="Add notes about the verification process..."
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={verificationData.override_requirements}
                    onChange={(e) => setVerificationData({...verificationData, override_requirements: e.target.checked})}
                  />
                }
                label="Override Standard Requirements"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVerificationDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={() => handleVerify(verificationVoter?.id, verificationData.verification_type)}
            startIcon={<CheckIcon />}
          >
            Update Verification
          </Button>
        </DialogActions>
      </Dialog>

      {/* Biometric Enrollment Dialog */}
      <Dialog
        open={biometricDialogOpen}
        onClose={() => setBiometricDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BiometricIcon />
            <Typography variant="h6">
              Biometric Enrollment: {verificationVoter?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>Current Status</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Chip
                      icon={<FaceIcon />}
                      label={biometricData.enrollment_status}
                      color={biometricData.enrollment_status === 'completed' ? 'success' : 'warning'}
                    />
                    {verificationVoter?.biometric_verified_at && (
                      <Typography variant="body2" color="textSecondary">
                        Enrolled on {new Date(verificationVoter.biometric_verified_at).toLocaleDateString()}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Enrollment Type</InputLabel>
                <Select
                  value={biometricData.enrollment_type}
                  onChange={(e) => setBiometricData({...biometricData, enrollment_type: e.target.value})}
                >
                  <MenuItem value="facial_recognition">Facial Recognition</MenuItem>
                  <MenuItem value="fingerprint">Fingerprint</MenuItem>
                  <MenuItem value="iris_scan">Iris Scan</MenuItem>
                  <MenuItem value="voice_recognition">Voice Recognition</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Quality Threshold"
                type="number"
                value={biometricData.quality_threshold}
                onChange={(e) => setBiometricData({...biometricData, quality_threshold: parseFloat(e.target.value)})}
                inputProps={{ min: 0.5, max: 1.0, step: 0.05 }}
                helperText="Minimum quality score (0.5 - 1.0)"
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={biometricData.enable_liveness_detection}
                    onChange={(e) => setBiometricData({...biometricData, enable_liveness_detection: e.target.checked})}
                  />
                }
                label="Enable Liveness Detection"
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={biometricData.require_multiple_angles}
                    onChange={(e) => setBiometricData({...biometricData, require_multiple_angles: e.target.checked})}
                  />
                }
                label="Require Multiple Angles"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Box sx={{ mt: 2 }}>
                <Typography variant="h6" gutterBottom>Enrollment Steps</Typography>
                <Stepper activeStep={biometricData.enrollment_status === 'completed' ? 3 : 1} orientation="vertical">
                  <Step>
                    <StepLabel>Identity Verification</StepLabel>
                    <StepContent>
                      <Typography>Verify voter identity before biometric enrollment</Typography>
                    </StepContent>
                  </Step>
                  <Step>
                    <StepLabel>Biometric Capture</StepLabel>
                    <StepContent>
                      <Typography>Capture high-quality biometric samples</Typography>
                    </StepContent>
                  </Step>
                  <Step>
                    <StepLabel>Quality Check</StepLabel>
                    <StepContent>
                      <Typography>Validate biometric quality meets requirements</Typography>
                    </StepContent>
                  </Step>
                  <Step>
                    <StepLabel>Enrollment Complete</StepLabel>
                    <StepContent>
                      <Typography>Biometric template stored securely</Typography>
                    </StepContent>
                  </Step>
                </Stepper>
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBiometricDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="outlined" 
            startIcon={<RefreshIcon />}
            onClick={() => setBiometricData({...biometricData, enrollment_status: 'pending'})}
          >
            Re-enroll
          </Button>
          <Button 
            variant="contained" 
            startIcon={<BiometricIcon />}
          >
            Start Enrollment
          </Button>
        </DialogActions>
      </Dialog>

      {/* Device Management Dialog */}
      <Dialog
        open={deviceDialogOpen}
        onClose={() => setDeviceDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DeviceIcon />
            <Typography variant="h6">
              Device Management: {verificationVoter?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>Device Statistics</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="primary">
                        {deviceData.registered_devices.length || 0}
                      </Typography>
                      <Typography variant="body2">Registered</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="warning.main">
                        {deviceData.pending_approvals.length || 0}
                      </Typography>
                      <Typography variant="body2">Pending</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="textSecondary">
                        {verificationVoter?.max_registered_devices || 3}
                      </Typography>
                      <Typography variant="body2">Max Allowed</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Registered Devices</Typography>
              {deviceData.registered_devices.length > 0 ? (
                <List>
                  {deviceData.registered_devices.map((device, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <DeviceIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={device.name || `Device ${index + 1}`}
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              ID: {device.id?.substring(0, 16)}...
                            </Typography>
                            <Typography variant="caption">
                              Last seen: {device.last_seen ? new Date(device.last_seen).toLocaleDateString() : 'Never'}
                            </Typography>
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <Tooltip title="Revoke device access">
                          <IconButton edge="end" color="error">
                            <CancelIcon />
                          </IconButton>
                        </Tooltip>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Alert severity="info">No devices registered</Alert>
              )}
            </Grid>
            
            {deviceData.pending_approvals.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>Pending Approvals</Typography>
                <List>
                  {deviceData.pending_approvals.map((device, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <WarningIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={`Pending Device ${index + 1}`}
                        secondary={`Requested: ${device.requested_at ? new Date(device.requested_at).toLocaleDateString() : 'Unknown'}`}
                      />
                      <ListItemSecondaryAction>
                        <Button variant="outlined" size="small" color="success" sx={{ mr: 1 }}>
                          Approve
                        </Button>
                        <Button variant="outlined" size="small" color="error">
                          Reject
                        </Button>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              </Grid>
            )}
            
            <Grid item xs={12}>
              <Divider />
              <Box sx={{ mt: 2 }}>
                <Typography variant="h6" gutterBottom>Device Settings</Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={deviceData.auto_approve_trusted}
                      onChange={(e) => setDeviceData({...deviceData, auto_approve_trusted: e.target.checked})}
                    />
                  }
                  label="Auto-approve trusted devices"
                />
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeviceDialogOpen(false)}>Close</Button>
          <Button variant="contained" startIcon={<RefreshIcon />}>
            Refresh Devices
          </Button>
        </DialogActions>
      </Dialog>

      {/* Security Settings Dialog */}
      <Dialog
        open={securityDialogOpen}
        onClose={() => setSecurityDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SecurityIcon />
            <Typography variant="h6">
              Security Settings: {verificationVoter?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>Current Status</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Chip
                      icon={<PinIcon />}
                      label={verificationVoter?.security_pin_hash ? 'PIN Set' : 'No PIN'}
                      color={verificationVoter?.security_pin_hash ? 'success' : 'default'}
                    />
                    <Chip
                      icon={<TouchIcon />}
                      label={verificationVoter?.two_factor_enabled ? '2FA Enabled' : '2FA Disabled'}
                      color={verificationVoter?.two_factor_enabled ? 'success' : 'default'}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Security PIN</Typography>
              <TextField
                fullWidth
                label="New Security PIN"
                type="password"
                value={securityData.security_pin}
                onChange={(e) => {
                  const newPin = e.target.value;
                  setSecurityData({
                    ...securityData, 
                    security_pin: newPin,
                    pin_strength: getPinStrength(newPin).level
                  });
                }}
                helperText="Enter a secure PIN for voting authentication"
                sx={{ mb: 2 }}
              />
              
              <TextField
                fullWidth
                label="Confirm Security PIN"
                type="password"
                value={securityData.confirm_pin}
                onChange={(e) => setSecurityData({...securityData, confirm_pin: e.target.value})}
                error={securityData.security_pin !== securityData.confirm_pin && securityData.confirm_pin.length > 0}
                helperText={securityData.security_pin !== securityData.confirm_pin && securityData.confirm_pin.length > 0 ? "PINs don't match" : ""}
              />
              
              {securityData.security_pin && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="body2" gutterBottom>PIN Strength:</Typography>
                  <Chip 
                    label={securityData.pin_strength} 
                    color={getPinStrength(securityData.security_pin).color}
                    size="small"
                  />
                </Box>
              )}
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Authentication Settings</Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={securityData.enable_biometric_fallback}
                    onChange={(e) => setSecurityData({...securityData, enable_biometric_fallback: e.target.checked})}
                  />
                }
                label="Enable Biometric Fallback"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={securityData.require_pin_change}
                    onChange={(e) => setSecurityData({...securityData, require_pin_change: e.target.checked})}
                  />
                }
                label="Require PIN Change on Next Login"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSecurityDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            startIcon={<SecurityIcon />}
            disabled={securityData.security_pin !== securityData.confirm_pin}
          >
            Update Security Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Voters; 
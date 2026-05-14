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
  CardActions,
  Divider,
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
  PlayArrow as ActivateIcon,
  Pause as DeactivateIcon,
  Publish as PublishIcon,
  Poll as PollIcon,
  People as PeopleIcon,
  Assignment as AssignmentIcon,
  Assessment as ResultsIcon,
  AccountTree as WorkflowIcon,
  Drafts as DraftIcon,
  CheckCircle as CompleteIcon,
  Cancel as CancelIcon,
  Settings as ManageIcon,
} from '@mui/icons-material';
import { electionsAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import ElectionResults from './ElectionResults';
import ElectionWorkflow from './ElectionWorkflow';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Create Election
      </Button>
    )}
  </GridToolbarContainer>
);

const Elections = () => {
  const { hasPermission } = usePermissions();
  const [elections, setElections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);
  const [workflowDialogOpen, setWorkflowDialogOpen] = useState(false);
  const [editingElection, setEditingElection] = useState(null);
  const [selectedElection, setSelectedElection] = useState(null);
  const [selectedElectionForResults, setSelectedElectionForResults] = useState(null);
  const [selectedElectionForWorkflow, setSelectedElectionForWorkflow] = useState(null);
  const [stats, setStats] = useState({});
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    election_type: 'general',
    election_category: '',
    start_date: '',
    end_date: '',
    registration_deadline: '',
    early_voting_start: '',
    early_voting_end: '',
    is_public: true,
    require_biometric: true,
    require_photo_id: true,
    allow_early_voting: false,
    max_votes_per_voter: 1,
    allow_vote_changes: false,
    require_all_ballots: false,
    jurisdiction: '',
    geographic_scope: '',
    eligible_voter_types: 'standard',
    is_test_election: false,
    audit_enabled: true,
    paper_trail_required: true,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Elections', 'view');
  const canCreate = hasPermission('Elections', 'create');
  const canUpdate = hasPermission('Elections', 'update');
  const canDelete = hasPermission('Elections', 'delete');

  useEffect(() => {
    if (canView) {
      loadElections();
      loadStats();
    }
  }, [canView]);

  const loadElections = async () => {
    try {
      setLoading(true);
      const response = await electionsAPI.getAll();
      setElections(response.data.data || []);
    } catch (error) {
      console.error('Error loading elections:', error);
      setError('Failed to load elections');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await electionsAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleAdd = () => {
    setEditingElection(null);
    setFormData({
      title: '',
      description: '',
      election_type: 'general',
      election_category: '',
      start_date: '',
      end_date: '',
      registration_deadline: '',
      early_voting_start: '',
      early_voting_end: '',
      is_public: true,
      require_biometric: true,
      require_photo_id: true,
      allow_early_voting: false,
      max_votes_per_voter: 1,
      allow_vote_changes: false,
      require_all_ballots: false,
      jurisdiction: '',
      geographic_scope: '',
      eligible_voter_types: 'standard',
      is_test_election: false,
      audit_enabled: true,
      paper_trail_required: true,
    });
    setDialogOpen(true);
  };

  const handleEdit = (election) => {
    setEditingElection(election);
    setFormData({
      title: election.title || '',
      description: election.description || '',
      election_type: election.election_type || 'general',
      election_category: election.election_category || '',
      start_date: election.start_date || '',
      end_date: election.end_date || '',
      registration_deadline: election.registration_deadline || '',
      early_voting_start: election.early_voting_start || '',
      early_voting_end: election.early_voting_end || '',
      is_public: election.is_public ?? true,
      require_biometric: election.require_biometric ?? true,
      require_photo_id: election.require_photo_id ?? true,
      allow_early_voting: election.allow_early_voting ?? false,
      max_votes_per_voter: election.max_votes_per_voter || 1,
      allow_vote_changes: election.allow_vote_changes ?? false,
      require_all_ballots: election.require_all_ballots ?? false,
      jurisdiction: election.jurisdiction || '',
      geographic_scope: election.geographic_scope || '',
      eligible_voter_types: election.eligible_voter_types || 'standard',
      is_test_election: election.is_test_election ?? false,
      audit_enabled: election.audit_enabled ?? true,
      paper_trail_required: election.paper_trail_required ?? true,
    });
    setDialogOpen(true);
  };

  const handleView = async (election) => {
    try {
      const response = await electionsAPI.getById(election.id);
      setSelectedElection(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError('Failed to load election details');
    }
  };

  const handleViewResults = (election) => {
    setSelectedElectionForResults(election);
    setResultsDialogOpen(true);
  };

  const handleWorkflow = (election) => {
    setSelectedElectionForWorkflow(election);
    setWorkflowDialogOpen(true);
  };

  const handleStatusChanged = (newStatus) => {
    // Refresh the elections list when status changes
    loadElections();
    setSuccess(`Election status changed to ${newStatus} successfully`);
  };

  const handleDelete = async (electionId) => {
    if (window.confirm('Are you sure you want to delete this election? This action cannot be undone.')) {
      try {
        await electionsAPI.delete(electionId);
        setSuccess('Election deleted successfully');
        loadElections();
        loadStats();
      } catch (error) {
        setError('Failed to delete election');
      }
    }
  };

  const handleActivate = async (electionId) => {
    try {
      await electionsAPI.activate(electionId);
      setSuccess('Election activated successfully');
      loadElections();
    } catch (error) {
      setError('Failed to activate election');
    }
  };

  const handlePublishResults = async (electionId) => {
    if (window.confirm('Are you sure you want to publish the results? This action cannot be undone.')) {
      try {
        await electionsAPI.publishResults(electionId);
        setSuccess('Results published successfully');
        loadElections();
      } catch (error) {
        setError('Failed to publish results');
      }
    }
  };

  const handleChangeStatus = async (electionId, newStatus) => {
    const statusLabels = {
      'draft': 'Draft',
      'active': 'Active',
      'completed': 'Completed',
      'cancelled': 'Cancelled'
    };
    
    const confirmMessage = `Are you sure you want to change the election status to ${statusLabels[newStatus]}?`;
    
    if (window.confirm(confirmMessage)) {
      try {
        await electionsAPI.changeStatus(electionId, newStatus);
        setSuccess(`Election status changed to ${statusLabels[newStatus]} successfully`);
        loadElections();
      } catch (error) {
        setError('Failed to change election status');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (editingElection) {
        await electionsAPI.update(editingElection.id, formData);
        setSuccess('Election updated successfully');
      } else {
        await electionsAPI.create(formData);
        setSuccess('Election created successfully');
      }
      setDialogOpen(false);
      loadElections();
      loadStats();
    } catch (error) {
      setError((error.response?.data?.error) || 'Operation failed');
    }
  };

  const getElectionStatusColor = (election) => {
    const now = new Date();
    const startDate = new Date(election.start_date);
    const endDate = new Date(election.end_date);
    
    if (!election.is_active) return 'default';
    if (now < startDate) return 'info';
    if (now >= startDate && now <= endDate) return 'success';
    if (now > endDate) return 'warning';
    return 'default';
  };

  const getElectionStatusText = (election) => {
    const now = new Date();
    const startDate = new Date(election.start_date);
    const endDate = new Date(election.end_date);
    
    if (!election.is_active) return 'Inactive';
    if (now < startDate) return 'Scheduled';
    if (now >= startDate && now <= endDate) return 'Active';
    if (now > endDate) return 'Ended';
    return 'Unknown';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'title', headerName: 'Name', width: 250 },
    {
      field: 'election_type',
      headerName: 'Type',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value || 'general'}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={getElectionStatusText(params.row)}
          color={getElectionStatusColor(params.row)}
          size="small"
        />
      ),
    },
    {
      field: 'start_date',
      headerName: 'Start Date',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        return new Date(params.value).toLocaleDateString();
      },
    },
    {
      field: 'end_date',
      headerName: 'End Date',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        return new Date(params.value).toLocaleDateString();
      },
    },
    {
      field: 'is_public',
      headerName: 'Public',
      width: 80,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Yes' : 'No'}
          color={params.value ? 'success' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'voting_method',
      headerName: 'Method',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value || 'single_choice'}
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
      width: 250,
      getActions: (params) => {
        const actions = [];
        
        if (canView) {
          actions.push(
            <Tooltip title="View election details and configuration" key="view">
            <GridActionsCellItem
              icon={<ViewIcon />}
              label="View Details"
              onClick={() => handleView(params.row)}
            />
            </Tooltip>
          );

          // Show results button for completed elections or published results
          if (params.row.results_published || params.row.status === 'completed') {
            actions.push(
              <Tooltip title="View election results and analytics" key="results">
                <GridActionsCellItem
                  icon={<ResultsIcon />}
                  label="View Results"
                  onClick={() => handleViewResults(params.row)}
                />
              </Tooltip>
            );
          }

          // Show workflow button for all elections
          actions.push(
            <Tooltip title="Manage election workflow and status" key="workflow">
              <GridActionsCellItem
                icon={<WorkflowIcon />}
                label="Manage Workflow"
                onClick={() => handleWorkflow(params.row)}
              />
            </Tooltip>
          );
        }
        
        if (canUpdate) {
          actions.push(
            <Tooltip title="Edit election configuration" key="edit">
            <GridActionsCellItem
              icon={<EditIcon />}
              label="Edit"
              onClick={() => handleEdit(params.row)}
            />
            </Tooltip>
          );
          
          // Quick activate button for non-active elections
          if (!params.row.is_active && params.row.status === 'draft') {
            actions.push(
              <Tooltip title="Activate election for voting" key="activate">
              <GridActionsCellItem
                icon={<ActivateIcon />}
                label="Activate"
                onClick={() => handleActivate(params.row.id)}
              />
              </Tooltip>
            );
          }
          
          // Status change buttons with unique icons
          if (params.row.status === 'active') {
            actions.push(
              <Tooltip title="Change election status to draft" key="to-draft">
              <GridActionsCellItem
                  icon={<DraftIcon />}
                  label="Set as Draft"
                onClick={() => handleChangeStatus(params.row.id, 'draft')}
              />
              </Tooltip>
            );
          }
          
          // Publish results button for completed elections
          if (params.row.is_active && new Date() > new Date(params.row.end_date)) {
            actions.push(
              <Tooltip title="Publish election results to public" key="publish">
              <GridActionsCellItem
                icon={<PublishIcon />}
                label="Publish Results"
                onClick={() => handlePublishResults(params.row.id)}
              />
              </Tooltip>
            );
          }
        }
        
        if (canDelete) {
          actions.push(
            <Tooltip title="Delete election (cannot be undone)" key="delete">
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
        You don't have permission to view elections.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Election Management
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Elections
              </Typography>
              <Typography variant="h5">
                {stats.total_elections || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Elections
              </Typography>
              <Typography variant="h5">
                {stats.active_elections || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Upcoming Elections
              </Typography>
              <Typography variant="h5">
                {stats.upcoming_elections || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Completed Elections
              </Typography>
              <Typography variant="h5">
                {stats.completed_elections || 0}
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

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={elections}
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

      {/* Add/Edit Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {editingElection ? 'Edit Election' : 'Create New Election'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            <Grid container spacing={2}>
              {/* Basic Information */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Election Name"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Election Type</InputLabel>
                  <Select
                    value={formData.election_type}
                    onChange={(e) => setFormData({...formData, election_type: e.target.value})}
                  >
                    <MenuItem value="general">General Election</MenuItem>
                    <MenuItem value="primary">Primary Election</MenuItem>
                    <MenuItem value="local">Local Election</MenuItem>
                    <MenuItem value="special">Special Election</MenuItem>
                    <MenuItem value="referendum">Referendum</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Election Category</InputLabel>
                  <Select
                    value={formData.election_category}
                    onChange={(e) => setFormData({...formData, election_category: e.target.value})}
                  >
                    <MenuItem value="">None</MenuItem>
                    <MenuItem value="primary">Primary</MenuItem>
                    <MenuItem value="general">General</MenuItem>
                    <MenuItem value="special">Special</MenuItem>
                    <MenuItem value="runoff">Runoff</MenuItem>
                    <MenuItem value="referendum">Referendum</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description"
                  multiline
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                />
              </Grid>

              {/* Dates */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Dates & Times
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Registration Deadline"
                  type="datetime-local"
                  value={formData.registration_deadline}
                  onChange={(e) => setFormData({...formData, registration_deadline: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Voting Start Date"
                  type="datetime-local"
                  value={formData.start_date}
                  onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                  required
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Voting End Date"
                  type="datetime-local"
                  value={formData.end_date}
                  onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                  required
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Early Voting Start Date"
                  type="datetime-local"
                  value={formData.early_voting_start}
                  onChange={(e) => setFormData({...formData, early_voting_start: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                  disabled={!formData.allow_early_voting}
                  helperText={!formData.allow_early_voting ? "Enable 'Allow Early Voting' to set dates" : ""}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Early Voting End Date"
                  type="datetime-local"
                  value={formData.early_voting_end}
                  onChange={(e) => setFormData({...formData, early_voting_end: e.target.value})}
                  InputLabelProps={{ shrink: true }}
                  disabled={!formData.allow_early_voting}
                  helperText={!formData.allow_early_voting ? "Enable 'Allow Early Voting' to set dates" : ""}
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
                <TextField
                  fullWidth
                  label="Geographic Scope"
                  value={formData.geographic_scope}
                  onChange={(e) => setFormData({...formData, geographic_scope: e.target.value})}
                  placeholder="e.g., City, County, State, Federal"
                />
              </Grid>

              {/* Voting Configuration */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Voting Configuration
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Eligible Voter Types</InputLabel>
                  <Select
                    value={formData.eligible_voter_types}
                    onChange={(e) => setFormData({...formData, eligible_voter_types: e.target.value})}
                  >
                    <MenuItem value="standard">Standard</MenuItem>
                    <MenuItem value="overseas">Overseas</MenuItem>
                    <MenuItem value="military">Military</MenuItem>
                    <MenuItem value="all">All Types</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Max Votes Per Voter"
                  type="number"
                  value={formData.max_votes_per_voter}
                  onChange={(e) => setFormData({...formData, max_votes_per_voter: parseInt(e.target.value)})}
                  inputProps={{ min: 1 }}
                />
              </Grid>

              {/* Settings */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Settings
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_public}
                      onChange={(e) => setFormData({...formData, is_public: e.target.checked})}
                    />
                  }
                  label="Public Election"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_test_election}
                      onChange={(e) => setFormData({...formData, is_test_election: e.target.checked})}
                    />
                  }
                  label="Test Election"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.allow_early_voting}
                      onChange={(e) => setFormData({...formData, allow_early_voting: e.target.checked})}
                    />
                  }
                  label="Allow Early Voting"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.require_photo_id}
                      onChange={(e) => setFormData({...formData, require_photo_id: e.target.checked})}
                    />
                  }
                  label="Require Photo ID"
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
                  label="Require Biometric"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.allow_vote_changes}
                      onChange={(e) => setFormData({...formData, allow_vote_changes: e.target.checked})}
                    />
                  }
                  label="Allow Vote Changes"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.require_all_ballots}
                      onChange={(e) => setFormData({...formData, require_all_ballots: e.target.checked})}
                    />
                  }
                  label="Require All Ballots"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.audit_enabled}
                      onChange={(e) => setFormData({...formData, audit_enabled: e.target.checked})}
                    />
                  }
                  label="Audit Enabled"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.paper_trail_required}
                      onChange={(e) => setFormData({...formData, paper_trail_required: e.target.checked})}
                    />
                  }
                  label="Paper Trail Required"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {editingElection ? 'Update' : 'Create'}
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
        <DialogTitle>Election Details</DialogTitle>
        <DialogContent>
          {selectedElection && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="h6">{selectedElection.title}</Typography>
                <Typography variant="body1" color="textSecondary">
                  {selectedElection.description}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Election Type</Typography>
                <Typography variant="body1">{selectedElection.election_type}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Status</Typography>
                <Chip
                  label={getElectionStatusText(selectedElection)}
                  color={getElectionStatusColor(selectedElection)}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Voting Period</Typography>
                <Typography variant="body1">
                  {new Date(selectedElection.start_date).toLocaleDateString()} - {new Date(selectedElection.end_date).toLocaleDateString()}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Registration Deadline</Typography>
                <Typography variant="body1">
                  {selectedElection.registration_deadline
                    ? new Date(selectedElection.registration_deadline).toLocaleDateString()
                    : 'N/A'
                  }
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Max Votes Per Voter</Typography>
                <Typography variant="body1">{selectedElection.max_votes_per_voter}</Typography>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="subtitle2">Security Features</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                  <Chip
                    label={`Photo ID: ${selectedElection.require_photo_id ? 'Required' : 'Optional'}`}
                    color={selectedElection.require_photo_id ? 'success' : 'default'}
                    size="small"
                  />
                  <Chip
                    label={`Biometric: ${selectedElection.require_biometric ? 'Required' : 'Optional'}`}
                    color={selectedElection.require_biometric ? 'success' : 'default'}
                    size="small"
                  />
                  <Chip
                    label={`Audit Trail: ${selectedElection.audit_enabled ? 'Enabled' : 'Disabled'}`}
                    color={selectedElection.audit_enabled ? 'success' : 'default'}
                    size="small"
                  />
                  <Chip
                    label={`Paper Trail: ${selectedElection.paper_trail_required ? 'Required' : 'Optional'}`}
                    color={selectedElection.paper_trail_required ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Election Results Dialog */}
      <ElectionResults
        election={selectedElectionForResults}
        open={resultsDialogOpen}
        onClose={() => setResultsDialogOpen(false)}
      />

      {/* Election Workflow Dialog */}
      <ElectionWorkflow
        election={selectedElectionForWorkflow}
        open={workflowDialogOpen}
        onClose={() => setWorkflowDialogOpen(false)}
        onStatusChange={handleStatusChanged}
      />
    </Box>
  );
};

export default Elections; 
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
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  RadioGroup,
  Radio,
  FormLabel,
  Checkbox,
  FormGroup,
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
  Publish as PublishIcon,
  VisibilityOff as UnpublishIcon,
  People as CandidatesIcon,
  ContentCopy as DuplicateIcon,
  Reorder as OrderIcon,
  Preview as PreviewIcon,
  Settings as ConfigIcon,
  LocationOn as GeographyIcon,
  Shuffle as RandomizeIcon,
  ViewModule as DisplayIcon,
  Rule as RulesIcon,
  Security as SecurityIcon,
  Assignment as TestIcon,
  ExpandMore as ExpandIcon,
  CheckCircle as RequiredIcon,
  Timeline as WorkflowIcon,
  RadioButtonChecked as RadioButtonCheckedIcon,
  CheckBox as CheckBoxIcon,
  List as ListIcon,
  ThumbUp as ThumbUpIcon,
  Ballot as BallotIcon,
  Print as PrintIcon,
} from '@mui/icons-material';
import { ballotsAPI, electionsAPI, candidatesAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import { showDeleteConfirm } from '../../../utils/swal';
import { validateNonNumericText, capitalizeError } from '../../../utils/validators';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Tooltip title="Create a new ballot for an election">
      <Button startIcon={<AddIcon />} onClick={onAdd}>
        Create Ballot
      </Button>
      </Tooltip>
    )}
  </GridToolbarContainer>
);

const Ballots = () => {
  const { hasPermission } = usePermissions();
  const [ballots, setBallots] = useState([]);
  const [elections, setElections] = useState([]);
  const [configTab, setConfigTab] = useState(0);
  const [ballotCandidates, setBallotCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [candidatesDialogOpen, setCandidatesDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingBallot, setEditingBallot] = useState(null);
  const [selectedBallot, setSelectedBallot] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [stats, setStats] = useState({});
  const [formData, setFormData] = useState({
    election_id: '',
    title: '',
    description: '',
    ballot_type: 'single_choice',
    instructions: '',
    question_text: '',
    position_title: '',
    order_index: 1,
    min_selections: 0,
    max_selections: 1,
    allow_write_in: false,
    require_selection: true,
    is_active: true,
    is_published: false,
    is_test_ballot: false,
    // Enhanced fields for missing backend functionality
    display_format: 'list',
    randomize_candidates: false,
    jurisdiction_restriction: '',
    voter_type_restriction: '',
  });
  const [advancedConfig, setAdvancedConfig] = useState({
    geographic_restrictions: {
      enabled: false,
      jurisdictions: [],
      districts: [],
      precincts: [],
    },
    voter_eligibility: {
      voter_types: [],
      age_requirements: { min: 18, max: null },
      residency_required: false,
      registration_cutoff_days: 0,
    },
    voting_rules: {
      ranked_choice_options: 3,
      approval_threshold: 0.5,
      write_in_validation: false,
      time_limit_minutes: null,
    },
    display_options: {
      candidate_photos: true,
      candidate_descriptions: true,
      party_affiliations: true,
      randomization_seed: null,
    },
  });
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Ballots', 'view');
  const canCreate = hasPermission('Ballots', 'create');
  const canUpdate = hasPermission('Ballots', 'update');
  const canDelete = hasPermission('Ballots', 'delete');

  useEffect(() => {
    if (canView) {
      loadBallots();
      loadElections();
      loadStats();
    }
  }, [canView]);

  const loadBallots = async () => {
    try {
      setLoading(true);
      const response = await ballotsAPI.getAll();
      setBallots(response.data.data || []);
    } catch (error) {
      console.error('Error loading ballots:', error);
      setError('Failed to load ballots');
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

  const loadStats = async () => {
    try {
      const response = await ballotsAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const loadBallotCandidates = async (ballotId) => {
    try {
      const response = await ballotsAPI.getCandidates(ballotId);
      setBallotCandidates(response.data.candidates || []);
    } catch (error) {
      console.error('Error loading ballot candidates:', error);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingBallot(null);
  };

  const handleAdd = () => {
    setEditingBallot(null);
    setFormError('');
    setFormData({
      election_id: '',
      title: '',
      description: '',
      ballot_type: 'single_choice',
      instructions: '',
      question_text: '',
      position_title: '',
      order_index: 1,
      min_selections: 0,
      max_selections: 1,
      allow_write_in: false,
      require_selection: true,
      is_active: true,
      is_published: false,
      is_test_ballot: false,
      // Enhanced fields for missing backend functionality
      display_format: 'list',
      randomize_candidates: false,
      jurisdiction_restriction: '',
      voter_type_restriction: '',
    });
    setActiveTab(0); // Reset to basic info tab
    setDialogOpen(true);
  };

  const handleEdit = (ballot) => {
    setEditingBallot(ballot);
    setFormError('');
    setFormData({
      election_id: ballot.election_id || '',
      title: ballot.title || '',
      description: ballot.description || '',
      ballot_type: ballot.ballot_type || 'single_choice',
      instructions: ballot.instructions || '',
      question_text: ballot.question_text || '',
      position_title: ballot.position_title || '',
      order_index: ballot.order_index || 1,
      min_selections: ballot.min_selections || 0,
      max_selections: ballot.max_selections || 1,
      allow_write_in: ballot.allow_write_in || false,
      require_selection: ballot.require_selection || true,
      is_active: ballot.is_active ?? true,
      is_published: ballot.is_published || false,
      is_test_ballot: ballot.is_test_ballot || false,
      // Enhanced fields for missing backend functionality
      display_format: ballot.display_format || 'list',
      randomize_candidates: ballot.randomize_candidates || false,
      jurisdiction_restriction: ballot.jurisdiction_restriction || '',
      voter_type_restriction: ballot.voter_type_restriction || '',
    });
    setActiveTab(0); // Reset to basic info tab
    setDialogOpen(true);
  };

  const handleView = async (ballot) => {
    try {
      const response = await ballotsAPI.getById(ballot.id);
      setSelectedBallot(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError(capitalizeError('Failed to load ballot details'));
    }
  };

  const handleViewCandidates = async (ballot) => {
    try {
      setSelectedBallot(ballot);
      await loadBallotCandidates(ballot.id);
      setCandidatesDialogOpen(true);
    } catch (error) {
      setError(capitalizeError('Failed to load ballot candidates'));
    }
  };

  const handleDelete = async (ballotId) => {
    const confirmed = await showDeleteConfirm('this ballot');
    if (confirmed) {
      try {
        await ballotsAPI.delete(ballotId);
        setSuccess('Ballot deleted successfully');
        loadBallots();
        loadStats();
      } catch (error) {
        setError(capitalizeError('Failed to delete ballot'));
      }
    }
  };

  const handlePublish = async (ballotId) => {
    try {
      await ballotsAPI.publish(ballotId);
      setSuccess('Ballot published successfully');
      loadBallots();
    } catch (error) {
      setError(capitalizeError('Failed to publish ballot'));
    }
  };

  const handleUnpublish = async (ballotId) => {
    try {
      await ballotsAPI.unpublish(ballotId);
      setSuccess('Ballot unpublished successfully');
      loadBallots();
    } catch (error) {
      setError(capitalizeError('Failed to unpublish ballot'));
    }
  };

  const handleDuplicate = async (ballotId) => {
    try {
      await ballotsAPI.duplicate(ballotId, { 
        title: `Copy of ${ballots.find(b => b.id === ballotId)?.title}` 
      });
      setSuccess('Ballot duplicated successfully');
      loadBallots();
      loadStats();
    } catch (error) {
      setError(capitalizeError('Failed to duplicate ballot'));
    }
  };

  // Enhanced handler functions
  const handlePreview = (ballot) => {
    setSelectedBallot(ballot);
    setPreviewDialogOpen(true);
  };

  const handleAdvancedConfig = (ballot) => {
    setSelectedBallot(ballot);
    setConfigTab(0);
    setAdvancedConfig({
      geographic_restrictions: {
        enabled: !!ballot.jurisdiction_restriction,
        jurisdictions: ballot.jurisdiction_restriction ? [ballot.jurisdiction_restriction] : [],
        districts: [],
        precincts: [],
      },
      voter_eligibility: {
        voter_types: ballot.voter_type_restriction ? ballot.voter_type_restriction.split(',') : [],
        age_requirements: { min: 18, max: null },
        residency_required: false,
        registration_cutoff_days: 0,
      },
      voting_rules: {
        ranked_choice_options: ballot.ballot_type === 'ranked_choice' ? 3 : 1,
        approval_threshold: 0.5,
        write_in_validation: ballot.allow_write_in,
        time_limit_minutes: null,
      },
      display_options: {
        candidate_photos: true,
        candidate_descriptions: true,
        party_affiliations: true,
        randomization_seed: ballot.randomize_candidates ? Date.now() : null,
      },
    });
    setConfigDialogOpen(true);
  };

  const handleWorkflow = (ballot) => {
    // Handle ballot workflow management
    setSelectedBallot(ballot);
    // This could open a workflow dialog similar to elections
  };

  const getBallotTypeDescription = (type) => {
    switch (type) {
      case 'single_choice': return 'Voters select one option';
      case 'multiple_choice': return 'Voters can select multiple options';
      case 'ranked_choice': return 'Voters rank options in order of preference';
      case 'approval': return 'Voters approve/disapprove each option';
      default: return 'Standard voting ballot';
    }
  };

  const getBallotIcon = (type) => {
    switch (type) {
      case 'single_choice': return <RadioButtonCheckedIcon />;
      case 'multiple_choice': return <CheckBoxIcon />;
      case 'ranked_choice': return <ListIcon />;
      case 'approval': return <ThumbUpIcon />;
      default: return <BallotIcon />;
    }
  };

  const validateBallotConfiguration = (ballot) => {
    const issues = [];
    
    if (!ballot.title) issues.push('Title is required');
    if (ballot.min_selections > ballot.max_selections) {
      issues.push('Minimum selections cannot exceed maximum selections');
    }
    if (ballot.ballot_type === 'ranked_choice' && ballot.max_selections < 2) {
      issues.push('Ranked choice ballots require at least 2 maximum selections');
    }
    if (!ballot.instructions) issues.push('Voting instructions are recommended');
    
    return issues;
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'title', headerName: 'Title', width: 250 },
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
      field: 'ballot_type',
      headerName: 'Type',
      width: 140,
      renderCell: (params) => (
        <Tooltip title={getBallotTypeDescription(params.value)}>
        <Chip
            icon={getBallotIcon(params.value)}
            label={params.value?.replace('_', ' ') || 'single choice'}
          color={getBallotTypeColor(params.value)}
          size="small"
          variant="outlined"
        />
        </Tooltip>
      ),
    },
    { field: 'position_title', headerName: 'Position', width: 150 },
    { 
      field: 'order_index', 
      headerName: 'Order', 
      width: 80,
      renderCell: (params) => (
        <Chip label={params.value || 0} size="small" variant="outlined" />
      ),
    },
    {
      field: 'min_selections',
      headerName: 'Min',
      width: 60,
    },
    {
      field: 'max_selections',
      headerName: 'Max',
      width: 60,
    },
    {
      field: 'is_published',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Published' : 'Draft'}
          color={params.value ? 'success' : 'default'}
          size="small"
          icon={params.value ? <PublishIcon /> : <TestIcon />}
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
      width: 400,
      getActions: (params) => {
        const actions = [];
        
        if (canView) {
          actions.push(
            <Tooltip title="View detailed ballot information and configuration">
            <GridActionsCellItem
              icon={<ViewIcon />}
              label="View Details"
              onClick={() => handleView(params.row)}
              />
            </Tooltip>,
            <Tooltip title="Preview how this ballot will appear to voters">
            <GridActionsCellItem
                icon={<PreviewIcon />}
                label="Preview"
                onClick={() => handlePreview(params.row)}
              />
            </Tooltip>,
            <Tooltip title="View and manage candidates for this ballot">
              <GridActionsCellItem
                icon={<CandidatesIcon />}
                label="Candidates"
              onClick={() => handleViewCandidates(params.row)}
            />
            </Tooltip>
          );
        }
        
        if (canUpdate) {
          actions.push(
            <Tooltip title="Edit ballot information and voting rules">
            <GridActionsCellItem
              icon={<EditIcon />}
              label="Edit"
              onClick={() => handleEdit(params.row)}
            />
            </Tooltip>,
            <Tooltip title="Configure advanced settings and restrictions">
              <GridActionsCellItem
                icon={<ConfigIcon />}
                label="Configure"
                onClick={() => handleAdvancedConfig(params.row)}
              />
            </Tooltip>
          );
          
          if (params.row.is_published) {
            actions.push(
              <Tooltip title="Unpublish ballot to make it unavailable for voting">
              <GridActionsCellItem
                  icon={<UnpublishIcon />}
                label="Unpublish"
                onClick={() => handleUnpublish(params.row.id)}
              />
              </Tooltip>
            );
          } else {
            actions.push(
              <Tooltip title="Publish ballot to make it available for voting">
              <GridActionsCellItem
                icon={<PublishIcon />}
                label="Publish"
                onClick={() => handlePublish(params.row.id)}
              />
              </Tooltip>
            );
          }
          
          actions.push(
            <Tooltip title="Create a copy of this ballot">
            <GridActionsCellItem
                icon={<DuplicateIcon />}
              label="Duplicate"
              onClick={() => handleDuplicate(params.row.id)}
            />
            </Tooltip>
          );
        }
        
        if (canDelete) {
          actions.push(
            <Tooltip title="Permanently delete this ballot">
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

  const getElectionName = (electionId) => {
    const election = elections.find(e => e.id === electionId);
    return election ? election.title : 'Unknown';
  };

  const getBallotTypeColor = (type) => {
    switch (type) {
      case 'single_choice': return 'primary';
      case 'multiple_choice': return 'secondary';
      case 'ranked_choice': return 'info';
      case 'approval': return 'warning';
      default: return 'default';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const titleErr = validateNonNumericText(formData.title, 'Ballot title', 3, 200);
    if (titleErr) {
      setFormError(capitalizeError(titleErr));
      return;
    }

    if (formData.min_selections > formData.max_selections) {
      setFormError(capitalizeError('Minimum selections cannot exceed maximum selections'));
      return;
    }

    try {
      if (editingBallot) {
        await ballotsAPI.update(editingBallot.id, formData);
        setSuccess('Ballot updated successfully');
      } else {
        await ballotsAPI.create(formData);
        setSuccess('Ballot created successfully');
      }
      setDialogOpen(false);
      loadBallots();
      loadStats();
    } catch (error) {
      setFormError(capitalizeError((error.response?.data?.error) || 'Operation failed'));
    }
  };

  if (!canView) {
    return (
      <Alert severity="error">
        You don't have permission to view ballots.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Ballot Management
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Ballots
              </Typography>
              <Typography variant="h5">
                {stats.total_ballots || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Published Ballots
              </Typography>
              <Typography variant="h5">
                {stats.published_ballots || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Draft Ballots
              </Typography>
              <Typography variant="h5">
                {stats.draft_ballots || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Ballots
              </Typography>
              <Typography variant="h5">
                {stats.active_ballots || 0}
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
          rows={ballots}
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

      {/* Enhanced Add/Edit Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {editingBallot ? 'Edit Ballot' : 'Create New Ballot'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
              <Tab label="Basic Information" icon={<ViewIcon />} />
              <Tab label="Voting Rules" icon={<RulesIcon />} />
              <Tab label="Display & Format" icon={<DisplayIcon />} />
              <Tab label="Restrictions" icon={<GeographyIcon />} />
            </Tabs>

            {/* Basic Information Tab */}
            {activeTab === 0 && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
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
                  <InputLabel>Ballot Type</InputLabel>
                  <Select
                    value={formData.ballot_type}
                    onChange={(e) => setFormData({...formData, ballot_type: e.target.value})}
                  >
                      <MenuItem value="single_choice">Single Choice</MenuItem>
                      <MenuItem value="multiple_choice">Multiple Choice</MenuItem>
                      <MenuItem value="ranked_choice">Ranked Choice</MenuItem>
                      <MenuItem value="approval">Approval</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Ballot Title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                />
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
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Position Title"
                  value={formData.position_title}
                  onChange={(e) => setFormData({...formData, position_title: e.target.value})}
                    helperText="e.g., Mayor, Governor, President"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Order Index"
                  type="number"
                  value={formData.order_index}
                  onChange={(e) => setFormData({...formData, order_index: parseInt(e.target.value)})}
                  inputProps={{ min: 1 }}
                    helperText="Order of appearance on ballot"
                />
              </Grid>
              
                {formData.ballot_type !== 'single_choice' && (
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Question Text"
                      multiline
                      rows={3}
                      value={formData.question_text}
                      onChange={(e) => setFormData({...formData, question_text: e.target.value})}
                      helperText="For referendum/proposition ballots"
                    />
                  </Grid>
                )}
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Voting Instructions"
                    multiline
                    rows={3}
                    value={formData.instructions}
                    onChange={(e) => setFormData({...formData, instructions: e.target.value})}
                    helperText="Instructions for voters on how to complete this ballot"
                  />
                </Grid>
              </Grid>
            )}

            {/* Voting Rules Tab */}
            {activeTab === 1 && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Minimum Selections"
                  type="number"
                  value={formData.min_selections}
                  onChange={(e) => setFormData({...formData, min_selections: parseInt(e.target.value)})}
                    inputProps={{ min: 0 }}
                    helperText="Minimum required selections (0 = optional)"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Maximum Selections"
                  type="number"
                  value={formData.max_selections}
                  onChange={(e) => setFormData({...formData, max_selections: parseInt(e.target.value)})}
                  inputProps={{ min: 1 }}
                    helperText="Maximum allowed selections"
                />
              </Grid>
              
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.allow_write_in}
                        onChange={(e) => setFormData({...formData, allow_write_in: e.target.checked})}
                      />
                    }
                    label="Allow Write-in Candidates"
                  />
                </Grid>
              
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.require_selection}
                        onChange={(e) => setFormData({...formData, require_selection: e.target.checked})}
                      />
                    }
                    label="Require Selection (Mandatory Ballot)"
                />
              </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.is_test_ballot}
                        onChange={(e) => setFormData({...formData, is_test_ballot: e.target.checked})}
                      />
                    }
                    label="Test Ballot"
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.randomize_candidates}
                        onChange={(e) => setFormData({...formData, randomize_candidates: e.target.checked})}
                      />
                    }
                    label="Randomize Candidate Order"
                  />
                </Grid>
              </Grid>
            )}

            {/* Display & Format Tab */}
            {activeTab === 2 && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Display Format</InputLabel>
                    <Select
                      value={formData.display_format}
                      onChange={(e) => setFormData({...formData, display_format: e.target.value})}
                    >
                      <MenuItem value="list">List Format</MenuItem>
                      <MenuItem value="grid">Grid Format</MenuItem>
                      <MenuItem value="carousel">Carousel Format</MenuItem>
                    </Select>
                  </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_active}
                      onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    />
                  }
                  label="Active"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_published}
                      onChange={(e) => setFormData({...formData, is_published: e.target.checked})}
                    />
                  }
                  label="Published"
                />
              </Grid>
              </Grid>
            )}

            {/* Restrictions Tab */}
            {activeTab === 3 && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Geographic Restrictions
                  </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Jurisdiction Restriction"
                    value={formData.jurisdiction_restriction}
                    onChange={(e) => setFormData({...formData, jurisdiction_restriction: e.target.value})}
                    helperText="Limit ballot to specific geographic area"
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Voter Type Restriction"
                    value={formData.voter_type_restriction}
                    onChange={(e) => setFormData({...formData, voter_type_restriction: e.target.value})}
                    helperText="Limit to specific voter types (comma-separated)"
                  />
                </Grid>
              </Grid>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {editingBallot ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Ballot Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PreviewIcon />
            <Typography variant="h6">
              Ballot Preview: {selectedBallot?.title}
            </Typography>
            <Chip 
              label={selectedBallot?.ballot_type?.replace('_', ' ')}
              color={getBallotTypeColor(selectedBallot?.ballot_type)}
              size="small"
            />
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedBallot && (
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  {selectedBallot.title}
                </Typography>
                
                {selectedBallot.position_title && (
                  <Typography variant="subtitle1" color="textSecondary" gutterBottom>
                    Position: {selectedBallot.position_title}
                  </Typography>
                )}
                
                {selectedBallot.description && (
                  <Typography variant="body1" paragraph>
                    {selectedBallot.description}
                  </Typography>
                )}
                
                {selectedBallot.question_text && (
                  <Box sx={{ p: 2, backgroundColor: 'grey.100', borderRadius: 1, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>Question:</Typography>
                    <Typography variant="body1">{selectedBallot.question_text}</Typography>
                  </Box>
                )}
                
                <Divider sx={{ my: 2 }} />
                
                <Typography variant="h6" gutterBottom>Voting Instructions:</Typography>
                <Typography variant="body2" paragraph>
                  {selectedBallot.instructions || 'No specific instructions provided.'}
                </Typography>
                
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Voting Rules: Select {selectedBallot.min_selections === 0 ? 'up to' : 'between'} {' '}
                    {selectedBallot.min_selections === 0 ? '' : selectedBallot.min_selections + ' and'} {' '}
                    {selectedBallot.max_selections} option{selectedBallot.max_selections > 1 ? 's' : ''}
                    {selectedBallot.allow_write_in && ' (Write-ins allowed)'}
                  </Typography>
                </Box>
                
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Display Format: {selectedBallot.display_format || 'list'} | 
                    Order: {selectedBallot.randomize_candidates ? 'Randomized' : 'Fixed'} |
                    {selectedBallot.require_selection ? ' Required' : ' Optional'}
                  </Typography>
                </Box>
                
                {(selectedBallot.jurisdiction_restriction || selectedBallot.voter_type_restriction) && (
                  <Box sx={{ mt: 2, p: 2, backgroundColor: 'warning.light', borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>Restrictions:</Typography>
                    {selectedBallot.jurisdiction_restriction && (
                      <Typography variant="body2">
                        • Geographic: {selectedBallot.jurisdiction_restriction}
                      </Typography>
                    )}
                    {selectedBallot.voter_type_restriction && (
                      <Typography variant="body2">
                        • Voter Types: {selectedBallot.voter_type_restriction}
                      </Typography>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>Close</Button>
          <Button variant="outlined" startIcon={<PrintIcon />}>
            Print Preview
          </Button>
        </DialogActions>
      </Dialog>

      {/* Advanced Configuration Dialog */}
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ConfigIcon />
            <Typography variant="h6">
              Advanced Configuration: {selectedBallot?.title}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ width: '100%' }}>
            <Tabs value={configTab} onChange={(e, newValue) => setConfigTab(newValue)}>
              <Tab label="Geographic Restrictions" icon={<GeographyIcon />} />
              <Tab label="Voter Eligibility" icon={<CandidatesIcon />} />
              <Tab label="Voting Rules" icon={<RulesIcon />} />
              <Tab label="Display Options" icon={<DisplayIcon />} />
            </Tabs>
            
            {/* Geographic Restrictions Tab */}
            {configTab === 0 && (
              <Box sx={{ mt: 2 }}>
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandIcon />}>
                    <Typography variant="h6">Geographic Restrictions</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                              checked={advancedConfig.geographic_restrictions.enabled}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                geographic_restrictions: {
                                  ...advancedConfig.geographic_restrictions,
                                  enabled: e.target.checked
                                }
                              })}
                    />
                  }
                          label="Enable Geographic Restrictions"
                />
              </Grid>
                      
                      {advancedConfig.geographic_restrictions.enabled && (
                        <>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              label="Jurisdictions"
                              value={advancedConfig.geographic_restrictions.jurisdictions.join(', ')}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                geographic_restrictions: {
                                  ...advancedConfig.geographic_restrictions,
                                  jurisdictions: e.target.value.split(',').map(j => j.trim())
                                }
                              })}
                              helperText="Comma-separated list"
                            />
                          </Grid>
                          
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              label="Districts"
                              value={advancedConfig.geographic_restrictions.districts.join(', ')}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                geographic_restrictions: {
                                  ...advancedConfig.geographic_restrictions,
                                  districts: e.target.value.split(',').map(d => d.trim())
                                }
                              })}
                              helperText="Comma-separated list"
                            />
                          </Grid>
                          
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              label="Precincts"
                              value={advancedConfig.geographic_restrictions.precincts.join(', ')}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                geographic_restrictions: {
                                  ...advancedConfig.geographic_restrictions,
                                  precincts: e.target.value.split(',').map(p => p.trim())
                                }
                              })}
                              helperText="Comma-separated list"
                            />
                          </Grid>
                        </>
                      )}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Box>
            )}
            
            {/* Voter Eligibility Tab */}
            {configTab === 1 && (
              <Box sx={{ mt: 2 }}>
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandIcon />}>
                    <Typography variant="h6">Voter Eligibility Requirements</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <FormLabel component="legend">Eligible Voter Types</FormLabel>
                        <FormGroup row>
                          {['standard', 'overseas', 'military', 'absentee'].map((type) => (
                            <FormControlLabel
                              key={type}
                              control={
                                <Checkbox
                                  checked={advancedConfig.voter_eligibility.voter_types.includes(type)}
                                  onChange={(e) => {
                                    const types = e.target.checked
                                      ? [...advancedConfig.voter_eligibility.voter_types, type]
                                      : advancedConfig.voter_eligibility.voter_types.filter(t => t !== type);
                                    setAdvancedConfig({
                                      ...advancedConfig,
                                      voter_eligibility: {
                                        ...advancedConfig.voter_eligibility,
                                        voter_types: types
                                      }
                                    });
                                  }}
                                />
                              }
                              label={type.charAt(0).toUpperCase() + type.slice(1)}
                            />
                          ))}
                        </FormGroup>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                        <TextField
                           fullWidth
                           label="Minimum Age"
                           type="number"
                           value={advancedConfig.voter_eligibility.age_requirements.min}
                           onChange={(e) => setAdvancedConfig({
                             ...advancedConfig,
                             voter_eligibility: {
                               ...advancedConfig.voter_eligibility,
                               age_requirements: {
                                 ...advancedConfig.voter_eligibility.age_requirements,
                                 min: parseInt(e.target.value)
                               }
                             }
                           })}
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Registration Cutoff (days)"
                          type="number"
                          value={advancedConfig.voter_eligibility.registration_cutoff_days}
                          onChange={(e) => setAdvancedConfig({
                            ...advancedConfig,
                            voter_eligibility: {
                              ...advancedConfig.voter_eligibility,
                              registration_cutoff_days: parseInt(e.target.value)
                            }
                          })}
                          helperText="Days before election registration closes"
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Box>
            )}
            
            {/* Voting Rules Tab */}
            {configTab === 2 && (
              <Box sx={{ mt: 2 }}>
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandIcon />}>
                    <Typography variant="h6">Advanced Voting Rules</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      {selectedBallot?.ballot_type === 'ranked_choice' && (
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Ranked Choice Options"
                            type="number"
                            value={advancedConfig.voting_rules.ranked_choice_options}
                            onChange={(e) => setAdvancedConfig({
                              ...advancedConfig,
                              voting_rules: {
                                ...advancedConfig.voting_rules,
                                ranked_choice_options: parseInt(e.target.value)
                              }
                            })}
                            helperText="Number of ranking options"
                          />
                        </Grid>
                      )}
                      
                      {selectedBallot?.ballot_type === 'approval' && (
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Approval Threshold"
                            type="number"
                            value={advancedConfig.voting_rules.approval_threshold}
                            onChange={(e) => setAdvancedConfig({
                              ...advancedConfig,
                              voting_rules: {
                                ...advancedConfig.voting_rules,
                                approval_threshold: parseFloat(e.target.value)
                              }
                            })}
                            inputProps={{ min: 0, max: 1, step: 0.1 }}
                            helperText="Threshold for approval (0-1)"
                          />
                        </Grid>
                      )}
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Time Limit (minutes)"
                          type="number"
                          value={advancedConfig.voting_rules.time_limit_minutes || ''}
                          onChange={(e) => setAdvancedConfig({
                            ...advancedConfig,
                            voting_rules: {
                              ...advancedConfig.voting_rules,
                              time_limit_minutes: e.target.value ? parseInt(e.target.value) : null
                            }
                          })}
                          helperText="Optional time limit for ballot completion"
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                              checked={advancedConfig.voting_rules.write_in_validation}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                voting_rules: {
                                  ...advancedConfig.voting_rules,
                                  write_in_validation: e.target.checked
                                }
                              })}
                    />
                  }
                          label="Validate Write-in Candidates"
                />
              </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Box>
            )}
            
            {/* Display Options Tab */}
            {configTab === 3 && (
              <Box sx={{ mt: 2 }}>
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandIcon />}>
                    <Typography variant="h6">Display and Presentation Options</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                              checked={advancedConfig.display_options.candidate_photos}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                display_options: {
                                  ...advancedConfig.display_options,
                                  candidate_photos: e.target.checked
                                }
                              })}
                    />
                  }
                          label="Show Candidate Photos"
                />
              </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={advancedConfig.display_options.candidate_descriptions}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                display_options: {
                                  ...advancedConfig.display_options,
                                  candidate_descriptions: e.target.checked
                                }
                              })}
                            />
                          }
                          label="Show Candidate Descriptions"
                        />
             </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={advancedConfig.display_options.party_affiliations}
                              onChange={(e) => setAdvancedConfig({
                                ...advancedConfig,
                                display_options: {
                                  ...advancedConfig.display_options,
                                  party_affiliations: e.target.checked
                                }
                              })}
                            />
                          }
                          label="Show Party Affiliations"
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Randomization Seed"
                          value={advancedConfig.display_options.randomization_seed || ''}
                          onChange={(e) => setAdvancedConfig({
                            ...advancedConfig,
                            display_options: {
                              ...advancedConfig.display_options,
                              randomization_seed: e.target.value ? parseInt(e.target.value) : null
                            }
                          })}
                          helperText="Fixed seed for consistent randomization"
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Box>
            )}
          </Box>
          </DialogContent>
          <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            startIcon={<ConfigIcon />}
            onClick={async () => {
              setError('');
              setSuccess('');
              try {
                await ballotsAPI.update(selectedBallot.id, {
                  jurisdiction_restriction: advancedConfig.geographic_restrictions.jurisdictions.join(','),
                  voter_type_restriction: advancedConfig.voter_eligibility.voter_types.join(',')
                });
                setSuccess('Configuration saved successfully');
                loadBallots();
                setConfigDialogOpen(false);
              } catch (err) {
                setError(err.response?.data?.error || 'Failed to save configuration');
              }
            }}
          >
            Save Configuration
            </Button>
          </DialogActions>
      </Dialog>

      {/* Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Ballot Details</DialogTitle>
        <DialogContent>
          {selectedBallot && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="h6">{selectedBallot.title}</Typography>
                <Typography variant="body1" color="textSecondary">
                  {selectedBallot.description}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Election</Typography>
                <Typography variant="body1">{getElectionName(selectedBallot.election_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Type</Typography>
                <Chip
                  label={selectedBallot.ballot_type}
                  color={getBallotTypeColor(selectedBallot.ballot_type)}
                  size="small"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Position</Typography>
                <Typography variant="body1">{selectedBallot.position_title || 'N/A'}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Order Index</Typography>
                <Typography variant="body1">{selectedBallot.order_index}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Selections</Typography>
                <Typography variant="body1">
                  {selectedBallot.min_selections} - {selectedBallot.max_selections}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Status</Typography>
                <Chip
                  label={selectedBallot.is_published ? 'Published' : 'Draft'}
                  color={selectedBallot.is_published ? 'success' : 'default'}
                />
              </Grid>
              
              {selectedBallot.question_text && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Question</Typography>
                  <Typography variant="body1">{selectedBallot.question_text}</Typography>
                </Grid>
              )}
              
              {selectedBallot.instructions && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Instructions</Typography>
                  <Typography variant="body1">{selectedBallot.instructions}</Typography>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Candidates Dialog */}
      <Dialog
        open={candidatesDialogOpen}
        onClose={() => setCandidatesDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Ballot Candidates - {selectedBallot?.title}
        </DialogTitle>
        <DialogContent>
          {ballotCandidates.length === 0 ? (
            <Alert severity="info">
              No candidates assigned to this ballot yet.
            </Alert>
          ) : (
            <List>
              {ballotCandidates.map((candidate, index) => (
                <ListItem key={candidate.id}>
                  <ListItemText
                    primary={candidate.name}
                    secondary={`${candidate.party || 'Independent'} - Order: ${candidate.order_index || index + 1}`}
                  />
                  <ListItemSecondaryAction>
                    <Chip
                      label={candidate.is_active ? 'Active' : 'Inactive'}
                      color={candidate.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCandidatesDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Ballots; 
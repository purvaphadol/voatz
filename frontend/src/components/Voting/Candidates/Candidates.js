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
  Switch,
  Grid,
  Card,
  CardContent,
  CardActions,
  Avatar,
  Divider,

  Stack,
  Badge,
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
  PersonOff as WithdrawIcon,
  PersonAdd as ReinstateIcon,
  Person as PersonIcon,
  People as PeopleIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  EmojiEvents as IncumbentIcon,
  Groups as TotalIcon,
  HowToReg as CandidateIcon,
  Star as EndorsedIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  CloudUpload as UploadIcon,
  Image as ImageIcon,
  Clear as ClearIcon,
  PhotoCamera as CameraIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import { candidatesAPI, ballotsAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import { showDeleteConfirm, showConfirmDialog } from '../../../utils/swal';
import { validateNonNumericText, validateEmail, validatePhone, validateUrl, capitalizeError } from '../../../utils/validators';

const CustomToolbar = ({ onAdd, hasCreatePermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasCreatePermission && (
      <Tooltip title="Add a new candidate to a ballot">
        <Button startIcon={<AddIcon />} onClick={onAdd}>
          Add Candidate
        </Button>
      </Tooltip>
    )}
  </GridToolbarContainer>
);

const Candidates = () => {
  const { hasPermission } = usePermissions();
  const [candidates, setCandidates] = useState([]);
  const [ballots, setBallots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [withdrawCandidate, setWithdrawCandidate] = useState(null);
  const [stats, setStats] = useState({});
  const [formData, setFormData] = useState({
    ballot_id: '',
    name: '',
    party: '',
    party_abbreviation: '',
    candidate_code: '',
    biography: '',
    description: '',
    platform_summary: '',
    title: '',
    website: '',
    email: '',
    phone: '',
    image_url: '',
    order_index: 1,
    is_incumbent: false,
    is_endorsed: false,
    age: '',
    education: '',
    occupation: '',
    campaign_website: '',
    key_issues: [],
  });
  const [withdrawalData, setWithdrawalData] = useState({
    withdrawal_reason: '',
    withdrawal_date: '',
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
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [uploadMethod, setUploadMethod] = useState('upload'); // 'upload' or 'url'
  const [uploading, setUploading] = useState(false);

  const canView = hasPermission('Candidates', 'view');
  const canCreate = hasPermission('Candidates', 'create');
  const canUpdate = hasPermission('Candidates', 'update');
  const canDelete = hasPermission('Candidates', 'delete');

  useEffect(() => {
    if (canView) {
      loadCandidates();
      loadBallots();
      loadStats();
    }
  }, [canView]);

  const loadCandidates = async () => {
    try {
      setLoading(true);
      const response = await candidatesAPI.getAll();
      setCandidates(response.data.data || []);
    } catch (error) {
      console.error('Error loading candidates:', error);
      setError('Failed to load candidates');
    } finally {
      setLoading(false);
    }
  };

  const loadBallots = async () => {
    try {
      const response = await ballotsAPI.getAll();
      setBallots(response.data.data || []);
    } catch (error) {
      console.error('Error loading ballots:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await candidatesAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleImageFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setError('Image size must be less than 5MB');
        return;
      }
      
      if (!file.type.startsWith('image/')) {
        setError('Please select a valid image file');
        return;
      }

      setImageFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target.result);
        setFormData({...formData, image_url: e.target.result});
      };
      reader.readAsDataURL(file);
    }
  };

  const handleImageUpload = async () => {
    if (!imageFile) return;

    setUploading(true);
    try {
      const response = await candidatesAPI.uploadImage(imageFile);
      const imageUrl = response.data.image_url;
      setFormData({ ...formData, image_url: imageUrl });
      setSuccess('Image uploaded successfully');
    } catch (error) {
      setError('Failed to upload image: ' + (error.response?.data?.error || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleClearImage = () => {
    setImageFile(null);
    setImagePreview('');
    setFormData({...formData, image_url: ''});
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      handleImageFileSelect({ target: { files: [file] } });
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormError('');
    setEditingCandidate(null);
  };

  const handleAdd = () => {
    setEditingCandidate(null);
    setFormError('');
    setFormData({
      ballot_id: '',
      name: '',
      party: '',
      party_abbreviation: '',
      candidate_code: '',
      biography: '',
      description: '',
      platform_summary: '',
      title: '',
      website: '',
      email: '',
      phone: '',
      image_url: '',
      order_index: 1,
      is_incumbent: false,
      is_endorsed: false,
      age: '',
      education: '',
      occupation: '',
      campaign_website: '',
      key_issues: [],
    });
    // Reset image state
    setImageFile(null);
    setImagePreview('');
    setUploadMethod('upload');
    setDialogOpen(true);
  };

  const handleEdit = (candidate) => {
    setEditingCandidate(candidate);
    setFormError('');
    setFormData({
      ballot_id: candidate.ballot_id || '',
      name: candidate.name || '',
      party: candidate.party || '',
      party_abbreviation: candidate.party_abbreviation || '',
      candidate_code: candidate.candidate_code || '',
      biography: candidate.biography || '',
      description: candidate.description || '',
      platform_summary: candidate.platform_summary || '',
      title: candidate.title || '',
      website: candidate.website || '',
      email: candidate.email || '',
      phone: candidate.phone || '',
      image_url: candidate.image_url || '',
      order_index: candidate.order_index || 1,
      is_incumbent: candidate.is_incumbent || false,
      is_endorsed: candidate.is_endorsed || false,
      age: candidate.age || '',
      education: candidate.education || '',
      occupation: candidate.occupation || '',
      campaign_website: candidate.campaign_website || '',
      key_issues: candidate.key_issues || [],
    });
    // Set image state for editing
    setImageFile(null);
    setImagePreview(candidate.image_url || '');
    setUploadMethod(candidate.image_url ? (candidate.image_url.startsWith('data:') ? 'upload' : 'url') : 'upload');
    setDialogOpen(true);
  };

  const handleView = async (candidate) => {
    try {
      const response = await candidatesAPI.getById(candidate.id);
      setSelectedCandidate(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError(capitalizeError('Failed to load candidate details'));
    }
  };

  const handleDelete = async (candidateId) => {
    const confirmed = await showDeleteConfirm('this candidate');
    if (confirmed) {
      try {
        await candidatesAPI.delete(candidateId);
        setSuccess('Candidate deleted successfully');
        loadCandidates();
        loadStats();
      } catch (error) {
        setError(capitalizeError('Failed to delete candidate'));
      }
    }
  };

  const handleWithdraw = (candidate) => {
    setWithdrawCandidate(candidate);
    setWithdrawalData({
      withdrawal_reason: '',
      withdrawal_date: new Date().toISOString().split('T')[0],
    });
    setWithdrawDialogOpen(true);
  };

  const handleConfirmWithdrawal = async () => {
    try {
      await candidatesAPI.withdraw(withdrawCandidate.id, withdrawalData);
      setSuccess('Candidate withdrawn successfully');
      setWithdrawDialogOpen(false);
      loadCandidates();
      loadStats();
    } catch (error) {
      setError(capitalizeError('Failed to withdraw candidate'));
    }
  };

  const handleReinstate = async (candidateId) => {
    const confirmed = await showConfirmDialog({
      title: 'Reinstate Candidate',
      text: 'Are you sure you want to reinstate this candidate back to active status?',
      icon: 'question',
      confirmButtonText: 'Yes, reinstate',
      confirmButtonColor: '#2e7d32',
    });
    if (confirmed) {
      try {
        await candidatesAPI.reinstate(candidateId);
        setSuccess('Candidate reinstated successfully');
        loadCandidates();
        loadStats();
      } catch (error) {
        setError(capitalizeError('Failed to reinstate candidate'));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');

    const nameErr = validateNonNumericText(formData.name, 'Candidate name', 2, 100);
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

    if (formData.image_url) {
      const urlErr = validateUrl(formData.image_url);
      if (urlErr) {
        setFormError(capitalizeError(urlErr));
        return;
      }
    }

    try {
      if (editingCandidate) {
        await candidatesAPI.update(editingCandidate.id, formData);
        setSuccess('Candidate updated successfully');
      } else {
        await candidatesAPI.create(formData);
        setSuccess('Candidate created successfully');
      }
      setDialogOpen(false);
      loadCandidates();
      loadStats();
    } catch (error) {
      console.error('Candidate operation failed:', error);
      setFormError(capitalizeError((error.response?.data?.error) || 'Operation failed'));
    }
  };

  const getBallotTitle = (ballotId) => {
    const ballot = ballots.find(b => b.id === ballotId);
    return ballot ? ballot.title : 'Unknown';
  };

  const getPartyColor = (party) => {
    switch (party?.toLowerCase()) {
      case 'democratic':
      case 'democrat':
        return 'primary';
      case 'republican':
        return 'error';
      case 'independent':
        return 'secondary';
      case 'green':
        return 'success';
      case 'libertarian':
        return 'warning';
      default:
        return 'default';
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'image_url',
      headerName: 'Photo',
      width: 80,
      renderCell: (params) => (
        <Avatar
          src={params.value}
          alt={params.row.name}
          sx={{ width: 40, height: 40 }}
          onError={(e) => {
            console.warn(`Image failed to load for ${params.row.name}:`, e);
          }}
        >
          <PersonIcon />
        </Avatar>
      ),
    },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'candidate_code', headerName: 'Code', width: 100 },
    {
      field: 'party',
      headerName: 'Party',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={params.value || 'Independent'}
          color={getPartyColor(params.value)}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'ballot_id',
      headerName: 'Ballot',
      width: 200,
      renderCell: (params) => (
        <Typography variant="body2">
          {getBallotTitle(params.value)}
        </Typography>
      ),
    },
    {
      field: 'is_incumbent',
      headerName: 'Incumbent',
      width: 100,
      renderCell: (params) => (
        <Tooltip title={params.value ? 'Current office holder' : 'Not an incumbent'}>
          <Chip
            label={params.value ? 'Yes' : 'No'}
            color={params.value ? 'success' : 'default'}
            size="small"
            icon={params.value ? <IncumbentIcon /> : undefined}
          />
        </Tooltip>
      ),
    },
    {
      field: 'is_withdrawn',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Tooltip title={params.value ? 'Candidate has withdrawn from election' : 'Active candidate in election'}>
          <Chip
            label={params.value ? 'Withdrawn' : 'Active'}
            color={params.value ? 'error' : 'success'}
            size="small"
            icon={params.value ? <InactiveIcon /> : <ActiveIcon />}
          />
        </Tooltip>
      ),
    },
    { field: 'order_index', headerName: 'Order', width: 80 },
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
      width: 200,
      getActions: (params) => {
        const actions = [];
        
        if (canView) {
          actions.push(
            <Tooltip title="View comprehensive candidate details, biography, and campaign information" key="view">
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
            <Tooltip title="Edit candidate information, party affiliation, and campaign details" key="edit">
              <GridActionsCellItem
                icon={<EditIcon />}
                label="Edit"
                onClick={() => handleEdit(params.row)}
              />
            </Tooltip>
          );
          
          if (params.row.is_withdrawn) {
            actions.push(
              <Tooltip title="Reinstate this withdrawn candidate back to active status" key="reinstate">
                <GridActionsCellItem
                  icon={<ReinstateIcon />}
                  label="Reinstate"
                  onClick={() => handleReinstate(params.row.id)}
                />
              </Tooltip>
            );
          } else {
            actions.push(
              <Tooltip title="Withdraw this candidate from the election with reason" key="withdraw">
                <GridActionsCellItem
                  icon={<WithdrawIcon />}
                  label="Withdraw"
                  onClick={() => handleWithdraw(params.row)}
                />
              </Tooltip>
            );
          }
        }
        
        if (canDelete) {
          actions.push(
            <Tooltip title="Permanently delete this candidate (cannot be undone if no votes cast)" key="delete">
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
        You don't have permission to view candidates.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48 }}>
          <PeopleIcon />
        </Avatar>
        <Typography variant="h4" gutterBottom>
          Candidate Management
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Candidates
                  </Typography>
                  <Typography variant="h5">
                    {stats.total_candidates || 0}
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
                    Active Candidates
                  </Typography>
                  <Typography variant="h5">
                    {stats.active_candidates || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'success.main', width: 56, height: 56 }}>
                  <ActiveIcon />
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
                    Withdrawn Candidates
                  </Typography>
                  <Typography variant="h5">
                    {stats.withdrawn_candidates || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'error.main', width: 56, height: 56 }}>
                  <InactiveIcon />
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
                    Incumbents
                  </Typography>
                  <Typography variant="h5">
                    {stats.incumbent_candidates || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'warning.main', width: 56, height: 56 }}>
                  <IncumbentIcon />
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
          rows={candidates}
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
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingCandidate ? 'Edit Candidate' : 'Add New Candidate'}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent ref={dialogContentRef}>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Tooltip title="Select which ballot this candidate will appear on">
                  <FormControl fullWidth required>
                    <InputLabel>Ballot</InputLabel>
                    <Select
                      value={formData.ballot_id}
                      onChange={(e) => setFormData({...formData, ballot_id: e.target.value})}
                    >
                      {ballots.map((ballot) => (
                        <MenuItem key={ballot.id} value={ballot.id}>
                          {ballot.title}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Tooltip>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Tooltip title="Unique identifier for this candidate (auto-generated if left empty)">
                  <TextField
                    fullWidth
                    label="Candidate Code"
                    value={formData.candidate_code}
                    onChange={(e) => setFormData({...formData, candidate_code: e.target.value})}
                    placeholder="Leave empty for auto-generation"
                  />
                </Tooltip>
              </Grid>
              
              <Grid item xs={12}>
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
                  label="Party"
                  value={formData.party}
                  onChange={(e) => setFormData({...formData, party: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Party Abbreviation"
                  value={formData.party_abbreviation}
                  onChange={(e) => setFormData({...formData, party_abbreviation: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Title/Position"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Tooltip title="Order in which this candidate appears on the ballot (1 = first position)">
                  <TextField
                    fullWidth
                    label="Display Order"
                    type="number"
                    value={formData.order_index}
                    onChange={(e) => setFormData({...formData, order_index: parseInt(e.target.value)})}
                    inputProps={{ min: 1 }}
                    helperText="Lower numbers appear first on ballot"
                  />
                </Tooltip>
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
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Website"
                  value={formData.website}
                  onChange={(e) => setFormData({...formData, website: e.target.value})}
                />
              </Grid>
              
              {/* Image Upload Section */}
              <Grid item xs={12}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Candidate Photo
                  </Typography>
                  
                  {/* Upload Method Tabs */}
                  <Tabs
                    value={uploadMethod}
                    onChange={(e, newValue) => setUploadMethod(newValue)}
                    sx={{ mb: 2 }}
                  >
                    <Tab 
                      value="upload" 
                      label="Upload Image" 
                      icon={<UploadIcon />}
                      iconPosition="start"
                    />
                    <Tab 
                      value="url" 
                      label="Image URL" 
                      icon={<LinkIcon />}
                      iconPosition="start"
                    />
                  </Tabs>

                  {/* File Upload */}
                  {uploadMethod === 'upload' && (
                    <Box>
                      {/* Upload Area */}
                      <Box
                        sx={{
                          border: '2px dashed #ccc',
                          borderRadius: 2,
                          p: 3,
                          textAlign: 'center',
                          backgroundColor: '#fafafa',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            borderColor: 'primary.main',
                            backgroundColor: '#f0f7ff',
                          },
                        }}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        onClick={() => document.getElementById('image-upload-input').click()}
                      >
                        <input
                          id="image-upload-input"
                          type="file"
                          accept="image/*"
                          onChange={handleImageFileSelect}
                          style={{ display: 'none' }}
                        />
                        
                        {imagePreview || formData.image_url ? (
                          <Box>
                            <Avatar
                              src={imagePreview || formData.image_url}
                              sx={{ width: 120, height: 120, mx: 'auto', mb: 2 }}
                            >
                              <PersonIcon sx={{ fontSize: 60 }} />
                            </Avatar>
                            <Typography variant="body2" color="textSecondary" gutterBottom>
                              {imageFile ? imageFile.name : 'Current image'}
                            </Typography>
                            <Stack direction="row" spacing={1} justifyContent="center">
                              <Button
                                startIcon={<CameraIcon />}
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  document.getElementById('image-upload-input').click();
                                }}
                              >
                                Change Image
                              </Button>
                              <Button
                                startIcon={<ClearIcon />}
                                size="small"
                                color="error"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleClearImage();
                                }}
                              >
                                Remove
                              </Button>
                            </Stack>
                          </Box>
                        ) : (
                          <Box>
                            <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                            <Typography variant="h6" gutterBottom>
                              Upload Candidate Photo
                            </Typography>
                            <Typography variant="body2" color="textSecondary" gutterBottom>
                              Drag and drop an image here, or click to browse
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Supports: JPG, PNG, GIF (Max: 5MB)
                            </Typography>
                          </Box>
                        )}
                      </Box>
                      
                      {imageFile && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="body2" color="textSecondary">
                            File: {imageFile.name} ({(imageFile.size / 1024 / 1024).toFixed(2)} MB)
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  )}

                  {/* URL Input */}
                  {uploadMethod === 'url' && (
                    <Box>
                      <TextField
                        fullWidth
                        label="Image URL"
                        value={formData.image_url}
                        onChange={(e) => {
                          setFormData({...formData, image_url: e.target.value});
                          setImagePreview(e.target.value);
                        }}
                        placeholder="https://example.com/candidate-photo.jpg"
                        sx={{ mb: 2 }}
                      />
                      
                      {formData.image_url && (
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="body2" gutterBottom>
                            Image Preview:
                          </Typography>
                          <Avatar
                            src={formData.image_url}
                            sx={{ width: 120, height: 120, mx: 'auto' }}
                            onError={() => setError('Invalid image URL')}
                          >
                            <PersonIcon sx={{ fontSize: 60 }} />
                          </Avatar>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Age"
                  type="number"
                  value={formData.age}
                  onChange={(e) => setFormData({...formData, age: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Education"
                  value={formData.education}
                  onChange={(e) => setFormData({...formData, education: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Occupation"
                  value={formData.occupation}
                  onChange={(e) => setFormData({...formData, occupation: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Biography"
                  multiline
                  rows={3}
                  value={formData.biography}
                  onChange={(e) => setFormData({...formData, biography: e.target.value})}
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
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Platform Summary"
                  multiline
                  rows={4}
                  value={formData.platform_summary}
                  onChange={(e) => setFormData({...formData, platform_summary: e.target.value})}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_incumbent}
                      onChange={(e) => setFormData({...formData, is_incumbent: e.target.checked})}
                    />
                  }
                  label="Incumbent"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_endorsed}
                      onChange={(e) => setFormData({...formData, is_endorsed: e.target.checked})}
                    />
                  }
                  label="Endorsed"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Tooltip title="Cancel and discard changes">
              <Button onClick={() => setDialogOpen(false)} startIcon={<InactiveIcon />}>
                Cancel
              </Button>
            </Tooltip>
            <Tooltip title={editingCandidate ? "Save changes to candidate information" : "Create new candidate with provided information"}>
              <Button type="submit" variant="contained" startIcon={editingCandidate ? <EditIcon /> : <AddIcon />}>
                {editingCandidate ? 'Update Candidate' : 'Create Candidate'}
              </Button>
            </Tooltip>
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
        <DialogTitle>Candidate Details</DialogTitle>
        <DialogContent>
          {selectedCandidate && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={3}>
                <Avatar
                  src={selectedCandidate.image_url}
                  alt={selectedCandidate.name}
                  sx={{ width: 120, height: 120, mx: 'auto' }}
                >
                  <PersonIcon sx={{ fontSize: 60 }} />
                </Avatar>
              </Grid>
              
              <Grid item xs={12} sm={9}>
                <Typography variant="h5" gutterBottom>
                  {selectedCandidate.name}
                </Typography>
                <Typography variant="h6" color="textSecondary" gutterBottom>
                  {selectedCandidate.party || 'Independent'}
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Tooltip title={selectedCandidate.is_incumbent ? 'Currently holds this office' : 'Challenging for this office'}>
                    <Chip
                      label={selectedCandidate.is_incumbent ? 'Incumbent' : 'Challenger'}
                      color={selectedCandidate.is_incumbent ? 'success' : 'default'}
                      size="small"
                      icon={selectedCandidate.is_incumbent ? <IncumbentIcon /> : <CandidateIcon />}
                    />
                  </Tooltip>
                  <Tooltip title={selectedCandidate.is_withdrawn ? 'Has withdrawn from this election' : 'Active candidate in this election'}>
                    <Chip
                      label={selectedCandidate.is_withdrawn ? 'Withdrawn' : 'Active'}
                      color={selectedCandidate.is_withdrawn ? 'error' : 'success'}
                      size="small"
                      icon={selectedCandidate.is_withdrawn ? <InactiveIcon /> : <ActiveIcon />}
                    />
                  </Tooltip>
                  {selectedCandidate.is_endorsed && (
                    <Tooltip title="Officially endorsed candidate">
                      <Chip
                        label="Endorsed"
                        color="primary"
                        size="small"
                        icon={<EndorsedIcon />}
                      />
                    </Tooltip>
                  )}
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Ballot</Typography>
                <Typography variant="body1">{getBallotTitle(selectedCandidate.ballot_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Candidate Code</Typography>
                <Typography variant="body1">{selectedCandidate.candidate_code || 'N/A'}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Email</Typography>
                <Typography variant="body1">{selectedCandidate.email || 'N/A'}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Phone</Typography>
                <Typography variant="body1">{selectedCandidate.phone || 'N/A'}</Typography>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="subtitle2">Website</Typography>
                <Typography variant="body1">{selectedCandidate.website || 'N/A'}</Typography>
              </Grid>
              
              {selectedCandidate.biography && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Biography</Typography>
                  <Typography variant="body1">{selectedCandidate.biography}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.description && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Description</Typography>
                  <Typography variant="body1">{selectedCandidate.description}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.platform_summary && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Platform Summary</Typography>
                  <Typography variant="body1">{selectedCandidate.platform_summary}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.title && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Title/Position</Typography>
                  <Typography variant="body1">{selectedCandidate.title}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.party_abbreviation && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Party Abbreviation</Typography>
                  <Typography variant="body1">{selectedCandidate.party_abbreviation}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.age && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Age</Typography>
                  <Typography variant="body1">{selectedCandidate.age}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.education && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Education</Typography>
                  <Typography variant="body1">{selectedCandidate.education}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.occupation && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Occupation</Typography>
                  <Typography variant="body1">{selectedCandidate.occupation}</Typography>
                </Grid>
              )}
              
              {selectedCandidate.is_withdrawn && (
                <>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" color="error">
                      Withdrawal Information
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Withdrawal Date</Typography>
                    <Typography variant="body1">
                      {selectedCandidate.withdrawal_date ? new Date(selectedCandidate.withdrawal_date).toLocaleDateString() : 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2">Withdrawal Reason</Typography>
                    <Typography variant="body1">{selectedCandidate.withdrawal_reason || 'N/A'}</Typography>
                  </Grid>
                </>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Tooltip title="Close candidate details">
            <Button onClick={() => setDetailsDialogOpen(false)} startIcon={<InactiveIcon />}>
              Close
            </Button>
          </Tooltip>
        </DialogActions>
      </Dialog>

      {/* Withdrawal Dialog */}
      <Dialog
        open={withdrawDialogOpen}
        onClose={() => setWithdrawDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Withdraw Candidate</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to withdraw <strong>{withdrawCandidate?.name}</strong>?
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Withdrawal Date"
                type="date"
                value={withdrawalData.withdrawal_date}
                onChange={(e) => setWithdrawalData({...withdrawalData, withdrawal_date: e.target.value})}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Withdrawal Reason"
                multiline
                rows={3}
                value={withdrawalData.withdrawal_reason}
                onChange={(e) => setWithdrawalData({...withdrawalData, withdrawal_reason: e.target.value})}
                required
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel withdrawal process">
            <Button onClick={() => setWithdrawDialogOpen(false)} startIcon={<InactiveIcon />}>
              Cancel
            </Button>
          </Tooltip>
          <Tooltip title="Confirm candidate withdrawal with provided reason">
            <Button
              onClick={handleConfirmWithdrawal}
              variant="contained"
              color="error"
              startIcon={<WithdrawIcon />}
            >
              Withdraw Candidate
            </Button>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Candidates; 
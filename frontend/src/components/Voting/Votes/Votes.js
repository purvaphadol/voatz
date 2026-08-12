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
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Stack,
  Badge,
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
  Visibility as ViewIcon,
  VerifiedUser as VerifyIcon,
  Flag as FlagIcon,
  Search as SearchIcon,
  Assessment as CountIcon,
  Security as SecurityIcon,
  History as HistoryIcon,
  HowToVote as VoteIcon,
  Gavel as AuditIcon,
  Timeline as TimelineIcon,
  CheckCircle as VerifiedIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  Ballot as BallotIcon,
  PersonSearch as TrackerIcon,
  Shield as IntegrityIcon,
  Analytics as AnalyticsIcon,
  MonitorHeart as MonitorIcon,
  Assignment as ReportIcon,
  TrendingUp as TrendingIcon,
  Speed as PerformanceIcon,
  Fingerprint as BiometricIcon,
  VpnKey as CryptoIcon,
  Policy as ComplianceIcon,
  DynamicFeed as RealTimeIcon,
} from '@mui/icons-material';
import { votesAPI, electionsAPI, ballotsAPI, votersAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';
import SearchableSelect from '../../Common/SearchableSelect';

const CustomToolbar = ({ onTrack, onRealTimeMonitor, onAuditReport, hasViewPermission }) => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <GridToolbarFilterButton />
    <GridToolbarExport />
    {hasViewPermission && (
      <>
        <Tooltip title="Track a specific vote using its tracking code">
          <Button startIcon={<TrackerIcon />} onClick={onTrack}>
            Track Vote
          </Button>
        </Tooltip>
        <Tooltip title="View real-time vote monitoring dashboard">
          <Button startIcon={<RealTimeIcon />} onClick={onRealTimeMonitor}>
            Real-Time Monitor
          </Button>
        </Tooltip>
        <Tooltip title="Generate comprehensive audit report">
          <Button startIcon={<ReportIcon />} onClick={onAuditReport}>
            Audit Report
          </Button>
        </Tooltip>
      </>
    )}
  </GridToolbarContainer>
);

const Votes = () => {
  const { hasPermission } = usePermissions();
  const [votes, setVotes] = useState([]);
  const [elections, setElections] = useState([]);
  const [ballots, setBallots] = useState([]);
  const [voters, setVoters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [trackingDialogOpen, setTrackingDialogOpen] = useState(false);
  const [verificationDialogOpen, setVerificationDialogOpen] = useState(false);
  const [flagDialogOpen, setFlagDialogOpen] = useState(false);
  const [selectedVote, setSelectedVote] = useState(null);
  const [trackingCode, setTrackingCode] = useState('');
  const [trackedVote, setTrackedVote] = useState(null);
  const [verificationData, setVerificationData] = useState({
    verification_method: 'blockchain',
    additional_checks: [],
  });
  const [flagData, setFlagData] = useState({
    flag_reason: '',
    flag_description: '',
    severity: 'low',
  });
  const [stats, setStats] = useState({});
  const [realTimeStats, setRealTimeStats] = useState({});
  const [monitorDialogOpen, setMonitorDialogOpen] = useState(false);
  const [auditReportDialogOpen, setAuditReportDialogOpen] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canView = hasPermission('Votes', 'view');
  const canCreate = hasPermission('Votes', 'create');
  const canUpdate = hasPermission('Votes', 'update');
  const canDelete = hasPermission('Votes', 'delete');

  useEffect(() => {
    if (canView) {
      loadVotes();
      loadElections();
      loadBallots();
      loadVoters();
      loadStats();
    }
  }, [canView]);

  const loadVotes = async () => {
    try {
      setLoading(true);
      const response = await votesAPI.getAll();
      setVotes(response.data.data || []);
    } catch (error) {
      console.error('Error loading votes:', error);
      setError('Failed to load votes');
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

  const loadBallots = async () => {
    try {
      const response = await ballotsAPI.getAll();
      setBallots(response.data.data || []);
    } catch (error) {
      console.error('Error loading ballots:', error);
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
      const response = await votesAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleView = async (vote) => {
    try {
      const response = await votesAPI.getById(vote.id);
      setSelectedVote(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      setError('Failed to load vote details');
    }
  };

  const handleTrack = () => {
    setTrackingCode('');
    setTrackedVote(null);
    setTrackingDialogOpen(true);
  };

  const handleRealTimeMonitor = () => {
    setMonitorDialogOpen(true);
    startRealTimeMonitoring();
  };

  const [generatingReport, setGeneratingReport] = useState(false);

  const handleAuditReport = () => {
    setAuditReportDialogOpen(true);
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      // Fetch all votes + stats for the report payload
      const [votesRes, statsRes] = await Promise.all([
        votesAPI.getAll({ per_page: 1000 }),
        votesAPI.getStats(),
      ]);

      const report = {
        generated_at: new Date().toISOString(),
        report_type: 'comprehensive_audit',
        sections: {
          audit_trail: {
            total_votes: statsRes.data.total_votes,
            votes: votesRes.data.data,
          },
          compliance: {
            verified_votes: statsRes.data.verified_votes,
            counted_votes: statsRes.data.counted_votes,
            flagged_votes: statsRes.data.flagged_votes,
            verification_rate: statsRes.data.verification_rate,
          },
          cryptographic: {
            vote_statuses: statsRes.data.vote_statuses,
            verification_types: statsRes.data.verification_types,
          },
          statistical: {
            vote_methods: statsRes.data.vote_methods,
            pending_votes: statsRes.data.pending_votes,
          },
        },
      };

      // Download as JSON file
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `vote_audit_report_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setSuccess('Audit report downloaded successfully');
      setAuditReportDialogOpen(false);
    } catch (err) {
      setError('Failed to generate report: ' + (err.response?.data?.error || err.message));
    } finally {
      setGeneratingReport(false);
    }
  };

  const startRealTimeMonitoring = () => {
    const interval = setInterval(async () => {
      try {
        const response = await votesAPI.getStats();
        setRealTimeStats(response.data);
      } catch (error) {
        console.error('Error loading real-time stats:', error);
      }
    }, 5000); // Update every 5 seconds
    
    setRefreshInterval(interval);
  };

  const stopRealTimeMonitoring = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  };

  useEffect(() => {
    return () => {
      stopRealTimeMonitoring();
    };
  }, []);

  const handleTrackVote = async () => {
    try {
      const response = await votesAPI.track(trackingCode);
      setTrackedVote(response.data);
      setSuccess('Vote found successfully');
    } catch (error) {
      setError('Vote not found or tracking code invalid');
    }
  };

  const handleVerify = (vote) => {
    setSelectedVote(vote);
    setVerificationData({
      verification_method: 'blockchain',
      additional_checks: [],
    });
    setVerificationDialogOpen(true);
  };

  const handleConfirmVerification = async () => {
    try {
      await votesAPI.verify(selectedVote.id, { verification_type: 'all' });
      setSuccess('Vote verification completed');
      setVerificationDialogOpen(false);
      loadVotes();
    } catch (error) {
      setError('Failed to verify vote');
    }
  };

  const handleFlag = (vote) => {
    setSelectedVote(vote);
    setFlagData({
      flag_reason: '',
      flag_description: '',
      severity: 'low',
    });
    setFlagDialogOpen(true);
  };

  const handleConfirmFlag = async () => {
    try {
      await votesAPI.flag(selectedVote.id, { reason: flagData.flag_description || flagData.flag_reason || 'Manual flag' });
      setSuccess('Vote flagged successfully');
      setFlagDialogOpen(false);
      loadVotes();
    } catch (error) {
      setError('Failed to flag vote');
    }
  };

  const getElectionName = (electionId) => {
    const election = elections.find(e => e.id === electionId);
    return election ? election.title : 'Unknown';
  };

  const getBallotTitle = (ballotId) => {
    const ballot = ballots.find(b => b.id === ballotId);
    return ballot ? ballot.title : 'Unknown';
  };

  const getVoterName = (voterId) => {
    const voter = voters.find(v => v.id === voterId);
    return voter ? voter.name : 'Unknown';
  };

  const getVoteStatusColor = (vote) => {
    if (vote.vote_status === 'flagged' || vote.is_flagged) return 'error';
    if (vote.vote_status === 'verified' || vote.is_verified) return 'success';
    if (vote.processing_status === 'pending') return 'warning';
    return 'default';
  };

  const getVoteStatusText = (vote) => {
    if (vote.vote_status === 'flagged' || vote.is_flagged) return 'Flagged';
    if (vote.vote_status === 'verified' || vote.is_verified) return 'Verified';
    if (vote.processing_status === 'pending') return 'Pending';
    return 'Unverified';
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'tracking_code', headerName: 'Tracking Code', width: 150 },
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
      field: 'vote_method',
      headerName: 'Method',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value || 'online'}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const vote = params.row;
        const statusColor = getVoteStatusColor(vote);
        const statusText = getVoteStatusText(vote);
        
        let StatusIcon = PendingIcon;
        let tooltipText = 'Vote status unknown';
        
        if (vote.vote_status === 'flagged' || vote.is_flagged) {
          StatusIcon = FlagIcon;
          tooltipText = 'Vote has been flagged for manual review and investigation';
        } else if (vote.vote_status === 'verified' || vote.is_verified) {
          StatusIcon = VerifiedIcon;
          tooltipText = 'Vote has been verified and is eligible for counting';
        } else if (vote.processing_status === 'pending') {
          StatusIcon = PendingIcon;
          tooltipText = 'Vote is pending verification checks';
        }
        
        return (
          <Tooltip title={tooltipText}>
            <Chip
              label={statusText}
              color={statusColor}
              size="small"
              icon={<StatusIcon />}
            />
          </Tooltip>
        );
      },
    },
    {
      field: 'cast_at',
      headerName: 'Cast At',
      width: 150,
      renderCell: (params) => {
        if (!params.value) return 'N/A';
        return new Date(params.value).toLocaleDateString();
      },
    },
    {
      field: 'verification_hash',
      headerName: 'Hash',
      width: 150,
      renderCell: (params) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
          {params.value ? `${params.value.substring(0, 12)}...` : 'N/A'}
        </Typography>
      ),
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
            <Tooltip title="View detailed vote information, audit trail, and verification status" key="view">
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
            <Tooltip title="Verify vote integrity using biometric, device, and identity checks" key="verify">
              <GridActionsCellItem
                icon={<VerifyIcon />}
                label="Verify"
                onClick={() => handleVerify(params.row)}
                sx={{ color: 'success.main' }}
              />
            </Tooltip>,
            <Tooltip title="Flag this vote for manual review and audit investigation" key="flag">
              <GridActionsCellItem
                icon={<FlagIcon />}
                label="Flag"
                onClick={() => handleFlag(params.row)}
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
        You don't have permission to view votes.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48 }}>
          <MonitorIcon />
        </Avatar>
        <Box>
          <Typography variant="h4" gutterBottom>
            Vote Monitoring & Audit
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Real-time vote tracking, verification, and audit trails for election integrity
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
                    Total Votes
                  </Typography>
                  <Typography variant="h5">
                    {stats.total_votes || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                  <VoteIcon />
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
                    Verified Votes
                  </Typography>
                  <Typography variant="h5">
                    {stats.verified_votes || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'success.main', width: 56, height: 56 }}>
                  <VerifiedIcon />
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
                    Flagged Votes
                  </Typography>
                  <Typography variant="h5">
                    {stats.flagged_votes || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'error.main', width: 56, height: 56 }}>
                  <FlagIcon />
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
                    Verification Rate
                  </Typography>
                  <Typography variant="h5">
                    {stats.verification_rate ? `${stats.verification_rate.toFixed(1)}%` : '0%'}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'info.main', width: 56, height: 56 }}>
                  <PerformanceIcon />
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
          rows={votes}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 25 },
            },
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          checkboxSelection
          disableRowSelectionOnClick
          loading={loading}
          slots={{
            toolbar: () => (
              <CustomToolbar 
                onTrack={handleTrack} 
                onRealTimeMonitor={handleRealTimeMonitor}
                onAuditReport={handleAuditReport}
                hasViewPermission={canView} 
              />
            ),
          }}
        />
      </Paper>

      {/* Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Vote Details</DialogTitle>
        <DialogContent>
          {selectedVote && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Tracking Code</Typography>
                <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                  {selectedVote.tracking_code}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Status</Typography>
                <Chip
                  label={getVoteStatusText(selectedVote)}
                  color={getVoteStatusColor(selectedVote)}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Voter</Typography>
                <Typography variant="body1">{getVoterName(selectedVote.voter_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Election</Typography>
                <Typography variant="body1">{getElectionName(selectedVote.election_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Ballot</Typography>
                <Typography variant="body1">{getBallotTitle(selectedVote.ballot_id)}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Vote Method</Typography>
                <Typography variant="body1">{selectedVote.vote_method || 'online'}</Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">Cast At</Typography>
                <Typography variant="body1">
                  {selectedVote.cast_at ? new Date(selectedVote.cast_at).toLocaleString() : 'N/A'}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2">IP Address</Typography>
                <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                  {selectedVote.ip_address || 'N/A'}
                </Typography>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="subtitle2">Verification Hash</Typography>
                <Typography variant="body1" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {selectedVote.verification_hash || 'N/A'}
                </Typography>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="subtitle2">Blockchain Hash</Typography>
                <Typography variant="body1" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {selectedVote.blockchain_hash || 'N/A'}
                </Typography>
              </Grid>
              
              {selectedVote.is_flagged && (
                <>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" color="error">
                      Flag Information
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Flag Reason</Typography>
                    <Typography variant="body1">{selectedVote.flag_reason || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2">Flag Severity</Typography>
                    <Chip
                      label={selectedVote.flag_severity || 'low'}
                      color={selectedVote.flag_severity === 'high' ? 'error' : 'warning'}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2">Flag Description</Typography>
                    <Typography variant="body1">{selectedVote.flag_description || 'N/A'}</Typography>
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

      {/* Tracking Dialog */}
      <Dialog
        open={trackingDialogOpen}
        onClose={() => setTrackingDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Track Vote</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Tracking Code"
            value={trackingCode}
            onChange={(e) => setTrackingCode(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button
            fullWidth
            variant="contained"
            onClick={handleTrackVote}
            disabled={!trackingCode}
          >
            Track Vote
          </Button>
          
          {trackedVote && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6">Vote Found</Typography>
                <Typography variant="body2">
                  Status: <Chip
                    label={getVoteStatusText(trackedVote)}
                    color={getVoteStatusColor(trackedVote)}
                    size="small"
                  />
                </Typography>
                <Typography variant="body2">
                  Cast: {trackedVote.cast_at ? new Date(trackedVote.cast_at).toLocaleString() : 'N/A'}
                </Typography>
                <Typography variant="body2">
                  Election: {getElectionName(trackedVote.election_id)}
                </Typography>
                <Typography variant="body2">
                  Ballot: {getBallotTitle(trackedVote.ballot_id)}
                </Typography>
              </CardContent>
            </Card>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTrackingDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Verification Dialog */}
      <Dialog
        open={verificationDialogOpen}
        onClose={() => setVerificationDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Verify Vote</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Verify vote with tracking code: <strong>{selectedVote?.tracking_code}</strong>
          </Typography>
          <Box sx={{ mt: 2 }}>
            <SearchableSelect
              options={[
                { id: 'blockchain', name: 'Blockchain Verification' },
                { id: 'hash', name: 'Hash Verification' },
                { id: 'signature', name: 'Digital Signature' },
                { id: 'manual', name: 'Manual Verification' }
              ]}
              getOptionLabel={(opt) => opt.name}
              getOptionValue={(opt) => opt.id}
              value={verificationData.verification_method}
              onChange={(e) => setVerificationData({...verificationData, verification_method: e.target.value})}
              label="Verification Method"
              margin="dense"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVerificationDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmVerification}
            variant="contained"
            color="success"
          >
            Verify
          </Button>
        </DialogActions>
      </Dialog>

      {/* Flag Dialog */}
      <Dialog
        open={flagDialogOpen}
        onClose={() => setFlagDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Flag Vote</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Flag vote with tracking code: <strong>{selectedVote?.tracking_code}</strong>
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Flag Reason</InputLabel>
                <Select
                  value={flagData.flag_reason}
                  onChange={(e) => setFlagData({...flagData, flag_reason: e.target.value})}
                >
                  <MenuItem value="suspicious_activity">Suspicious Activity</MenuItem>
                  <MenuItem value="technical_issue">Technical Issue</MenuItem>
                  <MenuItem value="voter_complaint">Voter Complaint</MenuItem>
                  <MenuItem value="audit_finding">Audit Finding</MenuItem>
                  <MenuItem value="other">Other</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={flagData.severity}
                  onChange={(e) => setFlagData({...flagData, severity: e.target.value})}
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                multiline
                rows={3}
                value={flagData.flag_description}
                onChange={(e) => setFlagData({...flagData, flag_description: e.target.value})}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFlagDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmFlag}
            variant="contained"
            color="error"
          >
            Flag Vote
          </Button>
        </DialogActions>
      </Dialog>

      {/* Real-Time Monitoring Dialog */}
      <Dialog
        open={monitorDialogOpen}
        onClose={() => {
          setMonitorDialogOpen(false);
          stopRealTimeMonitoring();
        }}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={2}>
            <RealTimeIcon />
            Real-Time Vote Monitoring
            <Badge color="success" variant="dot">
              <Chip label="Live" color="success" size="small" />
            </Badge>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            {/* Real-time stats */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Live Statistics (Updated every 5 seconds)
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <VoteIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                  <Typography variant="h4">
                    {realTimeStats.total_votes || stats.total_votes || 0}
                  </Typography>
                  <Typography color="textSecondary">Total Votes</Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <VerifiedIcon sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
                  <Typography variant="h4">
                    {realTimeStats.verified_votes || stats.verified_votes || 0}
                  </Typography>
                  <Typography color="textSecondary">Verified</Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <FlagIcon sx={{ fontSize: 48, color: 'error.main', mb: 1 }} />
                  <Typography variant="h4">
                    {realTimeStats.flagged_votes || stats.flagged_votes || 0}
                  </Typography>
                  <Typography color="textSecondary">Flagged</Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <PerformanceIcon sx={{ fontSize: 48, color: 'info.main', mb: 1 }} />
                  <Typography variant="h4">
                    {realTimeStats.verification_rate ? `${realTimeStats.verification_rate.toFixed(1)}%` : 
                     stats.verification_rate ? `${stats.verification_rate.toFixed(1)}%` : '0%'}
                  </Typography>
                  <Typography color="textSecondary">Verification Rate</Typography>
                </CardContent>
              </Card>
            </Grid>
            
            {/* Additional monitoring metrics */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                System Health Indicators
              </Typography>
            </Grid>
            
            {(() => {
              const liveStats = Object.keys(realTimeStats).length ? realTimeStats : stats;
              const flagged = liveStats.flagged_votes ?? 0;
              const total = liveStats.total_votes ?? 0;
              const verificationRate = liveStats.verification_rate ?? 0;
              const secureLabel = flagged === 0 ? 'All Systems Secure' : `${flagged} Flag(s) Detected`;
              const secureColor = flagged === 0 ? 'success' : 'error';
              const integrityLabel = verificationRate >= 90 ? 'Verified' : verificationRate >= 50 ? 'Partially Verified' : 'Needs Review';
              const integrityColor = verificationRate >= 90 ? 'success' : verificationRate >= 50 ? 'warning' : 'error';
              const onlineColor = total > 0 ? 'success' : 'default';

              return (
                <>
                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2}>
                          <SecurityIcon color={secureColor} />
                          <Box>
                            <Typography variant="h6">Security Status</Typography>
                            <Chip label={secureLabel} color={secureColor} size="small" />
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2}>
                          <IntegrityIcon color={integrityColor} />
                          <Box>
                            <Typography variant="h6">Data Integrity</Typography>
                            <Chip label={integrityLabel} color={integrityColor} size="small" />
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2}>
                          <MonitorIcon color={onlineColor} />
                          <Box>
                            <Typography variant="h6">Network Status</Typography>
                            <Chip label={total > 0 ? 'Online' : 'No Data Yet'} color={onlineColor} size="small" />
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                </>
              );
            })()}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Stop real-time monitoring and close">
            <Button onClick={() => {
              setMonitorDialogOpen(false);
              stopRealTimeMonitoring();
            }}>
              Close Monitor
            </Button>
          </Tooltip>
        </DialogActions>
      </Dialog>

      {/* Audit Report Dialog */}
      <Dialog
        open={auditReportDialogOpen}
        onClose={() => setAuditReportDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={2}>
            <AuditIcon />
            Generate Audit Report
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Generate comprehensive audit reports for vote monitoring and compliance verification.
          </Typography>
          
          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <TimelineIcon color="primary" />
                    <Box>
                      <Typography variant="h6">Vote Audit Trail</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Complete chronological record of all vote events
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <ComplianceIcon color="primary" />
                    <Box>
                      <Typography variant="h6">Compliance Report</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Verification and compliance status summary
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <CryptoIcon color="primary" />
                    <Box>
                      <Typography variant="h6">Cryptographic Verification</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Hash verification and blockchain integrity
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <AnalyticsIcon color="primary" />
                    <Box>
                      <Typography variant="h6">Statistical Analysis</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Vote patterns and anomaly detection
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel report generation">
            <Button onClick={() => setAuditReportDialogOpen(false)}>
              Cancel
            </Button>
          </Tooltip>
          <Tooltip title="Generate and download comprehensive audit report as JSON">
            <Button
              variant="contained"
              startIcon={generatingReport ? <CircularProgress size={16} color="inherit" /> : <ReportIcon />}
              onClick={handleGenerateReport}
              disabled={generatingReport}
            >
              {generatingReport ? 'Generating…' : 'Generate Report'}
            </Button>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Votes; 
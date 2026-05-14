import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  GetApp as ExportIcon,
  Assessment as ReportIcon,
  Visibility as ViewIcon,
  Print as PrintIcon,
} from '@mui/icons-material';
import { electionsAPI, ballotsAPI, candidatesAPI, votesAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const ElectionResults = ({ election, open, onClose }) => {
  const { hasPermission } = usePermissions();
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState(null);
  const [ballots, setBallots] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [votingStats, setVotingStats] = useState({});
  const [selectedBallot, setSelectedBallot] = useState(null);
  const [error, setError] = useState('');

  const canView = hasPermission('Elections', 'view');
  const canExport = hasPermission('Elections', 'export');

  useEffect(() => {
    if (open && election && canView) {
      loadResults();
    }
  }, [open, election, canView]);

  const loadResults = async () => {
    try {
      setLoading(true);
      setError('');

      // Load election ballots
      const ballotsResponse = await electionsAPI.getBallots(election.id);
      setBallots(ballotsResponse.data.ballots || []);

      // Load all candidates for this election
      const candidatesResponse = await candidatesAPI.getAll({ election_id: election.id });
      setCandidates(candidatesResponse.data.data || []);

      // Load voting statistics
      const statsResponse = await votesAPI.getStats({ election_id: election.id });
      setVotingStats(statsResponse.data || {});

      // Process results data
      processResultsData(ballotsResponse.data.ballots || [], candidatesResponse.data.data || []);

    } catch (error) {
      console.error('Error loading results:', error);
      setError('Failed to load election results');
    } finally {
      setLoading(false);
    }
  };

  const processResultsData = (ballotsData, candidatesData) => {
    if (!election) {
      setError('No election data available');
      return;
    }

    const resultsData = {
      totalVotes: election.total_votes_cast || 0,
      totalRegistered: election.total_registered_voters || 0,
      turnoutPercentage: election.turnout_percentage || 0,
      ballotResults: []
    };

    ballotsData.forEach(ballot => {
      const ballotCandidates = candidatesData.filter(c => c.ballot_id === ballot.id);
      const totalBallotVotes = ballotCandidates.reduce((sum, c) => sum + (c.total_votes_received || 0), 0);

      const candidateResults = ballotCandidates.map(candidate => ({
        id: candidate.id,
        name: candidate.name,
        party: candidate.party_affiliation || 'Independent',
        votes: candidate.total_votes_received || 0,
        percentage: totalBallotVotes > 0 ? ((candidate.total_votes_received || 0) / totalBallotVotes) * 100 : 0,
        isWinner: candidate.rank_position === 1
      })).sort((a, b) => b.votes - a.votes);

      resultsData.ballotResults.push({
        ballotId: ballot.id,
        ballotTitle: ballot.title,
        ballotType: ballot.ballot_type,
        positionTitle: ballot.position_title,
        totalVotes: totalBallotVotes,
        candidates: candidateResults
      });
    });

    setResults(resultsData);
  };

  const handleExportResults = async () => {
    try {
      if (!election || !results) {
        setError('No election data available for export');
        return;
      }

      // Implementation for exporting results
      const resultsData = {
        election: {
          title: election.title || 'Unknown Election',
          type: election.election_type || 'Unknown',
          date: election.end_date || new Date().toISOString(),
          totalVotes: results.totalVotes,
          turnout: results.turnoutPercentage
        },
        ballots: results.ballotResults
      };

      const dataStr = JSON.stringify(resultsData, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      
      const exportFileDefaultName = `election_results_${election.election_code || 'unknown'}_${new Date().toISOString().split('T')[0]}.json`;
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    } catch (error) {
      setError('Failed to export results');
    }
  };

  const getStatusColor = (election) => {
    if (!election) return 'default';
    if (election.results_published) return 'success';
    if (election.status === 'completed') return 'warning';
    if (election.status === 'active') return 'info';
    return 'default';
  };

  const getStatusText = (election) => {
    if (!election) return 'Unknown';
    if (election.results_published) return 'Results Published';
    if (election.status === 'completed') return 'Pending Results';
    if (election.status === 'active') return 'Voting Active';
    return election.status || 'Unknown';
  };

  if (!canView) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogContent>
          <Alert severity="error">
            You don't have permission to view election results.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }

  // Handle case where dialog is open but no election is selected
  if (open && !election) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogContent>
          <Alert severity="warning">
            No election selected. Please select an election to view results.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="xl" 
      fullWidth
      PaperProps={{
        sx: { height: '90vh' }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5" component="div">
              Election Results: {election?.title}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {election?.election_type} • {election?.election_code}
            </Typography>
          </Box>
          <Chip
            label={getStatusText(election)}
            color={getStatusColor(election)}
            size="small"
          />
        </Box>
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ width: '100%', mt: 2 }}>
            <LinearProgress />
            <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
              Loading results...
            </Typography>
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : results ? (
          <Box>
            {/* Overview Statistics */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Total Votes Cast
                    </Typography>
                    <Typography variant="h4">
                      {results.totalVotes.toLocaleString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Registered Voters
                    </Typography>
                    <Typography variant="h4">
                      {results.totalRegistered.toLocaleString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Voter Turnout
                    </Typography>
                    <Typography variant="h4">
                      {results.turnoutPercentage.toFixed(1)}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Ballots/Races
                    </Typography>
                    <Typography variant="h4">
                      {results.ballotResults.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Ballot Results */}
            {results.ballotResults.map((ballot, index) => (
              <Card key={ballot.ballotId} sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {ballot.ballotTitle}
                    {ballot.positionTitle && (
                      <Typography variant="body2" color="textSecondary" component="span" sx={{ ml: 1 }}>
                        • {ballot.positionTitle}
                      </Typography>
                    )}
                  </Typography>
                  
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Total Votes: {ballot.totalVotes.toLocaleString()} • Type: {ballot.ballotType}
                  </Typography>

                  <Grid container spacing={2}>
                    {/* Results Table */}
                    <Grid item xs={12} md={6}>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Candidate</TableCell>
                              <TableCell>Party</TableCell>
                              <TableCell align="right">Votes</TableCell>
                              <TableCell align="right">%</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {ballot.candidates.map((candidate) => (
                              <TableRow 
                                key={candidate.id}
                                sx={{ 
                                  backgroundColor: candidate.isWinner ? 'success.light' : 'inherit',
                                  '&:hover': { backgroundColor: 'action.hover' }
                                }}
                              >
                                <TableCell>
                                  <Box display="flex" alignItems="center">
                                    {candidate.name}
                                    {candidate.isWinner && (
                                      <Chip label="Winner" size="small" color="success" sx={{ ml: 1 }} />
                                    )}
                                  </Box>
                                </TableCell>
                                <TableCell>{candidate.party}</TableCell>
                                <TableCell align="right">{candidate.votes.toLocaleString()}</TableCell>
                                <TableCell align="right">{candidate.percentage.toFixed(1)}%</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Grid>

                    {/* Results Chart */}
                    <Grid item xs={12} md={6}>
                      <Box sx={{ height: 300 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={ballot.candidates.slice(0, 6)}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                              dataKey="name" 
                              angle={-45}
                              textAnchor="end"
                              height={80}
                              interval={0}
                            />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="votes" fill="#8884d8" />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}
          </Box>
        ) : (
          <Alert severity="info">
            No results data available for this election.
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        {canExport && results && (
          <Tooltip title="Export election results as JSON file">
            <Button
              startIcon={<ExportIcon />}
              onClick={handleExportResults}
              variant="outlined"
            >
              Export Results
            </Button>
          </Tooltip>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ElectionResults; 
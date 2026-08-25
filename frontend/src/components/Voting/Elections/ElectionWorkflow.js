import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
} from '@mui/material';
import {
  Assignment as DraftIcon,
  PlayArrow as ActiveIcon,
  CheckCircle as CompletedIcon,
  Cancel as CancelledIcon,
  Warning as WarningIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { electionsAPI } from '../../../services/api';

const ElectionWorkflow = ({ election, onStatusChange, open, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [error, setError] = useState('');

  const workflowSteps = [
    {
      key: 'draft',
      label: 'Draft',
      description: 'Election is being configured',
      icon: <DraftIcon />,
      color: 'default'
    },
    {
      key: 'active',
      label: 'Active',
      description: 'Voting is open',
      icon: <ActiveIcon />,
      color: 'info'
    },
    {
      key: 'completed',
      label: 'Completed',
      description: 'Voting ended, results available',
      icon: <CompletedIcon />,
      color: 'success'
    }
  ];

  const validateElectionForActivation = async () => {
    try {
      setLoading(true);
      setError('');

      const ballotsResponse = await electionsAPI.getBallots(election.id);
      const ballots = ballotsResponse.data.ballots || [];

      const checks = [];
      let canActivate = true;

      if (ballots.length === 0) {
        checks.push({ type: 'error', message: 'Election must have at least one ballot' });
        canActivate = false;
      }

      const activeBallots = ballots.filter(b => b.is_active);
      if (activeBallots.length === 0) {
        checks.push({ type: 'error', message: 'Election must have at least one active ballot' });
        canActivate = false;
      }

      if (canActivate) {
        checks.push({ type: 'success', message: 'Election configuration is valid' });
        checks.push({ type: 'success', message: `Found ${activeBallots.length} active ballot(s)` });
      }

      setValidationResults({ canActivate, checks, ballotCount: ballots.length });

    } catch (error) {
      setError('Failed to validate election configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      setLoading(true);
      setError('');

      if (newStatus === 'active' && !validationResults?.canActivate) {
        await validateElectionForActivation();
        return;
      }

      await electionsAPI.changeStatus(election.id, newStatus);
      onStatusChange && onStatusChange(newStatus);
      onClose();
    } catch (error) {
      setError('Failed to change election status');
    } finally {
      setLoading(false);
    }
  };

  const getNextPossibleStatuses = (currentStatus) => {
    // Note: Backend status transitions strictly produce 'draft', 'active', 'completed', 'cancelled'.
    // Aliases/legacy statuses like 'published', 'voting', 'auditing' map to their corresponding lifecycle phase for UI safety.
    switch (currentStatus) {
      case 'draft':
      case 'published':
        return ['active', 'cancelled'];
      case 'active':
      case 'voting':
        return ['completed', 'cancelled'];
      case 'completed':
      case 'auditing':
        return [];
      case 'cancelled':
        return ['draft'];
      default:
        return [];
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft':
      case 'published':
        return 'default';
      case 'active':
      case 'voting':
        return 'info';
      case 'completed':
      case 'auditing':
        return 'success';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  const getCurrentStep = () => {
    const idx = workflowSteps.findIndex(step => step.key === election?.status);
    return idx === -1 ? 0 : idx;
  };

  const nextStatuses = getNextPossibleStatuses(election?.status);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Election Workflow Management
        <Typography variant="body2" color="textSecondary">
          {election?.title} • {election?.election_code}
        </Typography>
      </DialogTitle>

      <DialogContent>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Current Status</Typography>
            <Chip
              label={election?.status || 'Unknown'}
              color={getStatusColor(election?.status)}
              size="medium"
            />
          </CardContent>
        </Card>

        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Election Lifecycle</Typography>
            <Stepper activeStep={getCurrentStep()} orientation="horizontal">
              {workflowSteps.map((step) => (
                <Step key={step.key}>
                  <StepLabel icon={step.icon}>
                    <Typography variant="body2">{step.label}</Typography>
                  </StepLabel>
                </Step>
              ))}
            </Stepper>
          </CardContent>
        </Card>

        {validationResults && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Validation Results</Typography>
              <List dense>
                {validationResults.checks.map((check, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {check.type === 'error' && <CloseIcon color="error" />}
                      {check.type === 'warning' && <WarningIcon color="warning" />}
                      {check.type === 'success' && <CheckIcon color="success" />}
                    </ListItemIcon>
                    <ListItemText primary={check.message} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        )}

        {nextStatuses.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Available Actions</Typography>
              <Box display="flex" gap={2} flexWrap="wrap">
                {nextStatuses.map((status) => (
                  <Tooltip key={status} title={status === 'active' ? 'Validate Election' : status.charAt(0).toUpperCase() + status.slice(1)}>
                    <span>
                      <Button
                        variant="outlined"
                        color={getStatusColor(status)}
                        onClick={() => status === 'active' ? validateElectionForActivation() : handleStatusChange(status)}
                        disabled={loading}
                      >
                        Change to {status.charAt(0).toUpperCase() + status.slice(1)}
                      </Button>
                    </span>
                  </Tooltip>
                ))}
              </Box>
              
              {validationResults?.canActivate && (
                <Tooltip title="Confirm Election Activation">
                  <span>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={() => handleStatusChange('active')}
                      disabled={loading}
                      sx={{ mt: 2 }}
                    >
                      Confirm Activation
                    </Button>
                  </span>
                </Tooltip>
              )}
            </CardContent>
          </Card>
        )}

        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ElectionWorkflow; 
import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Avatar,
} from '@mui/material';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { authAPI } from '../../services/api';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [formData, setFormData] = useState({
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [redirectCountdown, setRedirectCountdown] = useState(null);

  // Validate token presence on mount
  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset link.');
    }
  }, [token]);

  // Countdown and redirect after successful reset
  useEffect(() => {
    if (redirectCountdown === null) return;

    if (redirectCountdown <= 0) {
      navigate('/login');
      return;
    }

    const timer = setTimeout(() => {
      setRedirectCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [redirectCountdown, navigate]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const { newPassword, confirmPassword } = formData;

    // Client-side validation
    if (!newPassword || !confirmPassword) {
      setError('Both password fields are required');
      setLoading(false);
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      setLoading(false);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      const response = await authAPI.resetPassword(token, newPassword);
      setSuccess(response.data.message || 'Password reset successfully!');
      setRedirectCountdown(3);
    } catch (err) {
      const errorMessage =
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Failed to reset password. The link may have expired.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const isFormDisabled = loading || !token || redirectCountdown !== null;

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
              <LockOutlinedIcon />
            </Avatar>
            <Typography component="h1" variant="h5">
              Reset Password
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3, textAlign: 'center' }}>
              Enter your new password below.
            </Typography>

            {error && (
              <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ width: '100%', mb: 2 }}>
                {success}
                {redirectCountdown !== null && redirectCountdown > 0 && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Redirecting to login in {redirectCountdown} second{redirectCountdown !== 1 ? 's' : ''}...
                  </Typography>
                )}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1, width: '100%' }}>
              <TextField
                margin="normal"
                required
                fullWidth
                name="newPassword"
                label="New Password"
                type="password"
                id="new-password"
                autoComplete="new-password"
                autoFocus
                value={formData.newPassword}
                onChange={handleChange}
                disabled={isFormDisabled}
                helperText="Minimum 8 characters"
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="confirmPassword"
                label="Confirm Password"
                type="password"
                id="confirm-password"
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={isFormDisabled}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={isFormDisabled}
              >
                {loading ? <CircularProgress size={24} /> : 'Reset Password'}
              </Button>
            </Box>

            <Box sx={{ mt: 2 }}>
              <Link
                to="/login"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  color: '#1976d2',
                  fontSize: '0.875rem',
                  textDecoration: 'none',
                }}
              >
                <ArrowBackIcon fontSize="small" />
                Back to Login
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default ResetPassword;

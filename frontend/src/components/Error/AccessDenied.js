import React from 'react';
import { Box, Typography, Button, Container, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { Block as BlockIcon, Home as HomeIcon, ContactSupport as ContactIcon } from '@mui/icons-material';

const AccessDenied = ({ 
  title = "Access Denied", 
  message = "You don't have permission to access this page.",
  requiredPermission = null,
  showContactSupport = true 
}) => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  const handleGoBack = () => {
    navigate(-1);
  };

  return (
    <Container maxWidth="md">
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        textAlign="center"
      >
        <Paper elevation={3} sx={{ p: 6, borderRadius: 2 }}>
          <BlockIcon sx={{ fontSize: 120, color: 'warning.main', mb: 2 }} />
          
          <Typography variant="h3" component="h1" gutterBottom color="warning.main" sx={{ fontWeight: 'bold' }}>
            {title}
          </Typography>
          
          <Typography variant="h6" component="h2" gutterBottom color="text.secondary" sx={{ mb: 3 }}>
            {message}
          </Typography>
          
          {requiredPermission && (
            <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary', fontStyle: 'italic' }}>
              Required permission: <strong>{requiredPermission}</strong>
            </Typography>
          )}
          
          <Typography variant="body1" sx={{ mb: 4, maxWidth: 500 }}>
            If you believe this is an error, please contact your administrator to request access to this resource.
          </Typography>
          
          <Box display="flex" gap={2} justifyContent="center" flexWrap="wrap">
            <Button
              variant="contained"
              startIcon={<HomeIcon />}
              onClick={handleGoHome}
              size="large"
            >
              Go to Dashboard
            </Button>
            
            <Button
              variant="outlined"
              onClick={handleGoBack}
              size="large"
            >
              Go Back
            </Button>
            
            {showContactSupport && (
              <Button
                variant="text"
                startIcon={<ContactIcon />}
                size="large"
                sx={{ color: 'text.secondary' }}
              >
                Contact Support
              </Button>
            )}
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default AccessDenied; 
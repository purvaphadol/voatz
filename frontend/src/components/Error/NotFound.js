import React from 'react';
import { Box, Typography, Button, Container, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { Error as ErrorIcon, Home as HomeIcon } from '@mui/icons-material';

const NotFound = () => {
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
          <ErrorIcon sx={{ fontSize: 120, color: 'error.main', mb: 2 }} />
          
          <Typography variant="h1" component="h1" sx={{ fontSize: '4rem', fontWeight: 'bold', mb: 2 }}>
            404
          </Typography>
          
          <Typography variant="h4" component="h2" gutterBottom color="text.secondary">
            Page Not Found
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 4, maxWidth: 400 }}>
            The page you're looking for doesn't exist or has been moved to another location.
          </Typography>
          
          <Box display="flex" gap={2} justifyContent="center">
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
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default NotFound; 
import React from 'react';
import { Box, Typography, Paper, Avatar } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

const Profile = () => {
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        User Profile
      </Typography>
      
      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Box display="flex" alignItems="center" mb={3}>
          <Avatar sx={{ width: 80, height: 80, mr: 3, fontSize: '2rem' }}>
            {user && user.name && user.name.charAt(0)}
          </Avatar>
          <Box>
            <Typography variant="h5">{user && user.name}</Typography>
            <Typography variant="body1" color="text.secondary">
              {user && user.email}
            </Typography>
          </Box>
        </Box>
        
        <Typography variant="h6" gutterBottom>
          Account Information
        </Typography>
        <Typography variant="body1" gutterBottom>
          <strong>User ID:</strong> {user && user.id}
        </Typography>
        <Typography variant="body1" gutterBottom>
          <strong>Company:</strong> {user && user.company_name}
        </Typography>
      </Paper>
    </Box>
  );
};

export default Profile; 
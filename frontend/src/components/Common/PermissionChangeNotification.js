import React, { useState, useEffect } from 'react';
import { Snackbar, Alert, Button, Box } from '@mui/material';
import { Security as SecurityIcon, Refresh as RefreshIcon } from '@mui/icons-material';

const PermissionChangeNotification = ({ show, onAccept, onDismiss }) => {
  return (
    <Snackbar
      open={show}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      sx={{ zIndex: 9999 }}
    >
      <Alert 
        severity="warning" 
        variant="filled"
        icon={<SecurityIcon />}
        sx={{ 
          width: '100%',
          '& .MuiAlert-action': {
            alignItems: 'center'
          }
        }}
        action={
          <Box display="flex" gap={1}>
            <Button 
              color="inherit" 
              size="small" 
              onClick={onAccept}
              startIcon={<RefreshIcon />}
            >
              Apply Changes
            </Button>
            <Button 
              color="inherit" 
              size="small" 
              onClick={onDismiss}
            >
              Dismiss
            </Button>
          </Box>
        }
      >
        Your permissions have been updated by an administrator. Click "Apply Changes" to refresh.
      </Alert>
    </Snackbar>
  );
};

export default PermissionChangeNotification; 
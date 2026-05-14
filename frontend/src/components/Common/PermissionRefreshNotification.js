import React, { useState, useEffect } from 'react';
import { Snackbar, Alert } from '@mui/material';
import { usePermissions } from '../../contexts/PermissionContext';

const PermissionRefreshNotification = () => {
  const { lastRefresh } = usePermissions();
  const [open, setOpen] = useState(false);
  const [lastNotified, setLastNotified] = useState(null);

  useEffect(() => {
    if (lastRefresh && lastRefresh !== lastNotified) {
      setOpen(true);
      setLastNotified(lastRefresh);
    }
  }, [lastRefresh, lastNotified]);

  const handleClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
  };

  return (
    <Snackbar
      open={open}
      autoHideDuration={3000}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      <Alert 
        onClose={handleClose} 
        severity="success" 
        variant="filled"
        sx={{ width: '100%' }}
      >
        Permissions refreshed successfully!
      </Alert>
    </Snackbar>
  );
};

export default PermissionRefreshNotification; 
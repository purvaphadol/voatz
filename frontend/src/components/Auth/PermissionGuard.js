import React from 'react';
import { usePermissions } from '../../contexts/PermissionContext';
import AccessDenied from '../Error/AccessDenied';

const PermissionGuard = ({ 
  children, 
  module, 
  action = 'view',
  fallbackMessage = null,
  showInLayout = false 
}) => {
  const { hasPermission } = usePermissions();
  
  const canAccess = hasPermission(module, action);
  const requiredPermission = `${module}.${action}`;
  
  if (!canAccess) {
    const message = fallbackMessage || `You don't have permission to ${action} ${module.toLowerCase()}.`;
    
    if (showInLayout) {
      // Show access denied within the layout (for components that should stay in layout)
      return (
        <AccessDenied 
          title="Access Denied"
          message={message}
          requiredPermission={requiredPermission}
          showContactSupport={true}
        />
      );
    } else {
      // Show full-page access denied (breaks out of layout)
      return (
        <AccessDenied 
          title="Access Denied"
          message={message}
          requiredPermission={requiredPermission}
          showContactSupport={true}
        />
      );
    }
  }
  
  return children;
};

export default PermissionGuard; 
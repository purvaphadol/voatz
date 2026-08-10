import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { menuAPI } from '../services/api';

const PermissionContext = createContext();

export const usePermissions = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissions must be used within a PermissionProvider');
  }
  return context;
};

export const PermissionProvider = ({ children }) => {
  const { isAuthenticated, token } = useAuth();
  const [permissions, setPermissions] = useState({});
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const permissionsRef = useRef(permissions);

  useEffect(() => {
    permissionsRef.current = permissions;
  }, [permissions]);

  useEffect(() => {
    if (isAuthenticated() && token) {
      // Add a small delay to ensure token is properly set in API headers
      const timer = setTimeout(() => {
        loadPermissions();
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setPermissions({});
      setMenu([]);
    }
  }, [isAuthenticated(), token]);

  const loadPermissions = async (isAutoRefresh = false) => {
    if (!isAutoRefresh) {
      console.log('🔍 [PermissionContext] Loading permissions...');
    }
    setLoading(true);
    try {
      // Load sidebar menu with permissions
      const menuResponse = await menuAPI.getSidebar();
      if (!isAutoRefresh) {
        console.log('✅ [PermissionContext] Menu API response:', menuResponse.data);
      }
      
      const newMenu = menuResponse.data.menu || [];
      
      // Convert menu to permissions object for easy checking
      const newPermissionsObj = {};
      newMenu.forEach(module => {
        newPermissionsObj[module.module] = {};
        (module.actions || []).forEach(action => {
          newPermissionsObj[module.module][action.name] = true;
        });
      });
      
      // Check if permissions actually changed (for auto-refresh)
      if (isAutoRefresh) {
        const hasChanged = JSON.stringify(newPermissionsObj) !== JSON.stringify(permissionsRef.current);
        if (hasChanged) {
          console.log('🔄 [PermissionContext] Permissions changed detected - updating silently...');
        } else {
          setLoading(false);
          return; // No changes, don't update
        }
      }
      
      if (!isAutoRefresh) {
        console.log('📊 [PermissionContext] Converted permissions:', newPermissionsObj);
        
        // Check Users specifically
        if (newPermissionsObj.Users) {
          console.log('👥 [PermissionContext] Users permissions:', newPermissionsObj.Users);
          console.log('👥 [PermissionContext] Users.view:', !!newPermissionsObj.Users.view);
          console.log('👥 [PermissionContext] Users.create:', !!newPermissionsObj.Users.create);
        } else {
          console.log('❌ [PermissionContext] Users module not found in permissions');
        }
      }
      
      setMenu(newMenu);
      setPermissions(newPermissionsObj);
      setLastRefresh(new Date().toISOString());
      
    } catch (error) {
      console.error('❌ [PermissionContext] Error loading permissions:', error);
      // Don't clear permissions on error to avoid redirect loops
      // Only clear if it's not a 401 error (which would be handled by interceptor)
      if (error.response && error.response.status !== 401) {
        setPermissions({});
        setMenu([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Force refresh function for debugging
  const forceRefreshPermissions = async () => {
    console.log('🔄 [PermissionContext] Force refreshing permissions...');
    setPermissions({});
    setMenu([]);
    await loadPermissions();
  };

  // Regular refresh function
  const refreshPermissions = async () => {
    console.log('🔄 [PermissionContext] Refreshing permissions...');
    await loadPermissions();
  };

  // Add to window for debugging
  if (typeof window !== 'undefined') {
    window.forceRefreshPermissions = forceRefreshPermissions;
    window.refreshPermissions = refreshPermissions;
  }

  // Add keyboard shortcut for manual refresh (Ctrl+Shift+P)
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'P') {
        event.preventDefault();
        console.log('🔄 [PermissionContext] Manual refresh triggered via Ctrl+Shift+P');
        refreshPermissions();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [refreshPermissions]);

  // Listen for instant permission update events (e.g. from Role/Permission management components)
  useEffect(() => {
    const handlePermissionsUpdated = () => {
      console.log('🔄 [PermissionContext] Instant refresh triggered via permissionsUpdated event');
      refreshPermissions();
    };

    window.addEventListener('permissionsUpdated', handlePermissionsUpdated);
    return () => window.removeEventListener('permissionsUpdated', handlePermissionsUpdated);
  }, [refreshPermissions]);

  // Auto-refresh permissions every 2 minutes for other users' changes
  useEffect(() => {
    if (!isAuthenticated() || !autoRefreshEnabled) return;

    const interval = setInterval(() => {
      loadPermissions(true); // Pass true for auto-refresh
    }, 2 * 60 * 1000); // 2 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated(), autoRefreshEnabled]);

  const normalizeKey = (str) => {
    if (!str) return '';
    return str.toString().replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
  };

  const hasPermissionByRoute = (routeName, action = 'view') => {
    if (!routeName || !action) return false;
    const targetNorm = normalizeKey(routeName);

    const item = menu.find(m => {
      if (m.route_name && normalizeKey(m.route_name) === targetNorm) return true;
      if (m.route && normalizeKey(m.route) === targetNorm) return true;
      if (m.module && normalizeKey(m.module) === targetNorm) return true;
      return false;
    });

    if (item && item.actions) {
      return item.actions.some(a => a.name === action);
    }

    for (const key of Object.keys(permissions)) {
      if (normalizeKey(key) === targetNorm) {
        if (permissions[key] && permissions[key][action] === true) {
          return true;
        }
      }
    }

    return false;
  };

  const hasPermission = (module, action = 'view') => {
    if (!module || !action) return false;
    if (hasPermissionByRoute(module, action)) return true;
    if (permissions[module] && permissions[module][action] === true) {
      return true;
    }
    const targetNorm = normalizeKey(module);
    for (const key of Object.keys(permissions)) {
      if (normalizeKey(key) === targetNorm) {
        if (permissions[key] && permissions[key][action] === true) {
          return true;
        }
      }
    }
    return false;
  };

  const hasAnyPermission = (module) => {
    if (!module) return false;
    if (hasPermissionByRoute(module, 'view')) return true;
    if (permissions[module] && Object.keys(permissions[module]).length > 0) {
      return true;
    }
    const targetNorm = normalizeKey(module);
    for (const key of Object.keys(permissions)) {
      if (normalizeKey(key) === targetNorm) {
        if (permissions[key] && Object.keys(permissions[key]).length > 0) {
          return true;
        }
      }
    }
    return false;
  };

  const getModuleActions = (module) => {
    const menuItem = menu.find(item => item.module === module || item.route_name === module || item.route === module);
    return (menuItem && menuItem.actions) || [];
  };

  const toggleAutoRefresh = () => {
    setAutoRefreshEnabled(prev => !prev);
    console.log(`🔄 [PermissionContext] Auto-refresh ${!autoRefreshEnabled ? 'enabled' : 'disabled'}`);
  };

  const value = {
    permissions,
    menu,
    loading,
    lastRefresh,
    autoRefreshEnabled,
    hasPermission,
    hasPermissionByRoute,
    hasAnyPermission,
    getModuleActions,
    loadPermissions,
    refreshPermissions,
    forceRefreshPermissions,
    toggleAutoRefresh
  };

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  );
}; 
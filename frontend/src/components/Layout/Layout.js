import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Collapse,
  Chip,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Security as SecurityIcon,
  Business as BusinessIcon,
  AccountTree as AccountTreeIcon,
  Settings as SettingsIcon,
  Assignment as AssignmentIcon,
  History as HistoryIcon,
  Person as PersonIcon,
  ExpandLess,
  ExpandMore,
  Logout as LogoutIcon,
  Poll as PollIcon,
  Ballot as BallotIcon,
  PersonAdd as PersonAddIcon,
  HowToVote as HowToVoteIcon,
  Groups as GroupsIcon,
  AdminPanelSettings as RolesIcon,
  VpnKey as PermissionsIcon,
  Domain as CompaniesIcon,
  CorporateFare as DepartmentsIcon,
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import { usePermissions } from '../../contexts/PermissionContext';
import PermissionRefreshNotification from '../Common/PermissionRefreshNotification';

const drawerWidth = 280;

export const AVAILABLE_MODULE_ICONS = [
  'dashboard',
  'people',
  'roles',
  'departments',
  'companies',
  'modules',
  'permissions',
  'user_roles',
  'audit',
  'voters',
  'elections',
  'ballots',
  'candidates',
  'voter_registrations',
  'votes',
  'settings',
  'security',
  'business',
];

export const renderModuleIcon = (iconOrModule) => {
  if (!iconOrModule) return <SettingsIcon />;
  const key = iconOrModule.toString().toLowerCase().replace(/[\s\-_]/g, '');
  const iconMap = {
    dashboard: <DashboardIcon />,
    people: <PeopleIcon />,
    users: <PeopleIcon />,
    roles: <RolesIcon />,
    departments: <DepartmentsIcon />,
    companies: <CompaniesIcon />,
    modules: <AccountTreeIcon />,
    accounttree: <AccountTreeIcon />,
    permissions: <PermissionsIcon />,
    vpnkey: <PermissionsIcon />,
    userroles: <AssignmentIcon />,
    assignment: <AssignmentIcon />,
    audit: <HistoryIcon />,
    history: <HistoryIcon />,
    voters: <GroupsIcon />,
    groups: <GroupsIcon />,
    elections: <PollIcon />,
    poll: <PollIcon />,
    ballots: <BallotIcon />,
    candidates: <PersonIcon />,
    person: <PersonIcon />,
    voterregistrations: <PersonAddIcon />,
    personadd: <PersonAddIcon />,
    votes: <HowToVoteIcon />,
    howtovote: <HowToVoteIcon />,
    settings: <SettingsIcon />,
    security: <SecurityIcon />,
    business: <BusinessIcon />,
    domain: <CompaniesIcon />,
  };
  return iconMap[key] || <SettingsIcon />;
};

const getModuleIcon = (moduleName, iconName) => {
  return renderModuleIcon(iconName || moduleName);
};

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { 
    menu, 
    hasAnyPermission, 
    hasPermission,
    hasPermissionByRoute,
    permissions,
    loading: permissionsLoading, 
    lastRefresh
  } = usePermissions();
  
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [expandedMenus, setExpandedMenus] = useState({});

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleProfileMenuClose();
  };

  const handleMenuClick = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const toggleMenuExpand = (module) => {
    setExpandedMenus(prev => ({
      ...prev,
      [module]: !prev[module]
    }));
  };

  const navigationItems = [
    { path: '/dashboard', label: 'Dashboard', icon: <DashboardIcon />, permission: 'Dashboard', order: 1 },
    { path: '/users', label: 'Users', icon: <PeopleIcon />, permission: 'Users', order: 2 },
    { path: '/roles', label: 'Roles', icon: <RolesIcon />, permission: 'Roles', order: 3 },
    { path: '/departments', label: 'Departments', icon: <DepartmentsIcon />, permission: 'Departments', order: 4 },
    { path: '/companies', label: 'Companies', icon: <CompaniesIcon />, permission: 'Companies', order: 5 },
    { path: '/modules', label: 'Modules', icon: <AccountTreeIcon />, permission: 'Modules', order: 6 },
    { path: '/permissions', label: 'Permissions', icon: <PermissionsIcon />, permission: 'Permissions', order: 7 },
    { path: '/user-roles', label: 'User Roles', icon: <AssignmentIcon />, permission: 'UserRoles', order: 8 },
    { path: '/audit-logs', label: 'Audit Logs', icon: <HistoryIcon />, permission: 'Audit', order: 9 },
    // Voting System
    { path: '/voters', label: 'Voters', icon: <GroupsIcon />, permission: 'Voters', order: 10 },
    { path: '/elections', label: 'Elections', icon: <PollIcon />, permission: 'Elections', order: 11 },
    { path: '/ballots', label: 'Ballots', icon: <BallotIcon />, permission: 'Ballots', order: 12 },
    { path: '/candidates', label: 'Candidates', icon: <PersonIcon />, permission: 'Candidates', order: 13 },
    { path: '/voter-registrations', label: 'Registrations', icon: <PersonAddIcon />, permission: 'VoterRegistrations', order: 14 },
    { path: '/votes', label: 'Votes', icon: <HowToVoteIcon />, permission: 'Votes', order: 15 },
  ];

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Access Control
        </Typography>
      </Toolbar>
      <Divider />
      
      <List>
        {(() => {
          const normalizeKey = (str) => {
            if (!str) return '';
            return str.toString().replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
          };

          const hardcodedModuleMap = {};
          navigationItems.forEach((item) => {
            const routeSlug = item.path.replace('/', '');
            const keys = [
              routeSlug,
              normalizeKey(routeSlug),
              item.permission,
              normalizeKey(item.permission)
            ];
            keys.forEach(k => {
              if (k && !hardcodedModuleMap[k]) hardcodedModuleMap[k] = item;
            });
          });

          const allMenuItems = [];
          
          menu.forEach((moduleItem) => {
            const rName = moduleItem.route_name || moduleItem.route || moduleItem.module;
            if (hasPermissionByRoute(rName, 'view') || hasPermission(moduleItem.module, 'view')) {
              const hardcodedItem = 
                (moduleItem.route_name && hardcodedModuleMap[moduleItem.route_name]) ||
                (moduleItem.route && hardcodedModuleMap[moduleItem.route]) ||
                (moduleItem.route_name && hardcodedModuleMap[normalizeKey(moduleItem.route_name)]) ||
                (moduleItem.route && hardcodedModuleMap[normalizeKey(moduleItem.route)]) ||
                hardcodedModuleMap[moduleItem.module] ||
                hardcodedModuleMap[normalizeKey(moduleItem.module)];

              if (hardcodedItem) {
                allMenuItems.push({
                  type: 'hardcoded',
                  path: hardcodedItem.path,
                  label: moduleItem.module || hardcodedItem.label,
                  icon: hardcodedItem.icon,
                  module: moduleItem.module,
                  order_index: moduleItem.order_index
                });
              } else {
                allMenuItems.push({
                  type: 'dynamic',
                  path: `/${moduleItem.route || moduleItem.route_name}`,
                  label: moduleItem.module,
                  icon: getModuleIcon(moduleItem.module, moduleItem.icon),
                  module: moduleItem.module,
                  order_index: moduleItem.order_index
                });
              }
            }
          });
          
          allMenuItems.sort((a, b) => (a.order_index || 999) - (b.order_index || 999));

          if (allMenuItems.length === 0 && !permissionsLoading) {
            return (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  No modules have been provisioned for your company yet. Please contact your Platform Administrator.
                </Typography>
              </Box>
            );
          }
          
          return allMenuItems.map((item, index) => {
            const isActive = location.pathname === item.path;
            
            return (
              <ListItem key={`${item.type}-${item.path}-${index}`} disablePadding>
                <Tooltip title={`Navigate to ${item.label}`} placement="right">
                  <ListItemButton
                    selected={isActive}
                    onClick={() => handleMenuClick(item.path)}
                  >
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.label} />
                  </ListItemButton>
                </Tooltip>
              </ListItem>
            );
          });
        })()}
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {location.pathname.replace('/', '').replace('-', ' ').toUpperCase() || 'DASHBOARD'}
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {permissionsLoading && (
              <Tooltip title="Refreshing permissions...">
                <CircularProgress size={20} color="inherit" />
              </Tooltip>
            )}
            
            <Typography variant="body2">
              {user && (user.is_administrator ? 'Platform Administrator' : user.company_name)}
            </Typography>
            
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleProfileMenuOpen}
              color="inherit"
            >
              <Avatar sx={{ width: 32, height: 32 }}>
                {user && user.name && user.name.charAt(0)}
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>
      
      <Menu
        id="menu-appbar"
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={Boolean(anchorEl)}
        onClose={handleProfileMenuClose}
      >
        <MenuItem onClick={() => { handleMenuClick('/profile'); handleProfileMenuClose(); }}>
          <PersonIcon sx={{ mr: 1 }} />
          Profile
        </MenuItem>
        <MenuItem onClick={handleLogout}>
          <LogoutIcon sx={{ mr: 1 }} />
          Logout
        </MenuItem>
      </Menu>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="mailbox folders"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        {children}
        
        {/* Permission refresh notification */}
        <PermissionRefreshNotification />
      </Box>
    </Box>
  );
};

export default Layout; 
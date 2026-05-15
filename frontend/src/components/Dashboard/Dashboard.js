import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Avatar,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Chip,
} from '@mui/material';
import {
  People as PeopleIcon,
  Security as SecurityIcon,
  Business as BusinessIcon,
  History as HistoryIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import { usePermissions } from '../../contexts/PermissionContext';
import { usersAPI, rolesAPI, departmentsAPI, auditAPI } from '../../services/api';

const StatCard = ({ title, value, icon, color = 'primary' }) => (
  <Card>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="h6">
            {title}
          </Typography>
          <Typography variant="h4">
            {value}
          </Typography>
        </Box>
        <Avatar sx={{ bgcolor: `${color}.main`, width: 56, height: 56 }}>
          {icon}
        </Avatar>
      </Box>
    </CardContent>
  </Card>
);

const Dashboard = () => {
  const { user, isAuthenticated } = useAuth();
  const { menu, permissions, hasPermission } = usePermissions();
  const [stats, setStats] = useState({
    users: 0,
    roles: 0,
    departments: 0,
    auditLogs: 0,
  });
  const [recentActivities, setRecentActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Only load data if user is authenticated and permissions are loaded
    if (isAuthenticated() && user && Object.keys(permissions).length > 0) {
      loadDashboardData();
    }
  }, [isAuthenticated, user, permissions]);

  const loadDashboardData = async () => {
    try {
      // Always try to load basic stats
      const apiCalls = [
        usersAPI.getAll({ per_page: 1 }),
        rolesAPI.getAll({ per_page: 1 }),
        departmentsAPI.getAll({ per_page: 1 }),
      ];

      // Only add audit logs if user has permission
      if (hasPermission && hasPermission('Settings', 'view')) {
        apiCalls.push(auditAPI.getLogs({ per_page: 10 }));
      }

      const results = await Promise.allSettled(apiCalls);
      
      const [usersRes, rolesRes, departmentsRes, auditRes] = results;

      setStats({
        users: usersRes.status === 'fulfilled' ? (usersRes.value.data?.total || 0) : 0,
        roles: rolesRes.status === 'fulfilled' ? (rolesRes.value.data?.total || 0) : 0,
        departments: departmentsRes.status === 'fulfilled' ? (departmentsRes.value.data?.total || 0) : 0,
        auditLogs: auditRes && auditRes.status === 'fulfilled' ? (auditRes.value.data?.pagination?.total || 0) : 0,
      });

      if (auditRes && auditRes.status === 'fulfilled') {
        setRecentActivities(auditRes.value.data?.logs || []);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTotalPermissions = () => {
    return Object.values(permissions).reduce((total, modulePerms) => {
      return total + Object.keys(modulePerms).length;
    }, 0);
  };

  const getActivityIcon = (action) => {
    return (action && action.toLowerCase().includes('create')) ? 
      <CheckCircleIcon color="success" /> : 
      <ErrorIcon color="error" />;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome back, {user && user.name}!
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Here's what's happening in your {user && user.company_name} organization
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Users"
            value={stats.users}
            icon={<PeopleIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Roles"
            value={stats.roles}
            icon={<SecurityIcon />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Departments"
            value={stats.departments}
            icon={<BusinessIcon />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Audit Logs"
            value={stats.auditLogs}
            icon={<HistoryIcon />}
            color="warning"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activities
            </Typography>
            <List>
              {recentActivities.length === 0 ? (
                <Typography color="text.secondary">No recent activities</Typography>
              ) : (
                recentActivities.map((activity, index) => (
                  <React.Fragment key={activity.id || index}>
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar>
                          {getActivityIcon(activity.action)}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={`${activity.action} - ${activity.module || 'System'}`}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              User: {activity.user && activity.user.name ? activity.user.name : 'System'} | IP: {activity.ip_address || 'N/A'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {activity.timestamp ? new Date(activity.timestamp).toLocaleString() : 'N/A'}
                            </Typography>
                          </Box>
                        }
                      />
                      <Chip
                        label={activity.success ? 'Success' : 'Failed'}
                        color={activity.success ? 'success' : 'error'}
                        size="small"
                      />
                    </ListItem>
                    {index < recentActivities.length - 1 && <Divider />}
                  </React.Fragment>
                ))
              )}
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Your Permissions
            </Typography>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Total Permissions: {getTotalPermissions()}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Available Modules: {menu.length}
              </Typography>
                             {menu.map((moduleItem) => (
                 <Box key={moduleItem.module} sx={{ mt: 1 }}>
                   <Chip
                     label={`${moduleItem.module} (${(moduleItem.actions && moduleItem.actions.length) || 0})`}
                     size="small"
                     variant="outlined"
                     sx={{ mr: 1, mb: 1 }}
                   />
                 </Box>
               ))}
            </Box>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Info
            </Typography>
                         <Box>
               <Typography variant="body2" gutterBottom>
                 <strong>Company:</strong> {user && user.company_name}
               </Typography>
               <Typography variant="body2" gutterBottom>
                 <strong>Email:</strong> {user && user.email}
               </Typography>
               <Typography variant="body2" gutterBottom>
                 <strong>User ID:</strong> {user && user.id}
               </Typography>
             </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
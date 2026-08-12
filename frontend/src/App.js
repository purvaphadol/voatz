import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from './contexts/AuthContext';
import { PermissionProvider } from './contexts/PermissionContext';
import Login from './components/Auth/Login';
import ForgotPassword from './components/Auth/ForgotPassword';
import ResetPassword from './components/Auth/ResetPassword';
import Dashboard from './components/Dashboard/Dashboard';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Layout from './components/Layout/Layout';
import Users from './components/Users/Users';
import Roles from './components/Roles/Roles';
import Departments from './components/Departments/Departments';
import Companies from './components/Companies/Companies';
import Modules from './components/Modules/Modules';
import Permissions from './components/Permissions/Permissions';
import UserRoles from './components/UserRoles/UserRoles';
import AuditLogs from './components/Audit/AuditLogs';
import Profile from './components/Profile/Profile';
import TestModule from './components/TestModule/TestModule';
import DynamicModule from './components/DynamicModule/DynamicModule';
import NotFound from './components/Error/NotFound';
import PermissionGuard from './components/Auth/PermissionGuard';

// Voting System Components
import Voters from './components/Voting/Voters/Voters';
import Elections from './components/Voting/Elections/Elections';
import Ballots from './components/Voting/Ballots/Ballots';
import Candidates from './components/Voting/Candidates/Candidates';
import Votes from './components/Voting/Votes/Votes';
import VoterRegistrations from './components/Voting/VoterRegistrations/VoterRegistrations';

import './App.css';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          minHeight: '56px',
          '&:not(.MuiInputBase-multiline)': {
            height: '56px',
          },
          '&.MuiInputBase-multiline': {
            minHeight: 'auto',
            height: 'auto',
          },
        },
        input: {
          '&:not(.MuiInputBase-inputMultiline)': {
            padding: '16.5px 14px',
            boxSizing: 'border-box',
          },
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <PermissionProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Routes>
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="/dashboard" element={<Dashboard />} />
                        <Route 
                          path="/users" 
                          element={
                            <PermissionGuard route="users" action="view" showInLayout={true}>
                              <Users />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/roles" 
                          element={
                            <PermissionGuard route="roles" action="view" showInLayout={true}>
                              <Roles />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/departments" 
                          element={
                            <PermissionGuard route="departments" action="view" showInLayout={true}>
                              <Departments />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/companies" 
                          element={
                            <PermissionGuard route="companies" action="view" showInLayout={true}>
                              <Companies />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/modules" 
                          element={
                            <PermissionGuard route="modules" action="view" showInLayout={true}>
                              <Modules />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/permissions" 
                          element={
                            <PermissionGuard route="permissions" action="view" showInLayout={true}>
                              <Permissions />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/user-roles" 
                          element={
                            <PermissionGuard route="user-roles" action="view" showInLayout={true}>
                              <UserRoles />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/audit-logs" 
                          element={
                            <PermissionGuard route="audit-logs" action="view" showInLayout={true}>
                              <AuditLogs />
                            </PermissionGuard>
                          } 
                        />
                        <Route path="/profile" element={<Profile />} />
                        <Route path="/testmodule" element={<TestModule />} />
                        
                        {/* Voting System Routes */}
                        <Route 
                          path="/voters" 
                          element={
                            <PermissionGuard route="voters" action="view" showInLayout={true}>
                              <Voters />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/elections" 
                          element={
                            <PermissionGuard route="elections" action="view" showInLayout={true}>
                              <Elections />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/ballots" 
                          element={
                            <PermissionGuard route="ballots" action="view" showInLayout={true}>
                              <Ballots />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/candidates" 
                          element={
                            <PermissionGuard route="candidates" action="view" showInLayout={true}>
                              <Candidates />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/votes" 
                          element={
                            <PermissionGuard route="votes" action="view" showInLayout={true}>
                              <Votes />
                            </PermissionGuard>
                          } 
                        />
                        <Route 
                          path="/voter-registrations" 
                          element={
                            <PermissionGuard route="voter-registrations" action="view" showInLayout={true}>
                              <VoterRegistrations />
                            </PermissionGuard>
                          } 
                        />
                        
                        {/* Dynamic route for all other modules */}
                        {/* <Route path="/:moduleName" element={<DynamicModule />} /> */}
                        {/* 404 catch-all route - must be last */}
                        <Route path="*" element={<NotFound />} />
                      </Routes>
                    </Layout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </Router>
        </PermissionProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

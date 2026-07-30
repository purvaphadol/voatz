import axios from 'axios';
import Cookies from 'js-cookie';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://192.168.10.166:4000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      // Debug logging for token issues
      if (window.DEBUG_API) {
        console.log('🔑 [API] Adding token to request:', {
          url: config.url,
          method: config.method?.toUpperCase(),
          token: token.substring(0, 20) + '...'
        });
      }
    } else {
      console.warn('⚠️ [API] No access token found for request:', config.url);
    }
    return config;
  },
  (error) => {
    console.error('🚨 [API] Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    if (window.DEBUG_API) {
      console.log('✅ [API] Request successful:', {
        url: response.config.url,
        status: response.status,
        method: response.config.method?.toUpperCase()
      });
    }
    return response;
  },
  (error) => {
    // Enhanced error logging
    console.error('🚨 [API] Request failed:', {
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      status: error.response?.status,
      data: error.response?.data,
      headers: error.config?.headers
    });

    if (error.response && error.response.status === 401) {
      console.error('🔒 [API] 401 UNAUTHORIZED - Token may be expired or invalid');
      
      // Check if token exists
      const token = Cookies.get('access_token');
      if (!token) {
        console.error('🔒 [API] No token found in cookies');
      } else {
        console.error('🔒 [API] Token exists but was rejected by server');
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          console.error('🔒 [API] Token details:', {
            exp: new Date(payload.exp * 1000),
            iat: new Date(payload.iat * 1000),
            user_id: payload.sub,
            expired: new Date(payload.exp * 1000) < new Date()
          });
        } catch (e) {
          console.error('🔒 [API] Could not decode token:', e);
        }
      }
      
      // Only redirect if we're not already on the login page
      const currentPath = window.location.pathname;
      if (currentPath !== '/login') {
        console.log('🔒 [API] Redirecting to login page');
        // Token expired or invalid - clear auth data and redirect
        Cookies.remove('access_token');
        Cookies.remove('user');
        // Add a small delay to prevent redirect loops during component mounting
        setTimeout(() => {
          window.location.href = '/login';
        }, 100);
      }
    }
    return Promise.reject(error);
  }
);

// Debug mode (set to false in production)
window.DEBUG_API = false;

// Reusable API error handler
export const handleApiError = (error) => {
  return error.response?.data?.error || error.message || 'An unexpected error occurred';
};

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  refresh: () => api.post('/auth/refresh'),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
};

// Users API
export const usersAPI = {
  getAll: (params = {}) => api.get('/users/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
};

// Roles API
export const rolesAPI = {
  getAll: (params = {}) => api.get('/roles/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post('/roles/', data),
  update: (id, data) => api.put(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
};

// Departments API
export const departmentsAPI = {
  getAll: (params = {}) => api.get('/departments/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/departments/${id}`),
  create: (data) => api.post('/departments/', data),
  update: (id, data) => api.put(`/departments/${id}`, data),
  delete: (id) => api.delete(`/departments/${id}`),
};

// Companies API
export const companiesAPI = {
  getAll: (params = {}) => api.get('/companies/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/companies/${id}`),
  create: (data) => api.post('/companies/', data),
  update: (id, data) => api.put(`/companies/${id}`, data),
  delete: (id) => api.delete(`/companies/${id}`),
};

// Modules API
export const modulesAPI = {
  getAll: (params = {}) => api.get('/modules/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/modules/${id}`),
  create: (data) => api.post('/modules/', data),
  update: (id, data) => api.put(`/modules/${id}`, data),
  delete: (id) => api.delete(`/modules/${id}`),
};

// Module Actions API
export const moduleActionsAPI = {
  getModuleActions: (moduleId) => api.get(`/module-actions/module/${moduleId}/actions`),
  createAction: (moduleId, actionData) => api.post(`/module-actions/module/${moduleId}/actions`, actionData),
  updateAction: (actionId, actionData) => api.put(`/module-actions/action/${actionId}`, actionData),
  deleteAction: (actionId) => api.delete(`/module-actions/action/${actionId}`),
  createBulkActions: (moduleId, actionsData) => api.post('/module-actions/actions/bulk', {
    module_id: moduleId,
    actions: actionsData,
  }),
};

// Permissions API
export const permissionsAPI = {
  getUserPermissions: (userId) => userId ? api.get(`/permissions/user/${userId}`) : api.get('/permissions/user'),
  getUserPermissionsForManagement: (userId) => api.get(`/permissions/user/${userId}/management`),
  getRolePermissions: (roleId) => api.get(`/permissions/role/${roleId}`),
  updateRolePermissions: (roleId, permissions) => 
    api.post(`/permissions/role/${roleId}`, { permissions }),
  updateUserPermissions: (userId, permissions) => 
    api.post(`/permissions/user/${userId}`, { permissions }),
  getModuleActions: () => api.get('/permissions/module-actions'),
  getUserSummary: (userId) => api.get(`/permissions/user/${userId}/summary`),
};

// User Roles API
export const userRolesAPI = {
  getAll: (params = {}) => api.get('/user-roles/', { params: { per_page: 500, ...params } }),
  assign: (data) => api.post(`/user-roles/user/${data.user_id}/roles`, data),
  unassign: (mappingId) => api.delete(`/user-roles/user-role/${mappingId}`),
  getUserRoles: (userId) => api.get(`/user-roles/user/${userId}/roles`),
};

// Menu API
export const menuAPI = {
  getSidebar: () => api.get('/menu/sidebar'),
  getNavigation: () => api.get('/menu/navigation'),
  getPermissions: () => api.get('/menu/permissions'),
};

// Audit API
export const auditAPI = {
  getLogs: (params = {}) => api.get('/audit/logs', { params: { per_page: 500, ...params } }),
  getStats: () => api.get('/audit/stats'),
  getFailures: (params = {}) => api.get('/audit/failures', { params: { per_page: 500, ...params } }),
  exportLogs: (params = {}) => api.get('/audit/export', { params: { per_page: 500, ...params }, responseType: 'blob' }),
};

// Health API
export const healthAPI = {
  check: () => api.get('/health'),
};

// ===========================================
// VOTING SYSTEM APIs
// ===========================================

// Voters API
export const votersAPI = {
  getAll: (params = {}) => api.get('/voters/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/voters/${id}`),
  create: (data) => api.post('/voters/', data),
  update: (id, data) => api.put(`/voters/${id}`, data),
  delete: (id) => api.delete(`/voters/${id}`),
  verify: (id, data) => api.post(`/voters/${id}/verify`, data),
  getRegistrations: (id) => api.get(`/voters/${id}/registrations`),
  getVotes: (id) => api.get(`/voters/${id}/votes`),
  getStats: () => api.get('/voters/stats'),
};

// Elections API
export const electionsAPI = {
  getAll: (params = {}) => api.get('/elections/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/elections/${id}`),
  create: (data) => api.post('/elections/', data),
  update: (id, data) => api.put(`/elections/${id}`, data),
  delete: (id) => api.delete(`/elections/${id}`),
  activate: (id) => api.post(`/elections/${id}/activate`),
  publishResults: (id) => api.post(`/elections/${id}/publish-results`),
  changeStatus: (id, status) => api.post(`/elections/${id}/change-status`, { status }),
  getBallots: (id) => api.get(`/elections/${id}/ballots`),
  getRegistrations: (id, params = {}) => api.get(`/elections/${id}/registrations`, { params: { per_page: 500, ...params } }),
  getStats: () => api.get('/elections/stats'),
};

// Ballots API
export const ballotsAPI = {
  getAll: (params = {}) => api.get('/ballots/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/ballots/${id}`),
  create: (data) => api.post('/ballots/', data),
  update: (id, data) => api.put(`/ballots/${id}`, data),
  delete: (id) => api.delete(`/ballots/${id}`),
  publish: (id) => api.post(`/ballots/${id}/publish`),
  unpublish: (id) => api.post(`/ballots/${id}/unpublish`),
  getCandidates: (id) => api.get(`/ballots/${id}/candidates`),
  reorderCandidates: (id, data) => api.post(`/ballots/${id}/reorder`, data),
  duplicate: (id, data) => api.post(`/ballots/${id}/duplicate`, data),
  getStats: () => api.get('/ballots/stats'),
};

// Candidates API
export const candidatesAPI = {
  getAll: (params = {}) => api.get('/candidates/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/candidates/${id}`),
  create: (data) => api.post('/candidates/', data),
  update: (id, data) => api.put(`/candidates/${id}`, data),
  delete: (id) => api.delete(`/candidates/${id}`),
  withdraw: (id, data) => api.post(`/candidates/${id}/withdraw`, data),
  reinstate: (id) => api.post(`/candidates/${id}/reinstate`),
  getStats: () => api.get('/candidates/stats'),
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('image', file);
    return api.post('/candidates/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Votes API
export const votesAPI = {
  getAll: (params = {}) => api.get('/votes/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/votes/${id}`),
  cast: (data) => api.post('/votes/', data),
  verify: (id, data) => api.post(`/votes/${id}/verify`, data),
  count: (id) => api.post(`/votes/${id}/count`),
  flag: (id, data) => api.post(`/votes/${id}/flag`, data),
  track: (trackingCode) => api.get(`/votes/tracking/${trackingCode}`),
  bulkVerify: (data) => api.post('/votes/bulk-verify', data),
  getStats: () => api.get('/votes/stats'),
};

// Voter Registrations API
export const voterRegistrationsAPI = {
  getAll: (params = {}) => api.get('/voter-registrations/', { params: { per_page: 500, ...params } }),
  getById: (id) => api.get(`/voter-registrations/${id}`),
  create: (data) => api.post('/voter-registrations/', data),
  update: (id, data) => api.put(`/voter-registrations/${id}`, data),
  approve: (id, data) => api.post(`/voter-registrations/${id}/approve`, data),
  reject: (id, data) => api.post(`/voter-registrations/${id}/reject`, data),
  bulkApprove: (data) => api.post('/voter-registrations/bulk-approve', data),
  getStats: () => api.get('/voter-registrations/stats'),
};

export default api; 

import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      // Check for existing token on app load
      const savedToken = Cookies.get('access_token');
      const savedUser = Cookies.get('user');
      
      if (savedToken && savedUser) {
        try {
          setToken(savedToken);
          let parsedUser = JSON.parse(savedUser);
          
          if (!Array.isArray(parsedUser.roles)) {
            const response = await authAPI.getProfile();
            parsedUser = response.data;
            if (!Array.isArray(parsedUser.roles)) parsedUser.roles = [];
            Cookies.set('user', JSON.stringify(parsedUser), { expires: 1 });
          }
          
          setUser(parsedUser);
        } catch (error) {
          console.error('Error parsing saved user data or fetching profile:', error);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login({ email, password });
      const { access_token, user: userData } = response.data;
      
      if (!Array.isArray(userData.roles)) userData.roles = [];
      
      setToken(access_token);
      setUser(userData);
      
      // Save to cookies with 24 hour expiry
      Cookies.set('access_token', access_token, { expires: 1 });
      Cookies.set('user', JSON.stringify(userData), { expires: 1 });
      
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: (error.response && error.response.data && error.response.data.error) || 'Login failed'
      };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    Cookies.remove('access_token');
    Cookies.remove('user');
  };

  const isAuthenticated = () => {
    return !!(token && user);
  };

  const value = {
    user,
    token,
    login,
    logout,
    isAuthenticated,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 
import React, { createContext, useState, useEffect, useContext, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/unifiedApiClient';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  // Initialize state
  const [user, setUser] = useState(() => {
    // Try to get user from localStorage on initial load
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [loading, setLoading] = useState(true); // Start with loading true for initial auth check
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const initializingRef = useRef(false);
  const refreshingRef = useRef(false);

  // Initialize API client
  const client = useMemo(() => {
    const client = apiClient;
    // Check for existing refresh token
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      // Token exists, we'll attempt to refresh it in useEffect
      // Token exists, we'll attempt to refresh it in useEffect
    }
    return client;
  }, []);

  // Make navigate available globally for API client auth error handling
  useEffect(() => {
    window.__CAHOOTS_NAVIGATE = navigate;
    return () => {
      delete window.__CAHOOTS_NAVIGATE;
    };
  }, [navigate]);

  // Initialize auth state with race condition protection
  useEffect(() => {
    if (initializingRef.current) return;
    initializingRef.current = true;
    
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('token'); // Get actual stored token, not dev-bypass
        const refreshToken = localStorage.getItem('refresh_token');
        
        
        if (token || token === 'dev-bypass-token') {
          // Clear logout flag when user is authenticated with real token
          localStorage.removeItem('has_logged_out');
          
          // Verify token by fetching user data (works for both real tokens and dev-bypass-token)
          const userData = await apiClient.get('/auth/me');
          console.log('[AuthContext] Initial auth check - userData:', userData);
          console.log('[AuthContext] User role from /auth/me:', userData.role);
          console.log('[AuthContext] User email from /auth/me:', userData.email);
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        } else if (refreshToken) {
          // We have a refresh token but no access token, try to refresh
          try {
            // Use the refreshToken method from the API client
            await apiClient.refreshToken();
            
            // If successful, fetch user data
            const userData = await apiClient.get('/auth/me');
            setUser(userData);
            localStorage.setItem('user', JSON.stringify(userData));
          } catch (refreshErr) {
            console.error('[AuthContext] Token refresh failed:', refreshErr);
            // Remove invalid refresh token
            localStorage.removeItem('refresh_token');
            handleAuthError('Session expired. Please log in again.');
          }
        } else {
        }
      } catch (err) {
        // Token is invalid or expired
        console.error('[AuthContext] Auth initialization error:', err);
        handleAuthError('Session expired. Please log in again.');
      } finally {
        setLoading(false);
        initializingRef.current = false;
      }
    };

    initAuth();
  }, []);

  // Handle authentication errors consistently
  const handleAuthError = (message = 'Authentication failed') => {
    setUser(null);
    setError(message);
    apiClient.setAuthToken(null);
    localStorage.removeItem('user');
    
    // Auto-clear error after 5 seconds
    setTimeout(() => setError(null), 5000);
  };

  // Enhanced token refresh with retry logic
  const refreshToken = async () => {
    if (refreshingRef.current) return false;
    refreshingRef.current = true;
    
    try {
      setError(null);
      const response = await apiClient.refreshToken();
      
      // Fetch updated user data
      const userData = await apiClient.get('/auth/me');
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      
      return true;
    } catch (err) {
      handleAuthError('Session expired. Please log in again.');
      return false;
    } finally {
      refreshingRef.current = false;
    }
  };

  // Enhanced login with better error handling
  const login = async (email, password) => {
    try {
      setError(null);
      setLoading(true);

      // Create form data for OAuth2 token endpoint
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      // Pass config to set proper Content-Type for FormData
      const tokenResponse = await apiClient.post('/auth/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      const { access_token, refresh_token } = tokenResponse;

      // Store both tokens
      apiClient.setAuthToken(access_token);
      localStorage.setItem('refresh_token', refresh_token);
      
      // Clear logout flag on successful login
      localStorage.removeItem('has_logged_out');

      // Fetch user data
      const userData = await apiClient.get('/auth/me');
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));

      return userData;
    } catch (err) {
      const message = err.userMessage || 'Login failed. Please check your credentials.';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  // Enhanced registration
  const register = async (userData) => {
    try {
      setError(null);
      setLoading(true);
      
      const response = await apiClient.post('/auth/register', userData);
      return response;
    } catch (err) {
      const message = err.userMessage || 'Registration failed. Please try again.';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  // Enhanced logout with cleanup
  const logout = async () => {
    try {
      setLoading(true);
      
      // Call logout endpoint if authenticated
      if (user && apiClient.getAuthToken()) {
        await apiClient.post('/auth/logout');
      }
    } catch (err) {
      // Log error but don't prevent logout
      console.error('Logout API call failed:', err);
    } finally {
      // Always clean up local state
      setUser(null);
      setError(null);
      apiClient.setAuthToken(null);
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      
      // Clean up legacy global settings (migration cleanup)
      localStorage.removeItem('userSettings');
      
      // Set logout flag to prevent dev-bypass-token from auto-login
      localStorage.setItem('has_logged_out', 'true');
      
      // Clear any OAuth state
      sessionStorage.removeItem('oauth_state');
      sessionStorage.removeItem('oauth_retry_count');
      
      setLoading(false);
      
    }
  };

  // Enhanced OAuth URL generation
  const getOAuthUrl = async (provider) => {
    try {
      setError(null);
      
      const redirectUri = `${window.location.origin}/oauth/${provider}/callback`;
      const response = await apiClient.get(`/auth/${provider}/authorize`, {
        params: { redirect_uri: redirectUri }
      });
      
      // Store state for CSRF protection
      if (response.state) {
        sessionStorage.setItem('oauth_state', response.state);
      }
      
      return response.redirect_uri;
    } catch (err) {
      const message = err.userMessage || `Failed to get ${provider} authorization URL`;
      setError(message);
      throw new Error(message);
    }
  };

  // Enhanced OAuth callback handling
  const handleOAuthCallback = async (userData) => {
    try {
      setError(null);
      
      if (!userData?.id) {
        throw new Error('Invalid user data received from OAuth provider');
      }
      
      // Log the user data to check if role is included
      console.log('[AuthContext] handleOAuthCallback - userData:', userData);
      console.log('[AuthContext] User role:', userData.role);
      console.log('[AuthContext] User email:', userData.email);
      
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Clear logout flag on successful OAuth login
      localStorage.removeItem('has_logged_out');
      
      // Verify token was set by OAuth callback endpoint
      const token = apiClient.getAuthToken();
      if (!token) {
        throw new Error('No authentication token received');
      }
      
      // Clear OAuth state
      sessionStorage.removeItem('oauth_state');
      sessionStorage.removeItem('oauth_retry_count');
      
      return userData;
    } catch (err) {
      const message = err.message || 'Failed to process OAuth authentication';
      handleAuthError(message);
      throw new Error(message);
    }
  };

  // Enhanced authentication check
  const isAuthenticated = () => {
    const token = apiClient.getAuthToken();
    
    // In development mode, allow dev-bypass-token and set up user if needed
    if (token === 'dev-bypass-token') {
      // Only create dev user if we don't have one yet
      if (!user) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const parsedUser = JSON.parse(storedUser);
          setUser(parsedUser);
        } else {
          // Create default dev admin user (matches what the backend returns)
          const defaultUser = {
            id: 'dev-user-123',
            email: 'admin@cahoots.cc',
            username: 'admin',
            full_name: 'Admin User',
            role: 'admin',
            subscription_tier: 'enterprise',
            subscription_status: 'active',
            monthly_task_limit: 1000,
            tasks_created_this_month: 0
          };
          setUser(defaultUser);
          localStorage.setItem('user', JSON.stringify(defaultUser));
        }
      }
      return true;
    }
    
    return !!(user && token);
  };

  // Clear error manually
  const clearError = () => {
    setError(null);
  };

  const contextValue = {
    // State
    user,
    loading,
    error,
    
    // Actions
    login,
    register,
    logout,
    refreshToken,
    getOAuthUrl,
    handleOAuthCallback,
    isAuthenticated,
    clearError,
    
    // Internal state setters for OAuth callback component
    setUser,
    setLoading,
    setError
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Enhanced useAuth hook with better error handling
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
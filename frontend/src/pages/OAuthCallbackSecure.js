import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../services/unifiedApiClient';
import { withErrorHandling } from '../services/errorHandler';
import { LoadingTypes } from '../services/loadingService';
import { LoadingSpinner, ErrorMessage } from '../design-system';

const OAuthCallbackSecure = () => {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const { handleOAuthCallback } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const exchangeCodeForTokens = async () => {
      try {
        setError(null);
        
        // We're starting a fresh OAuth login flow
        console.log('%c === OAUTH CALLBACK SECURE - START === ', 'background: #222; color: #bada55; font-size: 16px');
        console.log('Starting OAuth callback secure flow...');
        
        // Log browser storage state
        console.log('localStorage items:', Object.keys(localStorage).reduce((acc, key) => {
          acc[key] = localStorage.getItem(key);
          return acc;
        }, {}));
        
        console.log('sessionStorage items:', Object.keys(sessionStorage).reduce((acc, key) => {
          acc[key] = sessionStorage.getItem(key);
          return acc;
        }, {}));
        
        // Log auth headers
        console.log('Current apiClient auth header configured');
        
        // Calculate time since OAuth redirect started (if available)
        const redirectTime = localStorage.getItem('oauth_redirect_time');
        if (redirectTime) {
          const elapsed = Date.now() - parseInt(redirectTime);
          console.log(`Time elapsed since OAuth redirect: ${elapsed}ms (${elapsed/1000} seconds)`);
        }
        
        // Parse query parameters to get the auth code
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        
        if (!code) {
          throw new Error('No authorization code found in URL');
        }
        
        console.log('Exchanging authorization code for tokens:', code);
        console.log('Using apiClient for token exchange');
        
        // Check if we have a valid code
        if (!code || code.trim() === '') {
          console.error('Invalid or empty authorization code');
          throw new Error('Invalid authorization code');
        }
        
        // Log the API endpoint being used for the token exchange
        const exchangeUrl = `/api/exchange-auth-code`;
        console.log('Token exchange endpoint:', exchangeUrl);
        
        // Exchange the auth code for tokens with enhanced error handling
        console.log('Sending token exchange request with code:', code);
        
        const { data: tokenData, error: tokenError } = await withErrorHandling(
          () => apiClient.postWithLoading('/exchange-auth-code', null, LoadingTypes.AUTH_OAUTH, {
            params: { code },
            withCredentials: true
          }),
          {
            customMessages: {
              AUTHENTICATION: 'OAuth authentication failed. Please try again.',
              VALIDATION_ERROR: 'Your login session has expired. Please try logging in again.',
              SERVER_ERROR: 'Server error during OAuth flow. Please try again later.'
            }
          }
        );
        
        if (tokenError) {
          if (tokenError.status === 400) {
            setError(tokenError.message);
            setLoading(false);
            return;
          }
          throw new Error(tokenError.message);
        }
        
        const response = { data: tokenData };
        console.log('Token exchange response received:', response.data ? 'success' : 'no data');
        
        if (!tokenData || !tokenData.access_token) {
          throw new Error('No access token returned from server');
        }
        
        console.log('Successfully exchanged auth code for tokens:', tokenData);
        
        // Store the tokens
        console.log('Storing access token in localStorage:', tokenData.access_token.substring(0, 10) + '...');
        localStorage.setItem('token', tokenData.access_token);
        
        // Verify the token was stored correctly
        const storedToken = localStorage.getItem('token');
        console.log('Verifying token storage - token exists:', !!storedToken);
        console.log('Stored token (first 10 chars):', storedToken ? storedToken.substring(0, 10) + '...' : 'null');
        
        if (tokenData.refresh_token) {
          console.log('Storing refresh token in localStorage');
          localStorage.setItem('refresh_token', tokenData.refresh_token);
        }
        
        // Token header is automatically handled by apiClient
        console.log('Token will be automatically handled by apiClient interceptor');
        
        // Fetch user data
        console.log('Fetching user data...');
        const { data: userData, error: userError } = await withErrorHandling(
          () => apiClient.get('/auth/me'),
          {
            customMessages: {
              AUTHENTICATION: 'Failed to fetch user data. Please try logging in again.',
              SERVER_ERROR: 'Server error while fetching user data. Please try again.'
            }
          }
        );
        
        if (userError) {
          throw new Error(userError.message);
        }
        
        console.log('User data fetched:', userData);
        
        // IMPORTANT: Update auth context with user data
        console.log('Authentication successful, updating auth context');
        
        // Ensure tokens are stored in localStorage
        console.log('Ensuring tokens are stored in localStorage...');
        localStorage.setItem('token', tokenData.access_token);
        if (tokenData.refresh_token) {
          localStorage.setItem('refresh_token', tokenData.refresh_token);
        }
        
        // Token header is automatically handled by apiClient
        console.log('Token automatically configured for future requests');
        
        // Update auth context with user data
        console.log('Updating auth context with user data...');
        await handleOAuthCallback(userData);
        
        // Double-check that token is in localStorage
        const token = localStorage.getItem('token');
        if (!token) {
          console.error('Token not found in localStorage after handleOAuthCallback');
          // Set token again to be sure
          localStorage.setItem('token', tokenData.access_token);
          console.log('Token manually set in localStorage');
        }
        
        // Set a flag in sessionStorage to indicate successful login
        sessionStorage.setItem('oauth_login_success', 'true');
        
        // Navigate to dashboard using React Router
        console.log('Navigating to dashboard...');
        navigate('/dashboard');
      } catch (err) {
        console.error('Error in authentication flow:', err);
        console.error('Error details:', err.response ? err.response.data : err.message);
        console.error('Error status:', err.response ? err.response.status : 'No status');
        console.error('Error headers:', err.response ? err.response.headers : 'No headers');
        
        // Handle expired or invalid authorization code
        if (err.response && err.response.status === 400) {
          setError('Authorization code expired or invalid. Please try logging in again.');
        } else {
          setError(err.message || 'Authentication failed');
        }
      } finally {
        setLoading(false);
      }
    };

    exchangeCodeForTokens();
  }, [location, navigate, handleOAuthCallback]);

  if (loading) {
    return (
      <div className="min-h-screen bg-brand-dark-bg flex items-center justify-center">
        <div className="flex flex-col items-center">
          <LoadingSpinner size="large" />
          <p className="text-brand-text mt-4">Completing authentication...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-brand-dark-bg flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <ErrorMessage message={error} className="mb-6" />
          <div className="text-center">
            <p className="text-brand-muted-text mb-4">
              Authentication failed. Please try again or use another authentication method.
            </p>
            <button 
              onClick={() => navigate('/login')} 
              className="btn btn-primary px-6 py-2 rounded-lg font-medium"
            >
              Return to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-dark-bg flex items-center justify-center">
      <div className="flex flex-col items-center">
        <LoadingSpinner size="large" />
        <p className="text-brand-text mt-4">Authentication successful! Redirecting to dashboard...</p>
      </div>
    </div>
  );
};

export default OAuthCallbackSecure;

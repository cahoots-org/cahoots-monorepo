import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../services/unifiedApiClient';
import { LoadingSpinner, ErrorMessage } from '../design-system';

const OAuthCallback = () => {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const { handleOAuthCallback } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { provider } = useParams(); // Get provider from URL params

  useEffect(() => {
    const processOAuthCallback = async () => {
      try {
        // Check if we've already processed this callback
        const currentUrl = window.location.href;
        const callbackProcessed = sessionStorage.getItem('processed_callback_url');
        
        if (callbackProcessed === currentUrl) {
          // This callback URL has already been processed
          navigate('/dashboard');
          return;
        }
        
        // Mark this callback as being processed
        sessionStorage.setItem('processed_callback_url', currentUrl);
        
        // Parse query parameters
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        const urlState = params.get('state');
        const oauthError = params.get('error');
        
        // Check for error parameter first
        if (oauthError) {
          throw new Error(`OAuth error: ${oauthError}`);
        }
        
        // Get stored state from sessionStorage (this is the state we sent to the backend)
        const storedState = sessionStorage.getItem('oauth_state');
        
        
        // Use provider from URL params or fallback to 'google' (for logging only)
        const providerForLog = provider || 'google';
        console.debug(`OAuth callback for provider: ${providerForLog}`);

        if (!code) {
          throw new Error(`Missing required OAuth parameter: code`);
        }
        
        // Use stored state if available, otherwise fall back to URL state
        const state = storedState || urlState;
        if (!state) {
          console.warn('Missing OAuth state parameter - not found in URL or sessionStorage');
          // Continue anyway since some providers might not use state
        }
        
        if (state) {
        }
        
        // Generate a unique key for this authorization code
        const codeKey = `oauth_code_${code.substring(0, 10)}`;
        
        // Check if we're already processing this code to prevent duplicate submissions
        const isProcessing = localStorage.getItem(codeKey);
        const processingStartTime = localStorage.getItem(`${codeKey}_start_time`);
        const currentTime = Date.now();
        
        // If we've been processing for more than 2 minutes, assume something went wrong and try again
        if (isProcessing && processingStartTime) {
          const processingTime = currentTime - parseInt(processingStartTime, 10);
          if (processingTime > 120000) { // 2 minutes
            // OAuth processing timeout detected, clearing stale flag
            localStorage.removeItem(codeKey);
            localStorage.removeItem(`${codeKey}_start_time`);
          }
        }
        
        // If still processing and not timed out, redirect to dashboard
        if (isProcessing) {
          // Authorization code is already being processed
          // Clear stored state
          sessionStorage.removeItem('oauth_state');
          // Redirect to dashboard
          navigate('/dashboard');
          return;
        }
        
        // Mark this code as being processed and record the start time
        localStorage.setItem(codeKey, 'true');
        localStorage.setItem(`${codeKey}_start_time`, currentTime.toString());
        
        // Clear any previous OAuth flow flags
        localStorage.removeItem('oauth_flow_started');
        localStorage.removeItem('oauth_in_progress');
        
        // Clear stored state before making the API call
        sessionStorage.removeItem('oauth_state');
        
        // Set a flag to indicate we're in the OAuth flow
        localStorage.setItem('oauth_in_progress', 'true');
        
        // Set a timeout to clear the processing flag after 5 minutes (300000ms)
        setTimeout(() => {
          localStorage.removeItem(codeKey);
          localStorage.removeItem(`${codeKey}_start_time`);
        }, 300000);
        
        // Use the dedicated token exchange endpoint
        
        // Make API call to exchange authorization code for tokens
        const data = await apiClient.post(`/auth/google/exchange`, { code });
        
        
        if (!data || !data.access_token) {
          throw new Error('No access token returned from server');
        }
        
        // Store access token in localStorage and unified API client
        localStorage.setItem('token', data.access_token);
        
        // Note: refresh_token is handled as an HttpOnly cookie by the backend
        // and should not be stored in localStorage for security reasons
        // We're removing any existing refresh_token from localStorage if it exists
        localStorage.removeItem('refresh_token');
        
        // Set token in unified API client
        apiClient.setAuthToken(data.access_token);
        
        // Verify that we can make authenticated requests
        try {
          // Verify authentication by fetching current user
          await apiClient.get('/auth/me');
        } catch (verifyError) {
          console.error('Failed to verify authentication:', verifyError);
          // Continue anyway, as the main auth flow should still work
        }
        
        // Update auth context with user data
        await handleOAuthCallback(data.user);
        
        // Clear processing flags
        localStorage.removeItem(codeKey);
        localStorage.removeItem(`${codeKey}_start_time`);
        localStorage.removeItem('oauth_in_progress');
        
        // Navigate to dashboard
        navigate('/dashboard');
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError(err.message || 'Authentication failed');
        
        // Clear any OAuth processing flags on error
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        if (code) {
          const codeKey = `oauth_code_${code.substring(0, 10)}`;
          localStorage.removeItem(codeKey);
          localStorage.removeItem(`${codeKey}_start_time`);
        }
        localStorage.removeItem('oauth_in_progress');
        localStorage.removeItem('oauth_flow_started');
      } finally {
        setLoading(false);
      }
    };

    processOAuthCallback();
  }, [handleOAuthCallback, location, navigate, provider]);

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
        <p className="text-brand-text mt-4">Redirecting to dashboard...</p>
      </div>
    </div>
  );
};

export default OAuthCallback;

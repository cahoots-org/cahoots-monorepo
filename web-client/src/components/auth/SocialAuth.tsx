declare const google: {
  accounts: {
    oauth2: {
      initTokenClient(config: {
        client_id: string;
        scope: string;
        callback: (response: { access_token: string }) => void;
      }): {
        requestAccessToken(): void;
      };
    };
  };
};

import { Button, Stack } from '@mantine/core';
import { IconBrandGithub, IconBrandGoogle } from '../../components/common/icons';
import { useAuthStore } from '../../stores/auth';
import { config } from '../../config/config';
import { notifications } from '@mantine/notifications';
import { useNavigate } from 'react-router-dom';

export function SocialAuth() {
  const { socialLogin } = useAuthStore();
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    try {
      console.log('[OAUTH_FLOW] Starting Google OAuth flow');
      
      const googleProvider = google.accounts.oauth2.initTokenClient({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        scope: 'email profile',
        callback: async (response) => {
          console.log('[OAUTH_FLOW] Received token from Google');
          
          if (!response?.access_token) {
            console.error('[OAUTH_FLOW] No access token received from Google');
            notifications.show({
              title: 'Authentication Error',
              message: 'Failed to receive access token from Google',
              color: 'red'
            });
            return;
          }
          
          try {
            // Get user info directly from Google
            const userResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
              headers: {
                'Authorization': `Bearer ${response.access_token}`
              }
            });
            
            if (!userResponse.ok) {
              throw new Error('Failed to get user info from Google');
            }
            
            const userData = await userResponse.json();
            console.log('[OAUTH_FLOW] Got user data:', {
              email: userData.email,
              name: userData.name
            });
            
            // Show loading state
            notifications.show({
              title: 'Authenticating',
              message: 'Please wait while we complete your login...',
              loading: true,
              autoClose: false,
              withCloseButton: false
            });
            
            try {
              console.log('[OAUTH_FLOW] Calling socialLogin...');
              // Format data according to SocialLoginRequest schema
              const socialLoginData = {
                provider: 'google',
                user_data: {
                  id: userData.id,
                  email: userData.email,
                  name: `${userData.given_name || ''} ${userData.family_name || ''}`.trim() || userData.name,
                  picture: userData.picture
                },
                access_token: response.access_token
              };
              
              console.log('[OAUTH_FLOW] Formatted social login data:', socialLoginData);
              
              // Add timeout to prevent infinite hang
              const loginPromise = socialLogin('google', socialLoginData);
              const timeoutPromise = new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Login request timed out after 10s')), 10000)
              );
              
              await Promise.race([loginPromise, timeoutPromise]);
              console.log('[OAUTH_FLOW] socialLogin completed successfully');
              
              // Clear loading notification
              notifications.clean();
              
              notifications.show({
                title: 'Success',
                message: 'Successfully logged in with Google',
                color: 'green'
              });

              // Verify auth state before navigation
              const authState = useAuthStore.getState();
              console.log('[OAUTH_FLOW] Auth state after login:', {
                isAuthenticated: authState.isAuthenticated,
                hasUser: !!authState.user
              });
              
              if (authState.isAuthenticated && authState.user) {
                navigate('/dashboard');
              } else {
                throw new Error('Authentication state not updated properly');
              }
            } catch (error: any) {
              console.error('[OAUTH_FLOW] socialLogin error:', {
                message: error.message,
                stack: error.stack,
                name: error.name
              });
              notifications.clean();
              notifications.show({
                title: 'Login Failed',
                message: error.message || 'An unexpected error occurred during login',
                color: 'red',
                autoClose: false
              });
            }
          } catch (error: any) {
            console.error('Social login error:', error);
            notifications.show({
              title: 'Login Failed',
              message: error.message || 'An unexpected error occurred during login',
              color: 'red',
              autoClose: false
            });
          }
        },
      });
      
      console.log('Requesting Google access token...');
      googleProvider.requestAccessToken();
    } catch (error: any) {
      console.error('Google OAuth initialization error:', error);
      notifications.show({
        title: 'Authentication Error',
        message: 'Failed to initialize Google login',
        color: 'red',
        autoClose: false
      });
    }
  };

  const handleGithubLogin = () => {
    const githubUrl = `https://github.com/login/oauth/authorize?client_id=${
      import.meta.env.VITE_GITHUB_CLIENT_ID
    }&scope=user:email&redirect_uri=${encodeURIComponent(import.meta.env.VITE_GITHUB_CALLBACK_URL)}`;
    window.location.href = githubUrl;
  };

  const buttonStyles = {
    root: {
      backgroundColor: config.ui.theme.surfaceColor,
      borderColor: config.ui.theme.borderColor,
      color: config.ui.theme.textColor,
      '&:hover': {
        backgroundColor: config.ui.theme.backgroundColor,
        transform: 'translateY(-1px)',
        boxShadow: config.ui.theme.shadows.button,
      },
    },
  };

  return (
    <Stack gap="sm">
      <Button
        leftSection={<IconBrandGoogle size={20} stroke={1.5} />}
        variant="outline"
        fullWidth
        onClick={handleGoogleLogin}
        styles={buttonStyles}
      >
        Continue with Google
      </Button>
      <Button
        leftSection={<IconBrandGithub size={20} stroke={1.5} />}
        variant="outline"
        fullWidth
        onClick={handleGithubLogin}
        styles={buttonStyles}
      >
        Continue with GitHub
      </Button>
    </Stack>
  );
} 
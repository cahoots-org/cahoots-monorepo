import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LoadingOverlay, Container, Text } from '@mantine/core';
import { useAuthStore } from '../../stores/auth';
import { notifications } from '@mantine/notifications';

export default function GitHubCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { socialLogin } = useAuthStore();

  useEffect(() => {
    const handleCallback = async () => {
      const searchParams = new URLSearchParams(location.search);
      const code = searchParams.get('code');
      const error = searchParams.get('error');
      
      if (error) {
        notifications.show({
          title: 'Authentication Error',
          message: searchParams.get('error_description') || 'Failed to authenticate with GitHub',
          color: 'red',
        });
        navigate('/login');
        return;
      }
      
      if (code) {
        try {
          await socialLogin('github', code);
          navigate('/dashboard');
        } catch (error: any) {
          console.error('GitHub auth error:', error);
          notifications.show({
            title: 'Authentication Error',
            message: error.message || 'Failed to authenticate with GitHub',
            color: 'red',
          });
          navigate('/login');
        }
      } else {
        navigate('/login');
      }
    };

    handleCallback();
  }, [location, socialLogin, navigate]);

  return (
    <Container style={{ height: '100vh', position: 'relative' }}>
      <LoadingOverlay visible={true} zIndex={1000} overlayProps={{ radius: "sm", blur: 2 }} />
      <Text ta="center" mt="xl">
        Authenticating with GitHub...
      </Text>
    </Container>
  );
} 
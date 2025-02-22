import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput, Button, Title, Text, Stack, Container, Card, Divider, Box } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useAuthStore } from '../../stores/auth';
import { SocialAuth } from '../../components/auth/SocialAuth';
import { Logo } from '../../components/common/Logo';
import { config } from '../../config/config';

interface LoginForm {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const form = useForm<LoginForm>({
    initialValues: {
      email: '',
      password: '',
    },
    validate: {
      email: (value) => (/^\S+@\S+$/.test(value) ? null : 'Invalid email'),
      password: (value) => (value.length >= 6 ? null : 'Password must be at least 6 characters'),
    },
  });

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (error) {
      notifications.show({
        title: 'Error',
        message: error,
        color: 'red',
      });
      clearError();
    }
  }, [error, clearError]);

  const handleSubmit = async (values: LoginForm) => {
    await login(values);
  };

  return (
    <Box
      style={{
        minHeight: '100vh',
        background: config.ui.theme.gradients.surface,
        paddingTop: '6rem',
        position: 'relative',
      }}
    >
      <Link 
        to="/" 
        style={{ 
          position: 'absolute',
          top: '2rem',
          left: '2rem',
          textDecoration: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}
      >
        <Logo size={24} />
        <Text 
          size="lg" 
          fw={500} 
          style={{ 
            color: config.ui.theme.textColor,
            marginLeft: '0.25rem'
          }}
        >
          CAHOOTS
        </Text>
      </Link>

      <Container size="xs">
        <Card
          shadow="md"
          padding="xl"
          style={{
            background: config.ui.theme.surfaceColor,
            border: `1px solid ${config.ui.theme.borderColor}`,
          }}
        >
          <Stack gap="md">
            <Text size="xl" fw={700} ta="center" c={config.ui.theme.textColor}>
              Sign in to continue
            </Text>

            <form onSubmit={form.onSubmit(handleSubmit)}>
              <Stack gap="md">
                <TextInput
                  label="Email"
                  placeholder="your@email.com"
                  required
                  {...form.getInputProps('email')}
                />

                <PasswordInput
                  label="Password"
                  placeholder="Your password"
                  required
                  {...form.getInputProps('password')}
                />

                <Button type="submit" fullWidth loading={isLoading}>
                  Sign in
                </Button>
              </Stack>
            </form>

            <Divider label="Or continue with" labelPosition="center" />
            
            <SocialAuth />

            <Text c="dimmed" size="sm" ta="center">
              Don't have an account?{' '}
              <Link 
                to="/register" 
                style={{ 
                  color: config.ui.theme.primaryColor,
                  fontWeight: 500,
                  textDecoration: 'none',
                }}
              >
                Sign up
              </Link>
            </Text>
          </Stack>
        </Card>
      </Container>
    </Box>
  );
} 
import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput, Button, Title, Text, Stack, Container, Card, Divider, Box } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useAuthStore } from '../../stores/auth';
import { SocialAuth } from '../../components/auth/SocialAuth';
import { Logo } from '../../components/common/Logo';
import { config } from '../../config/config';

interface RegisterForm {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const form = useForm<RegisterForm>({
    initialValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
    validate: {
      name: (value) => (value.length >= 2 ? null : 'Name must be at least 2 characters'),
      email: (value) => (/^\S+@\S+$/.test(value) ? null : 'Invalid email'),
      password: (value) => (value.length >= 6 ? null : 'Password must be at least 6 characters'),
      confirmPassword: (value, values) =>
        value === values.password ? null : 'Passwords do not match',
    },
  });

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
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

  const handleSubmit = async (values: RegisterForm) => {
    const { confirmPassword, ...registerData } = values;
    await register(registerData);
    notifications.show({
      title: 'Success',
      message: 'Registration successful! Please check your email to verify your account.',
      color: 'green',
    });
    navigate('/login');
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
              Create your account
            </Text>

            <form onSubmit={form.onSubmit(handleSubmit)}>
              <Stack gap="md">
                <TextInput
                  label="Name"
                  placeholder="Your name"
                  required
                  {...form.getInputProps('name')}
                />

                <TextInput
                  label="Email"
                  placeholder="your@email.com"
                  required
                  {...form.getInputProps('email')}
                />

                <PasswordInput
                  label="Password"
                  placeholder="Create a password"
                  required
                  {...form.getInputProps('password')}
                />

                <PasswordInput
                  label="Confirm Password"
                  placeholder="Confirm your password"
                  required
                  {...form.getInputProps('confirmPassword')}
                />

                <Button type="submit" fullWidth loading={isLoading}>
                  Create Account
                </Button>
              </Stack>
            </form>

            <Divider label="Or continue with" labelPosition="center" />
            
            <SocialAuth />

            <Text c="dimmed" size="sm" ta="center">
              Already have an account?{' '}
              <Link 
                to="/login" 
                style={{ 
                  color: config.ui.theme.primaryColor,
                  fontWeight: 500,
                  textDecoration: 'none',
                }}
              >
                Sign in
              </Link>
            </Text>
          </Stack>
        </Card>
      </Container>
    </Box>
  );
} 
import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput, Button, Title, Text, Stack, Container, Card } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useAuthStore } from '../../stores/auth';

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

  const handleSubmit = async (values: LoginForm) => {
    await login(values);
  };

  return (
    <Container size="xs" py="xl">
      <Card withBorder>
        <Stack gap="md">
          <Title order={2} ta="center">Welcome Back</Title>
          <Text c="dimmed" size="sm" ta="center">
            Enter your credentials to access your account
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

          <Text size="sm" ta="center">
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'inherit', fontWeight: 500 }}>
              Register
            </Link>
          </Text>
        </Stack>
      </Card>
    </Container>
  );
} 
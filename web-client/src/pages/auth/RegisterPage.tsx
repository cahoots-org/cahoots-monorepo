import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput, Button, Title, Text, Stack, Container, Card } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useAuthStore } from '../../stores/auth';

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
    <Container size="xs" py="xl">
      <Card withBorder>
        <Stack gap="md">
          <Title order={2} ta="center">Create Account</Title>
          <Text c="dimmed" size="sm" ta="center">
            Fill in your details to create a new account
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

          <Text size="sm" ta="center">
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'inherit', fontWeight: 500 }}>
              Sign in
            </Link>
          </Text>
        </Stack>
      </Card>
    </Container>
  );
} 
import { Container, Title, Text, Button, Stack, Group, Card, SimpleGrid, Box } from '@mantine/core';
import { Link } from 'react-router-dom';
import { IconPlus, IconFolder } from '../../components/common/icons';
import { config } from '../../config/config';
import { useAuthStore } from '../../stores/auth';

export function DashboardPage() {
  const { user } = useAuthStore();

  return (
    <Box style={{ background: config.ui.theme.backgroundColor, minHeight: '100vh' }}>
      <Container size="lg" py="xl">
        <Stack gap="xl">
          <Group justify="space-between" align="center">
            <Stack gap={0}>
              <Text size="lg" c="dimmed">Welcome back,</Text>
              <Title order={1} c="white">{user?.name}</Title>
            </Stack>
            <Button
              component={Link}
              to="/projects/new"
              leftSection={<IconPlus size={20} />}
              style={{
                backgroundImage: config.ui.theme.gradients.primary,
              }}
            >
              New Project
            </Button>
          </Group>

          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
            <Card
              component={Link}
              to="/projects"
              padding="xl"
              radius="md"
              style={{
                backgroundColor: config.ui.theme.surfaceColor,
                borderColor: config.ui.theme.borderColor,
                textDecoration: 'none',
              }}
            >
              <Group>
                <IconFolder size={30} stroke={1.5} color={config.ui.theme.primaryColor} />
                <Stack gap={0}>
                  <Text size="lg" fw={500} c="white">Your Projects</Text>
                  <Text size="sm" c="dimmed">View and manage your projects</Text>
                </Stack>
              </Group>
            </Card>

            {/* Add more dashboard cards here as needed */}
          </SimpleGrid>

          {/* Recent Activity or other dashboard sections can be added here */}
        </Stack>
      </Container>
    </Box>
  );
} 
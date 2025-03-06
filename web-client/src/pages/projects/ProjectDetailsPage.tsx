import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Title,
  Text,
  Stack,
  Card,
  Group,
  Badge,
  Button,
  Grid,
  Skeleton,
  Alert,
} from '@mantine/core';
import { IconAlertCircle, IconExternalLink } from '../../components/common/icons';
import { useProjectStore } from '../../stores/projects';

const statusColors = {
  initializing: 'blue',
  active: 'green',
  completed: 'teal',
  failed: 'red',
} as const;

export function ProjectDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const {
    currentProject,
    isLoading,
    error,
    fetchProjectDetails,
  } = useProjectStore();

  useEffect(() => {
    if (id) {
      fetchProjectDetails(id);
    }
  }, [id, fetchProjectDetails]);

  if (error) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle />} title="Error" color="red">
          {error}
        </Alert>
      </Container>
    );
  }

  if (isLoading || !currentProject) {
    return (
      <Container size="md" py="xl">
        <Stack gap="md">
          <Skeleton height={50} radius="md" />
          <Skeleton height={20} radius="md" width="60%" />
          <Grid>
            <Grid.Col span={6}>
              <Skeleton height={200} radius="md" />
            </Grid.Col>
            <Grid.Col span={6}>
              <Skeleton height={200} radius="md" />
            </Grid.Col>
          </Grid>
        </Stack>
      </Container>
    );
  }

  return (
    <Container size="md" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>{currentProject.name}</Title>
            <Text c="dimmed" size="sm">
              Created on {new Date(currentProject.created_at).toLocaleDateString()}
            </Text>
          </div>
          <Badge size="lg" color={statusColors[currentProject.status]}>
            {currentProject.status.charAt(0).toUpperCase() + currentProject.status.slice(1)}
          </Badge>
        </Group>

        <Text>{currentProject.description}</Text>

        <Grid>
          <Grid.Col span={6}>
            <Card withBorder>
              <Stack gap="md">
                <Title order={3}>Task Board</Title>
                {currentProject.task_board_url ? (
                  <Button
                    component="a"
                    href={currentProject.task_board_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    rightSection={<IconExternalLink size={16} />}
                  >
                    Open Task Board
                  </Button>
                ) : (
                  <Text c="dimmed">Task board is being set up...</Text>
                )}
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={6}>
            <Card withBorder>
              <Stack gap="md">
                <Title order={3}>Repository</Title>
                {currentProject.repository_url ? (
                  <Button
                    component="a"
                    href={currentProject.repository_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    rightSection={<IconExternalLink size={16} />}
                  >
                    Open Repository
                  </Button>
                ) : (
                  <Text c="dimmed">Repository is being set up...</Text>
                )}
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        <Card withBorder>
          <Stack gap="md">
            <Title order={3}>Project Status</Title>
            <Text>
              {currentProject.status === 'initializing'
                ? 'Setting up your project resources...'
                : currentProject.status === 'active'
                ? 'Your project is ready! You can start working on tasks.'
                : currentProject.status === 'completed'
                ? 'Project setup completed successfully.'
                : 'Project setup failed. Please contact support.'}
            </Text>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
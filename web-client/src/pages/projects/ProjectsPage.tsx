import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Stack,
  Text,
  Title,
  Badge,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useProjectStore } from '../../stores/projects';
import { CreateProjectModal } from './CreateProjectModal';
import { useDisclosure } from '@mantine/hooks';

export function ProjectsPage() {
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const { projects, isLoading, error, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'green';
      case 'completed':
        return 'blue';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  if (isLoading) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Loader size="lg" />
      </Stack>
    );
  }

  if (error) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Text c="red">{error}</Text>
        <Button onClick={() => fetchProjects()}>Retry</Button>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Projects</Title>
        <Button leftSection={<IconPlus size="1.2rem" />} onClick={openModal}>
          New Project
        </Button>
      </Group>

      <Grid>
        {projects.map((project) => (
          <Grid.Col key={project.id} span={{ base: 12, sm: 6, lg: 4 }}>
            <Card component={Link} to={`/projects/${project.id}`} withBorder>
              <Stack gap="md">
                <Group justify="space-between">
                  <Title order={3}>{project.name}</Title>
                  <Badge color={getStatusColor(project.status)}>
                    {project.status}
                  </Badge>
                </Group>
                <Text lineClamp={2}>{project.description}</Text>
                <Group gap="xs">
                  {project.task_board_url && (
                    <Button
                      component="a"
                      href={project.task_board_url}
                      target="_blank"
                      variant="light"
                      size="xs"
                    >
                      Task Board
                    </Button>
                  )}
                  {project.repository_url && (
                    <Button
                      component="a"
                      href={project.repository_url}
                      target="_blank"
                      variant="light"
                      size="xs"
                    >
                      Repository
                    </Button>
                  )}
                </Group>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>

      <CreateProjectModal opened={modalOpened} onClose={closeModal} />
    </Stack>
  );
} 
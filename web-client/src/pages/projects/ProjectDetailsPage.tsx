import { useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import {
  Title,
  Stack,
  Group,
  Button,
  Text,
  Card,
  Grid,
  Badge,
  Loader,
  Tabs,
} from '@mantine/core';
import { IconExternalLink } from '@tabler/icons-react';
import { useProjectStore } from '../../stores/projects';
import { useTaskStore, Task } from '../../stores/tasks';
import { TaskList } from '../../components/tasks/TaskList';
import { CreateTaskModal } from '../../components/tasks/CreateTaskModal';
import { useDisclosure } from '@mantine/hooks';

export function ProjectDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const {
    currentProject,
    isLoading: projectLoading,
    error: projectError,
    fetchProjectDetails,
  } = useProjectStore();
  const {
    tasks,
    isLoading: tasksLoading,
    error: tasksError,
    fetchTasks,
  } = useTaskStore();

  useEffect(() => {
    if (id) {
      fetchProjectDetails(id);
      fetchTasks(id);
    }
  }, [id, fetchProjectDetails, fetchTasks]);

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

  const filteredTasks = useMemo(() => {
    return {
      all: tasks,
      open: tasks.filter((task) => task.status === 'open'),
      in_progress: tasks.filter((task) => task.status === 'in_progress'),
      review: tasks.filter((task) => task.status === 'review'),
      testing: tasks.filter((task) => task.status === 'testing'),
      done: tasks.filter((task) => task.status === 'done'),
    };
  }, [tasks]);

  if (projectLoading) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Loader size="lg" />
      </Stack>
    );
  }

  if (projectError || !currentProject) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Text c="red">{projectError || 'Project not found'}</Text>
        <Button onClick={() => id && fetchProjectDetails(id)}>Retry</Button>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Card withBorder>
        <Stack gap="md">
          <Group justify="space-between">
            <Stack gap="xs">
              <Title order={2}>{currentProject.name}</Title>
              <Badge color={getStatusColor(currentProject.status)} size="lg">
                {currentProject.status}
              </Badge>
            </Stack>
            <Group>
              {currentProject.task_board_url && (
                <Button
                  component="a"
                  href={currentProject.task_board_url}
                  target="_blank"
                  variant="light"
                  rightSection={<IconExternalLink size="1.2rem" />}
                >
                  Task Board
                </Button>
              )}
              {currentProject.repository_url && (
                <Button
                  component="a"
                  href={currentProject.repository_url}
                  target="_blank"
                  variant="light"
                  rightSection={<IconExternalLink size="1.2rem" />}
                >
                  Repository
                </Button>
              )}
            </Group>
          </Group>
          <Text>{currentProject.description}</Text>
        </Stack>
      </Card>

      <Card withBorder>
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Tasks</Title>
            <Button onClick={openModal}>Add Task</Button>
          </Group>

          <Tabs defaultValue="all">
            <Tabs.List>
              <Tabs.Tab value="all">All</Tabs.Tab>
              <Tabs.Tab value="open">Open</Tabs.Tab>
              <Tabs.Tab value="in_progress">In Progress</Tabs.Tab>
              <Tabs.Tab value="review">Review</Tabs.Tab>
              <Tabs.Tab value="testing">Testing</Tabs.Tab>
              <Tabs.Tab value="done">Done</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="all" pt="md">
              <TaskList
                tasks={filteredTasks.all}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>

            <Tabs.Panel value="open" pt="md">
              <TaskList
                tasks={filteredTasks.open}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>

            <Tabs.Panel value="in_progress" pt="md">
              <TaskList
                tasks={filteredTasks.in_progress}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>

            <Tabs.Panel value="review" pt="md">
              <TaskList
                tasks={filteredTasks.review}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>

            <Tabs.Panel value="testing" pt="md">
              <TaskList
                tasks={filteredTasks.testing}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>

            <Tabs.Panel value="done" pt="md">
              <TaskList
                tasks={filteredTasks.done}
                isLoading={tasksLoading}
                error={tasksError}
                onRetry={() => id && fetchTasks(id)}
              />
            </Tabs.Panel>
          </Tabs>
        </Stack>
      </Card>

      {id && <CreateTaskModal projectId={id} opened={modalOpened} onClose={closeModal} />}
    </Stack>
  );
} 
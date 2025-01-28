import { Stack, Text, Button, Loader } from '@mantine/core';
import { Task } from '../../stores/tasks';
import { TaskCard } from './TaskCard';

interface TaskListProps {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function TaskList({ tasks, isLoading, error, onRetry }: TaskListProps) {
  if (isLoading) {
    return (
      <Stack align="center" justify="center" h={200}>
        <Loader size="lg" />
      </Stack>
    );
  }

  if (error) {
    return (
      <Stack align="center" justify="center" h={200}>
        <Text c="red">{error}</Text>
        <Button onClick={onRetry}>Retry</Button>
      </Stack>
    );
  }

  if (tasks.length === 0) {
    return (
      <Stack align="center" justify="center" h={200}>
        <Text c="dimmed">No tasks found</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md" mt="md">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} />
      ))}
    </Stack>
  );
} 
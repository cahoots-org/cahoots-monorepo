import { Card, Group, Stack, Text, Badge, Menu, ActionIcon } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { Task, useTaskStore } from '../../stores/tasks';

interface TaskCardProps {
  task: Task;
}

export function TaskCard({ task }: TaskCardProps) {
  const { updateTask } = useTaskStore();

  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'open':
        return 'blue';
      case 'in_progress':
        return 'yellow';
      case 'review':
        return 'purple';
      case 'testing':
        return 'cyan';
      case 'done':
        return 'green';
      default:
        return 'gray';
    }
  };

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'critical':
        return 'red';
      case 'high':
        return 'orange';
      case 'medium':
        return 'yellow';
      case 'low':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const handleStatusChange = async (newStatus: Task['status']) => {
    await updateTask(task.project_id, task.id, { status: newStatus });
  };

  return (
    <Card withBorder>
      <Group justify="space-between" align="flex-start">
        <Stack gap="xs">
          <Text fw={500}>{task.title}</Text>
          <Text size="sm" c="dimmed" lineClamp={2}>
            {task.description}
          </Text>
          <Group gap="xs">
            <Badge color={getStatusColor(task.status)}>{task.status.replace('_', ' ')}</Badge>
            <Badge color={getPriorityColor(task.priority)}>{task.priority}</Badge>
            {task.assignee && (
              <Badge variant="outline">Assigned to: {task.assignee}</Badge>
            )}
          </Group>
        </Stack>

        <Menu position="bottom-end" withArrow>
          <Menu.Target>
            <ActionIcon variant="subtle">
              <IconDotsVertical size="1.2rem" />
            </ActionIcon>
          </Menu.Target>

          <Menu.Dropdown>
            <Menu.Label>Change Status</Menu.Label>
            <Menu.Item onClick={() => handleStatusChange('open')}>
              Set to Open
            </Menu.Item>
            <Menu.Item onClick={() => handleStatusChange('in_progress')}>
              Set to In Progress
            </Menu.Item>
            <Menu.Item onClick={() => handleStatusChange('review')}>
              Set to Review
            </Menu.Item>
            <Menu.Item onClick={() => handleStatusChange('testing')}>
              Set to Testing
            </Menu.Item>
            <Menu.Item onClick={() => handleStatusChange('done')}>
              Set to Done
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </Card>
  );
} 
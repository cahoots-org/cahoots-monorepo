import {
  Modal,
  TextInput,
  Textarea,
  Button,
  Stack,
  Select,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useTaskStore, Task } from '../../stores/tasks';

interface CreateTaskForm {
  title: string;
  description: string;
  priority: Task['priority'];
  assignee?: string;
}

interface CreateTaskModalProps {
  projectId: string;
  opened: boolean;
  onClose: () => void;
}

export function CreateTaskModal({ projectId, opened, onClose }: CreateTaskModalProps) {
  const { createTask, isLoading } = useTaskStore();

  const form = useForm<CreateTaskForm>({
    initialValues: {
      title: '',
      description: '',
      priority: 'medium',
      assignee: '',
    },
    validate: {
      title: (value) => (value.length >= 3 ? null : 'Title must be at least 3 characters'),
      description: (value) =>
        value.length >= 10 ? null : 'Description must be at least 10 characters',
      priority: (value) =>
        ['low', 'medium', 'high', 'critical'].includes(value)
          ? null
          : 'Invalid priority',
    },
  });

  const handleSubmit = async (values: CreateTaskForm) => {
    try {
      await createTask(projectId, {
        ...values,
        status: 'open',
      });
      notifications.show({
        title: 'Success',
        message: 'Task created successfully',
        color: 'green',
      });
      form.reset();
      onClose();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to create task',
        color: 'red',
      });
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Create New Task"
      size="md"
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Task Title"
            placeholder="Enter task title"
            required
            {...form.getInputProps('title')}
          />

          <Textarea
            label="Description"
            placeholder="Enter task description"
            required
            minRows={3}
            {...form.getInputProps('description')}
          />

          <Select
            label="Priority"
            placeholder="Select priority"
            required
            data={[
              { value: 'low', label: 'Low' },
              { value: 'medium', label: 'Medium' },
              { value: 'high', label: 'High' },
              { value: 'critical', label: 'Critical' },
            ]}
            {...form.getInputProps('priority')}
          />

          <TextInput
            label="Assignee"
            placeholder="Enter assignee name"
            {...form.getInputProps('assignee')}
          />

          <Button type="submit" fullWidth loading={isLoading}>
            Create Task
          </Button>
        </Stack>
      </form>
    </Modal>
  );
} 
import { Modal, TextInput, Textarea, Button, Stack } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useProjectStore } from '../../stores/projects';

interface CreateProjectForm {
  name: string;
  description: string;
}

interface CreateProjectModalProps {
  opened: boolean;
  onClose: () => void;
}

export function CreateProjectModal({ opened, onClose }: CreateProjectModalProps) {
  const { createProject, isLoading } = useProjectStore();

  const form = useForm<CreateProjectForm>({
    initialValues: {
      name: '',
      description: '',
    },
    validate: {
      name: (value) => (value.length >= 3 ? null : 'Name must be at least 3 characters'),
      description: (value) => (value.length >= 10 ? null : 'Description must be at least 10 characters'),
    },
  });

  const handleSubmit = async (values: CreateProjectForm) => {
    try {
      await createProject(values);
      notifications.show({
        title: 'Success',
        message: 'Project created successfully',
        color: 'green',
      });
      form.reset();
      onClose();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to create project',
        color: 'red',
      });
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Create New Project"
      size="md"
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Project Name"
            placeholder="Enter project name"
            required
            {...form.getInputProps('name')}
          />

          <Textarea
            label="Description"
            placeholder="Enter project description"
            required
            minRows={3}
            {...form.getInputProps('description')}
          />

          <Button type="submit" fullWidth loading={isLoading}>
            Create Project
          </Button>
        </Stack>
      </form>
    </Modal>
  );
} 
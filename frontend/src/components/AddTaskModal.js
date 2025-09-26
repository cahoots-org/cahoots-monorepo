import React, { useState } from 'react';
import {
  Modal,
  Button,
  Text,
  Input,
  TextArea,
  Select,
  Switch,
  Badge,
  tokens,
} from '../design-system';

const AddTaskModal = ({ 
  isOpen, 
  onClose, 
  targetTask, 
  onAddTask 
}) => {
  const [taskData, setTaskData] = useState({
    description: '',
    position: 'after',
    auto_decompose: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!taskData.description.trim()) {
      setError('Task description is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onAddTask({
        target_task_id: targetTask.task_id,
        description: taskData.description.trim(),
        position: taskData.position,
        auto_decompose: taskData.auto_decompose,
      });

      // Reset form and close modal
      setTaskData({
        description: '',
        position: 'after',
        auto_decompose: true,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to add task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setTaskData(prev => ({ ...prev, [field]: value }));
    if (error) setError(null); // Clear error when user starts typing
  };

  if (!targetTask) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Task to Tree"
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: tokens.spacing[6],
          padding: tokens.spacing[1],
        }}>
          {/* Target Task Context */}
          <div style={{
            padding: tokens.spacing[4],
            backgroundColor: 'var(--color-surface)',
            borderRadius: tokens.borderRadius.md,
            border: '1px solid var(--color-border)',
          }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              color: 'var(--color-text-muted)',
              margin: 0,
              marginBottom: tokens.spacing[2],
            }}>
              Adding relative to:
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              color: 'var(--color-text)',
              margin: 0,
              fontWeight: tokens.typography.fontWeight.medium,
            }}>
              {targetTask.description}
            </Text>
            <div style={{ marginTop: tokens.spacing[2] }}>
              <Badge variant="secondary" size="sm">
                ID: {targetTask.task_id}
              </Badge>
            </div>
          </div>

          {/* Task Description */}
          <div>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium,
              color: 'var(--color-text)',
              margin: 0,
              marginBottom: tokens.spacing[2],
            }}>
              Task Description *
            </Text>
            <TextArea
              value={taskData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Describe the new task to add..."
              rows={3}
              style={{
                width: '100%',
                fontSize: tokens.typography.fontSize.sm[0],
              }}
            />
          </div>

          {/* Position Selection */}
          <div>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium,
              color: 'var(--color-text)',
              margin: 0,
              marginBottom: tokens.spacing[2],
            }}>
              Position
            </Text>
            <Select
              value={taskData.position}
              onChange={(e) => handleInputChange('position', e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="before">Before this task (as sibling)</option>
              <option value="after">After this task (as sibling)</option>
              <option value="child">As child of this task</option>
            </Select>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: 'var(--color-text-muted)',
              margin: 0,
              marginTop: tokens.spacing[1],
            }}>
              {taskData.position === 'child' 
                ? 'The new task will be added as a subtask'
                : `The new task will be added as a sibling ${taskData.position} the selected task`
              }
            </Text>
          </div>

          {/* Auto-decompose Option */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: tokens.spacing[4],
            backgroundColor: 'var(--color-surface)',
            borderRadius: tokens.borderRadius.md,
            border: '1px solid var(--color-border)',
          }}>
            <div>
              <Text style={{
                fontSize: tokens.typography.fontSize.sm[0],
                fontWeight: tokens.typography.fontWeight.medium,
                color: 'var(--color-text)',
                margin: 0,
                marginBottom: tokens.spacing[1],
              }}>
                Auto-decompose complex tasks
              </Text>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: 'var(--color-text-muted)',
                margin: 0,
              }}>
                Automatically break down the task if it appears complex
              </Text>
            </div>
            <Switch
              checked={taskData.auto_decompose}
              onChange={(checked) => handleInputChange('auto_decompose', checked)}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div style={{
              padding: tokens.spacing[3],
              backgroundColor: tokens.colors.error[500] + '15',
              border: `1px solid ${tokens.colors.error[500]}30`,
              borderRadius: tokens.borderRadius.md,
            }}>
              <Text style={{
                fontSize: tokens.typography.fontSize.sm[0],
                color: tokens.colors.error[400],
                margin: 0,
              }}>
                {error}
              </Text>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: tokens.spacing[3],
            paddingTop: tokens.spacing[2],
            borderTop: '1px solid var(--color-border)',
          }}>
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={isSubmitting}
              disabled={!taskData.description.trim()}
            >
              {isSubmitting ? 'Adding Task...' : 'Add Task'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
};

export default AddTaskModal;
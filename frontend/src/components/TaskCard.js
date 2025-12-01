// Redesigned TaskCard - Professional replacement using design system
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Badge,
  Button,
  Text,
  Caption,
  getComplexityIcon,
  getStatusIcon,
  getStatusVariant,
  ClockIcon,
  EyeIcon,
  TrashIcon,
  tokens,
} from '../design-system';
import { useDeleteTask, useCompleteTask } from '../hooks/api/useTasks';
import { useApp } from '../contexts/AppContext';
import { formatTaskDate } from '../utils/dateUtils';

const TaskCard = ({ 
  task, 
  onDelete, 
  navigateOnClick = false,
  variant = 'default',
  showActions = true,
}) => {
  const navigate = useNavigate();
  const { showSuccess, showError } = useApp();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);

  // Mutations
  const deleteTaskMutation = useDeleteTask();
  const completeTaskMutation = useCompleteTask();

  // Get appropriate icons
  const ComplexityIcon = getComplexityIcon(task.complexity_score || 0);
  const StatusIcon = getStatusIcon(task.status);

  // Handle task click navigation
  const handleTaskClick = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (navigateOnClick) {
      // Use new ProjectView for better UX
      navigate(`/projects/${task.task_id}`);
    }
  };

  // Handle task completion
  const handleComplete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (task.status === 'completed') return;
    
    try {
      setIsCompleting(true);
      await completeTaskMutation.mutateAsync(task.task_id);
      showSuccess('Task completed successfully!');
      
      if (onDelete) {
        onDelete(task.task_id);
      }
    } catch (error) {
      showError(error.message || 'Failed to complete task');
    } finally {
      setIsCompleting(false);
    }
  };

  // Handle task deletion
  const handleDelete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!window.confirm(`Are you sure you want to delete "${task.description.substring(0, 50)}..."? This will also delete all subtasks.`)) {
      return;
    }
    
    try {
      setIsDeleting(true);
      await deleteTaskMutation.mutateAsync(task.task_id);
      showSuccess('Task deleted successfully');
      
      if (onDelete) {
        onDelete(task.task_id);
      }
    } catch (error) {
      showError(error.message || 'Failed to delete task');
    } finally {
      setIsDeleting(false);
    }
  };


  // Complexity color coding
  const getComplexityColor = (complexity) => {
    if (complexity >= 8) return tokens.colors.error[400];
    if (complexity >= 5) return tokens.colors.warning[400];
    return tokens.colors.success[400];
  };

  return (
    <Card
      variant={variant}
      hover={navigateOnClick}
      padding="md"
      style={{
        cursor: navigateOnClick ? 'pointer' : 'default',
        position: 'relative',
        transition: `all ${tokens.transitionDuration.normal} ${tokens.transitionTimingFunction.ease}`,
      }}
      onClick={handleTaskClick}
    >
      {/* Header with status and complexity */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        justifyContent: 'space-between',
        marginBottom: tokens.spacing[3],
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
          <ComplexityIcon 
            size={20} 
            style={{ color: getComplexityColor(task.complexity_score || 0) }}
          />
          <Text 
            style={{ 
              fontWeight: tokens.typography.fontWeight.semibold,
              fontSize: tokens.typography.fontSize.base[0],
              lineHeight: '1.4',
              margin: 0,
            }}
          >
            {task.description.split('\n')[0].substring(0, 60)}
            {task.description.split('\n')[0].length > 60 && '...'}
          </Text>
        </div>
        
        <Badge 
          variant={getStatusVariant(task.status)}
          size="sm"
          icon={StatusIcon}
        >
          {task.status?.replace('_', ' ') || 'pending'}
        </Badge>
      </div>

      {/* Description */}
      <Text 
        style={{ 
          color: tokens.colors.dark.muted,
          fontSize: tokens.typography.fontSize.sm[0],
          lineHeight: '1.5',
          margin: `0 0 ${tokens.spacing[4]} 0`,
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {task.description}
      </Text>

      {/* Rejection reason for rejected tasks */}
      {task.status === 'rejected' && task.rejection_reason && (
        <div style={{
          padding: tokens.spacing[3],
          backgroundColor: `${tokens.colors.error[500]}10`,
          border: `1px solid ${tokens.colors.error[500]}30`,
          borderRadius: tokens.borderRadius.md,
          marginBottom: tokens.spacing[4],
        }}>
          <Text style={{
            fontSize: tokens.typography.fontSize.sm[0],
            color: tokens.colors.error[400],
            margin: 0,
            fontWeight: tokens.typography.fontWeight.medium,
          }}>
            Rejection Reason:
          </Text>
          <Text style={{
            fontSize: tokens.typography.fontSize.sm[0],
            color: tokens.colors.error[300],
            margin: `${tokens.spacing[1]} 0 0 0`,
            lineHeight: '1.4',
          }}>
            {task.rejection_reason}
          </Text>
        </div>
      )}

      {/* Metadata */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: tokens.spacing[4],
        flexWrap: 'wrap',
        gap: tokens.spacing[2],
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[4] }}>
          {/* Creation date */}
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[1] }}>
            <ClockIcon size={14} style={{ color: tokens.colors.dark.muted }} />
            <Caption>{formatTaskDate(task.created_at)}</Caption>
          </div>
        </div>

        {/* Subtask count */}
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[1] }}>
          <Caption>{task.total_subtasks || task.children_count || 0} subtasks</Caption>
        </div>
      </div>

      {/* Actions */}
      {showActions && (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          paddingTop: tokens.spacing[4],
          borderTop: `1px solid ${tokens.colors.dark.border}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
            <Button
              variant="ghost"
              size="sm"
              icon={EyeIcon}
              onClick={handleTaskClick}
            >
              View
            </Button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
            {task.status !== 'completed' && task.status !== 'rejected' && (
              <Button
                variant="success"
                size="sm"
                loading={isCompleting}
                onClick={handleComplete}
                disabled={isDeleting}
              >
                Complete
              </Button>
            )}
            
            <Button
              variant="danger"
              size="sm"
              icon={TrashIcon}
              loading={isDeleting}
              onClick={handleDelete}
              disabled={isCompleting}
            >
              Delete
            </Button>
          </div>
        </div>
      )}

      {/* Loading overlay */}
      {(isDeleting || isCompleting) && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: tokens.borderRadius.lg,
          zIndex: 1,
        }}>
          <Text style={{ color: tokens.colors.neutral[0] }}>
            {isDeleting ? 'Deleting...' : 'Completing...'}
          </Text>
        </div>
      )}
    </Card>
  );
};

export default TaskCard;
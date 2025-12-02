import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  Text,
  Heading1,
  Badge,
  LoadingSpinner,
  ErrorMessage,
  Modal,
  BackIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  RefreshIcon,
  tokens,
} from '../design-system';

import { useAuth } from '../contexts/AuthContext';
import { useApp } from '../contexts/AppContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import ExportModal from '../components/ExportModal';
import DecompositionStatus from '../components/DecompositionStatus';
import { formatDetailedDate } from '../utils/dateUtils';
import apiClient from '../services/unifiedApiClient';

// Import tab components
import { OverviewTab, SubtasksTab, StoriesTab, EventModelTab } from '../components/TaskBoard';
import SchemasTab from '../components/TaskBoard/SchemasTab';

const TaskBoard = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { showError, showSuccess } = useApp();
  const { connected, connect, disconnect, subscribe } = useWebSocket();
  const queryClient = useQueryClient();

  // State
  const [activeTab, setActiveTab] = useState('overview');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedSubtask, setSelectedSubtask] = useState(null);
  const [editMode, setEditMode] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Connect WebSocket when component mounts
  useEffect(() => {
    // Only connect if authenticated
    if (!isAuthenticated()) {
      return;
    }

    console.log('[TaskBoard] Connecting WebSocket...');
    connect().catch(err => {
      console.error('[TaskBoard] Failed to connect WebSocket:', err);
    });

    // Cleanup: disconnect when component unmounts
    return () => {
      console.log('[TaskBoard] Disconnecting WebSocket...');
      disconnect();
    };
  }, []); // Empty dependency array - only run on mount/unmount

  // WebSocket subscription for real-time updates
  useEffect(() => {
    if (!connected || !taskId) return;

    const unsubscribe = subscribe((data) => {
      // Check if this event is related to the current task or its children
      if (data.type?.includes('task') || data.type?.includes('decomposition')) {
        // Invalidate if it's the current task
        if (data.task_id === taskId || data.id === taskId) {
          queryClient.invalidateQueries(['tasks', 'detail', taskId]);
          queryClient.invalidateQueries(['tasks', 'tree', taskId]);
        }
        // Also invalidate if it's a child of the current task
        if (data.parent_id === taskId || data.root_task_id === taskId) {
          queryClient.invalidateQueries(['tasks', 'detail', taskId]);
          queryClient.invalidateQueries(['tasks', 'tree', taskId]);
        }
      }
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, [connected, subscribe, taskId, queryClient]);

  // Fetch task data
  const { data: task, isLoading: taskLoading, error: taskError } = useQuery({
    queryKey: ['tasks', 'detail', taskId],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}`);
      // apiClient.get already returns response.data, check if data is nested
      return response?.data || response;
    },
    enabled: !!taskId && isAuthenticated(),
  });

  // Fetch task tree
  const { data: taskTree, isLoading: treeLoading } = useQuery({
    queryKey: ['tasks', 'tree', taskId],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}/tree`);
      // apiClient.get already returns response.data, check if data is nested
      return response?.data || response;
    },
    enabled: !!taskId && isAuthenticated(),
  });

  // Task mutations
  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, updates }) => {
      const response = await apiClient.patch(`/tasks/${taskId}`, updates);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['task', taskId]);
      queryClient.invalidateQueries(['taskTree', taskId]);
      showSuccess('Task updated successfully');
    },
    onError: (error) => {
      showError('Failed to update task');
      console.error('Update task error:', error);
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId) => {
      await apiClient.delete(`/tasks/${taskId}`);
    },
    onSuccess: () => {
      showSuccess('Task deleted successfully');
      navigate('/dashboard');
    },
    onError: (error) => {
      showError('Failed to delete task');
      console.error('Delete task error:', error);
    },
  });


  // Build tabs with counts
  const hasEventModel = task?.metadata?.event_model_markdown ||
                        task?.metadata?.extracted_events?.length > 0 ||
                        task?.metadata?.commands?.length > 0 ||
                        task?.metadata?.read_models?.length > 0;

  const hasSchemas = (task?.metadata?.commands?.length > 0 && task?.metadata?.commands[0]?.parameters) ||
                     (task?.metadata?.extracted_events?.length > 0 && task?.metadata?.extracted_events[0]?.payload) ||
                     (task?.metadata?.read_models?.length > 0 && task?.metadata?.read_models[0]?.fields);

  const tabsWithCounts = task ? [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'subtasks', label: `Subtasks${task.children_count ? ` (${task.children_count})` : ''}`, icon: '🎯' },
    { id: 'stories', label: 'User Stories', icon: '📖' },
    { id: 'event-model', label: 'Event Model', icon: '🔄' },
    { id: 'schemas', label: 'Schemas', icon: '📐', hidden: !hasSchemas },
  ] : [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'subtasks', label: 'Subtasks', icon: '🎯' },
  ];

  // Event handlers
  const handleStatusChange = (taskId, newStatus) => {
    updateTaskMutation.mutate({ taskId, updates: { status: newStatus } });
  };

  const handleDeleteTask = () => {
    deleteTaskMutation.mutate(taskId);
    setShowDeleteModal(false);
  };

  const handleRefresh = () => {
    // Reconnect WebSocket if disconnected
    if (!connected) {
      connect().catch(err => console.error('Failed to reconnect:', err));
    }
    // Refresh data
    queryClient.invalidateQueries(['tasks', 'detail', taskId]);
    queryClient.invalidateQueries(['tasks', 'tree', taskId]);
  };

  // Loading state
  if (taskLoading) {
    return (
      <div className="loading-container" style={styles.loadingContainer}>
        <LoadingSpinner size="lg" />
        <Text style={styles.loadingText}>Loading task details...</Text>
      </div>
    );
  }

  // Error state
  if (taskError || !task) {
    return (
      <div className="container" style={styles.container}>
        <ErrorMessage
          title="Failed to load task"
          message={taskError?.message || 'Task not found'}
          onRetry={handleRefresh}
        />
      </div>
    );
  }

  return (
    <div className="container" style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.breadcrumb}>
            <Button
              variant="ghost"
              size="sm"
              icon={BackIcon}
              onClick={() => navigate('/dashboard')}
            >
              Dashboard
            </Button>
            <Text style={styles.breadcrumbSeparator}>›</Text>
            <Text style={styles.breadcrumbCurrent}>Task Details</Text>
          </div>

          <div style={styles.headerActions}>
            <ConnectionIndicator connected={connected} />
            <Button
              variant="ghost"
              size="sm"
              icon={RefreshIcon}
              onClick={handleRefresh}
              loading={taskLoading || treeLoading}
            >
              Refresh
            </Button>
          </div>
        </div>
      </header>

      {/* Task Overview Card */}
      <Card style={styles.taskOverviewCard}>
        <CardHeader style={styles.taskHeader}>
          <div style={styles.taskTitleSection}>
            <Heading1 style={styles.taskTitle}>{task.description}</Heading1>
            <div style={styles.taskMeta}>
              <Badge variant={getStatusVariant(task.status)}>
                {task.status}
              </Badge>
              <Text style={styles.metaText}>
                Created {formatDetailedDate(task.created_at)}
              </Text>
              {task.children_count > 0 && (
                <Text style={styles.metaText}>
                  {task.children_count} subtasks
                </Text>
              )}
            </div>
          </div>

          <div style={styles.taskActions}>
            <ExportModal
              task={task}
              localTaskTree={taskTree}
              onShowToast={(message, type) => {
                if (type === 'success') showSuccess(message);
                else showError(message);
              }}
            />

            {task.status !== 'completed' && (
              <Button
                variant="primary"
                size="sm"
                icon={CheckIcon}
                onClick={() => handleStatusChange(task.task_id, 'completed')}
                loading={updateTaskMutation.isPending}
              >
                Mark Complete
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              icon={EditIcon}
              onClick={() => setEditMode(true)}
            >
              Edit
            </Button>

            <Button
              variant="outline"
              size="sm"
              icon={TrashIcon}
              onClick={() => setShowDeleteModal(true)}
            >
              Delete
            </Button>
          </div>
        </CardHeader>

      </Card>

      {/* Decomposition Status */}
      <DecompositionStatus
        taskId={taskId}
        isDecomposing={task.status === 'processing'}
        onDecompositionComplete={handleRefresh}
      />

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Navigation Tabs */}
        <nav style={styles.tabNav}>
          {tabsWithCounts.filter(tab => !tab.hidden).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                ...styles.tab,
                ...(activeTab === tab.id ? styles.activeTab : {}),
              }}
              onMouseEnter={(e) => {
                if (activeTab !== tab.id) {
                  e.currentTarget.style.backgroundColor = 'var(--color-surface)';
                  e.currentTarget.style.color = 'var(--color-text)';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== tab.id) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--color-text-muted)';
                }
              }}
            >
              <span style={styles.tabIcon}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab Content */}
        <div style={styles.tabContent}>
          {activeTab === 'overview' && (
            <OverviewTab task={task} taskTree={taskTree} onNavigateToTab={setActiveTab} />
          )}

          {activeTab === 'subtasks' && (
            <SubtasksTab
              task={task}
              taskTree={taskTree}
              selectedSubtask={selectedSubtask}
              onSubtaskSelect={setSelectedSubtask}
              onStatusChange={handleStatusChange}
              onRefresh={handleRefresh}
              updating={updateTaskMutation.isPending}
            />
          )}

          {activeTab === 'stories' && (
            <StoriesTab task={task} />
          )}

          {activeTab === 'event-model' && (
            <EventModelTab task={task} taskTree={taskTree} />
          )}

          {activeTab === 'schemas' && (
            <SchemasTab task={task} taskTree={taskTree} />
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Task"
      >
        <div style={styles.modalContent}>
          <Text style={styles.modalText}>
            Are you sure you want to delete this task? This action cannot be undone.
            {task.children_count > 0 && (
              <> All {task.children_count} subtasks will also be deleted.</>
            )}
          </Text>

          <div style={styles.modalActions}>
            <Button
              variant="ghost"
              onClick={() => setShowDeleteModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleDeleteTask}
              loading={deleteTaskMutation.isPending}
              style={styles.deleteConfirmButton}
            >
              Delete Task
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

// Helper Components
const ConnectionIndicator = ({ connected }) => (
  <div style={styles.connectionIndicator}>
    <div style={{
      ...styles.connectionDot,
      backgroundColor: connected ? tokens.colors.success[500] : tokens.colors.error[500],
    }} />
    <Text style={styles.connectionText}>
      {connected ? 'Live' : 'Offline'}
    </Text>
  </div>
);

const getStatusVariant = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'processing': return 'info';
    case 'failed': return 'error';
    default: return 'warning';
  }
};

// Styles
const styles = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: tokens.spacing[4],
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    gap: tokens.spacing[4],
  },

  loadingText: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.lg[0],
  },

  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: tokens.spacing[2],
  },

  headerContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },

  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  breadcrumbSeparator: {
    color: 'var(--color-text-muted)',
  },

  breadcrumbCurrent: {
    color: 'var(--color-text)',
    fontWeight: tokens.typography.fontWeight.medium,
  },

  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },

  connectionIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  connectionDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },

  connectionText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },

  taskOverviewCard: {
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
  },

  taskHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: tokens.spacing[4],
    padding: tokens.spacing[4],
    borderBottom: `1px solid var(--color-border)`,
  },

  taskTitleSection: {
    flex: 1,
  },

  taskTitle: {
    marginBottom: tokens.spacing[3],
    color: 'var(--color-text)',
    lineHeight: tokens.typography.lineHeight.tight,
  },

  taskMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[4],
    flexWrap: 'wrap',
  },

  metaText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },

  taskActions: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flexShrink: 0,
    flexWrap: 'nowrap',
  },

  mainContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  tabNav: {
    display: 'flex',
    borderBottom: `2px solid var(--color-border)`,
    gap: tokens.spacing[2],
    overflowX: 'auto',
    overflowY: 'hidden',
    WebkitOverflowScrolling: 'touch',
    scrollbarWidth: 'thin',
  },

  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    borderBottom: '3px solid transparent',
    borderTopLeftRadius: tokens.borderRadius.md,
    borderTopRightRadius: tokens.borderRadius.md,
    transition: 'all 200ms ease',
    whiteSpace: 'nowrap',
    position: 'relative',
    marginBottom: '-2px', // Overlap with border
  },

  activeTab: {
    color: tokens.colors.primary[500],
    borderBottomColor: tokens.colors.primary[500],
    fontWeight: tokens.typography.fontWeight.semibold,
    backgroundColor: 'var(--color-surface)',
  },

  tabIcon: {
    fontSize: tokens.typography.fontSize.lg[0],
    lineHeight: 1,
  },

  tabContent: {
    minHeight: '400px',
  },

  modalContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  modalText: {
    color: 'var(--color-text)',
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
  },

  deleteConfirmButton: {
    backgroundColor: tokens.colors.error[500],
    borderColor: tokens.colors.error[500],
    '--color-primary': tokens.colors.error[500],
    '--color-primary-hover': tokens.colors.error[600],
  },
};

export default TaskBoard;

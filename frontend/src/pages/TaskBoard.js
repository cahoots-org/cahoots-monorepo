import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  IconButton,
  Text,
  Heading1,
  Heading2,
  Heading3,
  Badge,
  LoadingSpinner,
  EmptyState,
  ErrorMessage,
  Modal,
  Progress,
  Input,
  Select,
  BackIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  RefreshIcon,
  tokens,
} from '../design-system';

import { useAuth } from '../contexts/AuthContext';
import { useApp } from '../contexts/AppContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import ExportModal from '../components/ExportModal';
import TreeVisualization from '../components/TreeVisualization';
import DecompositionStatus from '../components/DecompositionStatus';
import { formatDetailedDate } from '../utils/dateUtils';
import apiClient from '../services/unifiedApiClient';

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
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Connect WebSocket when component mounts
  useEffect(() => {
    // Only connect if authenticated
    if (!isAuthenticated) {
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
      return response.data;
    },
    enabled: !!taskId && isAuthenticated,
  });

  // Fetch task tree
  const { data: taskTree, isLoading: treeLoading } = useQuery({
    queryKey: ['tasks', 'tree', taskId],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}/tree`);
      return response.data;
    },
    enabled: !!taskId && isAuthenticated,
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

  // Calculate task stats
  const taskStats = React.useMemo(() => {
    if (!taskTree) return { total: 1, completed: 0, pending: 1, inProgress: 0 };

    const calculateStats = (node) => {
      let stats = { total: 1, completed: 0, pending: 0, inProgress: 0 };

      switch (node.status) {
        case 'completed':
          stats.completed = 1;
          break;
        case 'processing':
          stats.inProgress = 1;
          break;
        default:
          stats.pending = 1;
      }

      if (node.children?.length > 0) {
        node.children.forEach(child => {
          const childStats = calculateStats(child);
          stats.total += childStats.total;
          stats.completed += childStats.completed;
          stats.pending += childStats.pending;
          stats.inProgress += childStats.inProgress;
        });
      }

      return stats;
    };

    return calculateStats(taskTree);
  }, [taskTree]);

  const completionRate = taskStats.total > 0 ? Math.round((taskStats.completed / taskStats.total) * 100) : 0;

  // Event handlers
  const handleStatusChange = (taskId, newStatus) => {
    updateTaskMutation.mutate({ taskId, updates: { status: newStatus } });
  };

  const handleDeleteTask = () => {
    deleteTaskMutation.mutate(taskId);
    setShowDeleteModal(false);
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries(['task', taskId]);
    queryClient.invalidateQueries(['taskTree', taskId]);
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

        {/* Progress Section */}
        {taskTree && taskStats.total > 1 && (
          <CardContent style={styles.progressSection}>
            <div style={styles.progressHeader}>
              <Heading3>Progress Overview</Heading3>
              <Text style={styles.progressPercentage}>{completionRate}% Complete</Text>
            </div>

            <Progress
              value={completionRate}
              variant={completionRate === 100 ? 'success' : 'primary'}
              style={styles.progressBar}
            />

            <div style={styles.statsGrid}>
              <StatCard
                label="Total"
                value={taskStats.total}
                color={tokens.colors.neutral[600]}
              />
              <StatCard
                label="Completed"
                value={taskStats.completed}
                color={tokens.colors.success[500]}
              />
              <StatCard
                label="In Progress"
                value={taskStats.inProgress}
                color={tokens.colors.info[500]}
              />
              <StatCard
                label="Pending"
                value={taskStats.pending}
                color={tokens.colors.warning[500]}
              />
            </div>
          </CardContent>
        )}
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
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                ...styles.tab,
                ...(activeTab === tab.id ? styles.activeTab : {}),
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
            <OverviewTab task={task} taskTree={taskTree} />
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
      {connected ? 'Connected' : 'Disconnected'}
    </Text>
  </div>
);

const StatCard = ({ label, value, color }) => (
  <div style={styles.statCard}>
    <Text style={{ ...styles.statValue, color }}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </div>
);

const OverviewTab = ({ task, taskTree }) => (
  <div style={styles.overviewGrid}>
    <Card>
      <CardHeader>
        <Heading3>Task Information</Heading3>
      </CardHeader>
      <CardContent style={styles.infoGrid}>
        <InfoItem label="Status" value={
          <Badge variant={getStatusVariant(task.status)}>
            {task.status}
          </Badge>
        } />
        <InfoItem label="Created" value={formatDetailedDate(task.created_at)} />
        <InfoItem label="Updated" value={formatDetailedDate(task.updated_at)} />
        <InfoItem label="Subtasks" value={`${task.children_count || 0} tasks`} />
      </CardContent>
    </Card>

    {task.context?.tech_stack && (
      <Card>
        <CardHeader>
          <Heading3>Technology Stack</Heading3>
        </CardHeader>
        <CardContent>
          <div style={styles.techStackGrid}>
            {Object.entries(task.context.tech_stack).map(([key, value]) => (
              <div key={key} style={styles.techStackItem}>
                <Text style={styles.techStackLabel}>
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </Text>
                <Text style={styles.techStackValue}>
                  {typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                </Text>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )}
  </div>
);

const SubtasksTab = ({
  taskTree,
  selectedSubtask,
  onSubtaskSelect,
  onStatusChange,
  onRefresh,
  updating
}) => {
  if (!taskTree) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>🎯</span>
        <h3 style={styles.emptyStateTitle}>No Subtasks</h3>
        <p style={styles.emptyStateDescription}>This task hasn't been decomposed into subtasks yet.</p>
      </div>
    );
  }

  const subtasksLayoutStyle = {
    display: 'grid',
    gridTemplateColumns: selectedSubtask ? '2fr 1fr' : '1fr',
    gap: tokens.spacing[6],
  };

  return (
    <div style={subtasksLayoutStyle}>
      <Card style={styles.treeCard}>
        <CardHeader>
          <Heading3>Task Hierarchy</Heading3>
        </CardHeader>
        <CardContent>
          <TreeVisualization
            taskTree={taskTree}
            onStatusChange={onStatusChange}
            updating={updating}
            onTaskSelect={onSubtaskSelect}
            onRefreshTree={onRefresh}
          />
        </CardContent>
      </Card>

      {selectedSubtask && (
        <Card style={styles.detailCard}>
          <CardHeader>
            <div style={styles.detailHeader}>
              <Heading3>Subtask Details</Heading3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSubtaskSelect(null)}
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <SubtaskDetails task={selectedSubtask} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

const StoriesTab = ({ task }) => {
  const [selectedStory, setSelectedStory] = useState(null);
  const [expandedEpics, setExpandedEpics] = useState(new Set());

  const epics = task.context?.epics || [];
  const userStories = task.context?.user_stories || [];

  // Group stories by epic
  const storiesByEpic = userStories.reduce((acc, story) => {
    const epicId = story.epic_id || 'unassigned';
    if (!acc[epicId]) {
      acc[epicId] = [];
    }
    acc[epicId].push(story);
    return acc;
  }, {});

  const toggleEpic = (epicId) => {
    const newExpanded = new Set(expandedEpics);
    if (newExpanded.has(epicId)) {
      newExpanded.delete(epicId);
    } else {
      newExpanded.add(epicId);
    }
    setExpandedEpics(newExpanded);
  };

  const expandAll = () => {
    const allEpicIds = epics.map(e => e.id);
    setExpandedEpics(new Set(allEpicIds));
  };

  const collapseAll = () => {
    setExpandedEpics(new Set());
  };

  if (epics.length === 0 && userStories.length === 0) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>📝</span>
        <h3 style={styles.emptyStateTitle}>No User Stories</h3>
        <p style={styles.emptyStateDescription}>User stories will appear here once the task is processed.</p>
      </div>
    );
  }

  return (
    <div style={styles.storiesContainer}>
      {/* Controls */}
      <div style={styles.storiesControls}>
        <div style={styles.storiesSummary}>
          <Badge variant="secondary">{epics.length} Epics</Badge>
          <Badge variant="info">{userStories.length} Stories</Badge>
        </div>
        <div style={styles.expandControls}>
          <Button variant="ghost" size="sm" onClick={expandAll}>Expand All</Button>
          <Button variant="ghost" size="sm" onClick={collapseAll}>Collapse All</Button>
        </div>
      </div>

      {/* Epics and Stories */}
      <div style={styles.epicsContainer}>
        {epics.map(epic => {
          const isExpanded = expandedEpics.has(epic.id);
          const epicStories = storiesByEpic[epic.id] || [];

          return (
            <Card key={epic.id} style={styles.epicCard}>
              <div
                style={styles.epicHeader}
                onClick={() => toggleEpic(epic.id)}
              >
                <div style={styles.epicHeaderLeft}>
                  <IconButton
                    icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
                    size="sm"
                    variant="ghost"
                  />
                  <div>
                    <div style={styles.epicTitle}>
                      <Heading3 style={{ margin: 0 }}>{epic.title}</Heading3>
                      <Badge variant="primary" size="sm">{epic.id}</Badge>
                    </div>
                    <Text style={styles.epicDescription}>{epic.description}</Text>
                  </div>
                </div>
                <div style={styles.epicStats}>
                  <Badge variant="secondary">{epicStories.length} stories</Badge>
                  <Badge variant={epic.priority <= 2 ? 'error' : epic.priority <= 3 ? 'warning' : 'info'}>
                    Priority {epic.priority}
                  </Badge>
                </div>
              </div>

              {isExpanded && (
                <div style={styles.storiesList}>
                  {epicStories.length === 0 ? (
                    <Text style={styles.noStoriesText}>No stories in this epic</Text>
                  ) : (
                    epicStories.map(story => (
                      <div
                        key={story.id}
                        style={{
                          ...styles.storyItem,
                          ...(selectedStory?.id === story.id ? styles.selectedStory : {})
                        }}
                        onClick={() => setSelectedStory(story.id === selectedStory?.id ? null : story)}
                      >
                        <div style={styles.storyItemHeader}>
                          <div style={styles.storyItemLeft}>
                            <Text style={styles.storyId}>{story.id}</Text>
                            <Text style={styles.storyTitle}>
                              <strong>As a</strong> {story.actor},
                              <strong> I want to</strong> {story.action}
                            </Text>
                          </div>
                          <div style={styles.storyItemRight}>
                            {story.story_points && (
                              <Badge variant="info" size="sm">{story.story_points} pts</Badge>
                            )}
                            <Badge
                              variant={
                                story.priority === 'must_have' ? 'error' :
                                story.priority === 'should_have' ? 'warning' :
                                'secondary'
                              }
                              size="sm"
                            >
                              {story.priority?.replace('_', ' ')}
                            </Badge>
                          </div>
                        </div>

                        {selectedStory?.id === story.id && (
                          <div style={styles.storyDetails}>
                            <Text style={styles.storyBenefit}>
                              <strong>So that</strong> {story.benefit}
                            </Text>
                            {story.acceptance_criteria?.length > 0 && (
                              <div style={styles.acceptanceCriteria}>
                                <Text style={styles.criteriaTitle}>Acceptance Criteria:</Text>
                                <ul style={styles.criteriaList}>
                                  {story.acceptance_criteria.map((criteria, idx) => (
                                    <li key={idx}>
                                      <Text style={styles.criteriaItem}>{criteria}</Text>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </Card>
          );
        })}

        {/* Unassigned stories (if any) */}
        {storiesByEpic.unassigned && storiesByEpic.unassigned.length > 0 && (
          <Card style={styles.epicCard}>
            <div style={styles.epicHeader}>
              <div style={styles.epicHeaderLeft}>
                <div>
                  <Heading3 style={{ margin: 0 }}>Unassigned Stories</Heading3>
                  <Text style={styles.epicDescription}>Stories not yet assigned to an epic</Text>
                </div>
              </div>
              <Badge variant="warning">{storiesByEpic.unassigned.length} stories</Badge>
            </div>
            <div style={styles.storiesList}>
              {storiesByEpic.unassigned.map(story => (
                <div
                  key={story.id}
                  style={{
                    ...styles.storyItem,
                    ...(selectedStory?.id === story.id ? styles.selectedStory : {})
                  }}
                  onClick={() => setSelectedStory(story.id === selectedStory?.id ? null : story)}
                >
                  <Text style={styles.storyTitle}>
                    <strong>As a</strong> {story.actor},
                    <strong> I want to</strong> {story.action}
                  </Text>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

const InfoItem = ({ label, value }) => (
  <div style={styles.infoItem}>
    <Text style={styles.infoLabel}>{label}</Text>
    <div style={styles.infoValue}>{value}</div>
  </div>
);

const SubtaskDetails = ({ task }) => (
  <div style={styles.subtaskDetails}>
    <InfoItem label="Description" value={task.description} />
    <InfoItem label="Status" value={
      <Badge variant={getStatusVariant(task.status)}>
        {task.status}
      </Badge>
    } />
    <InfoItem label="Created" value={formatDetailedDate(task.created_at)} />
    {task.story_points && (
      <InfoItem label="Story Points" value={task.story_points} />
    )}
    {task.implementation_details && (
      <InfoItem label="Implementation Details" value={task.implementation_details} />
    )}
  </div>
);

const UserStoryCard = ({ story }) => (
  <Card style={styles.storyCard}>
    <CardContent>
      <div style={styles.storyHeader}>
        <Badge variant="info">{story.epic_id || 'Unassigned'}</Badge>
      </div>

      <Text style={styles.storyText}>
        <strong>As a</strong> {story.actor}, <strong>I want to</strong> {story.action},
        <strong> so that</strong> {story.benefit}
      </Text>

      {story.acceptance_criteria?.length > 0 && (
        <div style={styles.criteriaSection}>
          <Text style={styles.criteriaTitle}>Acceptance Criteria:</Text>
          <ul style={styles.criteriaList}>
            {story.acceptance_criteria.map((criteria, index) => (
              <li key={index}>
                <Text style={styles.criteriaItem}>{criteria}</Text>
              </li>
            ))}
          </ul>
        </div>
      )}
    </CardContent>
  </Card>
);

// Helper functions
const getStatusVariant = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'processing': return 'info';
    case 'failed': return 'error';
    default: return 'warning';
  }
};

// Tab configuration
const tabs = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'subtasks', label: 'Subtasks', icon: '🎯' },
  { id: 'stories', label: 'User Stories', icon: '📝' },
];

// Styles
const styles = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: tokens.spacing[6],
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[6],
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
    gap: tokens.spacing[6],
    padding: tokens.spacing[6],
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


  progressSection: {
    padding: tokens.spacing[6],
  },

  progressHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: tokens.spacing[4],
  },

  progressPercentage: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.primary[500],
  },

  progressBar: {
    height: '8px',
    marginBottom: tokens.spacing[4],
  },

  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
    gap: tokens.spacing[4],
  },

  statCard: {
    textAlign: 'center',
  },

  statValue: {
    display: 'block',
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    lineHeight: 1,
  },

  statLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },

  mainContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  tabNav: {
    display: 'flex',
    borderBottom: `1px solid var(--color-border)`,
    gap: tokens.spacing[1],
  },

  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    fontSize: tokens.typography.fontSize.base[0],
    color: 'var(--color-text-muted)',
    borderBottom: '2px solid transparent',
    transition: tokens.transitions.colors,
  },

  activeTab: {
    color: tokens.colors.primary[500],
    borderBottomColor: tokens.colors.primary[500],
    fontWeight: tokens.typography.fontWeight.medium,
  },

  tabIcon: {
    fontSize: tokens.typography.fontSize.base[0],
  },

  tabContent: {
    minHeight: '400px',
  },

  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: tokens.spacing[6],
  },

  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: tokens.spacing[4],
  },

  infoItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },

  infoLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },

  infoValue: {
    color: 'var(--color-text)',
  },

  techStackGrid: {
    display: 'grid',
    gap: tokens.spacing[4],
  },

  techStackItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  techStackLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },

  techStackValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: tokens.typography.fontFamily.mono.join(', '),
    backgroundColor: 'var(--color-surface)',
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.base,
    border: `1px solid var(--color-border)`,
    whiteSpace: 'pre-wrap',
  },


  treeCard: {
    minHeight: '500px',
  },

  detailCard: {
    position: 'sticky',
    top: tokens.spacing[6],
    height: 'fit-content',
  },

  detailHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },

  subtaskDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  storiesContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  storiesControls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.base,
    border: `1px solid var(--color-border)`,
  },

  storiesSummary: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  expandControls: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  epicsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  epicCard: {
    overflow: 'hidden',
  },

  epicHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: tokens.spacing[4],
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface-hover)',
    },
  },

  epicHeaderLeft: {
    display: 'flex',
    gap: tokens.spacing[3],
    flex: 1,
  },

  epicTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  epicDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  epicStats: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  storiesList: {
    borderTop: `1px solid var(--color-border)`,
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-background)',
  },

  storyItem: {
    padding: tokens.spacing[3],
    borderRadius: tokens.borderRadius.base,
    border: `1px solid var(--color-border)`,
    marginBottom: tokens.spacing[2],
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface)',
    },
  },

  selectedStory: {
    backgroundColor: 'var(--color-surface)',
    borderColor: tokens.colors.primary[500],
  },

  storyItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: tokens.spacing[2],
  },

  storyItemLeft: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },

  storyItemRight: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  storyId: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    fontFamily: tokens.typography.fontFamily.mono.join(', '),
  },

  storyTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  storyDetails: {
    marginTop: tokens.spacing[3],
    paddingTop: tokens.spacing[3],
    borderTop: `1px solid var(--color-border)`,
  },

  storyBenefit: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[3],
    color: 'var(--color-text-muted)',
  },

  acceptanceCriteria: {
    marginTop: tokens.spacing[2],
  },

  noStoriesText: {
    textAlign: 'center',
    color: 'var(--color-text-muted)',
    padding: tokens.spacing[4],
  },

  storiesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
    gap: tokens.spacing[4],
  },

  storyCard: {
    height: 'fit-content',
  },

  storyHeader: {
    marginBottom: tokens.spacing[3],
  },

  storyText: {
    marginBottom: tokens.spacing[3],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  criteriaSection: {
    marginTop: tokens.spacing[3],
  },

  criteriaTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[2],
  },

  criteriaList: {
    marginLeft: tokens.spacing[4],
    marginTop: 0,
  },

  criteriaItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[1],
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

  emptyStateContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    textAlign: 'center',
    minHeight: '300px',
  },

  emptyStateIcon: {
    fontSize: '48px',
    marginBottom: tokens.spacing[4],
  },

  emptyStateTitle: {
    margin: 0,
    marginBottom: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
  },

  emptyStateDescription: {
    margin: 0,
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    maxWidth: '400px',
  },
};

export default TaskBoard;
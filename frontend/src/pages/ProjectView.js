/**
 * ProjectView - New review-first project page
 *
 * Replaces the tab-heavy TaskBoard with a cleaner summary-first approach:
 * 1. Shows project summary with stats and progress
 * 2. Expandable chapters/slices for drill-down
 * 3. Prominent export action when ready
 * 4. Easy refinement flow
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Button,
  Text,
  Badge,
  LoadingSpinner,
  ErrorMessage,
  BackIcon,
  RefreshIcon,
  tokens,
} from '../design-system';

import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useProjectContext } from '../hooks/api/useProjectContext';

import ProjectSummary from '../components/ProjectSummary';
import ChapterList from '../components/ChapterList';
import StoriesTab from '../components/TaskBoard/StoriesTab';
import RefineModal from '../components/RefineModal';

import apiClient from '../services/unifiedApiClient';

const ProjectView = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { connected, connect, disconnect, subscribe } = useWebSocket();
  const queryClient = useQueryClient();

  // UI State
  const [showRefineModal, setShowRefineModal] = useState(false);
  const [activeView, setActiveView] = useState('summary'); // summary, chapters, tasks

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Connect WebSocket
  useEffect(() => {
    if (!isAuthenticated()) return;

    connect().catch(err => {
      console.error('[ProjectView] Failed to connect WebSocket:', err);
    });

    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // Fetch task data
  const {
    data: task,
    isLoading: taskLoading,
    error: taskError,
  } = useQuery({
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

  // Fetch project context from Contex (used by ProjectSummary)
  useProjectContext(taskId);

  // WebSocket subscription for real-time updates
  useEffect(() => {
    if (!connected || !taskId) return;

    const unsubscribe = subscribe((data) => {
      if (data.task_id === taskId || data.root_task_id === taskId) {
        queryClient.invalidateQueries(['tasks', 'detail', taskId]);
        queryClient.invalidateQueries(['tasks', 'tree', taskId]);
      }
    });

    return () => unsubscribe?.();
  }, [connected, subscribe, taskId, queryClient]);

  const handleRefresh = () => {
    // Reconnect WebSocket if disconnected
    if (!connected) {
      connect().catch(err => console.error('Failed to reconnect:', err));
    }
    // Refresh data
    queryClient.invalidateQueries(['tasks', 'detail', taskId]);
    queryClient.invalidateQueries(['tasks', 'tree', taskId]);
    queryClient.invalidateQueries(['projects', 'context', taskId]);
  };

  const handleViewDetails = (view) => {
    setActiveView(view);
  };

  const handleRefineComplete = () => {
    handleRefresh();
  };

  // Get chapters from task metadata
  const chapters = task?.metadata?.chapters || [];

  // Slices are nested inside chapters - flatten them with chapter reference
  const slices = chapters.flatMap(chapter =>
    (chapter.slices || []).map(slice => ({
      ...slice,
      chapter: chapter.name
    }))
  );

  const isProcessing = task?.status === 'pending' || task?.status === 'processing';

  // Loading state
  if (taskLoading) {
    return (
      <div style={styles.loadingContainer}>
        <LoadingSpinner size="lg" />
        <Text style={styles.loadingText}>Loading project...</Text>
      </div>
    );
  }

  // Error state
  if (taskError || !task) {
    return (
      <div style={styles.container}>
        <ErrorMessage
          title="Failed to load project"
          message={taskError?.message || 'Project not found'}
          onRetry={handleRefresh}
        />
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <Button
            variant="ghost"
            size="sm"
            icon={BackIcon}
            onClick={() => navigate('/dashboard')}
          >
            Dashboard
          </Button>
        </div>

        <div style={styles.headerRight}>
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
      </header>

      {/* Project Summary */}
      <ProjectSummary
        task={task}
        taskTree={taskTree}
        onRefine={() => setShowRefineModal(true)}
        onViewDetails={handleViewDetails}
      />

      {/* View Toggle (only show when not processing) */}
      {!isProcessing && (
        <div style={styles.viewToggle}>
          <Button
            variant={activeView === 'summary' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('summary')}
          >
            Summary
          </Button>
          <Button
            variant={activeView === 'stories' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('stories')}
          >
            Epics & Stories
          </Button>
          <Button
            variant={activeView === 'chapters' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('chapters')}
          >
            Chapters ({chapters.length})
          </Button>
          <Button
            variant={activeView === 'tasks' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('tasks')}
          >
            All Tasks ({task?.children_count || 0})
          </Button>
        </div>
      )}

      {/* Content based on active view */}
      {!isProcessing && activeView === 'summary' && (
        <SummaryView task={task} taskTree={taskTree} />
      )}

      {!isProcessing && activeView === 'stories' && (
        <StoriesTab task={task} />
      )}

      {!isProcessing && activeView === 'chapters' && (
        <ChapterList
          chapters={chapters}
          slices={slices}
          onEditChapter={(chapter) => console.log('Edit chapter:', chapter)}
          onEditSlice={(slice) => console.log('Edit slice:', slice)}
          onAddSlice={(chapterName) => console.log('Add slice to:', chapterName)}
        />
      )}

      {!isProcessing && activeView === 'tasks' && (
        <TaskList taskTree={taskTree} />
      )}

      {/* Modals */}
      <RefineModal
        isOpen={showRefineModal}
        onClose={() => setShowRefineModal(false)}
        task={task}
        onRefineComplete={handleRefineComplete}
      />
    </div>
  );
};

/**
 * Simple task list for "All Tasks" view
 */
const TaskList = ({ taskTree }) => {
  // Flatten the tree structure into a list
  const flattenTree = (node, depth = 0) => {
    if (!node) return [];
    const tasks = [];
    // Add the current node (skip root at depth 0)
    if (depth > 0) {
      tasks.push({ ...node, depth });
    }
    // Recursively add children
    if (node.children && Array.isArray(node.children)) {
      node.children.forEach(child => {
        tasks.push(...flattenTree(child, depth + 1));
      });
    }
    return tasks;
  };

  const tasks = flattenTree(taskTree);

  if (tasks.length === 0) {
    return (
      <Card style={styles.emptyCard}>
        <Text style={styles.emptyText}>No tasks yet</Text>
      </Card>
    );
  }

  return (
    <Card style={styles.taskListCard}>
      <div style={styles.taskList}>
        {tasks.map((task) => (
          <div
            key={task.task_id || task.id}
            style={{
              ...styles.taskItem,
              paddingLeft: `${tokens.spacing[4]} + ${(task.depth - 1) * 24}px`,
            }}
          >
            <div style={styles.taskDepthIndicator}>
              {'└'.repeat(task.depth - 1)}
            </div>
            <div style={styles.taskContent}>
              <Text style={styles.taskDescription}>{task.description}</Text>
              <div style={styles.taskMeta}>
                <Badge
                  variant={task.is_atomic ? 'success' : 'secondary'}
                  style={styles.taskBadge}
                >
                  {task.is_atomic ? 'Atomic' : `Depth ${task.depth}`}
                </Badge>
                {task.story_points && (
                  <Badge variant="info" style={styles.taskBadge}>
                    {task.story_points} pts
                  </Badge>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

/**
 * Summary view showing event model overview
 */
const SummaryView = ({ task, taskTree }) => {
  const events = task?.metadata?.extracted_events || [];
  const commands = task?.metadata?.commands || [];
  const readModels = task?.metadata?.read_models || [];
  const swimlanes = task?.metadata?.swimlanes || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: tokens.spacing[5] }}>
      {/* Swimlanes Overview */}
      {swimlanes.length > 0 && (
        <Card style={{ padding: tokens.spacing[5] }}>
          <Text size="lg" weight="semibold" style={{ marginBottom: tokens.spacing[4] }}>
            System Components
          </Text>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: tokens.spacing[3],
          }}>
            {swimlanes.map((swimlane, i) => (
              <div key={i} style={{
                padding: tokens.spacing[4],
                backgroundColor: 'var(--color-bg-secondary)',
                borderRadius: tokens.borderRadius.md,
              }}>
                <Text weight="semibold" style={{ marginBottom: tokens.spacing[1] }}>
                  {swimlane.name}
                </Text>
                <Text size="sm" style={{ color: 'var(--color-text-muted)', marginBottom: tokens.spacing[3] }}>
                  {swimlane.description}
                </Text>
                <div style={{ display: 'flex', gap: tokens.spacing[2], flexWrap: 'wrap' }}>
                  <Badge variant="warning" size="sm">{swimlane.events?.length || 0} events</Badge>
                  <Badge variant="primary" size="sm">{swimlane.commands?.length || 0} commands</Badge>
                  <Badge variant="info" size="sm">{swimlane.read_models?.length || 0} views</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Event Model Elements */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: tokens.spacing[4],
      }}>
        {/* Events */}
        {events.length > 0 && (
          <Card style={{ padding: tokens.spacing[5] }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: tokens.spacing[3] }}>
              <Text size="lg" weight="semibold">Events</Text>
              <Badge variant="warning">{events.length}</Badge>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: tokens.spacing[2] }}>
              {events.slice(0, 15).map((event, i) => (
                <Badge key={i} variant="warning">
                  {typeof event === 'string' ? event : event.name}
                </Badge>
              ))}
              {events.length > 15 && (
                <Badge variant="secondary">+{events.length - 15} more</Badge>
              )}
            </div>
          </Card>
        )}

        {/* Commands */}
        {commands.length > 0 && (
          <Card style={{ padding: tokens.spacing[5] }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: tokens.spacing[3] }}>
              <Text size="lg" weight="semibold">Commands</Text>
              <Badge variant="primary">{commands.length}</Badge>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: tokens.spacing[2] }}>
              {commands.slice(0, 15).map((cmd, i) => (
                <Badge key={i} variant="primary">
                  {typeof cmd === 'string' ? cmd : cmd.name}
                </Badge>
              ))}
              {commands.length > 15 && (
                <Badge variant="secondary">+{commands.length - 15} more</Badge>
              )}
            </div>
          </Card>
        )}

        {/* Read Models */}
        {readModels.length > 0 && (
          <Card style={{ padding: tokens.spacing[5] }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: tokens.spacing[3] }}>
              <Text size="lg" weight="semibold">Read Models</Text>
              <Badge variant="info">{readModels.length}</Badge>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: tokens.spacing[2] }}>
              {readModels.slice(0, 15).map((rm, i) => (
                <Badge key={i} variant="info">
                  {typeof rm === 'string' ? rm : rm.name}
                </Badge>
              ))}
              {readModels.length > 15 && (
                <Badge variant="secondary">+{readModels.length - 15} more</Badge>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Empty state */}
      {events.length === 0 && commands.length === 0 && readModels.length === 0 && swimlanes.length === 0 && (
        <Card style={{ textAlign: 'center', padding: tokens.spacing[10] }}>
          <Text size="lg" weight="medium" style={{ marginBottom: tokens.spacing[2] }}>
            No event model data yet
          </Text>
          <Text style={{ color: 'var(--color-text-muted)' }}>
            Check the Chapters tab for the task breakdown, or wait for processing to complete.
          </Text>
        </Card>
      )}
    </div>
  );
};

/**
 * Connection indicator
 */
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

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: tokens.spacing[6],
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
  },

  // Header
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[6],
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },

  // Connection indicator
  connectionIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  connectionDot: {
    width: '8px',
    height: '8px',
    borderRadius: tokens.borderRadius.full,
  },
  connectionText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
  },

  // View toggle
  viewToggle: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[6],
    padding: tokens.spacing[2],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    width: 'fit-content',
  },

  // Task list
  taskListCard: {
    padding: 0,
    overflow: 'hidden',
  },
  taskList: {
    maxHeight: '600px',
    overflowY: 'auto',
  },
  taskItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[2],
    padding: tokens.spacing[3],
    borderBottom: `1px solid var(--color-border)`,
    transition: 'background-color 0.2s ease',
  },
  taskDepthIndicator: {
    color: 'var(--color-text-muted)',
    fontFamily: 'monospace',
    fontSize: tokens.typography.fontSize.sm[0],
    flexShrink: 0,
    width: '40px',
  },
  taskContent: {
    flex: 1,
  },
  taskDescription: {
    marginBottom: tokens.spacing[1],
  },
  taskMeta: {
    display: 'flex',
    gap: tokens.spacing[2],
  },
  taskBadge: {
    fontSize: tokens.typography.fontSize.xs[0],
  },

  // Empty state
  emptyCard: {
    padding: tokens.spacing[8],
    textAlign: 'center',
  },
  emptyText: {
    color: 'var(--color-text-muted)',
  },
};

export default ProjectView;

/**
 * ProjectSummary - High-level overview of a generated project plan
 *
 * Shows the transformation from prompt to structured project:
 * - Original prompt
 * - Processing status/progress
 * - Summary stats (tasks, events, commands, story points)
 * - Tech stack
 * - Quick actions (export, refine)
 */
import React from 'react';
import {
  Card,
  Button,
  Text,
  Heading3,
  Badge,
  LoadingSpinner,
  tokens,
} from '../design-system';
import { useProjectContext } from '../hooks/api/useProjectContext';
import ExportModal from './ExportModal';
import { useApp } from '../contexts/AppContext';

const ProjectSummary = ({
  task,
  taskTree,
  onRefine,
  onViewDetails,
  onResume
}) => {
  const { showError, showSuccess } = useApp();
  const { data: projectContext, isLoading: contextLoading } = useProjectContext(task?.task_id);

  const isProcessing = task?.status === 'submitted' || task?.status === 'processing';
  const stats = projectContext?.stats || {};
  const context = projectContext?.context || {};

  // Calculate totals from various sources
  const totalTasks = stats.total_tasks || taskTree?.tasks?.length || task?.children_count || 0;
  const totalEvents = stats.total_events || task?.metadata?.extracted_events?.length || 0;
  const totalCommands = stats.total_commands || task?.metadata?.commands?.length || 0;
  const totalReadModels = stats.total_read_models || task?.metadata?.read_models?.length || 0;
  const totalChapters = task?.metadata?.chapters?.length || 0;
  const totalStoryPoints = calculateStoryPoints(taskTree);

  return (
    <Card style={styles.container}>
      {/* Original Prompt */}
      <div style={styles.promptSection}>
        <Text style={styles.promptLabel}>You asked:</Text>
        <Text style={styles.promptText}>"{task?.description}"</Text>
      </div>

      {/* Processing Status */}
      {isProcessing && (
        <ProcessingStatus
          task={task}
          taskTree={taskTree}
          context={projectContext}
          contextLoading={contextLoading}
          onResume={onResume}
        />
      )}

      {/* Generated Summary */}
      {!isProcessing && (
        <>
          <div style={styles.summarySection}>
            <div style={styles.summaryHeader}>
              <Heading3 style={styles.summaryTitle}>We generated:</Heading3>
            </div>

            <div style={styles.statsGrid}>
              <StatCard
                value={totalTasks}
                label="Tasks"
                onClick={() => onViewDetails?.('subtasks')}
              />
              <StatCard
                value={totalChapters}
                label="Chapters"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalEvents}
                label="Events"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalCommands}
                label="Commands"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalReadModels}
                label="Read Models"
                onClick={() => onViewDetails?.('schemas')}
              />
              <StatCard
                value={totalStoryPoints}
                label="Story Points"
                subtitle={estimateSprints(totalStoryPoints)}
              />
            </div>
          </div>

          {/* Actions */}
          <div style={styles.actionsSection}>
            <ExportModal
              task={task}
              localTaskTree={taskTree}
              onShowToast={(message, type) => {
                if (type === 'success') showSuccess(message);
                else showError(message);
              }}
            />
            <Button
              variant="outline"
              size="md"
              onClick={onRefine}
            >
              Refine Plan
            </Button>
          </div>
        </>
      )}
    </Card>
  );
};

/**
 * Processing status with progress indicators
 */
const ProcessingStatus = ({ task, taskTree, context, contextLoading, onResume }) => {
  const stages = [
    { key: 'analyzing', label: 'Analyzing', icon: '🔍' },
    { key: 'decomposing', label: 'Decomposing', icon: '🎯' },
    { key: 'event_modeling', label: 'Event Modeling', icon: '⚡' },
    { key: 'finalizing', label: 'Finalizing', icon: '✨' },
  ];

  // Determine current stage based on task data (not just context)
  const currentStage = determineCurrentStage(context, task, taskTree);
  const currentStageIndex = stages.findIndex(s => s.key === currentStage);

  // Calculate progress from taskTree (real-time data)
  const taskCount = taskTree?.tasks ? Object.keys(taskTree.tasks).length : (task?.children_count || 0);
  const hasEpics = task?.context?.epics?.length > 0 || task?.metadata?.epics?.length > 0;
  const hasStories = task?.context?.user_stories?.length > 0 || task?.metadata?.user_stories?.length > 0;
  const hasEventModel = task?.metadata?.extracted_events?.length > 0 || task?.metadata?.commands?.length > 0;

  // Detect if processing was interrupted (status is submitted but has partial data)
  const isInterrupted = task?.status === 'submitted' && (taskCount > 1 || hasEpics);

  if (isInterrupted) {
    return (
      <div style={styles.processingSection}>
        <div style={styles.interruptedHeader}>
          <Text style={styles.interruptedIcon}>⚠️</Text>
          <Text style={styles.processingText}>Processing was interrupted</Text>
        </div>
        <Text style={styles.interruptedMessage}>
          This project was partially processed but didn't complete. You can resume processing to finish generating the event model.
        </Text>
        {onResume && (
          <Button
            variant="primary"
            onClick={onResume}
            style={{ marginTop: tokens.spacing[4] }}
          >
            Resume Processing
          </Button>
        )}
      </div>
    );
  }

  return (
    <div style={styles.processingSection}>
      <div style={styles.processingHeader}>
        <LoadingSpinner size="sm" />
        <Text style={styles.processingText}>Building your project plan...</Text>
      </div>

      <div style={styles.stagesContainer}>
        {stages.map((stage, index) => {
          const isComplete = index < currentStageIndex;
          const isCurrent = index === currentStageIndex;
          const isPending = index > currentStageIndex;

          return (
            <div key={stage.key} style={styles.stageItem}>
              <div style={{
                ...styles.stageIndicator,
                ...(isComplete && styles.stageComplete),
                ...(isCurrent && styles.stageCurrent),
                ...(isPending && styles.stagePending),
              }}>
                {isComplete ? '✓' : stage.icon}
              </div>
              <Text style={{
                ...styles.stageLabel,
                ...(isCurrent && styles.stageLabelCurrent),
                ...(isPending && styles.stageLabelPending),
              }}>
                {stage.label}
              </Text>
            </div>
          );
        })}
      </div>

      {/* Show what we have so far - using task/taskTree data directly */}
      {(taskCount > 0 || hasEpics || hasEventModel) && (
        <div style={styles.progressPreview}>
          <Text style={styles.progressPreviewLabel}>Found so far:</Text>
          <div style={styles.progressPreviewStats}>
            {taskCount > 0 && (
              <Badge variant="info">{taskCount} tasks</Badge>
            )}
            {hasEpics && (
              <Badge variant="info">
                {task?.context?.epics?.length || task?.metadata?.epics?.length} epics
              </Badge>
            )}
            {hasStories && (
              <Badge variant="info">
                {task?.context?.user_stories?.length || task?.metadata?.user_stories?.length} stories
              </Badge>
            )}
            {hasEventModel && (
              <Badge variant="info">
                {task?.metadata?.extracted_events?.length || 0} events
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Individual stat card
 */
const StatCard = ({ value, label, icon, subtitle, onClick }) => (
  <div
    style={{
      ...styles.statCard,
      ...(onClick && styles.statCardClickable),
    }}
    onClick={onClick}
  >
    <div style={styles.statIcon}>{icon}</div>
    <div style={styles.statValue}>{value}</div>
    <div style={styles.statLabel}>{label}</div>
    {subtitle && <div style={styles.statSubtitle}>{subtitle}</div>}
  </div>
);

// Helper functions
function calculateStoryPoints(taskTree) {
  // Recursively calculate story points from nested tree structure
  const sumPoints = (node) => {
    if (!node) return 0;
    let total = 0;

    // Add this node's points
    if (node.story_points) {
      total += node.story_points;
    } else if (node.is_atomic) {
      total += 2; // Default estimate for atomic tasks
    }

    // Recursively add children's points
    if (node.children && Array.isArray(node.children)) {
      node.children.forEach(child => {
        total += sumPoints(child);
      });
    }

    return total;
  };

  return sumPoints(taskTree);
}

function estimateSprints(points) {
  if (!points) return '';
  const sprints = Math.ceil(points / 20); // Assume 20 points per sprint
  return `~${sprints} sprint${sprints !== 1 ? 's' : ''}`;
}

function determineCurrentStage(context, task, taskTree) {
  // Check task/taskTree data first (more reliable than Context Engine)
  const hasEventModel = task?.metadata?.extracted_events?.length > 0 ||
                        task?.metadata?.commands?.length > 0;
  const hasTasks = taskTree?.tasks ? Object.keys(taskTree.tasks).length > 1 :
                   (task?.children_count > 0);
  const hasEpics = task?.context?.epics?.length > 0 || task?.metadata?.epics?.length > 0;

  if (hasEventModel) {
    return 'finalizing';
  }
  if (hasTasks) {
    return 'event_modeling';
  }
  if (hasEpics) {
    return 'decomposing';
  }

  // Fall back to context data if available
  if (context?.context) {
    const data = context.context;
    if (data.event_model || data.commands || data.extracted_events) {
      return 'finalizing';
    }
    if (data.decomposed_tasks) {
      return 'event_modeling';
    }
    if (data.epics_and_stories) {
      return 'decomposing';
    }
  }

  return 'analyzing';
}

const styles = {
  container: {
    padding: tokens.spacing[6],
    marginBottom: tokens.spacing[6],
  },

  // Prompt section
  promptSection: {
    marginBottom: tokens.spacing[6],
    paddingBottom: tokens.spacing[6],
    borderBottom: `1px solid var(--color-border)`,
  },
  promptLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  promptText: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.normal,
    fontStyle: 'italic',
    color: 'var(--color-text)',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflowY: 'auto',
    padding: tokens.spacing[2],
  },

  // Processing section
  processingSection: {
    padding: tokens.spacing[6],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
  },
  processingHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[6],
  },
  processingText: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  interruptedHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[3],
  },
  interruptedIcon: {
    fontSize: '24px',
  },
  interruptedMessage: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    lineHeight: 1.5,
  },
  stagesContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[6],
  },
  stageItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  stageIndicator: {
    width: '48px',
    height: '48px',
    borderRadius: tokens.borderRadius.full,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    transition: 'all 0.3s ease',
  },
  stageComplete: {
    backgroundColor: tokens.colors.success[500],
    color: 'white',
  },
  stageCurrent: {
    backgroundColor: tokens.colors.primary[500],
    color: 'white',
    animation: 'pulse 2s infinite',
  },
  stagePending: {
    backgroundColor: 'var(--color-bg-tertiary)',
    color: 'var(--color-text-muted)',
  },
  stageLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  stageLabelCurrent: {
    color: tokens.colors.primary[500],
  },
  stageLabelPending: {
    color: 'var(--color-text-muted)',
  },
  progressPreview: {
    marginTop: tokens.spacing[4],
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid var(--color-border)`,
  },
  progressPreviewLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  progressPreviewStats: {
    display: 'flex',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
  },

  // Summary section
  summarySection: {
    marginBottom: tokens.spacing[6],
  },
  summaryHeader: {
    marginBottom: tokens.spacing[4],
  },
  summaryTitle: {
    margin: 0,
    color: 'var(--color-text)',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
    gap: tokens.spacing[4],
  },
  statCard: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    textAlign: 'center',
    transition: 'all 0.2s ease',
  },
  statCardClickable: {
    cursor: 'pointer',
    '&:hover': {
      backgroundColor: 'var(--color-bg-tertiary)',
      transform: 'translateY(-2px)',
    },
  },
  statIcon: {
    fontSize: '24px',
    marginBottom: tokens.spacing[2],
  },
  statValue: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.primary[500],
  },
  statLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  statSubtitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },

  // Actions section
  actionsSection: {
    display: 'flex',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[6],
    borderTop: `1px solid var(--color-border)`,
  },
  exportButton: {
    flex: 1,
  },
};

export default ProjectSummary;

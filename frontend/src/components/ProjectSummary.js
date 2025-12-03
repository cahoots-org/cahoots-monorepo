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
  LoadingSpinner,
  tokens,
} from '../design-system';
import { useProjectContext } from '../hooks/api/useProjectContext';
import LiveActivityFeed from './LiveActivityFeed';

const ProjectSummary = ({
  task,
  taskTree,
  onRefine,
  onExport,
  onResume
}) => {
  const { data: projectContext, isLoading: contextLoading } = useProjectContext(task?.task_id);
  const isProcessing = task?.status === 'submitted' || task?.status === 'processing';

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

      {/* Actions (when not processing) */}
      {!isProcessing && (
        <div style={styles.actionsRow}>
          <Button
            variant="outline"
            size="md"
            onClick={onExport}
          >
            Export
          </Button>
          <Button
            variant="outline"
            size="md"
            onClick={onRefine}
          >
            Refine Plan
          </Button>
        </div>
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
      {/* Progress Header */}
      <div style={styles.processingHeader}>
        <div style={styles.processingTitleRow}>
          <LoadingSpinner size="sm" />
          <Text style={styles.processingText}>Building your project plan...</Text>
        </div>
        <Text style={styles.processingSubtext}>
          This usually takes 1-2 minutes depending on complexity
        </Text>
      </div>

      {/* Stage Progress Bar */}
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

      {/* Live Stats - what we've found so far */}
      <div style={styles.liveStatsContainer}>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>{taskCount}</Text>
          <Text style={styles.liveStatLabel}>tasks</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.context?.epics?.length || task?.metadata?.epics?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>epics</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.context?.user_stories?.length || task?.metadata?.user_stories?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>stories</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.metadata?.extracted_events?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>events</Text>
        </div>
      </div>

      {/* Live Activity Feed */}
      <LiveActivityFeed taskId={task?.task_id} />
    </div>
  );
};

// Helper function to determine current processing stage
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
  processingTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  processingText: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  processingSubtext: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },
  liveStatsContainer: {
    display: 'flex',
    gap: tokens.spacing[6],
    marginBottom: tokens.spacing[6],
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
  },
  liveStat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  liveStatValue: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: 'var(--color-text)',
    lineHeight: 1,
  },
  liveStatLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
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
  // Actions section
  actionsRow: {
    display: 'flex',
    gap: tokens.spacing[3],
    justifyContent: 'flex-start',
  },
};

export default ProjectSummary;

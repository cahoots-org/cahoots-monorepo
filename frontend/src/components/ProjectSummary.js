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
  onViewDetails
}) => {
  const { showError, showSuccess } = useApp();
  const { data: projectContext, isLoading: contextLoading } = useProjectContext(task?.task_id);

  const isProcessing = task?.status === 'pending' || task?.status === 'processing';
  const stats = projectContext?.stats || {};
  const context = projectContext?.context || {};

  // Calculate totals from various sources
  const totalTasks = stats.total_tasks || taskTree?.tasks?.length || task?.children_count || 0;
  const totalEvents = stats.total_events || task?.metadata?.extracted_events?.length || 0;
  const totalCommands = stats.total_commands || task?.metadata?.commands?.length || 0;
  const totalReadModels = stats.total_read_models || task?.metadata?.read_models?.length || 0;
  const totalChapters = task?.metadata?.chapters?.length || 0;
  const totalStoryPoints = calculateStoryPoints(taskTree);

  // Get tech stack from context or task metadata
  const techStack = context?.tech_stack || task?.metadata?.tech_stack || {};
  const technologies = extractTechnologies(techStack);

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
          context={projectContext}
          contextLoading={contextLoading}
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
                icon="🎯"
                onClick={() => onViewDetails?.('subtasks')}
              />
              <StatCard
                value={totalChapters}
                label="Chapters"
                icon="📖"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalEvents}
                label="Events"
                icon="⚡"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalCommands}
                label="Commands"
                icon="📝"
                onClick={() => onViewDetails?.('event-model')}
              />
              <StatCard
                value={totalReadModels}
                label="Read Models"
                icon="📊"
                onClick={() => onViewDetails?.('schemas')}
              />
              <StatCard
                value={totalStoryPoints}
                label="Story Points"
                icon="📈"
                subtitle={estimateSprints(totalStoryPoints)}
              />
            </div>
          </div>

          {/* Tech Stack */}
          {technologies.length > 0 && (
            <div style={styles.techSection}>
              <Text style={styles.techLabel}>Tech Stack:</Text>
              <div style={styles.techTags}>
                {technologies.map((tech, i) => (
                  <Badge key={i} variant="secondary" style={styles.techBadge}>
                    {tech}
                  </Badge>
                ))}
              </div>
            </div>
          )}

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
const ProcessingStatus = ({ task, context, contextLoading }) => {
  const stages = [
    { key: 'analyzing', label: 'Analyzing', icon: '🔍' },
    { key: 'decomposing', label: 'Decomposing', icon: '🎯' },
    { key: 'event_modeling', label: 'Event Modeling', icon: '⚡' },
    { key: 'finalizing', label: 'Finalizing', icon: '✨' },
  ];

  // Determine current stage based on context data
  const currentStage = determineCurrentStage(context);
  const currentStageIndex = stages.findIndex(s => s.key === currentStage);

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

      {/* Show what we have so far */}
      {context?.context && Object.keys(context.context).length > 0 && (
        <div style={styles.progressPreview}>
          <Text style={styles.progressPreviewLabel}>Found so far:</Text>
          <div style={styles.progressPreviewStats}>
            {context.stats?.total_tasks > 0 && (
              <Badge variant="info">{context.stats.total_tasks} tasks</Badge>
            )}
            {context.stats?.total_epics > 0 && (
              <Badge variant="info">{context.stats.total_epics} epics</Badge>
            )}
            {context.stats?.has_tech_stack && (
              <Badge variant="success">Tech stack identified</Badge>
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
  if (!taskTree?.tasks) return 0;

  let total = 0;
  Object.values(taskTree.tasks).forEach(task => {
    if (task.story_points) {
      total += task.story_points;
    } else if (task.is_atomic) {
      total += 2; // Default estimate for atomic tasks
    }
  });
  return total;
}

function estimateSprints(points) {
  if (!points) return '';
  const sprints = Math.ceil(points / 20); // Assume 20 points per sprint
  return `~${sprints} sprint${sprints !== 1 ? 's' : ''}`;
}

function extractTechnologies(techStack) {
  const techs = [];

  if (typeof techStack === 'object' && techStack !== null) {
    Object.entries(techStack).forEach(([category, value]) => {
      if (typeof value === 'string') {
        techs.push(value);
      } else if (typeof value === 'object' && value !== null) {
        Object.keys(value).forEach(tech => techs.push(tech));
      }
    });
  }

  // Return unique, top 6
  return [...new Set(techs)].slice(0, 6);
}

function determineCurrentStage(context) {
  if (!context?.context) return 'analyzing';

  const data = context.context;

  if (data.event_model || data.commands || data.extracted_events) {
    return 'finalizing';
  }
  if (data.decomposed_tasks) {
    return 'event_modeling';
  }
  if (data.epics_and_stories || data.tech_stack) {
    return 'decomposing';
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
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.medium,
    fontStyle: 'italic',
    color: 'var(--color-text)',
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

  // Tech section
  techSection: {
    marginBottom: tokens.spacing[6],
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid var(--color-border)`,
  },
  techLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  techTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },
  techBadge: {
    fontSize: tokens.typography.fontSize.sm[0],
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

/**
 * ProjectSummary - High-level overview of a generated project plan
 *
 * Shows the transformation from prompt to structured project:
 * - Original prompt
 * - Processing status/progress
 * - Summary stats (tasks, events, commands, story points)
 * - Tech stack
 * - Quick actions (export, refine, generate code)
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Text,
  LoadingSpinner,
  tokens,
} from '../design-system';
import { useProjectContext } from '../hooks/api/useProjectContext';
import LiveActivityFeed from './LiveActivityFeed';
import TechStackSelectionModal from './TechStackSelectionModal';
import CodeGenerationProgress from './CodeGenerationProgress';
import apiClient from '../services/unifiedApiClient';

const ProjectSummary = ({
  task,
  taskTree,
  onRefine,
  onExport,
  onResume
}) => {
  const { data: projectContext, isLoading: contextLoading } = useProjectContext(task?.task_id);
  const isProcessing = task?.status === 'submitted' || task?.status === 'processing';

  // Code generation state
  const [showTechStackModal, setShowTechStackModal] = useState(false);
  const [showGenerationProgress, setShowGenerationProgress] = useState(false);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [existingGeneration, setExistingGeneration] = useState(null);
  const [loadingGeneration, setLoadingGeneration] = useState(true);

  // Check if project has event model (required for code generation)
  const hasEventModel = task?.metadata?.extracted_events?.length > 0 ||
                        task?.metadata?.commands?.length > 0 ||
                        projectContext?.context?.event_model;

  // Check for existing generation on mount
  useEffect(() => {
    if (task?.task_id) {
      checkExistingGeneration();
    }
  }, [task?.task_id]);

  const checkExistingGeneration = async () => {
    setLoadingGeneration(true);
    try {
      const status = await apiClient.getGenerationStatus(task.task_id);
      setExistingGeneration(status);
      // If generation is in progress, show progress view
      if (['pending', 'initializing', 'generating', 'integrating'].includes(status?.status)) {
        setShowGenerationProgress(true);
      }
    } catch (err) {
      // 404 means no generation exists, which is fine
      if (err.response?.status !== 404) {
        console.error('Failed to check generation status:', err);
      }
      setExistingGeneration(null);
    } finally {
      setLoadingGeneration(false);
    }
  };

  const handleGenerateCode = () => {
    setShowTechStackModal(true);
  };

  const handleGenerationStarted = (status) => {
    setGenerationStatus(status);
    setExistingGeneration(status);
    setShowTechStackModal(false);
    setShowGenerationProgress(true);
  };

  const handleGenerationComplete = (result) => {
    setGenerationStatus(result);
    setExistingGeneration(result);
  };

  const handleCloseProgress = () => {
    setShowGenerationProgress(false);
    // Refresh the generation status
    checkExistingGeneration();
  };

  return (
    <>
      <Card style={styles.container}>
        {/* Original Prompt - Dramatically Enhanced */}
        <div style={styles.promptSection}>
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2], marginBottom: tokens.spacing[3] }}>
            <span style={{ fontSize: '24px' }}>💭</span>
            <Text style={styles.promptLabel}>Your Project Vision</Text>
          </div>
          <div style={styles.promptText} className="custom-scrollbar">
            <Text style={{ fontStyle: 'italic', fontSize: tokens.typography.fontSize.lg[0] }}>
              "{task?.description}"
            </Text>
          </div>
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

        {/* Code Generation Progress (inline when active) */}
        {showGenerationProgress && (
          <div style={styles.generationProgressSection}>
            <CodeGenerationProgress
              projectId={task?.task_id}
              onComplete={handleGenerationComplete}
              onClose={handleCloseProgress}
            />
          </div>
        )}

        {/* Existing Generation Status (completed/failed/cancelled) */}
        {!isProcessing && !showGenerationProgress && existingGeneration && (
          <ExistingGenerationStatus
            generation={existingGeneration}
            onRegenerate={handleGenerateCode}
            onViewProgress={() => setShowGenerationProgress(true)}
          />
        )}

        {/* Actions (when not processing) */}
        {!isProcessing && !showGenerationProgress && (
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
            {hasEventModel && !existingGeneration && (
              <Button
                variant="primary"
                size="md"
                onClick={handleGenerateCode}
              >
                Generate Code
              </Button>
            )}
          </div>
        )}
      </Card>

      {/* Tech Stack Selection Modal */}
      <TechStackSelectionModal
        isOpen={showTechStackModal}
        onClose={() => setShowTechStackModal(false)}
        projectId={task?.task_id}
        onGenerationStarted={handleGenerationStarted}
      />
    </>
  );
};

/**
 * Processing status with progress indicators
 */
const ProcessingStatus = ({ task, taskTree, context, contextLoading, onResume }) => {
  const stages = [
    { key: 'analyzing', label: 'Analysis', icon: '🔍' },
    { key: 'decomposing', label: 'Decomposition', icon: '🎯' },
    { key: 'event_modeling', label: 'Discovery', icon: '⚡' },
    { key: 'finalizing', label: 'Finalization', icon: '✨' },
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
          <Text style={styles.liveStatLabel}>TASKS</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.context?.epics?.length || task?.metadata?.epics?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>EPICS</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.context?.user_stories?.length || task?.metadata?.user_stories?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>STORIES</Text>
        </div>
        <div style={styles.liveStat}>
          <Text style={styles.liveStatValue}>
            {task?.metadata?.swimlanes?.length || 0}
          </Text>
          <Text style={styles.liveStatLabel}>FEATURES</Text>
        </div>
      </div>

      {/* Live Activity Feed */}
      <LiveActivityFeed taskId={task?.task_id} />
    </div>
  );
};

/**
 * Shows existing generation status (complete/failed/cancelled)
 */
const ExistingGenerationStatus = ({ generation, onRegenerate, onViewProgress }) => {
  const [copied, setCopied] = React.useState(false);

  const isComplete = generation?.status === 'complete';
  const isFailed = generation?.status === 'failed';
  const isCancelled = generation?.status === 'cancelled';
  const isInProgress = ['pending', 'initializing', 'generating', 'integrating'].includes(generation?.status);

  // Convert internal URL to external
  const getExternalUrl = (url) => url?.replace('http://gitea:3000', 'http://localhost:3001').replace(/\.git$/, '');
  const getCloneUrl = (url) => url?.replace('http://gitea:3000', 'http://localhost:3001');

  const handleCopy = async () => {
    const cloneCmd = `git clone ${getCloneUrl(generation.repo_url)}`;
    try {
      await navigator.clipboard.writeText(cloneCmd);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (isInProgress) {
    return (
      <div style={{
        ...styles.existingGenSection,
        borderColor: 'rgba(59, 130, 246, 0.3)',
      }}>
        <div style={styles.existingGenHeader}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            borderRadius: tokens.borderRadius.full,
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
          }}>
            <LoadingSpinner size="sm" />
          </div>
          <Text style={styles.existingGenTitle}>Code generation in progress...</Text>
        </div>
        <Button variant="outline" size="sm" onClick={onViewProgress}>
          View Progress
        </Button>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div style={{
        ...styles.existingGenSection,
        borderColor: 'rgba(34, 197, 94, 0.3)',
      }}>
        <div style={styles.existingGenHeader}>
          <span style={styles.existingGenIcon}>✓</span>
          <Text style={styles.existingGenTitle}>Code Generated</Text>
          <span style={styles.techStackBadge}>{generation.tech_stack}</span>
        </div>

        <div style={styles.repoInfoRow}>
          <a
            href={getExternalUrl(generation.repo_url)}
            target="_blank"
            rel="noopener noreferrer"
            style={styles.repoLinkInline}
            onMouseEnter={(e) => e.currentTarget.style.color = tokens.colors.primary[300]}
            onMouseLeave={(e) => e.currentTarget.style.color = tokens.colors.primary[400]}
          >
            View Repository →
          </a>
          <div 
            style={styles.cloneCommandInline}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.primary[500]}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--color-border)'}
          >
            <code style={styles.cloneCodeInline}>
              git clone {getCloneUrl(generation.repo_url)}
            </code>
            <button 
              style={{
                ...styles.copyButtonInline,
                backgroundColor: copied ? 'rgba(34, 197, 94, 0.1)' : 'transparent',
                color: copied ? tokens.colors.success[400] : tokens.colors.primary[400],
              }}
              onClick={handleCopy}
              onMouseEnter={(e) => {
                if (!copied) {
                  e.currentTarget.style.backgroundColor = 'var(--color-surface)';
                }
              }}
              onMouseLeave={(e) => {
                if (!copied) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>

        <div style={styles.existingGenActions}>
          <Button variant="outline" size="sm" onClick={onRegenerate}>
            Regenerate with Different Stack
          </Button>
        </div>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div style={{
        ...styles.existingGenSection,
        borderColor: 'rgba(239, 68, 68, 0.3)',
      }}>
        <div style={styles.existingGenHeader}>
          <span style={styles.existingGenIconError}>✕</span>
          <Text style={styles.existingGenTitleError}>Generation Failed</Text>
        </div>
        {generation.last_error && (
          <Text style={styles.errorMessage}>{generation.last_error}</Text>
        )}
        <div style={styles.existingGenActions}>
          <Button variant="outline" size="sm" onClick={onViewProgress}>
            View Details
          </Button>
          <Button variant="primary" size="sm" onClick={onRegenerate}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (isCancelled) {
    return (
      <div style={styles.existingGenSection}>
        <div style={styles.existingGenHeader}>
          <span style={styles.existingGenIconMuted}>&#9898;</span>
          <Text style={styles.existingGenTitle}>Generation Cancelled</Text>
        </div>
        <div style={styles.existingGenActions}>
          <Button variant="primary" size="sm" onClick={onRegenerate}>
            Start New Generation
          </Button>
        </div>
      </div>
    );
  }

  return null;
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
    padding: tokens.spacing[8],
    marginBottom: tokens.spacing[8],
    background: 'var(--color-surface)',
    borderRadius: tokens.borderRadius['2xl'],
    border: '1px solid var(--color-border)',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
  },

  // Prompt section
  promptSection: {
    marginBottom: tokens.spacing[8],
    padding: tokens.spacing[6],
    background: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.xl,
    border: '1px solid var(--color-border)',
  },
  promptLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.primary[400],
    fontWeight: tokens.typography.fontWeight.semibold,
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    marginBottom: tokens.spacing[3],
  },
  promptText: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflowY: 'auto',
    lineHeight: 1.6,
  },

  // Processing section
  processingSection: {
    padding: tokens.spacing[6],
    background: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.xl,
    border: '1px solid var(--color-border)',
    position: 'relative',
    overflow: 'hidden',
  },
  processingHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[6],
  },
  processingTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  processingText: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  processingSubtext: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  liveStatsContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: tokens.spacing[4],
    marginBottom: tokens.spacing[6],
  },
  liveStat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: tokens.spacing[5],
    background: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
    transition: 'all 0.2s ease',
  },
  liveStatValue: {
    fontSize: '40px',
    fontWeight: tokens.typography.fontWeight.bold,
    color: 'var(--color-text)',
    lineHeight: 1,
  },
  liveStatLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[2],
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
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
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: tokens.spacing[4],
    marginBottom: tokens.spacing[6],
  },
  stageItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  stageIndicator: {
    width: '72px',
    height: '72px',
    borderRadius: tokens.borderRadius.full,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '32px',
    transition: 'all 0.3s ease',
    border: '3px solid transparent',
  },
  stageComplete: {
    background: 'linear-gradient(135deg, #22C55E 0%, #16A34A 100%)',
    color: 'white',
    boxShadow: '0 8px 24px rgba(34, 197, 94, 0.5), 0 0 0 4px rgba(34, 197, 94, 0.2)',
    transform: 'scale(1.05)',
  },
  stageCurrent: {
    background: tokens.colors.primary[400],
    color: 'white',
    animation: 'stagePulse 2s ease-in-out infinite',
    boxShadow: `0 4px 16px rgba(255, 140, 26, 0.4)`,
    transform: 'scale(1.05)',
  },
  stagePending: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    color: 'var(--color-text-muted)',
    border: '3px dashed var(--color-border)',
    opacity: 0.5,
  },
  stageLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    transition: 'color 0.3s ease',
  },
  stageLabelCurrent: {
    color: tokens.colors.primary[400],
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  stageLabelPending: {
    color: 'var(--color-text-muted)',
  },
  // Actions section
  actionsRow: {
    display: 'flex',
    gap: tokens.spacing[4],
    justifyContent: 'flex-start',
    paddingTop: tokens.spacing[6],
    marginTop: tokens.spacing[6],
    borderTop: '1px solid var(--color-border)',
  },
  // Code generation progress
  generationProgressSection: {
    marginTop: tokens.spacing[6],
    borderTop: '1px solid var(--color-border)',
    paddingTop: tokens.spacing[6],
  },

  // Existing generation status
  existingGenSection: {
    padding: tokens.spacing[6],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[4],
    border: '1px solid var(--color-border)',
    transition: 'all 0.3s ease',
  },
  existingGenHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[4],
  },
  existingGenIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: 'rgba(34, 197, 94, 0.1)',
    color: tokens.colors.success[500],
    fontSize: '18px',
    fontWeight: 'bold',
  },
  existingGenIconError: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    color: tokens.colors.error[500],
    fontSize: '18px',
    fontWeight: 'bold',
  },
  existingGenIconMuted: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: 'var(--color-neutral-800)',
    color: 'var(--color-text-muted)',
    fontSize: '16px',
  },
  existingGenTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  existingGenTitleError: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.error[500],
  },
  techStackBadge: {
    fontSize: tokens.typography.fontSize.xs[0],
    backgroundColor: 'var(--color-surface)',
    color: tokens.colors.primary[400],
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.full,
    fontWeight: tokens.typography.fontWeight.semibold,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    border: '1px solid var(--color-border)',
  },
  repoInfoRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[4],
  },
  repoLinkInline: {
    color: tokens.colors.primary[400],
    textDecoration: 'none',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    transition: 'color 0.2s ease',
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  cloneCommandInline: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: 'var(--color-neutral-900)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
    overflow: 'hidden',
    transition: 'border-color 0.2s ease',
  },
  cloneCodeInline: {
    flex: 1,
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: 'var(--font-mono)',
    color: 'var(--color-text)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  copyButtonInline: {
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    backgroundColor: 'transparent',
    border: 'none',
    borderLeft: '1px solid var(--color-border)',
    color: tokens.colors.primary[400],
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  existingGenActions: {
    display: 'flex',
    gap: tokens.spacing[3],
  },
  errorMessage: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.error[400],
    marginBottom: tokens.spacing[4],
    padding: tokens.spacing[3],
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid rgba(239, 68, 68, 0.2)',
  },
};

export default ProjectSummary;

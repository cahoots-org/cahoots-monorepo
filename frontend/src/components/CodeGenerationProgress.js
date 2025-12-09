/**
 * CodeGenerationProgress - Displays real-time code generation progress
 *
 * Features:
 * - Progress bar with percentage
 * - Current task being processed (with description)
 * - List of completed/failed/blocked tasks
 * - Live WebSocket updates
 * - Actions: Cancel, Retry, Keep Trying
 */
import React, { useState, useEffect } from 'react';
import {
  Button,
  LoadingSpinner,
  tokens,
} from '../design-system';
import { useWebSocket } from '../contexts/WebSocketContext';
import apiClient from '../services/unifiedApiClient';

const CodeGenerationProgress = ({
  projectId,
  onComplete,
  onClose,
}) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const { lastMessage } = useWebSocket();

  // Fetch initial status
  useEffect(() => {
    fetchStatus();
  }, [projectId]);

  // Handle WebSocket messages for real-time updates
  useEffect(() => {
    if (!lastMessage) return;

    const { type, project_id } = lastMessage;
    if (project_id !== projectId) return;

    // Handle code generation events
    if (type?.startsWith('codegen.') || type?.startsWith('codegen:')) {
      // Update status from WebSocket data
      setStatus(prev => ({
        ...prev,
        status: lastMessage.status || prev?.status,
        progress_percent: lastMessage.progress_percent ?? lastMessage.progress ?? prev?.progress_percent,
        // Support both task and slice terminology
        completed_tasks: lastMessage.completed_tasks ?? lastMessage.completed_slices ?? prev?.completed_tasks,
        total_tasks: lastMessage.total_tasks ?? lastMessage.total_slices ?? prev?.total_tasks,
        current_task: lastMessage.task_description || lastMessage.current_slices?.[0] || prev?.current_task,
        last_error: lastMessage.error || prev?.last_error,
      }));

      // Handle completion
      if (type === 'codegen.completed' || type === 'codegen:generation_complete') {
        onComplete?.(lastMessage);
      }
    }
  }, [lastMessage, projectId, onComplete]);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getGenerationStatus(projectId);
      setStatus(response);
      setError(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('No generation in progress');
      } else {
        setError(err.userMessage || 'Failed to fetch status');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await apiClient.cancelGeneration(projectId);
      await fetchStatus();
    } catch (err) {
      setError(err.userMessage || 'Failed to cancel generation');
    } finally {
      setCancelling(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await apiClient.retryGeneration(projectId);
      await fetchStatus();
    } catch (err) {
      setError(err.userMessage || 'Failed to retry generation');
    } finally {
      setRetrying(false);
    }
  };

  const handleKeepTrying = async () => {
    try {
      await apiClient.addGenerationRetries(projectId);
      await fetchStatus();
    } catch (err) {
      setError(err.userMessage || 'Failed to add retries');
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingContainer}>
          <LoadingSpinner size="sm" />
          <span style={styles.loadingText}>Loading...</span>
        </div>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div style={styles.container}>
        <div style={styles.errorContainer}>
          <span style={styles.errorIcon}>!</span>
          <span style={styles.errorText}>{error}</span>
          <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
        </div>
      </div>
    );
  }

  const isInProgress = ['pending', 'initializing', 'generating', 'integrating'].includes(status?.status);
  const isComplete = status?.status === 'complete';
  const isFailed = status?.status === 'failed';
  const isCancelled = status?.status === 'cancelled';

  // Compact inline layout
  return (
    <div style={styles.container}>
      {/* In Progress - compact inline */}
      {isInProgress && (
        <div style={styles.inProgressRow}>
          <div style={styles.progressInfo}>
            <LoadingSpinner size="sm" />
            <div style={styles.progressTextContainer}>
              <span style={styles.statusText}>
                Building ({status?.tech_stack}) - {status?.completed_tasks || status?.completed_slices || 0}/{status?.total_tasks || status?.total_slices || 0} tasks
              </span>
              {status?.current_task && (
                <span style={styles.currentTask} title={status.current_task}>
                  {status.current_task.length > 50 ? status.current_task.substring(0, 50) + '...' : status.current_task}
                </span>
              )}
            </div>
          </div>
          <div style={styles.progressBarContainer}>
            <div style={styles.progressBarBackground}>
              <div style={{ ...styles.progressBarFill, width: `${status?.progress_percent || 0}%` }} />
            </div>
            <span style={styles.progressPercent}>{Math.round(status?.progress_percent || 0)}%</span>
          </div>
          <Button variant="outline" size="sm" onClick={handleCancel} disabled={cancelling}>
            Cancel
          </Button>
        </div>
      )}

      {/* Complete - compact inline */}
      {isComplete && (
        <div style={styles.completeRow}>
          <span style={styles.successIcon}>✓</span>
          <span style={styles.statusText}>
            Code generated ({status?.tech_stack}) - {status?.completed_tasks || status?.completed_slices} tasks
          </span>
          {status?.repo_url && <RepoActions repoUrl={status.repo_url} />}
          <Button variant="outline" size="sm" onClick={onClose}>Done</Button>
        </div>
      )}

      {/* Failed - compact inline */}
      {isFailed && (
        <div style={styles.failedRow}>
          <span style={styles.failedIcon}>!</span>
          <span style={styles.statusText}>
            Generation failed{status?.last_error ? `: ${status.last_error}` : ''}
          </span>
          {status?.can_retry ? (
            <Button variant="primary" size="sm" onClick={handleRetry} disabled={retrying}>
              {retrying ? 'Retrying...' : 'Retry'}
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={handleKeepTrying}>+3 Retries</Button>
          )}
        </div>
      )}

      {/* Cancelled - compact inline */}
      {isCancelled && (
        <div style={styles.cancelledRow}>
          <span style={styles.cancelledIcon}>○</span>
          <span style={styles.statusText}>Generation cancelled</span>
          <Button variant="primary" size="sm" onClick={onClose}>Done</Button>
        </div>
      )}
    </div>
  );
};

// Helper to convert internal repo URL to external URL
const getExternalRepoUrl = (internalUrl) => {
  // Replace internal Docker URL with external localhost URL
  // http://gitea:3000/cahoots/repo.git -> http://localhost:3001/cahoots/repo
  return internalUrl
    .replace('http://gitea:3000', 'http://localhost:3001')
    .replace(/\.git$/, '');
};

// Helper to get clone URL
const getCloneUrl = (internalUrl) => {
  // Replace internal Docker URL with external localhost URL for cloning
  return internalUrl.replace('http://gitea:3000', 'http://localhost:3001');
};

// Repo actions component - compact inline
const RepoActions = ({ repoUrl }) => {
  const [copied, setCopied] = React.useState(false);
  const externalUrl = getExternalRepoUrl(repoUrl);
  const cloneUrl = getCloneUrl(repoUrl);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`git clone ${cloneUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div style={styles.repoActions}>
      <a href={externalUrl} target="_blank" rel="noopener noreferrer" style={styles.repoLink}>
        View Repo
      </a>
      <button style={styles.copyBtn} onClick={handleCopy}>
        {copied ? 'Copied!' : 'Copy Clone URL'}
      </button>
    </div>
  );
};

const styles = {
  // Main container - compact
  container: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
  },
  // Loading state
  loadingContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[4],
    gap: tokens.spacing[3],
  },
  loadingText: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },
  // Error state
  errorContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[3],
  },
  errorIcon: {
    color: tokens.colors.error[500],
    fontSize: '16px',
  },
  errorText: {
    color: tokens.colors.error[600],
    fontSize: tokens.typography.fontSize.sm[0],
    flex: 1,
  },
  // Compact row layouts
  inProgressRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[4],
    flexWrap: 'wrap',
  },
  completeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    flexWrap: 'wrap',
  },
  failedRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    flexWrap: 'wrap',
  },
  cancelledRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  // Status text
  statusText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    flex: 1,
    minWidth: '150px',
  },
  // Progress info (spinner + text)
  progressInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flex: 1,
    minWidth: '200px',
  },
  progressTextContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  currentTask: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
  // Compact progress bar
  progressBarContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    minWidth: '120px',
    maxWidth: '200px',
  },
  progressBarBackground: {
    flex: 1,
    height: '6px',
    backgroundColor: 'var(--color-bg-tertiary)',
    borderRadius: tokens.borderRadius.full,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: tokens.colors.primary[500],
    borderRadius: tokens.borderRadius.full,
    transition: 'width 0.3s ease',
  },
  progressPercent: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    minWidth: '36px',
  },
  // Icons
  successIcon: {
    color: tokens.colors.success[500],
    fontSize: '18px',
    fontWeight: 'bold',
  },
  failedIcon: {
    color: tokens.colors.error[500],
    fontSize: '18px',
    fontWeight: 'bold',
  },
  cancelledIcon: {
    color: 'var(--color-text-muted)',
    fontSize: '16px',
  },
  // Repo actions - inline
  repoActions: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  repoLink: {
    color: tokens.colors.primary[500],
    textDecoration: 'none',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  copyBtn: {
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    backgroundColor: 'transparent',
    border: `1px solid ${tokens.colors.primary[500]}`,
    borderRadius: tokens.borderRadius.md,
    color: tokens.colors.primary[500],
    fontSize: tokens.typography.fontSize.xs[0],
    cursor: 'pointer',
  },
};

export default CodeGenerationProgress;

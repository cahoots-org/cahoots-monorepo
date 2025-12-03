/**
 * RefineModal - Smart refinement modal for project plans
 *
 * Flow:
 * 1. User provides feedback (chips + text)
 * 2. Shows processing state with live status
 * 3. Shows diff of changes for review
 * 4. User can accept or continue refining
 */
import React, { useState } from 'react';
import {
  Modal,
  Button,
  Text,
  Badge,
  LoadingSpinner,
  tokens,
} from '../design-system';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/unifiedApiClient';

// Quick feedback options for common refinements
const FEEDBACK_CHIPS = [
  { id: 'more-detail', label: 'More detail needed', icon: '🔍' },
  { id: 'too-complex', label: 'Too complex', icon: '📉' },
  { id: 'missing-features', label: 'Missing features', icon: '➕' },
  { id: 'wrong-tech', label: 'Wrong tech stack', icon: '🔧' },
  { id: 'scope-too-big', label: 'Scope too big', icon: '✂️' },
  { id: 'scope-too-small', label: 'Scope too small', icon: '📈' },
  { id: 'missing-security', label: 'Missing security', icon: '🔒' },
  { id: 'missing-testing', label: 'Missing testing', icon: '🧪' },
];

// Change type styling
const CHANGE_STYLES = {
  add_chapter: { icon: '📗', color: tokens.colors.success[500], label: 'Add Chapter' },
  remove_chapter: { icon: '📕', color: tokens.colors.error[500], label: 'Remove Chapter' },
  modify_chapter: { icon: '📘', color: tokens.colors.primary[500], label: 'Modify Chapter' },
  add_slice: { icon: '➕', color: tokens.colors.success[500], label: 'Add Slice' },
  remove_slice: { icon: '➖', color: tokens.colors.error[500], label: 'Remove Slice' },
  modify_slice: { icon: '✏️', color: tokens.colors.primary[500], label: 'Modify Slice' },
  add_event: { icon: '⚡', color: tokens.colors.success[500], label: 'Add Event' },
  add_command: { icon: '🎯', color: tokens.colors.success[500], label: 'Add Command' },
  general: { icon: '📝', color: tokens.colors.neutral[500], label: 'General' },
};

const RefineModal = ({
  isOpen,
  onClose,
  task,
  taskTree,
  onRefineComplete,
}) => {
  const { showSuccess, showError } = useApp();

  // Modal state: 'input' | 'processing' | 'review'
  const [modalState, setModalState] = useState('input');
  const [selectedChips, setSelectedChips] = useState([]);
  const [feedback, setFeedback] = useState('');
  const [processingStatus, setProcessingStatus] = useState('');
  const [refinementResult, setRefinementResult] = useState(null);

  const resetModal = () => {
    setModalState('input');
    setSelectedChips([]);
    setFeedback('');
    setProcessingStatus('');
    setRefinementResult(null);
  };

  const handleClose = () => {
    resetModal();
    onClose();
  };

  const toggleChip = (chipId) => {
    setSelectedChips(prev =>
      prev.includes(chipId)
        ? prev.filter(id => id !== chipId)
        : [...prev, chipId]
    );
  };

  const handleRefine = async () => {
    if (selectedChips.length === 0 && !feedback.trim()) {
      showError('Please provide some feedback');
      return;
    }

    setModalState('processing');
    setProcessingStatus('Analyzing your feedback...');

    try {
      // Build the refinement request
      const chipLabels = selectedChips.map(id =>
        FEEDBACK_CHIPS.find(c => c.id === id)?.label
      ).filter(Boolean);

      const refinementRequest = {
        feedback: feedback.trim(),
        quick_feedback: chipLabels,
        current_context: {
          description: task?.description,
          chapters: task?.metadata?.chapters?.map(c => ({
            name: c.name,
            description: c.description,
            slice_count: c.slices?.length || 0,
          })),
          event_count: task?.metadata?.extracted_events?.length || 0,
          command_count: task?.metadata?.commands?.length || 0,
          task_count: taskTree?.tasks ? Object.keys(taskTree.tasks).length : 0,
        },
      };

      setProcessingStatus('Generating refinements...');

      const response = await apiClient.post(
        `/tasks/${task.task_id}/refine`,
        refinementRequest
      );

      const data = response.data || response;

      setRefinementResult({
        changes: data.changes_made || [],
        summary: data.summary || 'Changes applied successfully',
        chaptersUpdated: data.chapters_updated || 0,
      });

      setModalState('review');
    } catch (error) {
      console.error('Refine error:', error);
      showError(error.response?.data?.detail || 'Failed to refine project');
      setModalState('input');
    }
  };

  const handleAcceptChanges = () => {
    showSuccess(refinementResult?.summary || 'Changes applied successfully');
    onRefineComplete?.();
    handleClose();
  };

  const handleContinueRefining = () => {
    // Keep result but go back to input
    setModalState('input');
    setSelectedChips([]);
    setFeedback('');
  };

  const handleStartOver = async () => {
    if (!window.confirm('This will regenerate everything from scratch. Are you sure?')) {
      return;
    }

    setModalState('processing');
    setProcessingStatus('Regenerating project plan...');

    try {
      await apiClient.post(`/tasks/${task.task_id}/reprocess`);
      showSuccess('Regenerating project plan from scratch...');
      onRefineComplete?.();
      handleClose();
    } catch (error) {
      console.error('Reprocess error:', error);
      showError(error.response?.data?.detail || 'Failed to regenerate project');
      setModalState('input');
    }
  };

  // Stats for display
  const chapterCount = task?.metadata?.chapters?.length || 0;
  const eventCount = task?.metadata?.extracted_events?.length || 0;
  const commandCount = task?.metadata?.commands?.length || 0;
  // Handle different taskTree structures: array, object, or fall back to children_count
  const taskCount = taskTree?.tasks
    ? (Array.isArray(taskTree.tasks) ? taskTree.tasks.length : Object.keys(taskTree.tasks).length)
    : (task?.children_count || 0);
  const storyCount = task?.context?.user_stories?.length || task?.metadata?.user_stories?.length || 0;
  const epicCount = task?.context?.epics?.length || task?.metadata?.epics?.length || 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        modalState === 'review'
          ? 'Review Changes'
          : modalState === 'processing'
          ? 'Refining Plan...'
          : 'Refine Project Plan'
      }
      size="lg"
    >
      <div style={styles.content}>
        {/* INPUT STATE */}
        {modalState === 'input' && (
          <>
            {/* Current Plan Summary */}
            <div style={styles.summarySection}>
              <Text style={styles.summaryLabel}>Current Plan</Text>
              <div style={styles.summaryStats}>
                <Badge variant="default">{epicCount} epics</Badge>
                <Badge variant="default">{storyCount} stories</Badge>
                <Badge variant="default">{taskCount} tasks</Badge>
                <Badge variant="default">{chapterCount} chapters</Badge>
                <Badge variant="default">{commandCount} commands</Badge>
                <Badge variant="default">{eventCount} events</Badge>
              </div>
            </div>

            {/* Quick Feedback Chips */}
            <div style={styles.section}>
              <label style={styles.label}>What needs improvement?</label>
              <div style={styles.chipGrid}>
                {FEEDBACK_CHIPS.map((chip) => (
                  <button
                    key={chip.id}
                    style={{
                      ...styles.chip,
                      ...(selectedChips.includes(chip.id) && styles.chipSelected),
                    }}
                    onClick={() => toggleChip(chip.id)}
                  >
                    <span style={styles.chipIcon}>{chip.icon}</span>
                    <span style={styles.chipLabel}>{chip.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Free-form Feedback */}
            <div style={styles.section}>
              <label style={styles.label}>Additional feedback</label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Describe what you'd like to change...

Examples:
- Add user authentication with OAuth
- Split the 'User Management' chapter into separate admin and user flows
- Remove the mobile app features, focus on web only
- Add more detail to the payment processing tasks"
                style={styles.textarea}
                rows={5}
              />
              <Text style={styles.hint}>
                Be specific about what to add, remove, or change. The AI will make targeted updates.
              </Text>
            </div>

            {/* Actions */}
            <div style={styles.actions}>
              <Button
                variant="ghost"
                onClick={handleStartOver}
                style={styles.startOverButton}
              >
                Start Over
              </Button>
              <div style={styles.primaryActions}>
                <Button variant="ghost" onClick={handleClose}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleRefine}
                  disabled={selectedChips.length === 0 && !feedback.trim()}
                >
                  Apply Changes
                </Button>
              </div>
            </div>
          </>
        )}

        {/* PROCESSING STATE */}
        {modalState === 'processing' && (
          <div style={styles.processingContainer}>
            <div style={styles.processingAnimation}>
              <LoadingSpinner size="lg" />
            </div>
            <Text style={styles.processingTitle}>{processingStatus}</Text>
            <Text style={styles.processingHint}>
              This usually takes 10-20 seconds
            </Text>

            {/* Show what feedback was given */}
            <div style={styles.feedbackSummary}>
              <Text style={styles.feedbackLabel}>Your feedback:</Text>
              <div style={styles.feedbackChips}>
                {selectedChips.map(id => {
                  const chip = FEEDBACK_CHIPS.find(c => c.id === id);
                  return chip ? (
                    <Badge key={id} variant="default">
                      {chip.icon} {chip.label}
                    </Badge>
                  ) : null;
                })}
              </div>
              {feedback.trim() && (
                <Text style={styles.feedbackText}>"{feedback.trim()}"</Text>
              )}
            </div>
          </div>
        )}

        {/* REVIEW STATE - Show diff */}
        {modalState === 'review' && refinementResult && (
          <>
            {/* Summary */}
            <div style={styles.reviewSummary}>
              <Text style={styles.reviewSummaryIcon}>✨</Text>
              <Text style={styles.reviewSummaryText}>
                {refinementResult.summary}
              </Text>
            </div>

            {/* Changes List */}
            <div style={styles.changesSection}>
              <Text style={styles.changesTitle}>
                {refinementResult.changes.length} change{refinementResult.changes.length !== 1 ? 's' : ''} made
              </Text>

              <div style={styles.changesList}>
                {refinementResult.changes.length === 0 ? (
                  <div style={styles.noChanges}>
                    <Text style={styles.noChangesText}>
                      No structural changes needed based on your feedback.
                    </Text>
                  </div>
                ) : (
                  refinementResult.changes.map((change, index) => {
                    const style = CHANGE_STYLES[change.type] || CHANGE_STYLES.general;
                    return (
                      <div key={index} style={styles.changeItem}>
                        <div style={styles.changeHeader}>
                          <span style={{ ...styles.changeIcon, color: style.color }}>
                            {style.icon}
                          </span>
                          <Badge
                            variant="default"
                            style={{ backgroundColor: `${style.color}20`, color: style.color }}
                          >
                            {style.label}
                          </Badge>
                          {change.target && (
                            <Text style={styles.changeTarget}>{change.target}</Text>
                          )}
                        </div>
                        <Text style={styles.changeDescription}>
                          {change.description}
                        </Text>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Actions */}
            <div style={styles.reviewActions}>
              <Button
                variant="ghost"
                onClick={handleContinueRefining}
              >
                Continue Refining
              </Button>
              <Button
                variant="primary"
                onClick={handleAcceptChanges}
              >
                Done
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};

const styles = {
  content: {
    padding: tokens.spacing[2],
    minHeight: '300px',
  },

  // Summary section
  summarySection: {
    backgroundColor: 'var(--color-bg-secondary)',
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[6],
  },
  summaryLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
    display: 'block',
  },
  summaryStats: {
    display: 'flex',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
  },

  section: {
    marginBottom: tokens.spacing[6],
  },

  label: {
    display: 'block',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[3],
  },

  chipGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },

  chip: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    backgroundColor: 'var(--color-bg-secondary)',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.full,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
  },
  chipSelected: {
    backgroundColor: tokens.colors.primary[500],
    borderColor: tokens.colors.primary[500],
    color: 'white',
  },
  chipIcon: {
    fontSize: '14px',
  },
  chipLabel: {
    fontWeight: tokens.typography.fontWeight.medium,
  },

  textarea: {
    width: '100%',
    padding: tokens.spacing[3],
    fontSize: tokens.typography.fontSize.base[0],
    fontFamily: 'inherit',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.lg,
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-text)',
    resize: 'vertical',
    lineHeight: 1.5,
  },

  hint: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[2],
    display: 'block',
  },

  actions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: tokens.spacing[4],
    borderTop: '1px solid var(--color-border)',
  },
  startOverButton: {
    color: 'var(--color-text-muted)',
  },
  primaryActions: {
    display: 'flex',
    gap: tokens.spacing[3],
  },

  // Processing state
  processingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    textAlign: 'center',
  },
  processingAnimation: {
    marginBottom: tokens.spacing[6],
  },
  processingTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[2],
  },
  processingHint: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[6],
  },
  feedbackSummary: {
    backgroundColor: 'var(--color-bg-secondary)',
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.lg,
    width: '100%',
    maxWidth: '400px',
  },
  feedbackLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
    display: 'block',
  },
  feedbackChips: {
    display: 'flex',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
    marginBottom: tokens.spacing[2],
  },
  feedbackText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    fontStyle: 'italic',
  },

  // Review state
  reviewSummary: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    backgroundColor: `${tokens.colors.success[500]}15`,
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[6],
    border: `1px solid ${tokens.colors.success[200]}`,
  },
  reviewSummaryIcon: {
    fontSize: '24px',
  },
  reviewSummaryText: {
    fontSize: tokens.typography.fontSize.base[0],
    color: 'var(--color-text)',
    lineHeight: 1.5,
  },

  changesSection: {
    marginBottom: tokens.spacing[6],
  },
  changesTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[3],
    display: 'block',
  },
  changesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
    maxHeight: '300px',
    overflowY: 'auto',
  },
  changeItem: {
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
  },
  changeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[2],
  },
  changeIcon: {
    fontSize: '16px',
  },
  changeTarget: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
  },
  changeDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    lineHeight: 1.5,
  },
  noChanges: {
    padding: tokens.spacing[6],
    textAlign: 'center',
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
  },
  noChangesText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },

  reviewActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[4],
    borderTop: '1px solid var(--color-border)',
  },
};

export default RefineModal;

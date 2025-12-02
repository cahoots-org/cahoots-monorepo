/**
 * RefineModal - Smart refinement modal for project plans
 *
 * Provides multiple ways to give feedback:
 * - Quick feedback chips for common refinements
 * - Free-form feedback text
 * - Specific element targeting (chapters, slices, tasks)
 *
 * Uses contextual LLM refinement instead of full regeneration
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

const RefineModal = ({
  isOpen,
  onClose,
  task,
  taskTree,
  onRefineComplete,
}) => {
  const { showSuccess, showError } = useApp();

  const [selectedChips, setSelectedChips] = useState([]);
  const [feedback, setFeedback] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [refinementStatus, setRefinementStatus] = useState(null);

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

    setIsRefining(true);
    setRefinementStatus('Analyzing your feedback...');

    try {
      // Build the refinement request
      const chipLabels = selectedChips.map(id =>
        FEEDBACK_CHIPS.find(c => c.id === id)?.label
      ).filter(Boolean);

      const refinementRequest = {
        feedback: feedback.trim(),
        quick_feedback: chipLabels,
        // Include current project context for incremental refinement
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

      setRefinementStatus('Refining project plan...');

      // Call the new refinement endpoint
      const response = await apiClient.post(
        `/tasks/${task.task_id}/refine`,
        refinementRequest
      );

      setRefinementStatus('Applying changes...');

      // The response contains what was changed
      const data = response.data || response;
      const summary = data.summary || 'Project plan refined successfully';

      showSuccess(summary);
      onRefineComplete?.();
      onClose();
    } catch (error) {
      console.error('Refine error:', error);
      showError(error.response?.data?.detail || 'Failed to refine project');
    } finally {
      setIsRefining(false);
      setRefinementStatus(null);
    }
  };

  const handleStartOver = async () => {
    if (!window.confirm('This will regenerate everything from scratch. Are you sure?')) {
      return;
    }

    setIsRefining(true);
    setRefinementStatus('Regenerating project plan...');

    try {
      await apiClient.post(`/tasks/${task.task_id}/reprocess`);
      showSuccess('Regenerating project plan from scratch...');
      onRefineComplete?.();
      onClose();
    } catch (error) {
      console.error('Reprocess error:', error);
      showError(error.response?.data?.detail || 'Failed to regenerate project');
    } finally {
      setIsRefining(false);
      setRefinementStatus(null);
    }
  };

  // Get summary of current project for context
  const chapterCount = task?.metadata?.chapters?.length || 0;
  const eventCount = task?.metadata?.extracted_events?.length || 0;
  const commandCount = task?.metadata?.commands?.length || 0;
  const taskCount = taskTree?.tasks ? Object.keys(taskTree.tasks).length - 1 : 0; // -1 to exclude root
  const storyCount = task?.context?.user_stories?.length || task?.metadata?.user_stories?.length || 0;
  const epicCount = task?.context?.epics?.length || task?.metadata?.epics?.length || 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Refine Project Plan"
      size="lg"
    >
      <div style={styles.content}>
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
                disabled={isRefining}
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
            disabled={isRefining}
          />
          <Text style={styles.hint}>
            Be specific about what to add, remove, or change. The AI will make targeted updates.
          </Text>
        </div>

        {/* Refinement Status */}
        {isRefining && (
          <div style={styles.statusSection}>
            <LoadingSpinner size="sm" />
            <Text style={styles.statusText}>{refinementStatus}</Text>
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <Button
            variant="ghost"
            onClick={handleStartOver}
            disabled={isRefining}
            style={styles.startOverButton}
          >
            Start Over
          </Button>
          <div style={styles.primaryActions}>
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={isRefining}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleRefine}
              loading={isRefining}
              disabled={selectedChips.length === 0 && !feedback.trim()}
            >
              {isRefining ? 'Refining...' : 'Apply Changes'}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  content: {
    padding: tokens.spacing[2],
  },

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
  },

  statusSection: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[4],
  },
  statusText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
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
};

export default RefineModal;

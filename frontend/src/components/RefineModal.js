/**
 * RefineModal - Modal for refining/regenerating the project plan
 *
 * Allows users to:
 * - Edit the original prompt
 * - Add additional context/requirements
 * - Choose what to regenerate (full, chapters only, event model only)
 */
import React, { useState } from 'react';
import {
  Modal,
  Button,
  Text,
  tokens,
} from '../design-system';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/unifiedApiClient';

const RefineModal = ({
  isOpen,
  onClose,
  task,
  onRefineComplete,
}) => {
  const { showSuccess, showError } = useApp();

  const [description, setDescription] = useState(task?.description || '');
  const [additionalContext, setAdditionalContext] = useState('');
  const [refineMode, setRefineMode] = useState('full');
  const [isRefining, setIsRefining] = useState(false);

  const handleRefine = async () => {
    if (!description.trim()) {
      showError('Please enter a description');
      return;
    }

    setIsRefining(true);

    try {
      // For now, we'll update the task description and trigger regeneration
      // In the future, this could be more granular

      if (refineMode === 'full') {
        // Update task description and regenerate everything
        await apiClient.patch(`/tasks/${task.task_id}`, {
          description: description.trim(),
          metadata: {
            ...task.metadata,
            additional_context: additionalContext.trim() || undefined,
            regenerated_at: new Date().toISOString(),
          },
        });

        // Trigger reprocessing
        await apiClient.post(`/tasks/${task.task_id}/reprocess`);

        showSuccess('Regenerating project plan...');
      } else if (refineMode === 'event-model') {
        // Just regenerate the event model
        await apiClient.post(`/events/generate-model/${task.task_id}`);
        showSuccess('Regenerating event model...');
      }

      onRefineComplete?.();
      onClose();
    } catch (error) {
      console.error('Refine error:', error);
      showError(error.response?.data?.detail || 'Failed to refine project');
    } finally {
      setIsRefining(false);
    }
  };

  const refineModes = [
    {
      id: 'full',
      label: 'Full Regeneration',
      description: 'Regenerate everything from scratch with the new description',
      icon: '🔄',
    },
    {
      id: 'event-model',
      label: 'Event Model Only',
      description: 'Keep tasks, regenerate commands, events, and read models',
      icon: '⚡',
    },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Refine Project Plan"
      size="lg"
    >
      <div style={styles.content}>
        {/* Description Editor */}
        <div style={styles.section}>
          <label style={styles.label}>Project Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what you want to build..."
            style={styles.textarea}
            rows={4}
          />
          <Text style={styles.hint}>
            Edit your original description to refine the generated plan
          </Text>
        </div>

        {/* Additional Context */}
        <div style={styles.section}>
          <label style={styles.label}>Additional Context (Optional)</label>
          <textarea
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            placeholder="Add any additional requirements, constraints, or preferences..."
            style={styles.textarea}
            rows={3}
          />
          <Text style={styles.hint}>
            Add details like: preferred technologies, must-have features, timeline constraints
          </Text>
        </div>

        {/* Refine Mode */}
        <div style={styles.section}>
          <label style={styles.label}>What to Regenerate</label>
          <div style={styles.modeGrid}>
            {refineModes.map((mode) => (
              <div
                key={mode.id}
                style={{
                  ...styles.modeCard,
                  ...(refineMode === mode.id && styles.modeCardSelected),
                }}
                onClick={() => setRefineMode(mode.id)}
              >
                <div style={styles.modeIcon}>{mode.icon}</div>
                <div style={styles.modeInfo}>
                  <Text style={styles.modeLabel}>{mode.label}</Text>
                  <Text style={styles.modeDescription}>{mode.description}</Text>
                </div>
                <div style={styles.modeRadio}>
                  <div style={{
                    ...styles.radioOuter,
                    ...(refineMode === mode.id && styles.radioOuterSelected),
                  }}>
                    {refineMode === mode.id && <div style={styles.radioInner} />}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Warning */}
        {refineMode === 'full' && (
          <div style={styles.warning}>
            <Text style={styles.warningText}>
              Full regeneration will replace all current tasks, chapters, and event model data.
              This action cannot be undone.
            </Text>
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
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
          >
            {isRefining ? 'Refining...' : 'Refine Plan'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  content: {
    padding: tokens.spacing[2],
  },

  section: {
    marginBottom: tokens.spacing[6],
  },

  label: {
    display: 'block',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[2],
  },

  textarea: {
    width: '100%',
    padding: tokens.spacing[3],
    fontSize: tokens.typography.fontSize.base[0],
    fontFamily: 'inherit',
    borderRadius: tokens.borderRadius.md,
    border: `1px solid var(--color-border)`,
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-text)',
    resize: 'vertical',
    outline: 'none',
    transition: 'border-color 0.2s ease',
  },

  hint: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },

  modeGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  modeCard: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.lg,
    border: `2px solid var(--color-border)`,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },

  modeCardSelected: {
    borderColor: tokens.colors.primary[500],
    backgroundColor: `${tokens.colors.primary[500]}10`,
  },

  modeIcon: {
    fontSize: '24px',
    width: '40px',
    textAlign: 'center',
  },

  modeInfo: {
    flex: 1,
  },

  modeLabel: {
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[1],
  },

  modeDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },

  modeRadio: {
    flexShrink: 0,
  },

  radioOuter: {
    width: '20px',
    height: '20px',
    borderRadius: tokens.borderRadius.full,
    border: `2px solid var(--color-border)`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
  },

  radioOuterSelected: {
    borderColor: tokens.colors.primary[500],
  },

  radioInner: {
    width: '10px',
    height: '10px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: tokens.colors.primary[500],
  },

  warning: {
    padding: tokens.spacing[4],
    backgroundColor: `${tokens.colors.warning[500]}15`,
    borderRadius: tokens.borderRadius.md,
    marginBottom: tokens.spacing[6],
  },

  warningText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.warning[700],
  },

  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid var(--color-border)`,
  },
};

export default RefineModal;

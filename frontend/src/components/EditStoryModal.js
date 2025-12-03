/**
 * EditStoryModal - Modal for editing user story details
 */
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Text,
  Badge,
  tokens,
} from '../design-system';

const EditStoryModal = ({
  isOpen,
  onClose,
  story,
  epicName,
  onSave,
  isLoading = false,
}) => {
  const [title, setTitle] = useState('');
  const [actor, setActor] = useState('');
  const [action, setAction] = useState('');
  const [benefit, setBenefit] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [storyPoints, setStoryPoints] = useState('');

  // Reset form when story changes
  useEffect(() => {
    if (story) {
      setTitle(story.title || story.name || '');
      setActor(story.actor || story.as_a || '');
      setAction(story.action || story.i_want || '');
      setBenefit(story.benefit || story.so_that || '');
      setAcceptanceCriteria(
        Array.isArray(story.acceptance_criteria)
          ? story.acceptance_criteria.join('\n')
          : story.acceptance_criteria || ''
      );
      setStoryPoints(story.story_points?.toString() || story.points?.toString() || '');
    }
  }, [story]);

  const handleSave = () => {
    if (!title.trim()) return;

    const criteriaArray = acceptanceCriteria
      .split('\n')
      .map(c => c.trim())
      .filter(Boolean);

    onSave({
      ...story,
      title: title.trim(),
      name: title.trim(),
      actor: actor.trim(),
      as_a: actor.trim(),
      action: action.trim(),
      i_want: action.trim(),
      benefit: benefit.trim(),
      so_that: benefit.trim(),
      acceptance_criteria: criteriaArray,
      story_points: storyPoints ? parseInt(storyPoints, 10) : undefined,
    });
  };

  const hasChanges = story && (
    title.trim() !== (story.title || story.name || '') ||
    actor.trim() !== (story.actor || story.as_a || '') ||
    action.trim() !== (story.action || story.i_want || '') ||
    benefit.trim() !== (story.benefit || story.so_that || '') ||
    storyPoints !== (story.story_points?.toString() || story.points?.toString() || '')
  );

  // Generate preview of user story format
  const storyPreview = actor && action && benefit
    ? `As a ${actor}, I want to ${action}, so that ${benefit}`
    : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit User Story"
      size="lg"
    >
      <div style={styles.content}>
        {/* Epic context */}
        {epicName && (
          <div style={styles.contextBadge}>
            <Text style={styles.contextLabel}>Epic:</Text>
            <Badge variant="default">{epicName}</Badge>
          </div>
        )}

        {/* Story Title */}
        <div style={styles.field}>
          <label style={styles.label}>Story Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief title for this story"
            style={styles.input}
            autoFocus
          />
        </div>

        {/* User Story Format */}
        <div style={styles.storyFormatSection}>
          <Text style={styles.sectionTitle}>User Story Format</Text>

          <div style={styles.storyRow}>
            <span style={styles.storyPrefix}>As a</span>
            <input
              type="text"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              placeholder="user role"
              style={styles.storyInput}
            />
          </div>

          <div style={styles.storyRow}>
            <span style={styles.storyPrefix}>I want to</span>
            <input
              type="text"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="action or feature"
              style={styles.storyInput}
            />
          </div>

          <div style={styles.storyRow}>
            <span style={styles.storyPrefix}>So that</span>
            <input
              type="text"
              value={benefit}
              onChange={(e) => setBenefit(e.target.value)}
              placeholder="benefit or value"
              style={styles.storyInput}
            />
          </div>

          {/* Preview */}
          {storyPreview && (
            <div style={styles.preview}>
              <Text style={styles.previewText}>{storyPreview}</Text>
            </div>
          )}
        </div>

        {/* Acceptance Criteria */}
        <div style={styles.field}>
          <label style={styles.label}>Acceptance Criteria</label>
          <textarea
            value={acceptanceCriteria}
            onChange={(e) => setAcceptanceCriteria(e.target.value)}
            placeholder="Enter each acceptance criterion on a new line:
- Given... When... Then...
- User can see...
- System validates..."
            style={styles.textarea}
            rows={5}
          />
          <Text style={styles.hint}>
            One criterion per line. Use Given/When/Then format when applicable.
          </Text>
        </div>

        {/* Story Points */}
        <div style={styles.field}>
          <label style={styles.label}>Story Points (optional)</label>
          <input
            type="number"
            value={storyPoints}
            onChange={(e) => setStoryPoints(e.target.value)}
            placeholder="Effort estimate"
            style={{ ...styles.input, width: '120px' }}
            min="0"
            max="100"
          />
          <Text style={styles.hint}>
            Fibonacci scale recommended: 1, 2, 3, 5, 8, 13, 21
          </Text>
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!title.trim() || isLoading}
            loading={isLoading}
          >
            Save Changes
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
  contextBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[5],
  },
  contextLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  field: {
    marginBottom: tokens.spacing[5],
  },
  label: {
    display: 'block',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[2],
  },
  sectionTitle: {
    display: 'block',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[3],
  },
  storyFormatSection: {
    backgroundColor: 'var(--color-bg-secondary)',
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[5],
  },
  storyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },
  storyPrefix: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
    minWidth: '80px',
  },
  storyInput: {
    flex: 1,
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-text)',
  },
  preview: {
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.md,
    borderLeft: `3px solid ${tokens.colors.primary[500]}`,
    marginTop: tokens.spacing[3],
  },
  previewText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    fontStyle: 'italic',
    lineHeight: 1.5,
  },
  input: {
    width: '100%',
    padding: tokens.spacing[3],
    fontSize: tokens.typography.fontSize.base[0],
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-text)',
  },
  textarea: {
    width: '100%',
    padding: tokens.spacing[3],
    fontSize: tokens.typography.fontSize.base[0],
    fontFamily: 'inherit',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-text)',
    resize: 'vertical',
    lineHeight: 1.5,
  },
  hint: {
    display: 'block',
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[4],
    borderTop: '1px solid var(--color-border)',
  },
};

export default EditStoryModal;

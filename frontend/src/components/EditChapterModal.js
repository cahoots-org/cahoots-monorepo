/**
 * EditChapterModal - Modal for editing chapter details
 */
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Text,
  tokens,
} from '../design-system';

const EditChapterModal = ({
  isOpen,
  onClose,
  chapter,
  onSave,
  isLoading = false,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  // Reset form when chapter changes
  useEffect(() => {
    if (chapter) {
      setName(chapter.name || '');
      setDescription(chapter.description || '');
    }
  }, [chapter]);

  const handleSave = () => {
    if (!name.trim()) return;

    onSave({
      ...chapter,
      name: name.trim(),
      description: description.trim(),
    });
  };

  const hasChanges = chapter && (
    name.trim() !== (chapter.name || '') ||
    description.trim() !== (chapter.description || '')
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Chapter"
      size="md"
    >
      <div style={styles.content}>
        {/* Chapter Name */}
        <div style={styles.field}>
          <label style={styles.label}>Chapter Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter chapter name"
            style={styles.input}
            autoFocus
          />
        </div>

        {/* Description */}
        <div style={styles.field}>
          <label style={styles.label}>Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this chapter covers..."
            style={styles.textarea}
            rows={4}
          />
        </div>

        {/* Feature count info */}
        {chapter?.slices?.length > 0 && (
          <div style={styles.info}>
            <Text style={styles.infoText}>
              This chapter contains {chapter.slices.length} feature{chapter.slices.length !== 1 ? 's' : ''}
            </Text>
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!name.trim() || !hasChanges || isLoading}
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
  info: {
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.md,
    marginBottom: tokens.spacing[5],
  },
  infoText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[4],
    borderTop: '1px solid var(--color-border)',
  },
};

export default EditChapterModal;

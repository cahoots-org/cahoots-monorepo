/**
 * EditEpicModal - Modal for editing epic details
 */
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Text,
  Badge,
  tokens,
} from '../design-system';

const EditEpicModal = ({
  isOpen,
  onClose,
  epic,
  onSave,
  isLoading = false,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [businessValue, setBusinessValue] = useState('');

  // Reset form when epic changes
  useEffect(() => {
    if (epic) {
      setName(epic.name || epic.title || '');
      setDescription(epic.description || '');
      setBusinessValue(epic.business_value || epic.businessValue || '');
    }
  }, [epic]);

  const handleSave = () => {
    if (!name.trim()) return;

    onSave({
      ...epic,
      name: name.trim(),
      title: name.trim(), // Some places use title instead of name
      description: description.trim(),
      business_value: businessValue.trim(),
    });
  };

  const hasChanges = epic && (
    name.trim() !== (epic.name || epic.title || '') ||
    description.trim() !== (epic.description || '') ||
    businessValue.trim() !== (epic.business_value || epic.businessValue || '')
  );

  const storyCount = epic?.stories?.length || epic?.user_stories?.length || 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Epic"
      size="md"
    >
      <div style={styles.content}>
        {/* Epic Name */}
        <div style={styles.field}>
          <label style={styles.label}>Epic Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter epic name"
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
            placeholder="Describe the epic's scope and goals..."
            style={styles.textarea}
            rows={4}
          />
        </div>

        {/* Business Value */}
        <div style={styles.field}>
          <label style={styles.label}>Business Value</label>
          <textarea
            value={businessValue}
            onChange={(e) => setBusinessValue(e.target.value)}
            placeholder="What business value does this epic deliver?"
            style={styles.textarea}
            rows={3}
          />
        </div>

        {/* Story count info */}
        {storyCount > 0 && (
          <div style={styles.info}>
            <Text style={styles.infoText}>
              This epic contains {storyCount} user stor{storyCount !== 1 ? 'ies' : 'y'}
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

export default EditEpicModal;

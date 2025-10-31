import React, { useState } from 'react';
import {
  Modal,
  Button,
  Text,
  LoadingSpinner,
  tokens,
} from '../design-system';

const AddSliceModal = ({ isOpen, onClose, onSave, chapterName }) => {
  const [sliceName, setSliceName] = useState('');
  const [sliceType, setSliceType] = useState('state_change');
  const [description, setDescription] = useState('');
  const [command, setCommand] = useState('');
  const [readModel, setReadModel] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!sliceName.trim()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await onSave({
        name: sliceName.trim(),
        type: sliceType,
        description: description.trim(),
        command: command.trim(),
        read_model: readModel.trim(),
        chapter: chapterName,
      });

      // Reset form
      setSliceName('');
      setSliceType('state_change');
      setDescription('');
      setCommand('');
      setReadModel('');
      onClose();
    } catch (error) {
      console.error('Error creating slice:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSliceName('');
      setSliceType('state_change');
      setDescription('');
      setCommand('');
      setReadModel('');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={`Add New Slice to ${chapterName}`} size="md">
      <div style={styles.form}>
        <div style={styles.helpText}>
          <Text style={styles.helpTextContent}>
            Enter a name for your slice and optionally fill in details. The AI will analyze your input and automatically fill in missing fields, generate events, create GWT scenarios, and ensure consistency with your event model.
          </Text>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>
            Slice Name <span style={styles.required}>*</span>
          </label>
          <input
            type="text"
            value={sliceName}
            onChange={(e) => setSliceName(e.target.value)}
            placeholder="e.g., AddItemToCart, ViewCartItems"
            style={styles.input}
            disabled={isSubmitting}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Slice Type</label>
          <select
            value={sliceType}
            onChange={(e) => setSliceType(e.target.value)}
            style={styles.select}
            disabled={isSubmitting}
          >
            <option value="state_change">State Change (Command → Event)</option>
            <option value="state_view">State View (Read Model)</option>
            <option value="automation">Automation (Event → Event)</option>
          </select>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this slice does..."
            style={styles.textarea}
            rows={3}
            disabled={isSubmitting}
          />
        </div>

        {sliceType === 'state_change' && (
          <div style={styles.formGroup}>
            <label style={styles.label}>Command Name (optional)</label>
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="e.g., AddItem (AI will generate if blank)"
              style={styles.input}
              disabled={isSubmitting}
            />
          </div>
        )}

        {sliceType === 'state_view' && (
          <div style={styles.formGroup}>
            <label style={styles.label}>Read Model Name (optional)</label>
            <input
              type="text"
              value={readModel}
              onChange={(e) => setReadModel(e.target.value)}
              placeholder="e.g., CartItems (AI will generate if blank)"
              style={styles.input}
              disabled={isSubmitting}
            />
          </div>
        )}

        <div style={styles.footer}>
          <Button
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!sliceName.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="small" />
                <span style={{ marginLeft: tokens.spacing[2] }}>Analyzing...</span>
              </>
            ) : (
              'Create & Analyze'
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  helpText: {
    padding: tokens.spacing[3],
    backgroundColor: tokens.colors.info[50],
    border: `1px solid ${tokens.colors.info[200]}`,
    borderRadius: tokens.borderRadius.base,
  },

  helpTextContent: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.info[800],
    lineHeight: '1.5',
  },

  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  label: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
  },

  required: {
    color: tokens.colors.error[500],
  },

  input: {
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    outline: 'none',
    transition: 'border-color 0.2s',
  },

  select: {
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    outline: 'none',
    transition: 'border-color 0.2s',
  },

  textarea: {
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    outline: 'none',
    transition: 'border-color 0.2s',
    fontFamily: 'inherit',
    resize: 'vertical',
  },

  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
    marginTop: tokens.spacing[4],
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid var(--color-border)`,
  },
};

export default AddSliceModal;

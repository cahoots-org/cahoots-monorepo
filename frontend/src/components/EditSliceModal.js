/**
 * EditSliceModal - Modal for editing slice details
 */
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Text,
  Badge,
  tokens,
} from '../design-system';

const SLICE_TYPES = [
  { value: 'state_change', label: 'User Action', description: 'Something the user does that changes data' },
  { value: 'state_view', label: 'Screen/View', description: 'What the user sees on screen' },
  { value: 'automation', label: 'Background Process', description: 'Runs automatically behind the scenes' },
];

const EditSliceModal = ({
  isOpen,
  onClose,
  slice,
  chapterName,
  onSave,
  isLoading = false,
}) => {
  const [sliceType, setSliceType] = useState('state_change');
  const [command, setCommand] = useState('');
  const [readModel, setReadModel] = useState('');
  const [events, setEvents] = useState('');
  const [description, setDescription] = useState('');

  // Reset form when slice changes
  useEffect(() => {
    if (slice) {
      setSliceType(slice.type || 'state_change');
      setCommand(slice.command || '');
      setReadModel(slice.read_model || '');
      setEvents(Array.isArray(slice.events) ? slice.events.join(', ') : '');
      setDescription(slice.description || '');
    }
  }, [slice]);

  const handleSave = () => {
    const eventsArray = events
      .split(',')
      .map(e => e.trim())
      .filter(Boolean);

    const updatedSlice = {
      ...slice,
      type: sliceType,
      events: eventsArray,
      gwt_scenarios: slice?.gwt_scenarios || [],
    };

    if (sliceType === 'state_change' || sliceType === 'automation') {
      updatedSlice.command = command.trim();
      delete updatedSlice.read_model;
    } else if (sliceType === 'state_view') {
      updatedSlice.read_model = readModel.trim();
      delete updatedSlice.command;
    }

    if (description.trim()) {
      updatedSlice.description = description.trim();
    }

    onSave(updatedSlice, chapterName);
  };

  const getDisplayName = () => {
    if (sliceType === 'state_view') {
      return readModel || 'Unnamed Screen';
    }
    return command || 'Unnamed Action';
  };

  const isValid = () => {
    if (sliceType === 'state_view') {
      return readModel.trim().length > 0;
    }
    return command.trim().length > 0;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Feature"
      size="lg"
    >
      <div style={styles.content}>
        {/* Module context */}
        {chapterName && (
          <div style={styles.contextBadge}>
            <Text style={styles.contextLabel}>Module:</Text>
            <Badge variant="default">{chapterName}</Badge>
          </div>
        )}

        {/* Feature Type */}
        <div style={styles.field}>
          <label style={styles.label}>Feature Type</label>
          <div style={styles.typeGrid}>
            {SLICE_TYPES.map((type) => (
              <button
                key={type.value}
                style={{
                  ...styles.typeButton,
                  ...(sliceType === type.value && styles.typeButtonSelected),
                }}
                onClick={() => setSliceType(type.value)}
              >
                <Text style={styles.typeLabel}>{type.label}</Text>
                <Text style={styles.typeDescription}>{type.description}</Text>
              </button>
            ))}
          </div>
        </div>

        {/* Action Name (for state_change and automation) */}
        {(sliceType === 'state_change' || sliceType === 'automation') && (
          <div style={styles.field}>
            <label style={styles.label}>Action Name</label>
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="e.g., CreateUser, ProcessPayment"
              style={styles.input}
            />
            <Text style={styles.hint}>
              Use PascalCase for action names (e.g., CreateOrder, UpdateProfile)
            </Text>
          </div>
        )}

        {/* Screen Name (for state_view) */}
        {sliceType === 'state_view' && (
          <div style={styles.field}>
            <label style={styles.label}>Screen Name</label>
            <input
              type="text"
              value={readModel}
              onChange={(e) => setReadModel(e.target.value)}
              placeholder="e.g., UserProfile, OrderSummary"
              style={styles.input}
            />
            <Text style={styles.hint}>
              Use PascalCase for screen names (e.g., UserDashboard, ProductCatalog)
            </Text>
          </div>
        )}

        {/* System Events */}
        <div style={styles.field}>
          <label style={styles.label}>
            {sliceType === 'state_view' ? 'Events that update this screen' : 'System events triggered'}
          </label>
          <input
            type="text"
            value={events}
            onChange={(e) => setEvents(e.target.value)}
            placeholder="e.g., UserCreated, OrderPlaced (comma-separated)"
            style={styles.input}
          />
          <Text style={styles.hint}>
            Separate multiple events with commas. Use past tense (e.g., Created, Updated, Deleted)
          </Text>
        </div>

        {/* Description */}
        <div style={styles.field}>
          <label style={styles.label}>Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this feature does..."
            style={styles.textarea}
            rows={3}
          />
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!isValid() || isLoading}
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
  typeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: tokens.spacing[3],
  },
  typeButton: {
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-bg-secondary)',
    border: '2px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.15s ease',
  },
  typeButtonSelected: {
    borderColor: tokens.colors.primary[500],
    backgroundColor: `${tokens.colors.primary[500]}10`,
  },
  typeLabel: {
    display: 'block',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[1],
  },
  typeDescription: {
    display: 'block',
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
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

export default EditSliceModal;

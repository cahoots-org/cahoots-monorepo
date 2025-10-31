import React, { useState } from 'react';
import { Button, tokens } from '../design-system';

/**
 * EditableElement - Wrapper for inline editing of Event Model elements
 *
 * Handles:
 * - Inline editing on click
 * - Triggering cascade analysis
 * - Showing change preview
 * - Applying accepted changes
 */
const EditableElement = ({
  children,
  value,
  onEdit,
  elementType,
  elementId,
  field,
  multiline = false,
  placeholder = "Click to edit",
  disabled = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');

  const handleStartEdit = () => {
    if (disabled) return;
    setIsEditing(true);
    setEditValue(value || '');
  };

  const handleSave = async () => {
    if (editValue === value) {
      // No change, just exit edit mode
      setIsEditing(false);
      return;
    }

    // Trigger cascade analysis through parent
    await onEdit({
      type: elementType,
      id: elementId,
      field: field,
      oldValue: value,
      newValue: editValue,
    });

    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(value || '');
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && !multiline && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
  };

  if (isEditing) {
    return (
      <div style={styles.editContainer}>
        {multiline ? (
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
            style={styles.textarea}
            placeholder={placeholder}
          />
        ) : (
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
            style={styles.input}
            placeholder={placeholder}
          />
        )}
        <div style={styles.editActions}>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
          >
            Save
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleStartEdit}
      style={{
        ...styles.viewContainer,
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.6 : 1,
      }}
      title={disabled ? '' : 'Click to edit'}
    >
      {children || (
        <span style={styles.placeholder}>
          {placeholder}
        </span>
      )}
      {!disabled && (
        <span style={styles.editIcon}>✏️</span>
      )}
    </div>
  );
};

const styles = {
  viewContainer: {
    position: 'relative',
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.base,
    transition: 'background-color 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  editIcon: {
    opacity: 0,
    fontSize: '14px',
    marginLeft: 'auto',
    transition: 'opacity 0.2s ease',
  },

  'viewContainer:hover .editIcon': {
    opacity: 1,
  },

  editContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  input: {
    width: '100%',
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `2px solid ${tokens.colors.primary[500]}`,
    borderRadius: tokens.borderRadius.base,
    outline: 'none',
    fontFamily: 'inherit',
  },

  textarea: {
    width: '100%',
    minHeight: '80px',
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `2px solid ${tokens.colors.primary[500]}`,
    borderRadius: tokens.borderRadius.base,
    outline: 'none',
    fontFamily: 'inherit',
    resize: 'vertical',
  },

  editActions: {
    display: 'flex',
    gap: tokens.spacing[2],
    justifyContent: 'flex-end',
  },

  placeholder: {
    color: tokens.colors.neutral[400],
    fontStyle: 'italic',
  },
};

// Add hover effect via CSS
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    .editable-element:hover .edit-icon {
      opacity: 1 !important;
    }
    .editable-element:hover {
      background-color: ${tokens.colors.neutral[50]};
    }
  `;
  document.head.appendChild(style);
}

export default EditableElement;

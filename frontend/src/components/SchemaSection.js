import React, { useState } from 'react';
import { Button, Text, tokens } from '../design-system';
import SchemaField from './SchemaField';

const SchemaSection = ({ title, items, itemType, onUpdate, editable = true }) => {
  const [addingNew, setAddingNew] = useState(false);
  const [newField, setNewField] = useState({
    name: '',
    type: 'string',
    description: '',
    required: false,
    source: { type: 'ui_input', details: '' }
  });

  const handleAddField = (itemName) => {
    setAddingNew(itemName);
    setNewField({
      name: '',
      type: 'string',
      description: '',
      required: false,
      source: { type: 'ui_input', details: '' }
    });
  };

  const handleSaveNew = (itemName) => {
    if (!newField.name.trim()) return;

    // Find the item and add the field
    const updatedItems = items.map(item => {
      if (item.name === itemName) {
        const fieldArray = itemType === 'command' ? 'parameters' :
                          itemType === 'event' ? 'payload' : 'fields';
        return {
          ...item,
          [fieldArray]: [...(item[fieldArray] || []), newField]
        };
      }
      return item;
    });

    onUpdate(updatedItems);
    setAddingNew(false);
  };

  const handleCancelNew = () => {
    setAddingNew(false);
  };

  const handleUpdateField = (itemName, fieldIndex, updatedField) => {
    const updatedItems = items.map(item => {
      if (item.name === itemName) {
        const fieldArray = itemType === 'command' ? 'parameters' :
                          itemType === 'event' ? 'payload' : 'fields';
        const fields = [...(item[fieldArray] || [])];
        fields[fieldIndex] = updatedField;
        return { ...item, [fieldArray]: fields };
      }
      return item;
    });

    onUpdate(updatedItems);
  };

  const handleRemoveField = (itemName, fieldIndex) => {
    if (!window.confirm('Remove this field?')) return;

    const updatedItems = items.map(item => {
      if (item.name === itemName) {
        const fieldArray = itemType === 'command' ? 'parameters' :
                          itemType === 'event' ? 'payload' : 'fields';
        const fields = [...(item[fieldArray] || [])];
        fields.splice(fieldIndex, 1);
        return { ...item, [fieldArray]: fields };
      }
      return item;
    });

    onUpdate(updatedItems);
  };

  const getFieldArray = (item) => {
    if (itemType === 'command') return item.parameters || [];
    if (itemType === 'event') return item.payload || [];
    return item.fields || [];
  };

  const getFieldArrayName = () => {
    if (itemType === 'command') return 'Parameters';
    if (itemType === 'event') return 'Payload';
    return 'Fields';
  };

  const getItemIcon = () => {
    if (itemType === 'command') return '⚡';
    if (itemType === 'event') return '📝';
    return '📊';
  };

  if (!items || items.length === 0) {
    return (
      <div style={styles.emptyState}>
        <Text style={styles.emptyText}>No {title.toLowerCase()} defined</Text>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <Text style={styles.sectionTitle}>{title}</Text>

      {items.map((item, itemIdx) => {
        const fields = getFieldArray(item);

        return (
          <div key={itemIdx} style={styles.itemContainer}>
            <div style={styles.itemHeader}>
              <div style={styles.itemInfo}>
                <span style={styles.itemIcon}>{getItemIcon()}</span>
                <Text style={styles.itemName}>{item.name}</Text>
                {item.description && (
                  <Text style={styles.itemDescription}>{item.description}</Text>
                )}
              </div>
            </div>

            <div style={styles.fieldsContainer}>
              <div style={styles.fieldsHeader}>
                <Text style={styles.fieldsTitle}>
                  {getFieldArrayName()} ({fields.length})
                </Text>
                {editable && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAddField(item.name)}
                  >
                    + Add Field
                  </Button>
                )}
              </div>

              {fields.length === 0 && !addingNew && (
                <div style={styles.noFields}>
                  <Text style={styles.noFieldsText}>No fields defined</Text>
                </div>
              )}

              {fields.map((field, fieldIdx) => (
                <SchemaField
                  key={fieldIdx}
                  field={field}
                  onUpdate={(updatedField) => handleUpdateField(item.name, fieldIdx, updatedField)}
                  onRemove={() => handleRemoveField(item.name, fieldIdx)}
                  editable={editable}
                  showSource={true}
                />
              ))}

              {addingNew === item.name && (
                <div style={styles.newFieldForm}>
                  <div style={styles.formRow}>
                    <input
                      type="text"
                      value={newField.name}
                      onChange={(e) => setNewField({ ...newField, name: e.target.value })}
                      placeholder="Field name"
                      style={styles.input}
                      autoFocus
                    />
                    <select
                      value={newField.type}
                      onChange={(e) => setNewField({ ...newField, type: e.target.value })}
                      style={styles.select}
                    >
                      <option value="string">String</option>
                      <option value="integer">Integer</option>
                      <option value="decimal">Decimal</option>
                      <option value="boolean">Boolean</option>
                      <option value="datetime">DateTime</option>
                      <option value="array">Array</option>
                      <option value="object">Object</option>
                    </select>
                  </div>
                  <textarea
                    value={newField.description}
                    onChange={(e) => setNewField({ ...newField, description: e.target.value })}
                    placeholder="Description"
                    style={styles.textarea}
                    rows={2}
                  />
                  <div style={styles.formRow}>
                    <label style={styles.checkbox}>
                      <input
                        type="checkbox"
                        checked={newField.required}
                        onChange={(e) => setNewField({ ...newField, required: e.target.checked })}
                      />
                      <span style={styles.checkboxLabel}>Required</span>
                    </label>
                  </div>
                  <div style={styles.formActions}>
                    <Button variant="ghost" size="sm" onClick={handleCancelNew}>
                      Cancel
                    </Button>
                    <Button variant="primary" size="sm" onClick={() => handleSaveNew(item.name)}>
                      Add Field
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const styles = {
  container: {
    marginBottom: tokens.spacing[6],
  },

  sectionTitle: {
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[4],
  },

  itemContainer: {
    marginBottom: tokens.spacing[4],
    border: `2px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.lg,
    backgroundColor: 'var(--color-surface)',
    overflow: 'hidden',
  },

  itemHeader: {
    padding: tokens.spacing[3],
    backgroundColor: tokens.colors.neutral[50],
    borderBottom: `1px solid var(--color-border)`,
  },

  itemInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  itemIcon: {
    fontSize: tokens.typography.fontSize.xl[0],
  },

  itemName: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.bold,
    fontFamily: tokens.typography.fontFamily.mono,
    color: 'var(--color-text)',
  },

  itemDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    marginLeft: tokens.spacing[2],
  },

  fieldsContainer: {
    padding: tokens.spacing[3],
  },

  fieldsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[3],
  },

  fieldsTitle: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
  },

  noFields: {
    padding: tokens.spacing[4],
    textAlign: 'center',
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.base,
  },

  noFieldsText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
  },

  newFieldForm: {
    padding: tokens.spacing[3],
    border: `2px solid ${tokens.colors.success[500]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: tokens.colors.success[50],
    marginTop: tokens.spacing[2],
  },

  formRow: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[2],
  },

  input: {
    flex: 1,
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'white',
    color: 'var(--color-text)',
    fontFamily: tokens.typography.fontFamily.mono,
  },

  select: {
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'white',
    color: 'var(--color-text)',
    minWidth: '120px',
  },

  textarea: {
    width: '100%',
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.sm[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'white',
    color: 'var(--color-text)',
    fontFamily: 'inherit',
    resize: 'vertical',
    marginBottom: tokens.spacing[2],
  },

  checkbox: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    cursor: 'pointer',
  },

  checkboxLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
  },

  formActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
  },

  emptyState: {
    padding: tokens.spacing[8],
    textAlign: 'center',
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.lg,
    border: `1px dashed ${tokens.colors.neutral[300]}`,
  },

  emptyText: {
    fontSize: tokens.typography.fontSize.base[0],
    color: tokens.colors.neutral[500],
  },
};

export default SchemaSection;

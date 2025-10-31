import React, { useState } from 'react';
import { Button, Text, tokens } from '../design-system';

const SchemaField = ({ field, onUpdate, onRemove, editable = true, showSource = true }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedField, setEditedField] = useState(field);

  const handleSave = () => {
    onUpdate(editedField);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedField(field);
    setIsEditing(false);
  };

  const typeColors = {
    string: tokens.colors.info[500],
    integer: tokens.colors.success[500],
    decimal: tokens.colors.secondary[500],
    boolean: tokens.colors.warning[500],
    datetime: tokens.colors.primary[500],
    array: tokens.colors.info[600],
    object: tokens.colors.secondary[600],
  };

  const sourceTypeLabels = {
    ui_input: '🖱️ UI Input',
    url_parameter: '🔗 URL Param',
    read_model: '📊 Read Model',
    system: '⚙️ System',
    session: '👤 Session',
    command_parameter: '⚡ Command',
    derived: '🧮 Derived',
    lookup: '🔍 Lookup',
    event_field: '📝 Event',
    aggregation: '∑ Aggregation',
  };

  if (isEditing) {
    return (
      <div style={styles.editingContainer}>
        <div style={styles.editRow}>
          <input
            type="text"
            value={editedField.name}
            onChange={(e) => setEditedField({ ...editedField, name: e.target.value })}
            placeholder="Field name"
            style={styles.input}
          />
          <select
            value={editedField.type}
            onChange={(e) => setEditedField({ ...editedField, type: e.target.value })}
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
          value={editedField.description || ''}
          onChange={(e) => setEditedField({ ...editedField, description: e.target.value })}
          placeholder="Description"
          style={styles.textarea}
          rows={2}
        />
        <div style={styles.editActions}>
          <Button variant="ghost" size="sm" onClick={handleCancel}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleSave}>
            Save
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.fieldContainer}>
      <div style={styles.fieldHeader} onClick={() => setIsExpanded(!isExpanded)}>
        <div style={styles.fieldInfo}>
          <span style={styles.expandIcon}>{isExpanded ? '▼' : '▶'}</span>
          <Text style={styles.fieldName}>{field.name}</Text>
          <span style={{ ...styles.typeBadge, backgroundColor: typeColors[field.type] || tokens.colors.neutral[500] }}>
            {field.type}
          </span>
          {field.required && <span style={styles.requiredBadge}>required</span>}
        </div>
        {editable && (
          <div style={styles.fieldActions} onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
              Edit
            </Button>
            <Button variant="ghost" size="sm" onClick={onRemove}>
              Remove
            </Button>
          </div>
        )}
      </div>

      {isExpanded && (
        <div style={styles.fieldDetails}>
          {field.description && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Description:</Text>
              <Text style={styles.detailValue}>{field.description}</Text>
            </div>
          )}

          {showSource && field.source && (
            <div style={styles.sourceSection}>
              <Text style={styles.detailLabel}>Data Source:</Text>
              <div style={styles.sourceContent}>
                <span style={styles.sourceTypeBadge}>
                  {sourceTypeLabels[field.source.type] || field.source.type}
                </span>
                {field.source.from && (
                  <Text style={styles.sourceFrom}>{field.source.from}</Text>
                )}
                {field.source.details && (
                  <Text style={styles.sourceDetails}>{field.source.details}</Text>
                )}
                {field.source.events && field.source.events.length > 0 && (
                  <div style={styles.sourceEvents}>
                    <Text style={styles.sourceEventsLabel}>Source Events:</Text>
                    {field.source.events.map((event, idx) => (
                      <span key={idx} style={styles.eventBadge}>{event}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {field.constraints && Object.keys(field.constraints).length > 0 && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Constraints:</Text>
              <div style={styles.constraints}>
                {Object.entries(field.constraints).map(([key, value]) => (
                  <span key={key} style={styles.constraintBadge}>
                    {key}: {JSON.stringify(value)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {field.type === 'array' && field.item_type && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Item Type:</Text>
              <span style={{ ...styles.typeBadge, backgroundColor: typeColors[field.item_type] || tokens.colors.neutral[500] }}>
                {field.item_type}
              </span>
            </div>
          )}

          {field.schema && field.schema.length > 0 && (
            <div style={styles.nestedSchema}>
              <Text style={styles.detailLabel}>Object Schema:</Text>
              {field.schema.map((nestedField, idx) => (
                <SchemaField
                  key={idx}
                  field={nestedField}
                  onUpdate={() => {}}
                  onRemove={() => {}}
                  editable={false}
                  showSource={false}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles = {
  fieldContainer: {
    marginBottom: tokens.spacing[2],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
  },

  fieldHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[2],
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },

  fieldInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flex: 1,
  },

  expandIcon: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    width: '12px',
  },

  fieldName: {
    fontWeight: tokens.typography.fontWeight.medium,
    fontFamily: tokens.typography.fontFamily.mono,
    color: 'var(--color-text)',
  },

  typeBadge: {
    padding: `${tokens.spacing[0.5]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.full,
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'white',
  },

  requiredBadge: {
    padding: `${tokens.spacing[0.5]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.full,
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    backgroundColor: tokens.colors.error[500],
    color: 'white',
  },

  fieldActions: {
    display: 'flex',
    gap: tokens.spacing[1],
  },

  fieldDetails: {
    padding: tokens.spacing[3],
    paddingTop: 0,
    borderTop: `1px solid var(--color-border)`,
  },

  detailRow: {
    marginBottom: tokens.spacing[2],
  },

  detailLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[600],
    marginBottom: tokens.spacing[1],
    display: 'block',
  },

  detailValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
  },

  sourceSection: {
    marginBottom: tokens.spacing[2],
  },

  sourceContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
    padding: tokens.spacing[2],
    backgroundColor: tokens.colors.info[50],
    border: `1px solid ${tokens.colors.info[100]}`,
    borderRadius: tokens.borderRadius.base,
  },

  sourceTypeBadge: {
    display: 'inline-block',
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.base,
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    backgroundColor: tokens.colors.info[600],
    color: 'white',
    alignSelf: 'flex-start',
  },

  sourceFrom: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: tokens.typography.fontFamily.mono,
    color: tokens.colors.info[700],
  },

  sourceDetails: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.info[700],
  },

  sourceEvents: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },

  sourceEventsLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.info[700],
  },

  eventBadge: {
    display: 'inline-block',
    padding: `${tokens.spacing[0.5]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.base,
    fontSize: tokens.typography.fontSize.xs[0],
    backgroundColor: tokens.colors.info[100],
    color: tokens.colors.info[700],
    marginRight: tokens.spacing[1],
  },

  constraints: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[1],
  },

  constraintBadge: {
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.base,
    fontSize: tokens.typography.fontSize.xs[0],
    backgroundColor: tokens.colors.warning[100],
    color: tokens.colors.warning[700],
  },

  nestedSchema: {
    marginTop: tokens.spacing[2],
    paddingLeft: tokens.spacing[3],
    borderLeft: `2px solid ${tokens.colors.neutral[300]}`,
  },

  editingContainer: {
    padding: tokens.spacing[3],
    border: `2px solid ${tokens.colors.info[500]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    marginBottom: tokens.spacing[2],
  },

  editRow: {
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
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    fontFamily: tokens.typography.fontFamily.mono,
  },

  select: {
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.base[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    minWidth: '120px',
  },

  textarea: {
    width: '100%',
    padding: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.sm[0],
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    fontFamily: 'inherit',
    resize: 'vertical',
    marginBottom: tokens.spacing[2],
  },

  editActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
  },
};

export default SchemaField;

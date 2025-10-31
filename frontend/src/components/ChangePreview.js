import React, { useState } from 'react';
import {
  Modal,
  Card,
  CardContent,
  Button,
  Text,
  Heading3,
  Badge,
  tokens,
} from '../design-system';

/**
 * ChangePreview - Modal for reviewing and accepting/rejecting cascade changes
 *
 * Shows user what other elements will change when they edit something,
 * with checkboxes to selectively apply changes.
 */
const ChangePreview = ({ changes, isOpen, onClose, onAccept, onReject, loading }) => {
  const [selectedChanges, setSelectedChanges] = useState(
    changes ? changes.map((_, idx) => idx) : []
  );

  if (!changes) return null;

  const toggleChange = (index) => {
    setSelectedChanges(prev =>
      prev.includes(index)
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  const toggleAll = () => {
    if (selectedChanges.length === changes.length) {
      setSelectedChanges([]);
    } else {
      setSelectedChanges(changes.map((_, idx) => idx));
    }
  };

  const handleAccept = () => {
    const selectedChangeObjects = changes.filter((_, idx) => selectedChanges.includes(idx));
    onAccept(selectedChangeObjects);
  };

  const getChangeIcon = (type) => {
    const icons = {
      command: '🔵',
      event: '🟠',
      read_model: '🟢',
      task: '🎯',
      gwt: '📋',
      swimlane: '🏊',
      diagram: '🎨',
      automation: '⚙️',
    };
    return icons[type] || '📌';
  };

  const getActionColor = (action) => {
    const colors = {
      create: tokens.colors.success[500],
      update: tokens.colors.info[500],
      delete: tokens.colors.error[500],
    };
    return colors[action] || tokens.colors.neutral[500];
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Review Proposed Changes"
      maxWidth="800px"
    >
      <div style={styles.container}>
        <Text style={styles.description}>
          Your edit will trigger the following changes to maintain consistency across
          the Event Model, tasks, and diagram:
        </Text>

        <div style={styles.controls}>
          <Text style={styles.selectedCount}>
            {selectedChanges.length} of {changes.length} selected
          </Text>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleAll}
          >
            {selectedChanges.length === changes.length ? 'Deselect All' : 'Select All'}
          </Button>
        </div>

        <div style={styles.changesList}>
          {changes.map((change, index) => (
            <Card
              key={index}
              style={{
                ...styles.changeCard,
                opacity: selectedChanges.includes(index) ? 1 : 0.6,
                borderLeft: `4px solid ${getActionColor(change.action)}`,
              }}
            >
              <CardContent style={styles.changeContent}>
                <div style={styles.changeHeader}>
                  <input
                    type="checkbox"
                    checked={selectedChanges.includes(index)}
                    onChange={() => toggleChange(index)}
                    style={styles.checkbox}
                  />

                  <div style={styles.changeInfo}>
                    <div style={styles.changeTitleRow}>
                      <span style={styles.changeIcon}>{getChangeIcon(change.type)}</span>
                      <Heading3 style={styles.changeTitle}>
                        {change.action} {change.type}: {change.id}
                      </Heading3>
                      <Badge
                        variant={
                          change.action === 'create' ? 'success' :
                          change.action === 'update' ? 'info' :
                          'error'
                        }
                        size="sm"
                      >
                        {change.action}
                      </Badge>
                    </div>

                    <Text style={styles.changeReason}>{change.reason}</Text>

                    {change.action === 'update' && change.field && (
                      <div style={styles.diffContainer}>
                        <Text style={styles.diffLabel}>Field: <code>{change.field}</code></Text>
                        {change.old_value && (
                          <div style={styles.diffOld}>
                            <Text style={styles.diffOldLabel}>Before:</Text>
                            <Text style={styles.diffValue}>
                              {typeof change.old_value === 'object'
                                ? JSON.stringify(change.old_value, null, 2)
                                : change.old_value}
                            </Text>
                          </div>
                        )}
                        <div style={styles.diffNew}>
                          <Text style={styles.diffNewLabel}>After:</Text>
                          <Text style={styles.diffValue}>
                            {typeof change.value === 'object'
                              ? JSON.stringify(change.value, null, 2)
                              : change.value}
                          </Text>
                        </div>
                      </div>
                    )}

                    {change.action === 'create' && change.data && (
                      <div style={styles.createData}>
                        <Text style={styles.diffLabel}>New element:</Text>
                        <pre style={styles.codeBlock}>
                          {JSON.stringify(change.data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div style={styles.actions}>
          <Button
            variant="outline"
            onClick={onReject || onClose}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleAccept}
            disabled={selectedChanges.length === 0 || loading}
            loading={loading}
          >
            Apply {selectedChanges.length} Change{selectedChanges.length !== 1 ? 's' : ''}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  description: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  controls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[3],
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.md,
  },

  selectedCount: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
  },

  changesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
    maxHeight: '500px',
    overflowY: 'auto',
    padding: tokens.spacing[1],
  },

  changeCard: {
    transition: 'all 0.2s ease',
    cursor: 'pointer',
  },

  changeContent: {
    padding: tokens.spacing[3],
  },

  changeHeader: {
    display: 'flex',
    gap: tokens.spacing[3],
    alignItems: 'flex-start',
  },

  checkbox: {
    marginTop: '4px',
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },

  changeInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  changeTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  changeIcon: {
    fontSize: '20px',
    lineHeight: 1,
  },

  changeTitle: {
    margin: 0,
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    flex: 1,
  },

  changeReason: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    fontStyle: 'italic',
  },

  diffContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
    marginTop: tokens.spacing[2],
  },

  diffLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
  },

  diffOld: {
    backgroundColor: tokens.colors.error[50],
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.base,
    borderLeft: `3px solid ${tokens.colors.error[400]}`,
  },

  diffOldLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.error[700],
    marginBottom: tokens.spacing[1],
  },

  diffNew: {
    backgroundColor: tokens.colors.success[50],
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.base,
    borderLeft: `3px solid ${tokens.colors.success[400]}`,
  },

  diffNewLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.success[700],
    marginBottom: tokens.spacing[1],
  },

  diffValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: tokens.typography.fontFamily.mono.join(', '),
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },

  createData: {
    marginTop: tokens.spacing[2],
  },

  codeBlock: {
    backgroundColor: tokens.colors.neutral[100],
    padding: tokens.spacing[3],
    borderRadius: tokens.borderRadius.base,
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: tokens.typography.fontFamily.mono.join(', '),
    overflowX: 'auto',
    margin: 0,
  },

  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
    paddingTop: tokens.spacing[3],
    borderTop: `1px solid ${tokens.colors.neutral[200]}`,
  },
};

export default ChangePreview;

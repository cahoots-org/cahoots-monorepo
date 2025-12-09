/**
 * UnifiedEditModal - Unified editing experience with cascade preview
 *
 * This component provides a two-step editing flow:
 * 1. Edit Form: User modifies the artifact
 * 2. Cascade Preview: User reviews and approves/rejects cascade effects
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Button,
  Text,
  Badge,
  Spinner,
  tokens,
} from '../design-system';
import ChangePreview from './ChangePreview';
import apiClient from '../services/unifiedApiClient';

// Artifact type configurations
const ARTIFACT_CONFIGS = {
  epic: {
    label: 'Epic',
    icon: '🎯',
    fields: ['name', 'title', 'description', 'business_value'],
    displayName: (a) => a.name || a.title || 'Untitled Epic',
  },
  story: {
    label: 'User Story',
    icon: '📖',
    fields: ['title', 'actor', 'action', 'benefit', 'description', 'acceptance_criteria'],
    displayName: (a) => a.title || `As a ${a.actor}, ${a.action}` || 'Untitled Story',
  },
  swimlane: {
    label: 'Swimlane',
    icon: '🏢',
    fields: ['name', 'description', 'commands', 'read_models', 'automations'],
    displayName: (a) => a.name || 'Untitled Swimlane',
  },
  chapter: {
    label: 'Chapter',
    icon: '📑',
    fields: ['name', 'title', 'description'],
    displayName: (a) => a.name || a.title || 'Untitled Chapter',
  },
  slice: {
    label: 'Slice',
    icon: '🔹',
    fields: ['command', 'read_model', 'automation_name', 'gwt_scenarios'],
    displayName: (a) => a.command || a.read_model || a.automation_name || 'Untitled Slice',
  },
  command: {
    label: 'Command',
    icon: '🔵',
    fields: ['name', 'description', 'aggregate'],
    displayName: (a) => a.name || 'Untitled Command',
  },
  event: {
    label: 'Event',
    icon: '🟠',
    fields: ['name', 'description', 'aggregate', 'triggered_by'],
    displayName: (a) => a.name || 'Untitled Event',
  },
  read_model: {
    label: 'Read Model',
    icon: '🟢',
    fields: ['name', 'description', 'data_source'],
    displayName: (a) => a.name || 'Untitled Read Model',
  },
  requirement: {
    label: 'Requirement',
    icon: '📋',
    fields: ['id', 'requirement', 'category', 'priority'],
    displayName: (a) => a.id || a.requirement?.substring(0, 30) || 'Untitled Requirement',
  },
  gwt: {
    label: 'GWT Scenario',
    icon: '🧪',
    fields: ['given', 'when', 'then'],
    displayName: (a) => `Given: ${a.given?.substring(0, 20)}...` || 'Untitled Scenario',
  },
};

const UnifiedEditModal = ({
  isOpen,
  onClose,
  taskId,
  artifactType,
  artifact,
  onSaveComplete,
  customFields = null, // Optional: override default fields for this artifact type
}) => {
  // Flow state: 'editing' | 'analyzing' | 'preview' | 'applying'
  const [flowState, setFlowState] = useState('editing');
  const [editedValues, setEditedValues] = useState({});
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);

  // Get config for this artifact type
  const config = ARTIFACT_CONFIGS[artifactType] || {
    label: artifactType,
    icon: '📄',
    fields: Object.keys(artifact || {}),
    displayName: () => 'Unknown',
  };

  const fieldsToEdit = customFields || config.fields;

  // Initialize edited values when artifact changes
  useEffect(() => {
    if (artifact) {
      const initialValues = {};
      fieldsToEdit.forEach(field => {
        initialValues[field] = artifact[field] ?? '';
      });
      setEditedValues(initialValues);
    }
  }, [artifact, fieldsToEdit]);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setFlowState('editing');
      setAnalysisResult(null);
      setError(null);
    }
  }, [isOpen]);

  // Handle field changes
  const handleFieldChange = (field, value) => {
    setEditedValues(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  // Calculate what changed
  const getChangedFields = useCallback(() => {
    const changes = {};
    fieldsToEdit.forEach(field => {
      const original = artifact?.[field] ?? '';
      const edited = editedValues[field] ?? '';

      // Compare values (handle objects by JSON stringify)
      const originalStr = typeof original === 'object' ? JSON.stringify(original) : String(original);
      const editedStr = typeof edited === 'object' ? JSON.stringify(edited) : String(edited);

      if (originalStr !== editedStr) {
        changes[field] = edited;
      }
    });
    return changes;
  }, [artifact, editedValues, fieldsToEdit]);

  const hasChanges = Object.keys(getChangedFields()).length > 0;

  // Analyze edit and get cascade effects
  const handleAnalyze = async () => {
    const changes = getChangedFields();
    if (Object.keys(changes).length === 0) return;

    setFlowState('analyzing');
    setError(null);

    try {
      const result = await apiClient.analyzeEdit(taskId, {
        artifact_type: artifactType,
        artifact_id: artifact.id || artifact.name || artifact.title,
        changes,
      });

      setAnalysisResult(result);
      setFlowState('preview');
    } catch (err) {
      setError(err.userMessage || 'Failed to analyze edit');
      setFlowState('editing');
    }
  };

  // Apply the edit with selected cascades
  const handleApplyChanges = async (selectedCascades) => {
    setFlowState('applying');
    setError(null);

    try {
      // Transform selected cascades back to ArtifactChange format
      const approvedCascades = selectedCascades.map(c => ({
        artifact_type: c.type,
        artifact_id: c.id,
        field: c.field,
        old_value: c.old_value,
        new_value: c.value,
        reason: c.reason,
      }));

      const result = await apiClient.applyEdit(taskId, {
        artifact_type: artifactType,
        artifact_id: artifact.id || artifact.name || artifact.title,
        changes: getChangedFields(),
        approved_cascades: approvedCascades,
      });

      if (result.success) {
        onSaveComplete?.(result.updated_task);
        onClose();
      } else {
        setError('Failed to apply changes');
        setFlowState('preview');
      }
    } catch (err) {
      setError(err.userMessage || 'Failed to apply changes');
      setFlowState('preview');
    }
  };

  // Skip cascade preview and apply directly
  const handleApplyDirectOnly = async () => {
    setFlowState('applying');
    setError(null);

    try {
      const result = await apiClient.applyEdit(taskId, {
        artifact_type: artifactType,
        artifact_id: artifact.id || artifact.name || artifact.title,
        changes: getChangedFields(),
        approved_cascades: [],
      });

      if (result.success) {
        onSaveComplete?.(result.updated_task);
        onClose();
      } else {
        setError('Failed to apply changes');
        setFlowState('preview');
      }
    } catch (err) {
      setError(err.userMessage || 'Failed to apply changes');
      setFlowState('preview');
    }
  };

  // Render the edit form
  const renderEditForm = () => (
    <div style={styles.formContainer}>
      {fieldsToEdit.map(field => (
        <div key={field} style={styles.field}>
          <label style={styles.label}>{formatFieldLabel(field)}</label>
          {renderFieldInput(field)}
        </div>
      ))}
    </div>
  );

  // Render appropriate input for field type
  const renderFieldInput = (field) => {
    const value = editedValues[field] ?? '';

    // Array fields (like acceptance_criteria, gwt_scenarios)
    if (Array.isArray(value) || Array.isArray(artifact?.[field])) {
      return (
        <textarea
          value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              handleFieldChange(field, parsed);
            } catch {
              handleFieldChange(field, e.target.value);
            }
          }}
          style={{ ...styles.textarea, fontFamily: 'monospace' }}
          rows={6}
          placeholder={`Enter ${formatFieldLabel(field)} as JSON array...`}
        />
      );
    }

    // Long text fields
    if (['description', 'benefit', 'business_value', 'given', 'when', 'then', 'requirement'].includes(field)) {
      return (
        <textarea
          value={value}
          onChange={(e) => handleFieldChange(field, e.target.value)}
          style={styles.textarea}
          rows={4}
          placeholder={`Enter ${formatFieldLabel(field)}...`}
        />
      );
    }

    // Short text fields
    return (
      <input
        type="text"
        value={value}
        onChange={(e) => handleFieldChange(field, e.target.value)}
        style={styles.input}
        placeholder={`Enter ${formatFieldLabel(field)}...`}
      />
    );
  };

  // Format field name for display
  const formatFieldLabel = (field) => {
    return field
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  // Transform cascade changes for ChangePreview component
  const transformCascadesForPreview = () => {
    if (!analysisResult?.cascade_changes) return [];

    return analysisResult.cascade_changes.map(change => ({
      type: change.artifact_type,
      id: change.artifact_id,
      action: 'update',
      field: change.field,
      old_value: change.old_value,
      value: change.new_value,
      reason: change.reason,
    }));
  };

  // Render based on flow state
  if (flowState === 'preview' && analysisResult) {
    const cascadeChanges = transformCascadesForPreview();
    const hasCascades = cascadeChanges.length > 0;

    return (
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title="Review Changes"
        maxWidth="900px"
      >
        <div style={styles.previewContainer}>
          {/* Direct change summary */}
          <div style={styles.directChangeCard}>
            <div style={styles.directChangeHeader}>
              <span style={styles.icon}>{config.icon}</span>
              <Text style={styles.directChangeTitle}>
                Direct Edit: {config.label}
              </Text>
              <Badge variant="info" size="sm">Your Change</Badge>
            </div>
            <div style={styles.directChangeContent}>
              {Object.entries(getChangedFields()).map(([field, value]) => (
                <div key={field} style={styles.changeItem}>
                  <Text style={styles.changeField}>{formatFieldLabel(field)}:</Text>
                  <div style={styles.changeValues}>
                    <Text style={styles.oldValue}>
                      {typeof artifact[field] === 'object'
                        ? JSON.stringify(artifact[field])
                        : String(artifact[field] || '(empty)')}
                    </Text>
                    <span style={styles.arrow}>→</span>
                    <Text style={styles.newValue}>
                      {typeof value === 'object'
                        ? JSON.stringify(value)
                        : String(value || '(empty)')}
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cascade effects */}
          {hasCascades ? (
            <>
              <div style={styles.cascadeHeader}>
                <Text style={styles.cascadeTitle}>
                  Cascade Effects ({cascadeChanges.length} suggested changes)
                </Text>
                <Text style={styles.cascadeDescription}>
                  These changes are suggested to maintain consistency across all artifacts.
                  Select which ones to apply:
                </Text>
              </div>
              <ChangePreview
                changes={cascadeChanges}
                isOpen={true}
                onClose={() => setFlowState('editing')}
                onAccept={handleApplyChanges}
                onReject={handleApplyDirectOnly}
                loading={flowState === 'applying'}
              />
            </>
          ) : (
            <div style={styles.noCascades}>
              <Text style={styles.noCascadesText}>
                No cascade effects detected. Your change is isolated.
              </Text>
              <div style={styles.actions}>
                <Button variant="ghost" onClick={() => setFlowState('editing')}>
                  Back to Edit
                </Button>
                <Button
                  variant="primary"
                  onClick={handleApplyDirectOnly}
                  loading={flowState === 'applying'}
                >
                  Apply Change
                </Button>
              </div>
            </div>
          )}

          {error && (
            <div style={styles.error}>
              <Text style={styles.errorText}>{error}</Text>
            </div>
          )}
        </div>
      </Modal>
    );
  }

  // Main edit form view
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit ${config.label}`}
      maxWidth="600px"
    >
      <div style={styles.container}>
        {/* Header with artifact info */}
        <div style={styles.header}>
          <span style={styles.headerIcon}>{config.icon}</span>
          <Text style={styles.headerTitle}>
            {config.displayName(artifact || {})}
          </Text>
        </div>

        {/* Edit form */}
        {renderEditForm()}

        {/* Error display */}
        {error && (
          <div style={styles.error}>
            <Text style={styles.errorText}>{error}</Text>
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleAnalyze}
            disabled={!hasChanges || flowState === 'analyzing'}
            loading={flowState === 'analyzing'}
          >
            {flowState === 'analyzing' ? 'Analyzing...' : 'Review Changes'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  container: {
    padding: tokens.spacing[2],
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[5],
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.md,
  },
  headerIcon: {
    fontSize: '24px',
  },
  headerTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
  },
  formContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  label: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
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
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    paddingTop: tokens.spacing[5],
    marginTop: tokens.spacing[4],
    borderTop: '1px solid var(--color-border)',
  },
  error: {
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-error-bg)',
    borderRadius: tokens.borderRadius.md,
    marginTop: tokens.spacing[4],
  },
  errorText: {
    color: 'var(--color-error)',
    fontSize: tokens.typography.fontSize.sm[0],
  },
  // Preview styles
  previewContainer: {
    padding: tokens.spacing[2],
  },
  directChangeCard: {
    backgroundColor: 'var(--color-bg-secondary)',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing[4],
    marginBottom: tokens.spacing[5],
  },
  directChangeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },
  icon: {
    fontSize: '20px',
  },
  directChangeTitle: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
    flex: 1,
  },
  directChangeContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  changeItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },
  changeField: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },
  changeValues: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
  },
  oldValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-error)',
    textDecoration: 'line-through',
    opacity: 0.7,
  },
  arrow: {
    color: 'var(--color-text-muted)',
  },
  newValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-success)',
    fontWeight: tokens.typography.fontWeight.medium,
  },
  cascadeHeader: {
    marginBottom: tokens.spacing[4],
  },
  cascadeTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[2],
  },
  cascadeDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  noCascades: {
    textAlign: 'center',
    padding: tokens.spacing[6],
  },
  noCascadesText: {
    fontSize: tokens.typography.fontSize.base[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[4],
  },
};

export default UnifiedEditModal;

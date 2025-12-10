import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  Button,
  Text,
  LoadingSpinner,
  tokens,
} from '../../design-system';
import { useApp } from '../../contexts/AppContext';
import SchemaSection from '../SchemaSection';
import ChangePreview from '../ChangePreview';
import { useCascadeEdits } from '../../hooks/useCascadeEdits';
import unifiedApiClient from '../../services/unifiedApiClient';

const SchemasTab = ({ task, taskTree }) => {
  const queryClient = useQueryClient();
  const { showError, showSuccess } = useApp();
  const [activeSection, setActiveSection] = useState('commands'); // 'commands', 'events', 'read_models'

  const isProcessing = task.status === 'processing' || task.status === 'pending';

  // Setup cascade edits
  const currentState = {
    event_model: {
      commands: task.metadata?.commands || [],
      events: task.metadata?.extracted_events || [],
      read_models: task.metadata?.read_models || [],
      swimlanes: task.metadata?.swimlanes || [],
      slices: task.metadata?.slices || [],
      chapters: task.metadata?.chapters || [],
    },
    tasks: taskTree?.children || [],
    diagram: task.metadata?.diagram_layout || {},
  };

  const {
    isAnalyzing,
    isApplying,
    previewChanges,
    error: cascadeError,
    applyCascade,
    cancelCascade,
  } = useCascadeEdits(task.task_id, currentState);

  // Extract data
  const commands = task.metadata?.commands || [];
  const events = task.metadata?.extracted_events || [];
  const readModels = task.metadata?.read_models || [];

  // Handle schema updates with cascading
  const handleUpdateCommands = async (updatedCommands) => {
    try {
      // Prepare cascade payload
      const changes = {
        commands: updatedCommands
      };

      // Call cascade endpoint
      const response = await unifiedApiClient.post(`/tasks/${task.task_id}/cascade`, {
        changes,
        analysis_prompt: 'User updated command schemas. Analyze and propagate changes to ensure consistency across the event model.'
      });

      if (response.data.changes && response.data.changes.length > 0) {
        // Show preview modal
        // This will be handled by the useCascadeEdits hook
        showSuccess('Changes analyzed! Review the proposed updates.');
      } else {
        // No cascading changes needed, just update
        await unifiedApiClient.put(`/tasks/${task.task_id}`, {
          metadata: {
            ...task.metadata,
            commands: updatedCommands
          }
        });
        queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
        showSuccess('Commands updated successfully!');
      }
    } catch (error) {
      console.error('Error updating commands:', error);
      showError(error.response?.data?.detail || 'Failed to update commands');
    }
  };

  const handleUpdateEvents = async (updatedEvents) => {
    try {
      const changes = {
        events: updatedEvents
      };

      const response = await unifiedApiClient.post(`/tasks/${task.task_id}/cascade`, {
        changes,
        analysis_prompt: 'User updated event schemas. Analyze and propagate changes to ensure consistency across the event model.'
      });

      if (response.data.changes && response.data.changes.length > 0) {
        showSuccess('Changes analyzed! Review the proposed updates.');
      } else {
        await unifiedApiClient.put(`/tasks/${task.task_id}`, {
          metadata: {
            ...task.metadata,
            extracted_events: updatedEvents
          }
        });
        queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
        showSuccess('Events updated successfully!');
      }
    } catch (error) {
      console.error('Error updating events:', error);
      showError(error.response?.data?.detail || 'Failed to update events');
    }
  };

  const handleUpdateReadModels = async (updatedReadModels) => {
    try {
      const changes = {
        read_models: updatedReadModels
      };

      const response = await unifiedApiClient.post(`/tasks/${task.task_id}/cascade`, {
        changes,
        analysis_prompt: 'User updated read model schemas. Analyze and propagate changes to ensure consistency across the event model.'
      });

      if (response.data.changes && response.data.changes.length > 0) {
        showSuccess('Changes analyzed! Review the proposed updates.');
      } else {
        await unifiedApiClient.put(`/tasks/${task.task_id}`, {
          metadata: {
            ...task.metadata,
            read_models: updatedReadModels
          }
        });
        queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
        showSuccess('Read models updated successfully!');
      }
    } catch (error) {
      console.error('Error updating read models:', error);
      showError(error.response?.data?.detail || 'Failed to update read models');
    }
  };

  // If task is still processing, show loading state
  if (isProcessing) {
    return (
      <div style={styles.emptyStateContainer}>
        <div style={styles.loadingAnimation}>
          <LoadingSpinner size="large" />
        </div>
        <h3 style={styles.emptyStateTitle}>Generating Schemas</h3>
        <p style={styles.emptyStateDescription}>
          Data structures are being generated as part of the system blueprint analysis...
        </p>
      </div>
    );
  }

  // No schemas yet - show empty state
  if (commands.length === 0 && events.length === 0 && readModels.length === 0) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>📐</span>
        <h3 style={styles.emptyStateTitle}>No Schemas Available</h3>
        <p style={styles.emptyStateDescription}>
          Data structures will be generated when the system blueprint is created.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Tab Navigation */}
      <div style={styles.tabNav}>
        <button
          style={{
            ...styles.tabButton,
            ...(activeSection === 'commands' ? styles.tabButtonActive : {}),
          }}
          onClick={() => setActiveSection('commands')}
        >
          ⚡ User Actions ({commands.length})
        </button>
        <button
          style={{
            ...styles.tabButton,
            ...(activeSection === 'events' ? styles.tabButtonActive : {}),
          }}
          onClick={() => setActiveSection('events')}
        >
          ⚙️ Background Processes ({events.length})
        </button>
        <button
          style={{
            ...styles.tabButton,
            ...(activeSection === 'read_models' ? styles.tabButtonActive : {}),
          }}
          onClick={() => setActiveSection('read_models')}
        >
          📊 Screens/Views ({readModels.length})
        </button>
      </div>

      {/* Help Text */}
      <Card style={styles.helpCard}>
        <CardContent>
          <Text style={styles.helpTitle}>💡 About Data Structures</Text>
          <Text style={styles.helpText}>
            Data structures define the exact shape of information flowing through your app.
            Each user action, background process, and screen has typed fields that track where data comes from.
            Editing these will automatically update related parts of your system to keep everything consistent.
          </Text>
        </CardContent>
      </Card>

      {/* Data Flow Validation Results */}
      {task.metadata?.data_flow_validation && !task.metadata.data_flow_validation.valid && (
        <Card style={styles.errorCard}>
          <CardContent>
            <Text style={styles.errorTitle}>⚠️ Issues Found</Text>
            <Text style={styles.errorText}>
              {task.metadata.data_flow_validation.errors?.length || 0} issues found in your data flow.
              Fix these to ensure your app is ready for code generation.
            </Text>
            <div style={styles.errorList}>
              {(task.metadata.data_flow_validation.errors || []).slice(0, 5).map((error, idx) => (
                <div key={idx} style={styles.errorItem}>
                  <Text style={styles.errorMessage}>{error.message}</Text>
                  {error.suggestions && error.suggestions.length > 0 && (
                    <Text style={styles.errorSuggestion}>💡 {error.suggestions[0]}</Text>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Section Content */}
      {activeSection === 'commands' && (
        <SchemaSection
          title="User Actions"
          items={commands}
          itemType="command"
          onUpdate={handleUpdateCommands}
          editable={true}
        />
      )}

      {activeSection === 'events' && (
        <SchemaSection
          title="Background Processes"
          items={events}
          itemType="event"
          onUpdate={handleUpdateEvents}
          editable={true}
        />
      )}

      {activeSection === 'read_models' && (
        <SchemaSection
          title="Screens/Views"
          items={readModels}
          itemType="read_model"
          onUpdate={handleUpdateReadModels}
          editable={true}
        />
      )}

      {/* Cascade Analysis Loading State */}
      {isAnalyzing && (
        <Card style={{ marginTop: tokens.spacing[4], border: `2px solid ${tokens.colors.info[300]}` }}>
          <CardContent style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3], padding: tokens.spacing[4] }}>
            <LoadingSpinner size="medium" />
            <div>
              <Text style={{ fontWeight: tokens.typography.fontWeight.semibold, marginBottom: tokens.spacing[1] }}>
                Analyzing Changes...
              </Text>
              <Text style={{ color: 'var(--color-text-muted)', fontSize: tokens.typography.fontSize.sm[0] }}>
                Checking how this change affects the rest of your app.
              </Text>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cascade Error State */}
      {cascadeError && (
        <Card style={{ marginTop: tokens.spacing[4], border: `2px solid ${tokens.colors.error[300]}` }}>
          <CardContent style={{ padding: tokens.spacing[4] }}>
            <Text style={{ fontWeight: tokens.typography.fontWeight.semibold, marginBottom: tokens.spacing[2], color: tokens.colors.error[700] }}>
              Analysis Failed
            </Text>
            <Text>{cascadeError}</Text>
          </CardContent>
        </Card>
      )}

      {/* Cascade Preview Modal */}
      <ChangePreview
        changes={previewChanges?.changes || []}
        isOpen={!!previewChanges}
        onClose={cancelCascade}
        onAccept={async (selectedChanges) => {
          await applyCascade(selectedChanges);
          queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
          queryClient.invalidateQueries(['tasks', 'tree', task.task_id]);
        }}
        onReject={cancelCascade}
        loading={isApplying}
      />
    </div>
  );
};

const styles = {
  container: {
    padding: tokens.spacing[4],
  },

  emptyStateContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    textAlign: 'center',
    minHeight: '300px',
  },

  loadingAnimation: {
    marginBottom: tokens.spacing[4],
  },

  emptyStateIcon: {
    fontSize: '48px',
    marginBottom: tokens.spacing[4],
  },

  emptyStateTitle: {
    margin: 0,
    marginBottom: tokens.spacing[2],
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text)',
  },

  emptyStateDescription: {
    margin: 0,
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    maxWidth: '400px',
  },

  tabNav: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[4],
    borderBottom: `2px solid var(--color-border)`,
    paddingBottom: tokens.spacing[2],
  },

  tabButton: {
    padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.medium,
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: tokens.borderRadius.base,
    cursor: 'pointer',
    color: 'var(--color-text-muted)',
    transition: 'all 0.2s',
  },

  tabButtonActive: {
    backgroundColor: tokens.colors.primary[100],
    color: tokens.colors.primary[700],
    fontWeight: tokens.typography.fontWeight.semibold,
  },

  helpCard: {
    marginBottom: tokens.spacing[4],
    backgroundColor: tokens.colors.info[50],
    border: `1px solid ${tokens.colors.info[100]}`,
  },

  helpTitle: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.info[700],
    marginBottom: tokens.spacing[2],
  },

  helpText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.info[700],
    lineHeight: '1.6',
  },

  errorCard: {
    marginBottom: tokens.spacing[4],
    backgroundColor: tokens.colors.error[50],
    border: `2px solid ${tokens.colors.error[500]}`,
  },

  errorTitle: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.error[700],
    marginBottom: tokens.spacing[2],
  },

  errorText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.error[700],
    marginBottom: tokens.spacing[3],
  },

  errorList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  errorItem: {
    padding: tokens.spacing[2],
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.error[100]}`,
    borderRadius: tokens.borderRadius.base,
  },

  errorMessage: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.error[700],
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[1],
  },

  errorSuggestion: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.error[600],
    fontStyle: 'italic',
  },
};

export default SchemasTab;

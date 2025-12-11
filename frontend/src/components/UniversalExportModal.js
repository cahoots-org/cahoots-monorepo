/**
 * UniversalExportModal - Export project artifacts in various formats
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { Modal, Text, Button, tokens } from '../design-system';

const STORAGE_KEY = 'cahoots_export_preferences';

const ARTIFACT_CATEGORIES = [
  {
    name: 'Project Structure',
    artifacts: [
      { id: 'epics', name: 'Epics' },
      { id: 'stories', name: 'User Stories' },
      { id: 'tasks', name: 'Implementation Tasks' },
    ],
  },
  {
    name: 'Event Model',
    artifacts: [
      { id: 'commands', name: 'Commands' },
      { id: 'events', name: 'Events' },
      { id: 'read_models', name: 'Read Models' },
    ],
  },
  {
    name: 'Requirements',
    artifacts: [
      { id: 'functional_requirements', name: 'Functional Requirements' },
      { id: 'non_functional_requirements', name: 'Non-Functional Requirements' },
    ],
  },
  {
    name: 'Test Artifacts',
    artifacts: [
      { id: 'acceptance_criteria', name: 'Acceptance Criteria' },
      { id: 'gwt_scenarios', name: 'GWT Scenarios' },
    ],
  },
  {
    name: 'Documentation',
    artifacts: [
      { id: 'executive_summary', name: 'Executive Summary' },
      { id: 'proposal', name: 'Full Proposal' },
    ],
  },
];

const ALL_ARTIFACT_IDS = ARTIFACT_CATEGORIES.flatMap(c => c.artifacts.map(a => a.id));

const FORMATS = [
  { id: 'json', name: 'JSON', icon: '{ }' },
  { id: 'csv', name: 'CSV', icon: 'table' },
  { id: 'markdown', name: 'Markdown', icon: 'md' },
  { id: 'yaml', name: 'YAML', icon: 'yml' },
  { id: 'llm_prompt', name: 'LLM Prompt', icon: 'ai' },
];

const PROMPT_TEMPLATES = [
  { id: 'design_review', name: 'Design Review', description: 'Review architecture and design decisions' },
  { id: 'implementation_guide', name: 'Implementation Guide', description: 'Step-by-step implementation instructions' },
  { id: 'test_generation', name: 'Test Generation', description: 'Generate test cases from requirements' },
  { id: 'documentation', name: 'Documentation', description: 'Create technical documentation' },
  { id: 'custom', name: 'Custom', description: 'Write your own prompt' },
];

const PRESETS = [
  { id: 'all', name: 'All Artifacts', artifacts: ALL_ARTIFACT_IDS },
  { id: 'pm', name: 'PM Package', artifacts: ['epics', 'stories', 'tasks', 'functional_requirements', 'non_functional_requirements'] },
  { id: 'dev', name: 'Dev Package', artifacts: ['epics', 'stories', 'tasks', 'commands', 'events', 'read_models', 'gwt_scenarios'] },
  { id: 'consultant', name: 'Consultant Package', artifacts: ['epics', 'stories', 'functional_requirements', 'non_functional_requirements', 'executive_summary', 'proposal'] },
];

const UniversalExportModal = ({ isOpen, onClose, taskId, onSuccess }) => {
  // Load saved preferences or use defaults
  const loadPreferences = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load export preferences:', e);
    }
    // Default: all artifacts selected
    return {
      artifacts: ALL_ARTIFACT_IDS,
      format: 'json',
      outputMethod: 'download',
      downloadStructure: 'single',
      includeMetadata: true,
      includeIds: true,
      flattenHierarchy: false,
      promptTemplate: 'design_review',
      customInstructions: '',
    };
  };

  const [preferences, setPreferences] = useState(loadPreferences);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Save preferences when they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
    } catch (e) {
      console.warn('Failed to save export preferences:', e);
    }
  }, [preferences]);

  const updatePreference = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const toggleArtifact = (artifactId) => {
    setPreferences(prev => {
      const artifacts = prev.artifacts.includes(artifactId)
        ? prev.artifacts.filter(id => id !== artifactId)
        : [...prev.artifacts, artifactId];
      return { ...prev, artifacts };
    });
  };

  const applyPreset = (presetId) => {
    const preset = PRESETS.find(p => p.id === presetId);
    if (preset) {
      updatePreference('artifacts', preset.artifacts);
    }
  };

  const clearSelection = () => {
    updatePreference('artifacts', []);
  };

  const handleExport = async () => {
    if (preferences.artifacts.length === 0) {
      setError('Please select at least one artifact to export');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const requestBody = {
        artifacts: preferences.artifacts,
        format: preferences.format,
        include_metadata: preferences.includeMetadata,
        include_ids: preferences.includeIds,
        flatten_hierarchy: preferences.flattenHierarchy,
      };

      // Add download structure for non-LLM formats when downloading
      if (preferences.outputMethod === 'download' && preferences.format !== 'llm_prompt') {
        requestBody.download_structure = preferences.downloadStructure || 'single';
      }

      // Add LLM prompt specific fields
      if (preferences.format === 'llm_prompt') {
        requestBody.prompt_template = preferences.promptTemplate;
        if (preferences.promptTemplate === 'custom' && preferences.customInstructions) {
          requestBody.custom_instructions = preferences.customInstructions;
        }
      }

      // Get auth token
      const token = localStorage.getItem('token') || 'dev-bypass-token';
      const apiUrl = window.CAHOOTS_CONFIG?.API_URL || '/api';

      if (preferences.outputMethod === 'clipboard') {
        // For clipboard, we need to get the content as text
        const response = await axios.post(
          `${apiUrl}/tasks/${taskId}/export`,
          requestBody,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            responseType: 'text',
          }
        );

        await navigator.clipboard.writeText(response.data);
        onSuccess?.('Copied to clipboard');
        onClose();
      } else {
        // For download, get as blob
        const response = await axios.post(
          `${apiUrl}/tasks/${taskId}/export`,
          requestBody,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            responseType: 'blob',
          }
        );

        // Determine file extension based on format and structure
        let extension;
        let mimeType = 'application/octet-stream';

        if (requestBody.download_structure === 'zip') {
          extension = 'zip';
          mimeType = 'application/zip';
        } else if (preferences.format === 'markdown') {
          extension = 'md';
          mimeType = 'text/markdown';
        } else if (preferences.format === 'llm_prompt') {
          extension = 'txt';
          mimeType = 'text/plain';
        } else {
          extension = preferences.format;
        }

        // Create download link
        const blob = new Blob([response.data], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${taskId}-export.${extension}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        onSuccess?.('Export downloaded successfully');
        onClose();
      }
    } catch (err) {
      console.error('Export failed:', err);
      setError(err.message || 'Export failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Export Project" size="xl">
      <div style={styles.container}>
        {error && (
          <div style={styles.error}>
            <Text style={styles.errorText}>{error}</Text>
          </div>
        )}

        <div style={styles.columns}>
          {/* Left Column: Artifact Selection */}
          <div style={styles.leftColumn}>
            <Text style={styles.sectionTitle}>Select Artifacts</Text>

            {ARTIFACT_CATEGORIES.map(category => (
              <div key={category.name} style={styles.category}>
                <Text style={styles.categoryName}>{category.name}</Text>
                {category.artifacts.map(artifact => (
                  <label key={artifact.id} style={styles.artifactRow}>
                    <input
                      type="checkbox"
                      checked={preferences.artifacts.includes(artifact.id)}
                      onChange={() => toggleArtifact(artifact.id)}
                      style={styles.checkbox}
                    />
                    <Text style={styles.artifactName}>{artifact.name}</Text>
                  </label>
                ))}
              </div>
            ))}
          </div>

          {/* Right Column: Format & Options */}
          <div style={styles.rightColumn}>
            <Text style={styles.sectionTitle}>Format & Options</Text>

            {/* Format Selection */}
            <div style={styles.section}>
              <Text style={styles.label}>Format</Text>
              <div style={styles.formatGrid}>
                {FORMATS.map(fmt => (
                  <div
                    key={fmt.id}
                    style={{
                      ...styles.formatOption,
                      ...(preferences.format === fmt.id ? styles.formatOptionSelected : {}),
                    }}
                    onClick={() => updatePreference('format', fmt.id)}
                  >
                    <span style={styles.formatIcon}>{fmt.icon}</span>
                    <Text style={styles.formatName}>{fmt.name}</Text>
                  </div>
                ))}
              </div>
            </div>

            {/* LLM Prompt Options */}
            {preferences.format === 'llm_prompt' && (
              <div style={styles.section}>
                <Text style={styles.label}>Prompt Template</Text>
                <select
                  value={preferences.promptTemplate}
                  onChange={(e) => updatePreference('promptTemplate', e.target.value)}
                  style={styles.select}
                >
                  {PROMPT_TEMPLATES.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
                <Text style={styles.templateDescription}>
                  {PROMPT_TEMPLATES.find(t => t.id === preferences.promptTemplate)?.description}
                </Text>

                {preferences.promptTemplate === 'custom' && (
                  <textarea
                    value={preferences.customInstructions}
                    onChange={(e) => updatePreference('customInstructions', e.target.value)}
                    placeholder="Enter your custom instructions for the LLM..."
                    style={styles.textarea}
                    rows={4}
                  />
                )}
              </div>
            )}

            {/* Output Method */}
            <div style={styles.section}>
              <Text style={styles.label}>Output</Text>
              <div style={styles.radioGroup}>
                <label style={styles.radioLabel}>
                  <input
                    type="radio"
                    name="outputMethod"
                    value="download"
                    checked={preferences.outputMethod === 'download'}
                    onChange={() => updatePreference('outputMethod', 'download')}
                    style={styles.radio}
                  />
                  <Text>Download File</Text>
                </label>
                <label style={styles.radioLabel}>
                  <input
                    type="radio"
                    name="outputMethod"
                    value="clipboard"
                    checked={preferences.outputMethod === 'clipboard'}
                    onChange={() => updatePreference('outputMethod', 'clipboard')}
                    style={styles.radio}
                  />
                  <Text>Copy to Clipboard</Text>
                </label>
              </div>
            </div>

            {/* Download Structure (only for download, not clipboard) */}
            {preferences.outputMethod === 'download' && preferences.format !== 'llm_prompt' && (
              <div style={styles.section}>
                <Text style={styles.label}>Download Structure</Text>
                <div style={styles.radioGroup}>
                  <label style={styles.radioLabel}>
                    <input
                      type="radio"
                      name="downloadStructure"
                      value="single"
                      checked={preferences.downloadStructure === 'single'}
                      onChange={() => updatePreference('downloadStructure', 'single')}
                      style={styles.radio}
                    />
                    <Text>Single Document</Text>
                  </label>
                  <label style={styles.radioLabel}>
                    <input
                      type="radio"
                      name="downloadStructure"
                      value="zip"
                      checked={preferences.downloadStructure === 'zip'}
                      onChange={() => updatePreference('downloadStructure', 'zip')}
                      style={styles.radio}
                    />
                    <Text>ZIP Archive</Text>
                  </label>
                </div>
                <Text style={styles.structureHint}>
                  {preferences.downloadStructure === 'zip'
                    ? 'Each artifact type in a separate file'
                    : 'All artifacts combined in one file'}
                </Text>
              </div>
            )}

            {/* Options */}
            <div style={styles.section}>
              <Text style={styles.label}>Options</Text>
              <label style={styles.optionRow}>
                <input
                  type="checkbox"
                  checked={preferences.includeMetadata}
                  onChange={(e) => updatePreference('includeMetadata', e.target.checked)}
                  style={styles.checkbox}
                />
                <Text>Include metadata</Text>
              </label>
              <label style={styles.optionRow}>
                <input
                  type="checkbox"
                  checked={preferences.includeIds}
                  onChange={(e) => updatePreference('includeIds', e.target.checked)}
                  style={styles.checkbox}
                />
                <Text>Include IDs</Text>
              </label>
              {preferences.format === 'csv' && (
                <label style={styles.optionRow}>
                  <input
                    type="checkbox"
                    checked={preferences.flattenHierarchy}
                    onChange={(e) => updatePreference('flattenHierarchy', e.target.checked)}
                    style={styles.checkbox}
                  />
                  <Text>Flatten hierarchy</Text>
                </label>
              )}
            </div>
          </div>
        </div>

        {/* Presets */}
        <div style={styles.presetsSection}>
          <Text style={styles.label}>Quick Presets</Text>
          <div style={styles.presetButtons}>
            {PRESETS.map(preset => (
              <Button
                key={preset.id}
                variant="ghost"
                size="sm"
                onClick={() => applyPreset(preset.id)}
              >
                {preset.name}
              </Button>
            ))}
            <Button variant="ghost" size="sm" onClick={clearSelection}>
              Clear
            </Button>
          </div>
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <Text style={styles.selectionCount}>
            {preferences.artifacts.length} artifact{preferences.artifacts.length !== 1 ? 's' : ''} selected
          </Text>
          <div style={styles.actionButtons}>
            <Button variant="ghost" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleExport}
              loading={loading}
              disabled={preferences.artifacts.length === 0}
              icon={ArrowDownTrayIcon}
            >
              {preferences.outputMethod === 'clipboard' ? 'Copy' : 'Export'}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

const styles = {
  container: {
    padding: tokens.spacing[4],
  },
  error: {
    backgroundColor: `${tokens.colors.error[500]}15`,
    border: `1px solid ${tokens.colors.error[500]}`,
    borderRadius: tokens.borderRadius.md,
    padding: tokens.spacing[3],
    marginBottom: tokens.spacing[4],
  },
  errorText: {
    color: tokens.colors.error[600],
    fontSize: tokens.typography.fontSize.sm[0],
  },
  columns: {
    display: 'grid',
    gridTemplateColumns: '1fr 1.2fr',
    gap: tokens.spacing[8],
    marginBottom: tokens.spacing[4],
  },
  leftColumn: {
    maxHeight: '450px',
    overflowY: 'auto',
    paddingRight: tokens.spacing[3],
  },
  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },
  sectionTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: tokens.spacing[3],
  },
  category: {
    marginBottom: tokens.spacing[4],
  },
  categoryName: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  artifactRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[1]} 0`,
    cursor: 'pointer',
  },
  artifactName: {
    fontSize: tokens.typography.fontSize.sm[0],
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  section: {
    marginBottom: tokens.spacing[2],
  },
  label: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[2],
    display: 'block',
  },
  formatGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },
  formatOption: {
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.md,
    border: '2px solid var(--color-border)',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    minWidth: '70px',
  },
  formatOptionSelected: {
    borderColor: tokens.colors.primary[400],
    backgroundColor: `${tokens.colors.primary[400]}10`,
  },
  formatIcon: {
    display: 'block',
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '2px',
    fontFamily: 'monospace',
  },
  formatName: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  select: {
    width: '100%',
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
    backgroundColor: 'var(--color-surface)',
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[2],
  },
  templateDescription: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  textarea: {
    width: '100%',
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
    backgroundColor: 'var(--color-surface)',
    fontSize: tokens.typography.fontSize.sm[0],
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  radioGroup: {
    display: 'flex',
    gap: tokens.spacing[4],
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    cursor: 'pointer',
  },
  radio: {
    cursor: 'pointer',
  },
  optionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[2],
    cursor: 'pointer',
  },
  presetsSection: {
    borderTop: '1px solid var(--color-border)',
    paddingTop: tokens.spacing[4],
    marginBottom: tokens.spacing[4],
  },
  presetButtons: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },
  actions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTop: '1px solid var(--color-border)',
    paddingTop: tokens.spacing[4],
  },
  selectionCount: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  actionButtons: {
    display: 'flex',
    gap: tokens.spacing[2],
  },
  structureHint: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },
};

export default UniversalExportModal;

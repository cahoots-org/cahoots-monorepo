/**
 * TechStackSelectionModal - Modal for selecting tech stack before code generation
 *
 * Features:
 * - Lists available tech stacks with descriptions
 * - Shows tech stack details on selection
 * - Allows starting code generation
 */
import React, { useState, useEffect } from 'react';
import {
  Button,
  Text,
  LoadingSpinner,
  tokens,
} from '../design-system';
import apiClient from '../services/unifiedApiClient';

const TechStackSelectionModal = ({
  isOpen,
  onClose,
  projectId,
  onGenerationStarted,
}) => {
  const [techStacks, setTechStacks] = useState([]);
  const [selectedStack, setSelectedStack] = useState(null);
  const [stackDetails, setStackDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available tech stacks
  useEffect(() => {
    if (isOpen) {
      fetchTechStacks();
    }
  }, [isOpen]);

  // Fetch details when stack is selected
  useEffect(() => {
    if (selectedStack) {
      fetchStackDetails(selectedStack);
    }
  }, [selectedStack]);

  const fetchTechStacks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getTechStacks();
      setTechStacks(response.tech_stacks || []);
      if (response.tech_stacks?.length > 0) {
        setSelectedStack(response.tech_stacks[0].name);
      }
    } catch (err) {
      setError('Failed to load tech stacks. Please try again.');
      console.error('Failed to fetch tech stacks:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStackDetails = async (stackName) => {
    try {
      const details = await apiClient.getTechStackDetails(stackName);
      setStackDetails(details);
    } catch (err) {
      console.error('Failed to fetch stack details:', err);
    }
  };

  const handleStartGeneration = async () => {
    if (!selectedStack) return;

    setStarting(true);
    setError(null);
    try {
      const response = await apiClient.startCodeGeneration(projectId, selectedStack);
      onGenerationStarted?.(response);
      onClose();
    } catch (err) {
      setError(err.userMessage || 'Failed to start code generation. Please try again.');
      console.error('Failed to start generation:', err);
    } finally {
      setStarting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <Text style={styles.title}>Generate Code</Text>
          <button style={styles.closeButton} onClick={onClose}>
            &times;
          </button>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {loading ? (
            <div style={styles.loadingContainer}>
              <LoadingSpinner size="lg" />
              <Text style={styles.loadingText}>Loading tech stacks...</Text>
            </div>
          ) : (
            <>
              {/* Error Display */}
              {error && (
                <div style={styles.errorBanner}>
                  <Text style={styles.errorText}>{error}</Text>
                </div>
              )}

              {/* Tech Stack Selection - Grouped by Category */}
              <Text style={styles.sectionTitle}>Select a Tech Stack</Text>
              {Object.entries(
                techStacks.reduce((acc, stack) => {
                  const category = stack.category || 'backend';
                  if (!acc[category]) acc[category] = [];
                  acc[category].push(stack);
                  return acc;
                }, {})
              ).map(([category, stacks]) => (
                <div key={category} style={styles.categorySection}>
                  <Text style={styles.categoryTitle}>{getCategoryLabel(category)}</Text>
                  <div style={styles.stackGrid}>
                    {stacks.map((stack) => (
                      <div
                        key={stack.name}
                        style={{
                          ...styles.stackCard,
                          ...(selectedStack === stack.name && styles.stackCardSelected),
                        }}
                        onClick={() => setSelectedStack(stack.name)}
                      >
                        <div style={styles.stackIcon}>
                          {getStackIcon(stack.name, stack.category)}
                        </div>
                        <Text style={styles.stackName}>{stack.display_name}</Text>
                        <Text style={styles.stackDescription}>{stack.description}</Text>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Stack Details */}
              {stackDetails && (
                <div style={styles.detailsSection}>
                  <Text style={styles.sectionTitle}>Stack Details</Text>
                  <div style={styles.detailsGrid}>
                    <DetailItem
                      label="Source Directory"
                      value={stackDetails.src_dir}
                    />
                    <DetailItem
                      label="Test Directory"
                      value={stackDetails.test_dir}
                    />
                    <DetailItem
                      label="Test Command"
                      value={stackDetails.test_command}
                      isCode
                    />
                    <DetailItem
                      label="Build Command"
                      value={stackDetails.build_command}
                      isCode
                    />
                  </div>

                  {/* Dependencies Preview */}
                  {stackDetails.base_dependencies && Object.keys(stackDetails.base_dependencies).length > 0 && (
                    <div style={styles.depsSection}>
                      <Text style={styles.depsTitle}>Key Dependencies</Text>
                      <div style={styles.depsGrid}>
                        {Object.entries(stackDetails.base_dependencies).slice(0, 6).map(([name, version]) => (
                          <div key={name} style={styles.depBadge}>
                            <Text style={styles.depName}>{name}</Text>
                            <Text style={styles.depVersion}>{version}</Text>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <Button variant="outline" onClick={onClose} disabled={starting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleStartGeneration}
            disabled={!selectedStack || starting}
          >
            {starting ? (
              <>
                <LoadingSpinner size="sm" />
                <span style={{ marginLeft: '8px' }}>Starting...</span>
              </>
            ) : (
              'Start Generation'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

// Helper component for detail items
const DetailItem = ({ label, value, isCode }) => (
  <div style={styles.detailItem}>
    <Text style={styles.detailLabel}>{label}</Text>
    <Text style={{
      ...styles.detailValue,
      ...(isCode && styles.codeValue),
    }}>
      {value || '-'}
    </Text>
  </div>
);

// Get icon based on stack name or category
const getStackIcon = (stackName, category) => {
  const stackIcons = {
    'nodejs-api': '🟢',
    'nodejs-cli': '💻',
    'python-api': '🐍',
    'python-cli': '🐍',
    'go-api': '🔵',
    'react-spa': '⚛️',
  };

  if (stackIcons[stackName]) {
    return stackIcons[stackName];
  }

  // Fallback to category-based icons
  const categoryIcons = {
    'backend': '⚙️',
    'frontend': '🖥️',
    'cli': '💻',
    'worker': '⏱️',
  };
  return categoryIcons[category] || '📦';
};

// Get category display name
const getCategoryLabel = (category) => {
  const labels = {
    'backend': 'Backend APIs',
    'frontend': 'Frontend Apps',
    'cli': 'CLI Tools',
    'worker': 'Background Workers',
  };
  return labels[category] || category;
};

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.xl,
    maxWidth: '700px',
    width: '90%',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.3)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[6],
    borderBottom: '1px solid var(--color-border)',
  },
  title: {
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: 'var(--color-text-muted)',
    padding: tokens.spacing[2],
    lineHeight: 1,
  },
  content: {
    padding: tokens.spacing[6],
    overflowY: 'auto',
    flex: 1,
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[10],
    gap: tokens.spacing[4],
  },
  loadingText: {
    color: 'var(--color-text-muted)',
  },
  errorBanner: {
    backgroundColor: 'var(--color-danger-bg)',
    border: '1px solid var(--color-danger-border)',
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing[4],
    marginBottom: tokens.spacing[4],
  },
  errorText: {
    color: 'var(--color-danger)',
    fontSize: tokens.typography.fontSize.sm[0],
  },
  sectionTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: tokens.spacing[4],
  },
  categorySection: {
    marginBottom: tokens.spacing[6],
  },
  categoryTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[3],
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  stackGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: tokens.spacing[4],
    marginBottom: tokens.spacing[6],
  },
  stackCard: {
    backgroundColor: 'var(--color-bg-secondary)',
    border: '2px solid var(--color-border)',
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing[4],
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'center',
  },
  stackCardSelected: {
    borderColor: tokens.colors.primary[500],
    backgroundColor: 'var(--color-primary-bg)',
  },
  stackIcon: {
    fontSize: '32px',
    marginBottom: tokens.spacing[2],
  },
  stackName: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginBottom: tokens.spacing[1],
  },
  stackDescription: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    lineHeight: 1.4,
  },
  detailsSection: {
    marginTop: tokens.spacing[6],
    paddingTop: tokens.spacing[6],
    borderTop: '1px solid var(--color-border)',
  },
  detailsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: tokens.spacing[4],
  },
  detailItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },
  detailLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  detailValue: {
    fontSize: tokens.typography.fontSize.sm[0],
  },
  codeValue: {
    fontFamily: 'monospace',
    backgroundColor: 'var(--color-bg-tertiary)',
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.md,
  },
  depsSection: {
    marginTop: tokens.spacing[4],
  },
  depsTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  depsGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },
  depBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
    backgroundColor: 'var(--color-bg-tertiary)',
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.md,
    fontSize: tokens.typography.fontSize.xs[0],
  },
  depName: {
    fontWeight: tokens.typography.fontWeight.medium,
  },
  depVersion: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.xs[0],
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    padding: tokens.spacing[6],
    borderTop: '1px solid var(--color-border)',
  },
};

export default TechStackSelectionModal;

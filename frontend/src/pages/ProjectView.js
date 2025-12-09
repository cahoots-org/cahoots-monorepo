/**
 * ProjectView - Persona-aware project page (Simplified)
 *
 * Three personas with focused killer features:
 * - PM: Story points + JIRA/CSV export
 * - Dev: Event model + GWT scenarios
 * - Consultant: Scope summary + Proposal export
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Button,
  Text,
  Badge,
  LoadingSpinner,
  ErrorMessage,
  BackIcon,
  RefreshIcon,
  EditIcon,
  IconButton,
  tokens,
} from '../design-system';

import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useProjectContext } from '../hooks/api/useProjectContext';
import { useApp } from '../contexts/AppContext';

import ProjectSummary from '../components/ProjectSummary';
import RefineModal from '../components/RefineModal';
import ExportModal from '../components/ExportModal';
import UnifiedEditModal from '../components/UnifiedEditModal';

// Persona components
import PersonaSelectorBar from '../components/persona/PersonaSelectorBar';
import StoryPointDashboard from '../components/persona/pm/StoryPointDashboard';
import EventModelFlow from '../components/persona/dev/EventModelFlow';
import ExecutiveSummary from '../components/persona/consultant/ExecutiveSummary';

import {
  getPersonaTabs,
  generateProposalMarkdown,
  extractGWTScenarios,
  groupStoriesByEpic,
} from '../utils/personaDataTransforms';
import apiClient from '../services/unifiedApiClient';

const PERSONA_STORAGE_KEY = 'cahoots_persona_preference';

const ProjectView = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { connected, connect, disconnect, subscribe } = useWebSocket();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useApp();

  const [persona, setPersona] = useState(() => {
    return localStorage.getItem(PERSONA_STORAGE_KEY) || 'pm';
  });
  const [activeTab, setActiveTab] = useState(null);
  const [showRefineModal, setShowRefineModal] = useState(false);
  const [editModal, setEditModal] = useState({ open: false, type: null, artifact: null });

  useEffect(() => {
    const tabs = getPersonaTabs(persona);
    setActiveTab(tabs[0]?.id || null);
  }, [persona]);

  const handlePersonaChange = useCallback((newPersona) => {
    setPersona(newPersona);
    localStorage.setItem(PERSONA_STORAGE_KEY, newPersona);
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (!isAuthenticated()) return;
    connect().catch(err => console.error('[ProjectView] WebSocket error:', err));
    return () => disconnect();
  }, [isAuthenticated]);

  const {
    data: task,
    isLoading: taskLoading,
    error: taskError,
  } = useQuery({
    queryKey: ['tasks', 'detail', taskId],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}`);
      return response?.data || response;
    },
    enabled: !!taskId && isAuthenticated(),
  });

  const { data: taskTree, isLoading: treeLoading } = useQuery({
    queryKey: ['tasks', 'tree', taskId],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}/tree`);
      return response?.data || response;
    },
    enabled: !!taskId && isAuthenticated(),
  });

  useProjectContext(taskId);

  useEffect(() => {
    if (!connected || !taskId) return;
    const unsubscribe = subscribe((data) => {
      if (data.task_id === taskId || data.root_task_id === taskId) {
        queryClient.invalidateQueries(['tasks', 'detail', taskId]);
        queryClient.invalidateQueries(['tasks', 'tree', taskId]);
      }
    });
    return () => unsubscribe?.();
  }, [connected, subscribe, taskId, queryClient]);

  const handleRefresh = () => {
    if (!connected) connect().catch(console.error);
    queryClient.invalidateQueries(['tasks', 'detail', taskId]);
    queryClient.invalidateQueries(['tasks', 'tree', taskId]);
  };

  const handleResume = async () => {
    try {
      await apiClient.post(`/tasks/${taskId}/reprocess`);
      handleRefresh();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  };

  // Edit handlers
  const handleEditArtifact = useCallback((artifactType, artifact) => {
    setEditModal({ open: true, type: artifactType, artifact });
  }, []);

  const handleEditComplete = useCallback((updatedTask) => {
    setEditModal({ open: false, type: null, artifact: null });
    handleRefresh();
    showSuccess('Changes saved successfully!');
  }, [handleRefresh, showSuccess]);

  const isProcessing = task?.status === 'submitted' || task?.status === 'processing';
  const tabs = getPersonaTabs(persona);

  if (taskLoading) {
    return (
      <div style={styles.loadingContainer}>
        <LoadingSpinner size="lg" />
        <Text style={styles.loadingText}>Loading project...</Text>
      </div>
    );
  }

  if (taskError || !task) {
    return (
      <div style={styles.container}>
        <ErrorMessage
          title="Failed to load project"
          message={taskError?.message || 'Project not found'}
          onRetry={handleRefresh}
        />
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <Button
          variant="ghost"
          size="sm"
          icon={BackIcon}
          onClick={() => navigate('/dashboard')}
        >
          Dashboard
        </Button>

        {!isProcessing && (
          <PersonaSelectorBar
            activePersona={persona}
            onPersonaChange={handlePersonaChange}
          />
        )}

        <div style={styles.headerRight}>
          <ConnectionIndicator connected={connected} />
          <Button
            variant="ghost"
            size="sm"
            icon={RefreshIcon}
            onClick={handleRefresh}
            loading={taskLoading || treeLoading}
          >
            Refresh
          </Button>
        </div>
      </header>

      {/* Processing state */}
      {isProcessing && (
        <ProjectSummary
          task={task}
          taskTree={taskTree}
          onRefine={() => setShowRefineModal(true)}
          onResume={handleResume}
        />
      )}

      {/* Persona Hero */}
      {!isProcessing && (
        <>
          {persona === 'pm' && <StoryPointDashboard task={task} taskTree={taskTree} />}
          {persona === 'dev' && <EventModelFlow task={task} />}
          {persona === 'consultant' && <ExecutiveSummary task={task} taskTree={taskTree} />}
        </>
      )}

      {/* Tab Nav */}
      {!isProcessing && (
        <div style={styles.tabNav}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                ...styles.tabButton,
                ...(activeTab === tab.id ? styles.tabButtonActive : {}),
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Tab Content */}
      {!isProcessing && (
        <div style={styles.tabContent}>
          {/* PM Tabs */}
          {persona === 'pm' && activeTab === 'overview' && (
            <PMOverviewTab task={task} onEditArtifact={handleEditArtifact} />
          )}
          {persona === 'pm' && activeTab === 'export' && (
            <PMExportTab
              task={task}
              taskTree={taskTree}
              onShowToast={(msg, type) => type === 'error' ? showError(msg) : showSuccess(msg)}
            />
          )}

          {/* Dev Tabs */}
          {persona === 'dev' && activeTab === 'eventmodel' && (
            <DevEventModelTab task={task} onEditArtifact={handleEditArtifact} />
          )}
          {persona === 'dev' && activeTab === 'scenarios' && (
            <DevScenariosTab task={task} onEditArtifact={handleEditArtifact} />
          )}

          {/* Consultant Tabs */}
          {persona === 'consultant' && activeTab === 'scope' && (
            <ConsultantScopeTab task={task} onEditArtifact={handleEditArtifact} />
          )}
          {persona === 'consultant' && activeTab === 'requirements' && (
            <ConsultantRequirementsTab task={task} onEditArtifact={handleEditArtifact} />
          )}
          {persona === 'consultant' && activeTab === 'proposal' && (
            <ConsultantProposalTab task={task} taskTree={taskTree} onSuccess={showSuccess} />
          )}
        </div>
      )}

      {/* Modals */}
      <RefineModal
        isOpen={showRefineModal}
        onClose={() => setShowRefineModal(false)}
        task={task}
        taskTree={taskTree}
        onRefineComplete={handleRefresh}
      />

      <UnifiedEditModal
        isOpen={editModal.open}
        onClose={() => setEditModal({ open: false, type: null, artifact: null })}
        taskId={taskId}
        artifactType={editModal.type}
        artifact={editModal.artifact}
        onSaveComplete={handleEditComplete}
      />
    </div>
  );
};

/* ========== PM TABS ========== */

const PMOverviewTab = ({ task, onEditArtifact }) => {
  const epicsWithStories = groupStoriesByEpic(task);
  const [expandedStories, setExpandedStories] = useState({});

  const toggleStory = (storyKey) => {
    setExpandedStories(prev => ({
      ...prev,
      [storyKey]: !prev[storyKey]
    }));
  };

  // Helper to format story title
  const getStoryTitle = (story) => {
    if (story.title) return story.title;
    if (story.name) return story.name;
    if (story.actor && story.action) {
      return `As a ${story.actor}, ${story.action}`;
    }
    return 'Untitled Story';
  };

  // Get acceptance criteria from story
  const getAcceptanceCriteria = (story) => {
    if (story.acceptance_criteria && Array.isArray(story.acceptance_criteria)) {
      return story.acceptance_criteria;
    }
    if (story.gwt_scenarios && Array.isArray(story.gwt_scenarios)) {
      return story.gwt_scenarios.map(gwt =>
        `Given ${gwt.given}, when ${gwt.when}, then ${gwt.then}`
      );
    }
    return [];
  };

  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>Epics & Stories</Text>
      {epicsWithStories.length === 0 ? (
        <Text style={styles.emptyText}>No epics defined yet.</Text>
      ) : (
        <div style={styles.epicList}>
          {epicsWithStories.map((epic, i) => (
            <div key={i} style={styles.epicItem}>
              <div style={styles.epicItemHeader}>
                <Text style={styles.epicName}>{epic.name || epic.title}</Text>
                {onEditArtifact && (
                  <IconButton
                    icon={EditIcon}
                    size="sm"
                    variant="ghost"
                    onClick={() => onEditArtifact('epic', epic)}
                    title="Edit epic"
                  />
                )}
              </div>
              <Text style={styles.epicDesc}>{epic.description}</Text>
              {epic.stories && epic.stories.length > 0 ? (
                <div style={styles.storyList}>
                  {epic.stories.map((story, j) => {
                    const storyKey = `${i}-${j}`;
                    const isExpanded = expandedStories[storyKey];
                    const criteria = getAcceptanceCriteria(story);
                    const hasCriteria = criteria.length > 0;

                    return (
                      <div key={j} style={styles.storyItemWrapper}>
                        <div
                          style={{
                            ...styles.storyItem,
                            cursor: hasCriteria ? 'pointer' : 'default',
                          }}
                          onClick={() => hasCriteria && toggleStory(storyKey)}
                        >
                          <div style={styles.storyHeader}>
                            {hasCriteria && (
                              <span style={styles.storyChevron}>
                                {isExpanded ? '▼' : '▶'}
                              </span>
                            )}
                            <Text style={styles.storyTitle}>{getStoryTitle(story)}</Text>
                          </div>
                          <div style={styles.storyActions}>
                            {hasCriteria && (
                              <Badge style={styles.criteriaBadge}>
                                {criteria.length} criteria
                              </Badge>
                            )}
                            {onEditArtifact && (
                              <IconButton
                                icon={EditIcon}
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onEditArtifact('story', story);
                                }}
                                title="Edit story"
                              />
                            )}
                          </div>
                        </div>
                        {isExpanded && hasCriteria && (
                          <div style={styles.criteriaContainer}>
                            <Text style={styles.criteriaLabel}>Acceptance Criteria:</Text>
                            <ul style={styles.criteriaList}>
                              {criteria.map((criterion, k) => (
                                <li key={k} style={styles.criteriaItem}>
                                  {typeof criterion === 'string'
                                    ? criterion
                                    : criterion.description || JSON.stringify(criterion)
                                  }
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Text style={styles.noStoriesText}>No stories assigned</Text>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

const PMExportTab = ({ task, taskTree, onShowToast }) => {
  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>Export Project</Text>
      <Text style={styles.exportDesc}>
        Export your epics and stories to your preferred format.
      </Text>
      <ExportModal
        isOpen={true}
        onClose={() => {}}
        task={task}
        localTaskTree={taskTree}
        onShowToast={onShowToast}
        inline={true}
      />
    </Card>
  );
};

/* ========== DEV TABS ========== */

const DevEventModelTab = ({ task, onEditArtifact }) => {
  const events = task?.metadata?.extracted_events || [];
  const commands = task?.metadata?.commands || [];
  const readModels = task?.metadata?.read_models || [];

  const EditableBadge = ({ item, type, variant }) => {
    const itemObj = typeof item === 'string' ? { name: item } : item;
    return (
      <div
        style={styles.editableBadge}
        onClick={() => onEditArtifact && onEditArtifact(type, itemObj)}
        title={onEditArtifact ? `Click to edit ${type}` : undefined}
      >
        <Badge variant={variant}>
          {itemObj.name}
        </Badge>
        {onEditArtifact && <span style={styles.editHint}>Edit</span>}
      </div>
    );
  };

  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>Full Event Model</Text>
      <div style={styles.modelSection}>
        <Text style={styles.sectionHeader}>Commands ({commands.length})</Text>
        <div style={styles.badgeGrid}>
          {commands.map((cmd, i) => (
            <EditableBadge key={i} item={cmd} type="command" variant="primary" />
          ))}
        </div>
      </div>
      <div style={styles.modelSection}>
        <Text style={styles.sectionHeader}>Events ({events.length})</Text>
        <div style={styles.badgeGrid}>
          {events.map((evt, i) => (
            <EditableBadge key={i} item={evt} type="event" variant="warning" />
          ))}
        </div>
      </div>
      <div style={styles.modelSection}>
        <Text style={styles.sectionHeader}>Read Models ({readModels.length})</Text>
        <div style={styles.badgeGrid}>
          {readModels.map((rm, i) => (
            <EditableBadge key={i} item={rm} type="read_model" variant="info" />
          ))}
        </div>
      </div>
    </Card>
  );
};

const DevScenariosTab = ({ task, onEditArtifact }) => {
  const gwtScenarios = extractGWTScenarios(task);

  // Stories are in context, not metadata
  const stories = task?.context?.user_stories || task?.metadata?.user_stories || [];

  // Build test scenarios from acceptance criteria
  const buildTestScenarios = () => {
    const scenarios = [];
    stories.forEach((story) => {
      const storyTitle = story.title || story.name ||
        (story.actor && story.action ? `As a ${story.actor}, ${story.action}` : 'Untitled');

      const criteria = Array.isArray(story.acceptance_criteria)
        ? story.acceptance_criteria
        : story.acceptance_criteria ? [story.acceptance_criteria] : [];

      criteria.forEach((ac) => {
        scenarios.push({
          storyTitle,
          story, // Include full story for editing
          criterion: typeof ac === 'string' ? ac : ac.description || JSON.stringify(ac),
        });
      });
    });
    return scenarios;
  };

  const testScenarios = gwtScenarios.length > 0 ? null : buildTestScenarios();
  const hasGWT = gwtScenarios.length > 0;

  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>Test Scenarios</Text>
      {hasGWT ? (
        <div style={styles.scenarioList}>
          {gwtScenarios.map((s, i) => (
            <div key={i} style={styles.scenarioItem}>
              <div style={styles.scenarioHeader}>
                <Text style={styles.scenarioStory}>{s.storyTitle}</Text>
                {onEditArtifact && (
                  <IconButton
                    icon={EditIcon}
                    size="sm"
                    variant="ghost"
                    onClick={() => onEditArtifact('gwt', { ...s, id: `gwt_${i}` })}
                    title="Edit scenario"
                  />
                )}
              </div>
              <div style={styles.gwtBlock}>
                <Text style={styles.gwtLine}><strong>Given</strong> {s.given}</Text>
                <Text style={styles.gwtLine}><strong>When</strong> {s.when}</Text>
                <Text style={styles.gwtLine}><strong>Then</strong> {s.then}</Text>
              </div>
            </div>
          ))}
        </div>
      ) : testScenarios && testScenarios.length > 0 ? (
        <div style={styles.scenarioList}>
          {testScenarios.map((scenario, i) => (
            <div key={i} style={styles.testScenarioItem}>
              <div style={styles.scenarioHeader}>
                <Text style={styles.scenarioStory}>{scenario.storyTitle}</Text>
                {onEditArtifact && (
                  <IconButton
                    icon={EditIcon}
                    size="sm"
                    variant="ghost"
                    onClick={() => onEditArtifact('story', scenario.story)}
                    title="Edit story"
                  />
                )}
              </div>
              <div style={styles.testCriterion}>
                <span style={styles.testIcon}>✓</span>
                <Text style={styles.testText}>{scenario.criterion}</Text>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Text style={styles.emptyText}>No test scenarios defined yet.</Text>
      )}
    </Card>
  );
};

/* ========== CONSULTANT TABS ========== */

const ConsultantScopeTab = ({ task, onEditArtifact }) => {
  // Use swimlanes as feature breakdown (more granular), fallback to epics
  const swimlanes = task?.metadata?.swimlanes || [];
  const epics = task?.context?.epics || task?.metadata?.epics || [];

  // Helper to format command names into readable actions
  const formatAction = (cmd) => {
    // Convert "AddToCart" -> "Add to cart", "ProcessPayment" -> "Process payment"
    return cmd
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .toLowerCase()
      .replace(/^./, c => c.toUpperCase());
  };

  // Helper to format read model names into what users see
  const formatView = (rm) => {
    return rm
      .replace(/([A-Z])/g, ' $1')
      .replace(/View$|Display$|Screen$|Page$/i, '')
      .trim()
      .toLowerCase()
      .replace(/^./, c => c.toUpperCase());
  };

  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>What You're Building</Text>

      {swimlanes.length === 0 && epics.length === 0 ? (
        <Text style={styles.emptyText}>No features defined yet.</Text>
      ) : swimlanes.length > 0 ? (
        <div style={styles.capabilityList}>
          {swimlanes.map((sw, i) => (
            <div key={i} style={styles.capabilityCard}>
              <div style={styles.capabilityHeader}>
                <Text style={styles.capabilityName}>{sw.name}</Text>
                {onEditArtifact && (
                  <IconButton
                    icon={EditIcon}
                    size="sm"
                    variant="ghost"
                    onClick={() => onEditArtifact('swimlane', sw)}
                    title="Edit swimlane"
                  />
                )}
              </div>
              {sw.description && (
                <Text style={styles.capabilityDesc}>{sw.description}</Text>
              )}

              {/* What users can DO - the commands as readable actions */}
              {sw.commands?.length > 0 && (
                <div style={styles.capabilitySection}>
                  <Text style={styles.capabilitySectionTitle}>Users can:</Text>
                  <ul style={styles.capabilityActionList}>
                    {sw.commands.map((cmd, j) => (
                      <li key={j} style={styles.capabilityAction}>{formatAction(cmd)}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* What users can SEE - the read models as screens/views */}
              {sw.read_models?.length > 0 && (
                <div style={styles.capabilitySection}>
                  <Text style={styles.capabilitySectionTitle}>Users see:</Text>
                  <ul style={styles.capabilityActionList}>
                    {sw.read_models.map((rm, j) => (
                      <li key={j} style={styles.capabilityAction}>{formatView(rm)}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Automations as "The system will..." */}
              {sw.automations?.length > 0 && (
                <div style={styles.capabilitySection}>
                  <Text style={styles.capabilitySectionTitle}>Automatic behaviors:</Text>
                  <ul style={styles.capabilityActionList}>
                    {sw.automations.map((auto, j) => (
                      <li key={j} style={styles.capabilityAction}>{formatAction(auto)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div style={styles.capabilityList}>
          {epics.map((epic, i) => (
            <div key={i} style={styles.capabilityCard}>
              <Text style={styles.capabilityName}>{epic.title || epic.name}</Text>
              {epic.description && (
                <Text style={styles.capabilityDesc}>{epic.description}</Text>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

const ConsultantRequirementsTab = ({ task, onEditArtifact }) => {
  const requirements = task?.metadata?.requirements || {};
  const functional = requirements.functional_requirements || [];
  const nonFunctional = requirements.non_functional_requirements || [];

  const priorityColors = {
    'Must Have': tokens.colors.error[500],
    'Should Have': tokens.colors.warning[500],
    'Could Have': tokens.colors.info[500],
  };

  if (functional.length === 0 && nonFunctional.length === 0) {
    return (
      <Card style={styles.tabCard}>
        <Text style={styles.tabTitle}>Requirements</Text>
        <Text style={styles.emptyText}>No requirements generated yet. Requirements are generated during task analysis.</Text>
      </Card>
    );
  }

  return (
    <Card style={styles.tabCard}>
      <Text style={styles.tabTitle}>Requirements</Text>

      {functional.length > 0 && (
        <div style={styles.reqSection}>
          <Text style={styles.reqSectionTitle}>Functional Requirements</Text>
          <div style={styles.reqList}>
            {functional.map((req, i) => (
              <div key={i} style={styles.reqItem}>
                <div style={styles.reqHeader}>
                  <Badge variant="secondary" style={styles.reqId}>{req.id}</Badge>
                  <Badge style={{
                    ...styles.reqCategory,
                    backgroundColor: `${tokens.colors.info[500]}20`,
                    color: tokens.colors.info[500]
                  }}>{req.category}</Badge>
                  <Text style={{
                    ...styles.reqPriority,
                    color: priorityColors[req.priority] || tokens.colors.neutral[500]
                  }}>{req.priority}</Text>
                  {onEditArtifact && (
                    <IconButton
                      icon={EditIcon}
                      size="sm"
                      variant="ghost"
                      onClick={() => onEditArtifact('requirement', req)}
                      title="Edit requirement"
                      style={styles.reqEditButton}
                    />
                  )}
                </div>
                <Text style={styles.reqText}>{req.requirement}</Text>
              </div>
            ))}
          </div>
        </div>
      )}

      {nonFunctional.length > 0 && (
        <div style={styles.reqSection}>
          <Text style={styles.reqSectionTitle}>Non-Functional Requirements</Text>
          <div style={styles.reqList}>
            {nonFunctional.map((req, i) => (
              <div key={i} style={styles.reqItem}>
                <div style={styles.reqHeader}>
                  <Badge variant="secondary" style={styles.reqId}>{req.id}</Badge>
                  <Badge style={{
                    ...styles.reqCategory,
                    backgroundColor: `${tokens.colors.secondary[500]}20`,
                    color: tokens.colors.secondary[500]
                  }}>{req.category}</Badge>
                  <Text style={{
                    ...styles.reqPriority,
                    color: priorityColors[req.priority] || tokens.colors.neutral[500]
                  }}>{req.priority}</Text>
                  {onEditArtifact && (
                    <IconButton
                      icon={EditIcon}
                      size="sm"
                      variant="ghost"
                      onClick={() => onEditArtifact('non_functional_requirement', req)}
                      title="Edit requirement"
                      style={styles.reqEditButton}
                    />
                  )}
                </div>
                <Text style={styles.reqText}>{req.requirement}</Text>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

const ConsultantProposalTab = ({ task, taskTree, onSuccess }) => {
  const markdown = generateProposalMarkdown(task, taskTree);

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${task.task_id || 'project'}-proposal.md`;
    a.click();
    URL.revokeObjectURL(url);
    onSuccess('Proposal downloaded');
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    onSuccess('Copied to clipboard');
  };

  // Simple markdown to HTML renderer for preview
  const renderMarkdown = (md) => {
    return md
      .split('\n')
      .map((line, i) => {
        // Headers
        if (line.startsWith('### ')) {
          return <h4 key={i} style={styles.proposalH3}>{line.slice(4)}</h4>;
        }
        if (line.startsWith('## ')) {
          return <h3 key={i} style={styles.proposalH2}>{line.slice(3)}</h3>;
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} style={styles.proposalH1}>{line.slice(2)}</h2>;
        }
        // Bold text with **
        if (line.startsWith('**') && line.includes(':**')) {
          const parts = line.match(/^\*\*(.+?):\*\*\s*(.*)$/);
          if (parts) {
            return (
              <p key={i} style={styles.proposalBoldLine}>
                <strong>{parts[1]}:</strong> {parts[2]}
              </p>
            );
          }
        }
        // List items
        if (line.startsWith('- ')) {
          // Check for bold in list item (e.g., "- **FR-001** (Cart): ...")
          const boldMatch = line.match(/^- \*\*(.+?)\*\*\s*(.*)$/);
          if (boldMatch) {
            return (
              <li key={i} style={styles.proposalListItem}>
                <strong>{boldMatch[1]}</strong> {boldMatch[2]}
              </li>
            );
          }
          return <li key={i} style={styles.proposalListItem}>{line.slice(2)}</li>;
        }
        // Horizontal rule
        if (line.startsWith('---')) {
          return <hr key={i} style={styles.proposalHr} />;
        }
        // Italic (footer)
        if (line.startsWith('*') && line.endsWith('*')) {
          return <p key={i} style={styles.proposalFooter}>{line.slice(1, -1)}</p>;
        }
        // Empty lines
        if (line.trim() === '') {
          return <div key={i} style={{ height: '0.5rem' }} />;
        }
        // Regular paragraph
        return <p key={i} style={styles.proposalPara}>{line}</p>;
      });
  };

  return (
    <Card style={styles.tabCard}>
      <div style={styles.proposalHeader}>
        <Text style={styles.tabTitle}>Proposal Preview</Text>
        <div style={styles.proposalActions}>
          <Button variant="secondary" onClick={handleCopy} style={styles.proposalBtn}>
            Copy
          </Button>
          <Button variant="primary" onClick={handleDownload} style={styles.proposalBtn}>
            Download .md
          </Button>
        </div>
      </div>

      <div style={styles.proposalPreview}>
        {renderMarkdown(markdown)}
      </div>
    </Card>
  );
};

/* ========== HELPERS ========== */

const ConnectionIndicator = ({ connected }) => (
  <div style={styles.connIndicator}>
    <div style={{
      ...styles.connDot,
      backgroundColor: connected ? tokens.colors.success[500] : tokens.colors.error[500],
    }} />
    <Text style={styles.connText}>{connected ? 'Live' : 'Offline'}</Text>
  </div>
);

/* ========== STYLES ========== */

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: tokens.spacing[6],
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    gap: tokens.spacing[4],
  },
  loadingText: {
    color: 'var(--color-text-muted)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[6],
    gap: tokens.spacing[4],
    flexWrap: 'wrap',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  connIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  connDot: {
    width: '8px',
    height: '8px',
    borderRadius: tokens.borderRadius.full,
  },
  connText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
  },
  tabNav: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[4],
  },
  tabButton: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[3]} ${tokens.spacing[5]}`,
    border: 'none',
    borderRadius: tokens.borderRadius.lg,
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  tabButtonActive: {
    backgroundColor: tokens.colors.primary[400],
    color: 'white',
  },
  tabContent: {
    minHeight: '200px',
  },
  tabCard: {
    padding: tokens.spacing[6],
  },
  tabTitle: {
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginBottom: tokens.spacing[4],
  },
  emptyText: {
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
  exportDesc: {
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[4],
  },
  exportBtn: {
    minWidth: '200px',
  },
  // PM styles
  epicList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },
  epicItem: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  epicItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  epicName: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginBottom: tokens.spacing[1],
  },
  epicDesc: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[3],
  },
  storyList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
    paddingLeft: tokens.spacing[4],
    borderLeft: `2px solid ${tokens.colors.primary[400]}`,
  },
  storyItemWrapper: {
    marginBottom: tokens.spacing[2],
  },
  storyItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.md,
    transition: 'background-color 0.15s ease',
  },
  storyHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  storyChevron: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    width: '12px',
  },
  storyTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
  },
  storyActions: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  criteriaBadge: {
    fontSize: tokens.typography.fontSize.xs[0],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    backgroundColor: 'var(--color-surface)',
  },
  criteriaContainer: {
    marginLeft: tokens.spacing[6],
    marginTop: tokens.spacing[2],
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
  },
  criteriaLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: tokens.spacing[2],
  },
  noStoriesText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
    paddingLeft: tokens.spacing[4],
  },
  // Dev styles
  modelSection: {
    marginBottom: tokens.spacing[4],
  },
  sectionHeader: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  badgeGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },
  editableBadge: {
    position: 'relative',
    cursor: 'pointer',
    transition: 'transform 0.15s ease',
  },
  editHint: {
    position: 'absolute',
    bottom: '-16px',
    left: '50%',
    transform: 'translateX(-50%)',
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    opacity: 0,
    transition: 'opacity 0.15s ease',
  },
  scenarioList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },
  scenarioItem: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  scenarioHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[2],
  },
  scenarioStory: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.primary[400],
  },
  gwtBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },
  gwtLine: {
    fontSize: tokens.typography.fontSize.sm[0],
  },
  testScenarioItem: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  testCriterion: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[2],
  },
  testIcon: {
    color: tokens.colors.success[500],
    fontWeight: tokens.typography.fontWeight.bold,
    flexShrink: 0,
  },
  testText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
  },
  criteriaList: {
    margin: 0,
    paddingLeft: tokens.spacing[5],
  },
  criteriaItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[1],
  },
  // Consultant styles
  scopeList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },
  scopeItem: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  scopeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[2],
  },
  scopeName: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  scopeDesc: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
  featureMetrics: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginLeft: 'auto',
  },
  // Requirements styles
  reqSection: {
    marginBottom: tokens.spacing[6],
  },
  reqSectionTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginBottom: tokens.spacing[4],
    paddingBottom: tokens.spacing[2],
    borderBottom: '1px solid var(--color-border)',
  },
  reqList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },
  reqItem: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
  },
  reqHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[2],
  },
  reqId: {
    fontFamily: 'monospace',
    fontSize: tokens.typography.fontSize.xs[0],
  },
  reqCategory: {
    fontSize: tokens.typography.fontSize.xs[0],
  },
  reqPriority: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
  reqEditButton: {
    marginLeft: 'auto',
    opacity: 0.7,
    transition: 'opacity 0.2s ease',
  },
  reqText: {
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },
  // Consultant Capability styles - focused on what the product DOES
  capabilityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },
  capabilityCard: {
    padding: tokens.spacing[5],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  capabilityHeader: {
    marginBottom: tokens.spacing[2],
  },
  capabilityName: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.primary[400],
  },
  capabilityDesc: {
    fontSize: tokens.typography.fontSize.base[0],
    color: 'var(--color-text)',
    lineHeight: tokens.typography.lineHeight.relaxed,
    marginBottom: tokens.spacing[4],
  },
  capabilitySection: {
    marginTop: tokens.spacing[3],
  },
  capabilitySectionTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  capabilityActionList: {
    margin: 0,
    paddingLeft: tokens.spacing[5],
    listStyleType: 'disc',
  },
  capabilityAction: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    lineHeight: tokens.typography.lineHeight.relaxed,
    marginBottom: tokens.spacing[1],
  },
  // Proposal preview styles
  proposalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[4],
    flexWrap: 'wrap',
    gap: tokens.spacing[3],
  },
  proposalActions: {
    display: 'flex',
    gap: tokens.spacing[2],
  },
  proposalBtn: {
    minWidth: '100px',
  },
  proposalPreview: {
    padding: tokens.spacing[5],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
    maxHeight: '600px',
    overflowY: 'auto',
  },
  proposalH1: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    marginBottom: tokens.spacing[4],
    color: 'var(--color-text)',
  },
  proposalH2: {
    fontSize: tokens.typography.fontSize.xl[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginTop: tokens.spacing[5],
    marginBottom: tokens.spacing[3],
    color: tokens.colors.primary[400],
  },
  proposalH3: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginTop: tokens.spacing[4],
    marginBottom: tokens.spacing[2],
    color: 'var(--color-text)',
  },
  proposalPara: {
    fontSize: tokens.typography.fontSize.base[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
    marginBottom: tokens.spacing[2],
    color: 'var(--color-text)',
  },
  proposalBoldLine: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[1],
    color: 'var(--color-text)',
  },
  proposalListItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
    marginLeft: tokens.spacing[5],
    marginBottom: tokens.spacing[1],
    color: 'var(--color-text)',
  },
  proposalHr: {
    border: 'none',
    borderTop: '1px solid var(--color-border)',
    marginTop: tokens.spacing[6],
    marginBottom: tokens.spacing[3],
  },
  proposalFooter: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontStyle: 'italic',
    color: 'var(--color-text-muted)',
  },
};

export default ProjectView;

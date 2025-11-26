import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  Text,
  Heading2,
  Heading3,
  Badge,
  LoadingSpinner,
  IconButton,
  ChevronDownIcon,
  ChevronRightIcon,
  PlusIcon,
  EditIcon,
  TrashIcon,
  PlayIcon,
  tokens,
} from '../../design-system';
import { useApp } from '../../contexts/AppContext';
import EditableElement from '../EditableElement';
import ChangePreview from '../ChangePreview';
import AddSliceModal from '../AddSliceModal';
import { useCascadeEdits } from '../../hooks/useCascadeEdits';
import unifiedApiClient from '../../services/unifiedApiClient';

const EventModelTab = ({ task, taskTree }) => {
  const queryClient = useQueryClient();
  const { showError, showSuccess } = useApp();

  const [expandedChapters, setExpandedChapters] = useState(new Set());
  const [expandedSlices, setExpandedSlices] = useState(new Set());
  const [expandedElements, setExpandedElements] = useState(new Set());
  const [showSwimlanes, setShowSwimlanes] = useState(false);
  const [addSliceModalOpen, setAddSliceModalOpen] = useState(false);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

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
    handleEdit: handleCascadeEdit,
  } = useCascadeEdits(task.task_id, currentState);

  // Extract data
  const chapters = task.metadata?.chapters || [];
  const swimlanes = task.metadata?.swimlanes || [];
  const commands = task.metadata?.commands || [];
  const events = task.metadata?.extracted_events || [];
  const readModels = task.metadata?.read_models || [];
  const wireframes = task.metadata?.wireframes || [];
  const dataFlow = task.metadata?.data_flow || [];

  // Build full slice objects from chapter structure
  const slices = [];
  chapters.forEach(chapter => {
    (chapter.slices || []).forEach(sliceRef => {
      // Look up full command/event/read_model objects
      const cmd = commands.find(c => c.name === sliceRef.command);
      // Handle both 'events' (for commands) and 'source_events' (for read models)
      const eventNames = sliceRef.events || sliceRef.source_events || sliceRef.trigger_events || sliceRef.result_events || [];
      const evts = eventNames.map(name => events.find(e => e.name === name)).filter(Boolean);
      const rm = readModels.find(r => r.name === sliceRef.read_model);

      // Find wireframe for this slice
      const sliceName = sliceRef.command || sliceRef.read_model || sliceRef.name;
      const wireframe = wireframes.find(w => w.slice === sliceName);

      // Include automation slices (which have type but no command/read_model)
      if (cmd || rm || sliceRef.type === 'automation') {
        slices.push({
          name: sliceRef.command || sliceRef.read_model || sliceRef.name || 'Unnamed Slice',
          description: cmd?.description || rm?.description || sliceRef.description || '',
          chapter: chapter.name,
          swimlane: cmd?.swimlane || rm?.swimlane || evts[0]?.swimlane,
          command: cmd || {},
          event: evts[0] || {},
          events: evts,
          read_model: rm || {},
          gwt_scenarios: sliceRef.gwt_scenarios || [],
          wireframe: wireframe || sliceRef.wireframe,
          type: sliceRef.type,
          // Automation-specific fields
          trigger_events: sliceRef.trigger_events || [],
          result_events: sliceRef.result_events || [],
        });
      }
    });
  });

  // Toggle handlers
  const toggleChapter = (chapterId) => {
    const newExpanded = new Set(expandedChapters);
    if (newExpanded.has(chapterId)) {
      newExpanded.delete(chapterId);
    } else {
      newExpanded.add(chapterId);
    }
    setExpandedChapters(newExpanded);
  };

  const toggleSlice = (sliceId) => {
    const newExpanded = new Set(expandedSlices);
    if (newExpanded.has(sliceId)) {
      newExpanded.delete(sliceId);
    } else {
      newExpanded.add(sliceId);
    }
    setExpandedSlices(newExpanded);
  };

  const toggleElement = (elementKey) => {
    const newExpanded = new Set(expandedElements);
    if (newExpanded.has(elementKey)) {
      newExpanded.delete(elementKey);
    } else {
      newExpanded.add(elementKey);
    }
    setExpandedElements(newExpanded);
  };

  // Add slice handler
  const handleAddSliceClick = (chapterName) => {
    setSelectedChapter(chapterName);
    setAddSliceModalOpen(true);
  };

  const handleSaveSlice = async (sliceData) => {
    try {
      // Call backend to add slice with LLM analysis
      const response = await unifiedApiClient.post(`/tasks/${task.task_id}/slices`, sliceData);

      showSuccess('Slice created and analyzed successfully!');

      // Invalidate queries to refresh task data
      queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
      queryClient.invalidateQueries(['tasks', 'tree', task.task_id]);
    } catch (error) {
      console.error('Error creating slice:', error);
      showError(error.response?.data?.detail || 'Failed to create slice');
      throw error;
    }
  };

  // If task is still processing, show loading state
  if (isProcessing) {
    return (
      <div style={styles.emptyStateContainer}>
        <div style={styles.loadingAnimation}>
          <div style={styles.pulseCircle}>
            <span style={styles.loadingEmoji}>🔄</span>
          </div>
          <LoadingSpinner size="large" />
        </div>
        <h3 style={styles.emptyStateTitle}>Generating Event Model</h3>
        <p style={styles.emptyStateDescription}>
          Our AI is analyzing your task to extract events, commands, and read models.
          This usually takes 20-30 seconds...
        </p>
        <div style={styles.loadingSteps}>
          <div style={styles.loadingStep}>
            <div style={styles.stepDot} />
            <Text style={styles.stepText}>Identifying domain events</Text>
          </div>
          <div style={styles.loadingStep}>
            <div style={styles.stepDot} />
            <Text style={styles.stepText}>Extracting commands and interactions</Text>
          </div>
          <div style={styles.loadingStep}>
            <div style={styles.stepDot} />
            <Text style={styles.stepText}>Building read models</Text>
          </div>
          <div style={styles.loadingStep}>
            <div style={styles.stepDot} />
            <Text style={styles.stepText}>Organizing into chapters and swimlanes</Text>
          </div>
        </div>
      </div>
    );
  }

  // Handler for generating event model
  const handleGenerateEventModel = async () => {
    setIsGenerating(true);
    try {
      const result = await unifiedApiClient.post(`/events/generate-model/${task.task_id}`);
      showSuccess(`Event model generated: ${result.commands_count} commands, ${result.events_count} events, ${result.chapters_count} chapters`);

      // Refresh task data
      queryClient.invalidateQueries(['tasks', 'detail', task.task_id]);
      queryClient.invalidateQueries(['tasks', 'tree', task.task_id]);
    } catch (error) {
      console.error('Error generating event model:', error);
      showError(error.response?.data?.detail || 'Failed to generate event model');
    } finally {
      setIsGenerating(false);
    }
  };

  // No slices yet - show empty state
  if (slices.length === 0 && chapters.length === 0) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>📊</span>
        <h3 style={styles.emptyStateTitle}>No Event Model</h3>
        <p style={styles.emptyStateDescription}>
          Event model has not been generated yet for this task.
        </p>
        <Button
          variant="primary"
          size="lg"
          icon={PlayIcon}
          onClick={handleGenerateEventModel}
          disabled={isGenerating}
          style={{ marginTop: tokens.spacing[4] }}
        >
          {isGenerating ? 'Generating...' : 'Generate Event Model'}
        </Button>
        {isGenerating && (
          <div style={{ marginTop: tokens.spacing[4], display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
            <LoadingSpinner size="small" />
            <Text style={{ color: 'var(--color-text-muted)' }}>
              Analyzing tasks and building event model... This may take 30-60 seconds.
            </Text>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Chapters and Slices */}
      {chapters.map((chapter) => {
        const isChapterExpanded = expandedChapters.has(chapter.name);
        const chapterSlices = slices.filter(s => s.chapter === chapter.name);

        return (
          <Card key={chapter.name} style={styles.chapterCard}>
            <div
              style={styles.chapterHeader}
              onClick={() => toggleChapter(chapter.name)}
            >
              <div style={styles.chapterHeaderLeft}>
                <IconButton
                  icon={isChapterExpanded ? ChevronDownIcon : ChevronRightIcon}
                  size="sm"
                  variant="ghost"
                />
                <div>
                  <div style={styles.chapterTitle}>
                    <span style={styles.chapterIcon}>📖</span>
                    <Heading2 style={{ margin: 0 }}>Chapter: {chapter.name}</Heading2>
                  </div>
                  <Text style={styles.chapterDescription}>{chapter.description}</Text>
                </div>
              </div>
              <div style={styles.chapterActions}>
                <Badge variant="info">{chapterSlices.length} slices</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={PlusIcon}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAddSliceClick(chapter.name);
                  }}
                >
                  Add Slice
                </Button>
              </div>
            </div>

            {isChapterExpanded && (
              <CardContent style={styles.chapterContent}>
                {chapterSlices.length === 0 ? (
                  <Text style={styles.noSlicesText}>No slices in this chapter yet</Text>
                ) : (
                  chapterSlices.map((slice) => (
                    <SliceCard
                      key={slice.name}
                      slice={slice}
                      isExpanded={expandedSlices.has(slice.name)}
                      onToggle={() => toggleSlice(slice.name)}
                      expandedElements={expandedElements}
                      onToggleElement={toggleElement}
                      handleCascadeEdit={handleCascadeEdit}
                      swimlanes={swimlanes}
                      dataFlow={dataFlow}
                      events={events}
                    />
                  ))
                )}
              </CardContent>
            )}
          </Card>
        );
      })}

      {/* Orphaned slices (not in any chapter) */}
      {slices.filter(s => !s.chapter || !chapters.find(c => c.name === s.chapter)).length > 0 && (
        <Card style={styles.chapterCard}>
          <div style={styles.chapterHeader}>
            <div style={styles.chapterHeaderLeft}>
              <div>
                <Heading2 style={{ margin: 0 }}>Unassigned Slices</Heading2>
                <Text style={styles.chapterDescription}>Slices not assigned to a chapter</Text>
              </div>
            </div>
            <Badge variant="warning">
              {slices.filter(s => !s.chapter || !chapters.find(c => c.name === s.chapter)).length} slices
            </Badge>
          </div>
          <CardContent style={styles.chapterContent}>
            {slices
              .filter(s => !s.chapter || !chapters.find(c => c.name === s.chapter))
              .map((slice) => (
                <SliceCard
                  key={slice.name}
                  slice={slice}
                  isExpanded={expandedSlices.has(slice.name)}
                  onToggle={() => toggleSlice(slice.name)}
                  expandedElements={expandedElements}
                  onToggleElement={toggleElement}
                  handleCascadeEdit={handleCascadeEdit}
                  swimlanes={swimlanes}
                  dataFlow={dataFlow}
                  events={events}
                />
              ))}
          </CardContent>
        </Card>
      )}

      {/* Data Flow Section - REMOVED: Data flow now shown in context with wireframes per slice */}

      {/* Swimlanes Section */}
      <Card style={styles.swimlanesCard}>
        <div
          style={styles.swimlanesHeader}
          onClick={() => setShowSwimlanes(!showSwimlanes)}
        >
          <div style={styles.swimlanesHeaderLeft}>
            <IconButton
              icon={showSwimlanes ? ChevronDownIcon : ChevronRightIcon}
              size="sm"
              variant="ghost"
            />
            <div>
              <Heading2 style={{ margin: 0 }}>🏊 Swimlanes & Organization</Heading2>
              <Text style={styles.swimlanesDescription}>
                Business capabilities that group related functionality
              </Text>
            </div>
          </div>
          <Badge variant="secondary">{swimlanes.length} swimlanes</Badge>
        </div>

        {showSwimlanes && (
          <CardContent>
            <div style={styles.swimlanesGrid}>
              {swimlanes.map((swimlane, idx) => (
                <Card key={idx} style={styles.swimlaneCard}>
                  <CardContent>
                    <Heading3 style={styles.swimlaneName}>{swimlane.name}</Heading3>
                    <Text style={styles.swimlaneDescription}>{swimlane.description}</Text>
                    <div style={styles.swimlaneStats}>
                      <Badge variant="info" size="sm">{swimlane.commands?.length || 0} commands</Badge>
                      <Badge variant="secondary" size="sm">{swimlane.events?.length || 0} events</Badge>
                      <Badge variant="success" size="sm">{swimlane.read_models?.length || 0} read models</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Cascade Analysis Loading State */}
      {isAnalyzing && (
        <Card style={{ marginTop: tokens.spacing[4], border: `2px solid ${tokens.colors.info[300]}` }}>
          <CardContent style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3], padding: tokens.spacing[4] }}>
            <LoadingSpinner size="medium" />
            <div>
              <Heading3 style={{ margin: 0, marginBottom: tokens.spacing[1] }}>Analyzing Cascade Changes...</Heading3>
              <Text style={{ color: 'var(--color-text-muted)' }}>
                The AI is analyzing how this change affects the rest of your Event Model.
              </Text>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cascade Error State */}
      {cascadeError && (
        <Card style={{ marginTop: tokens.spacing[4], border: `2px solid ${tokens.colors.error[300]}` }}>
          <CardContent style={{ padding: tokens.spacing[4] }}>
            <Heading3 style={{ margin: 0, marginBottom: tokens.spacing[2], color: tokens.colors.error[700] }}>
              Cascade Analysis Failed
            </Heading3>
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

      {/* Add Slice Modal */}
      <AddSliceModal
        isOpen={addSliceModalOpen}
        onClose={() => setAddSliceModalOpen(false)}
        onSave={handleSaveSlice}
        chapterName={selectedChapter}
      />
    </div>
  );
};

// Slice Card Component
const SliceCard = ({
  slice,
  isExpanded,
  onToggle,
  expandedElements,
  onToggleElement,
  handleCascadeEdit,
  swimlanes,
  dataFlow,
  events
}) => {
  const command = slice.command || {};
  const event = slice.event || {};
  const readModel = slice.read_model || {};
  const gwtScenarios = slice.gwt_scenarios || [];

  return (
    <div style={styles.sliceCard}>
      <div style={styles.sliceHeader} onClick={onToggle}>
        <div style={styles.sliceHeaderLeft}>
          <IconButton
            icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
            size="sm"
            variant="ghost"
          />
          <div>
            <div style={styles.sliceTitle}>
              <span style={styles.sliceIcon}>🎯</span>
              <Heading3 style={{ margin: 0 }}>Slice: {slice.name}</Heading3>
            </div>
            {slice.description && (
              <Text style={styles.sliceDescription}>{slice.description}</Text>
            )}
          </div>
        </div>
        {slice.swimlane && (
          <Badge variant="primary" size="sm">🏊 {slice.swimlane}</Badge>
        )}
      </div>

      {isExpanded && (
        <div style={styles.sliceContent}>
          {/* Automation-specific rendering */}
          {slice.type === 'automation' && (
            <div style={styles.automationFlow}>
              <div style={styles.automationHeader}>
                <span style={styles.automationIcon}>⚙️</span>
                <Text style={styles.automationTitle}>Automation: {slice.name}</Text>
              </div>

              {/* Trigger Events */}
              {slice.trigger_events && slice.trigger_events.length > 0 && (
                <div style={styles.automationSection}>
                  <Text style={styles.automationLabel}>Triggered by:</Text>
                  <div style={styles.eventList}>
                    {slice.trigger_events.map((eventName, idx) => {
                      const evt = events.find(e => e.name === eventName);
                      return (
                        <div key={idx} style={styles.eventBadge}>
                          <span>🟠</span>
                          <Text style={styles.eventName}>{eventName}</Text>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div style={styles.flowArrow}>
                <Text style={styles.flowText}>↓ processes</Text>
              </div>

              {/* Result Events */}
              {slice.result_events && slice.result_events.length > 0 && (
                <div style={styles.automationSection}>
                  <Text style={styles.automationLabel}>Produces:</Text>
                  <div style={styles.eventList}>
                    {slice.result_events.map((eventName, idx) => {
                      const evt = events.find(e => e.name === eventName);
                      return (
                        <div key={idx} style={styles.eventBadge}>
                          <span>🟠</span>
                          <Text style={styles.eventName}>{eventName}</Text>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Standard slice rendering (command → event → read model) */}
          {slice.type !== 'automation' && (
            <>
              {/* Command */}
              {command.name && (
                <SliceElement
                  type="command"
                  icon="🔵"
                  label="Command"
                  element={command}
                  elementKey={`${slice.name}-command`}
                  isExpanded={expandedElements.has(`${slice.name}-command`)}
                  onToggle={() => onToggleElement(`${slice.name}-command`)}
                  handleCascadeEdit={handleCascadeEdit}
                  swimlanes={swimlanes}
                />
              )}

              {/* Flow indicator */}
              {command.name && event.name && (
                <div style={styles.flowArrow}>
                  <Text style={styles.flowText}>↓ triggers</Text>
                </div>
              )}

              {/* Event */}
              {event.name && (
                <SliceElement
                  type="event"
                  icon="🟠"
                  label="Event"
                  element={event}
                  elementKey={`${slice.name}-event`}
                  isExpanded={expandedElements.has(`${slice.name}-event`)}
                  onToggle={() => onToggleElement(`${slice.name}-event`)}
                  handleCascadeEdit={handleCascadeEdit}
                  swimlanes={swimlanes}
                />
              )}

              {/* Flow indicator */}
              {event.name && readModel.name && (
                <div style={styles.flowArrow}>
                  <Text style={styles.flowText}>↓ updates</Text>
                </div>
              )}

              {/* Read Model */}
              {readModel.name && (
                <SliceElement
                  type="read_model"
                  icon="🟢"
                  label="Read Model"
                  element={readModel}
                  elementKey={`${slice.name}-readmodel`}
                  isExpanded={expandedElements.has(`${slice.name}-readmodel`)}
                  onToggle={() => onToggleElement(`${slice.name}-readmodel`)}
                  handleCascadeEdit={handleCascadeEdit}
                  swimlanes={swimlanes}
                />
              )}
            </>
          )}

          {/* Wireframe */}
          {slice.wireframe && slice.wireframe.components && slice.wireframe.components.length > 0 && (
            <div style={styles.wireframeSection}>
              <div style={styles.wireframeHeader}>
                <span style={styles.wireframeIcon}>📱</span>
                <Text style={styles.wireframeTitle}>UI Wireframe: {slice.wireframe.name}</Text>
              </div>
              <div style={styles.wireframeComponents}>
                {slice.wireframe.components.map((component, idx) => (
                  <div key={idx} style={styles.wireframeComponent}>
                    <div style={styles.componentHeader}>
                      <span style={styles.componentIcon}>
                        {component.type === 'input' ? '📝' :
                         component.type === 'button' ? '🔘' :
                         component.type === 'text' ? '📄' :
                         component.type === 'list' ? '📋' :
                         component.type === 'table' ? '📊' :
                         component.type === 'form' ? '📑' : '📦'}
                      </span>
                      <Text style={styles.componentType}>{component.type}</Text>
                      <Text style={styles.componentLabel}>{component.label}</Text>
                    </div>
                    {component.field && (
                      <Text style={styles.componentField}>Field: {component.field}</Text>
                    )}
                    {component.triggers && (
                      <Text style={styles.componentTriggers}>→ Triggers: {component.triggers}</Text>
                    )}
                    {component.displays && (
                      <Text style={styles.componentDisplays}>← Displays: {Array.isArray(component.displays) ? component.displays.join(', ') : component.displays}</Text>
                    )}
                  </div>
                ))}
              </div>

              {/* Data Flow for this wireframe */}
              {(() => {
                const sliceDataFlows = dataFlow.filter(flow =>
                  flow.from && flow.to && (
                    flow.from.includes(slice.wireframe.name) ||
                    flow.to.includes(slice.wireframe.name) ||
                    flow.from.includes(slice.name) ||
                    flow.to.includes(slice.name)
                  )
                );

                if (sliceDataFlows.length > 0) {
                  return (
                    <div style={styles.sliceDataFlow}>
                      <Text style={styles.sliceDataFlowTitle}>💧 Data Flow ({sliceDataFlows.length})</Text>
                      {sliceDataFlows.map((flow, idx) => (
                        <div key={idx} style={styles.sliceDataFlowItem}>
                          <div style={styles.sliceDataFlowPath}>
                            <Text style={styles.sliceDataFlowFrom}>{flow.from.split(':')[1] || flow.from}</Text>
                            <span style={styles.sliceDataFlowArrow}>→</span>
                            <Text style={styles.sliceDataFlowTo}>{flow.to.split(':')[1] || flow.to}</Text>
                          </div>
                          {flow.description && (
                            <Text style={styles.sliceDataFlowDesc}>{flow.description}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          )}

          {/* GWT Scenarios */}
          {gwtScenarios.length > 0 && (
            <div style={styles.gwtSection}>
              <div style={styles.gwtHeader}>
                <span style={styles.gwtIcon}>✅</span>
                <Text style={styles.gwtTitle}>GWT Scenarios ({gwtScenarios.length})</Text>
                <Button variant="ghost" size="sm" icon={PlusIcon}>Add</Button>
              </div>
              <div style={styles.gwtList}>
                {gwtScenarios.map((gwt, idx) => (
                  <div key={idx} style={styles.gwtItem}>
                    {gwt.given && (
                      <div style={styles.gwtRow}>
                        <Text style={styles.gwtLabel}>Given:</Text>
                        <Text style={styles.gwtText}>{gwt.given}</Text>
                      </div>
                    )}
                    {gwt.when && (
                      <div style={styles.gwtRow}>
                        <Text style={styles.gwtLabel}>When:</Text>
                        <Text style={styles.gwtText}>{gwt.when}</Text>
                      </div>
                    )}
                    {gwt.then && (
                      <div style={styles.gwtRow}>
                        <Text style={styles.gwtLabel}>Then:</Text>
                        <Text style={styles.gwtText}>{gwt.then}</Text>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Slice Element Component (Command/Event/Read Model)
const SliceElement = ({
  type,
  icon,
  label,
  element,
  elementKey,
  isExpanded,
  onToggle,
  handleCascadeEdit,
  swimlanes
}) => {
  return (
    <div style={styles.elementContainer}>
      <div style={styles.elementHeader} onClick={onToggle}>
        <div style={styles.elementHeaderLeft}>
          <span style={styles.elementIcon}>{icon}</span>
          <Text style={styles.elementLabel}>{label}:</Text>
          <Text style={styles.elementName}>{element.name}</Text>
        </div>
        <div style={styles.elementHeaderRight}>
          {element.swimlane && (
            <Badge variant="primary" size="sm">🏊 {element.swimlane}</Badge>
          )}
          <IconButton
            icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
            size="sm"
            variant="ghost"
          />
        </div>
      </div>

      {isExpanded && (
        <div style={styles.elementDetails}>
          <div style={styles.detailRow}>
            <Text style={styles.detailLabel}>Name:</Text>
            <EditableElement
              value={element.name}
              onEdit={(newValue) => handleCascadeEdit({
                type: type,
                id: element.name,
                field: 'name',
                oldValue: element.name,
                newValue: newValue,
              })}
              elementType={type}
              elementId={element.name}
              field="name"
            >
              <Text style={styles.detailValue}>{element.name}</Text>
            </EditableElement>
          </div>

          {element.description && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Description:</Text>
              <EditableElement
                value={element.description}
                onEdit={(newValue) => handleCascadeEdit({
                  type: type,
                  id: element.name,
                  field: 'description',
                  oldValue: element.description,
                  newValue: newValue,
                })}
                elementType={type}
                elementId={element.name}
                field="description"
                multiline
              >
                <Text style={styles.detailValue}>{element.description}</Text>
              </EditableElement>
            </div>
          )}

          {element.swimlane && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Swimlane:</Text>
              <Text style={styles.detailValue}>{element.swimlane}</Text>
            </div>
          )}

          {element.triggered_by && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Triggered By:</Text>
              <Text style={styles.detailValue}>{element.triggered_by}</Text>
            </div>
          )}

          {element.triggers_events && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Triggers Events:</Text>
              <Text style={styles.detailValue}>{element.triggers_events.join(', ')}</Text>
            </div>
          )}

          {element.data_source && (
            <div style={styles.detailRow}>
              <Text style={styles.detailLabel}>Data Source:</Text>
              <Text style={styles.detailValue}>{element.data_source.join(', ')}</Text>
            </div>
          )}

          <div style={styles.detailActions}>
            <Button variant="ghost" size="sm" icon={TrashIcon}>Delete</Button>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
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

  // Chapter styles
  chapterCard: {
    border: `2px solid ${tokens.colors.info[200]}`,
    backgroundColor: 'var(--color-surface)',
  },

  chapterHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: tokens.spacing[4],
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface-hover)',
    },
  },

  chapterHeaderLeft: {
    display: 'flex',
    gap: tokens.spacing[3],
    flex: 1,
    alignItems: 'flex-start',
  },

  chapterTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  chapterIcon: {
    fontSize: '20px',
  },

  chapterDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  chapterActions: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  chapterContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-background)',
  },

  noSlicesText: {
    textAlign: 'center',
    color: 'var(--color-text-muted)',
    padding: tokens.spacing[4],
  },

  // Slice styles
  sliceCard: {
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'var(--color-surface)',
    overflow: 'hidden',
  },

  sliceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: tokens.spacing[3],
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface-hover)',
    },
  },

  sliceHeaderLeft: {
    display: 'flex',
    gap: tokens.spacing[2],
    flex: 1,
    alignItems: 'flex-start',
  },

  sliceTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  sliceIcon: {
    fontSize: '16px',
  },

  sliceDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  sliceContent: {
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-background)',
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  // Element styles (command/event/read model)
  elementContainer: {
    border: `1px solid var(--color-border)`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: 'var(--color-surface)',
  },

  elementHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[2],
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface-hover)',
    },
  },

  elementHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  elementHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  elementIcon: {
    fontSize: '16px',
  },

  elementLabel: {
    fontWeight: tokens.typography.fontWeight.medium,
    fontSize: tokens.typography.fontSize.sm[0],
  },

  elementName: {
    fontWeight: tokens.typography.fontWeight.semibold,
  },

  elementDetails: {
    padding: tokens.spacing[3],
    borderTop: `1px solid var(--color-border)`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  detailRow: {
    display: 'flex',
    gap: tokens.spacing[2],
    alignItems: 'flex-start',
  },

  detailLabel: {
    fontWeight: tokens.typography.fontWeight.medium,
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    minWidth: '120px',
  },

  detailValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    flex: 1,
  },

  detailActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[2],
    marginTop: tokens.spacing[2],
    paddingTop: tokens.spacing[2],
    borderTop: `1px solid var(--color-border)`,
  },

  // Flow arrow
  flowArrow: {
    display: 'flex',
    justifyContent: 'center',
    padding: `${tokens.spacing[1]} 0`,
  },

  flowText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },

  // Wireframe styles
  wireframeSection: {
    marginTop: tokens.spacing[2],
    padding: tokens.spacing[3],
    border: `1px solid ${tokens.colors.info[200]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: tokens.colors.info[50],
  },

  wireframeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },

  wireframeIcon: {
    fontSize: '16px',
  },

  wireframeTitle: {
    fontWeight: tokens.typography.fontWeight.medium,
    fontSize: tokens.typography.fontSize.sm[0],
  },

  wireframeComponents: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  wireframeComponent: {
    padding: tokens.spacing[2],
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.info[200]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  componentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  componentIcon: {
    fontSize: '14px',
  },

  componentType: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.info[700],
    textTransform: 'uppercase',
    backgroundColor: tokens.colors.info[100],
    padding: `2px ${tokens.spacing[1]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  componentLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },

  componentField: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
    marginLeft: tokens.spacing[5],
  },

  componentTriggers: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.primary[700],
    marginLeft: tokens.spacing[5],
    fontWeight: tokens.typography.fontWeight.medium,
  },

  componentDisplays: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.success[700],
    marginLeft: tokens.spacing[5],
    fontWeight: tokens.typography.fontWeight.medium,
  },

  // Slice-specific data flow styles (shown in wireframe context)
  sliceDataFlow: {
    marginTop: tokens.spacing[3],
    paddingTop: tokens.spacing[3],
    borderTop: `1px solid ${tokens.colors.info[300]}`,
  },

  sliceDataFlowTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.info[800],
    textTransform: 'uppercase',
    marginBottom: tokens.spacing[2],
  },

  sliceDataFlowItem: {
    padding: `${tokens.spacing[1]} 0`,
  },

  sliceDataFlowPath: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
    marginBottom: tokens.spacing[1],
  },

  sliceDataFlowFrom: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: 'monospace',
    color: tokens.colors.primary[700],
    backgroundColor: tokens.colors.primary[50],
    padding: `2px ${tokens.spacing[1]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  sliceDataFlowArrow: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.info[500],
  },

  sliceDataFlowTo: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: 'monospace',
    color: tokens.colors.success[700],
    backgroundColor: tokens.colors.success[50],
    padding: `2px ${tokens.spacing[1]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  sliceDataFlowDesc: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
    marginLeft: tokens.spacing[4],
  },

  // GWT styles
  gwtSection: {
    marginTop: tokens.spacing[2],
    padding: tokens.spacing[3],
    border: `1px solid ${tokens.colors.success[200]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: tokens.colors.success[50],
  },

  gwtHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[2],
  },

  gwtIcon: {
    fontSize: '16px',
  },

  gwtTitle: {
    fontWeight: tokens.typography.fontWeight.medium,
    fontSize: tokens.typography.fontSize.sm[0],
    flex: 1,
  },

  gwtList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  gwtItem: {
    padding: tokens.spacing[2],
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.success[200]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  gwtRow: {
    display: 'flex',
    gap: tokens.spacing[2],
    alignItems: 'flex-start',
    marginBottom: tokens.spacing[1],
  },

  gwtLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[700],
    textTransform: 'uppercase',
    minWidth: '60px',
  },

  gwtText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[700],
    flex: 1,
  },

  // Data flow styles
  dataFlowCard: {
    border: `2px solid ${tokens.colors.warning[200]}`,
    backgroundColor: 'var(--color-surface)',
  },

  dataFlowHeaderContent: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  dataFlowIcon: {
    fontSize: '24px',
  },

  dataFlowDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
    marginTop: tokens.spacing[1],
  },

  dataFlowList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  dataFlowItem: {
    padding: tokens.spacing[3],
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.warning[200]}`,
    borderRadius: tokens.borderRadius.base,
  },

  dataFlowPath: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  dataFlowFrom: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.primary[700],
    fontFamily: 'monospace',
    backgroundColor: tokens.colors.primary[50],
    padding: `2px ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  dataFlowArrow: {
    fontSize: tokens.typography.fontSize.lg[0],
    color: tokens.colors.warning[500],
  },

  dataFlowTo: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.success[700],
    fontFamily: 'monospace',
    backgroundColor: tokens.colors.success[50],
    padding: `2px ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.sm,
  },

  // Swimlanes section
  swimlanesCard: {
    border: `2px solid ${tokens.colors.primary[200]}`,
  },

  swimlanesHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[4],
    cursor: 'pointer',
  },

  swimlanesHeaderLeft: {
    display: 'flex',
    gap: tokens.spacing[3],
    alignItems: 'flex-start',
  },

  swimlanesDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  swimlanesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: tokens.spacing[3],
  },

  swimlaneCard: {
    border: `1px solid ${tokens.colors.primary[200]}`,
    backgroundColor: tokens.colors.primary[50],
  },

  swimlaneName: {
    margin: 0,
    marginBottom: tokens.spacing[2],
    color: tokens.colors.primary[700],
  },

  swimlaneDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[3],
  },

  swimlaneStats: {
    display: 'flex',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
  },

  // Automation styles
  automationFlow: {
    padding: tokens.spacing[3],
    border: `2px solid ${tokens.colors.warning[300]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: tokens.colors.warning[50],
  },

  automationHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },

  automationIcon: {
    fontSize: '20px',
  },

  automationTitle: {
    fontWeight: tokens.typography.fontWeight.semibold,
    fontSize: tokens.typography.fontSize.base[0],
    color: tokens.colors.warning[800],
  },

  automationSection: {
    marginBottom: tokens.spacing[2],
  },

  automationLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[2],
  },

  eventList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[2],
  },

  eventBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.warning[200]}`,
    borderRadius: tokens.borderRadius.base,
  },

  eventName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    fontFamily: tokens.typography.fontFamily.mono,
  },

  // Loading animation styles
  loadingAnimation: {
    position: 'relative',
    marginBottom: tokens.spacing[6],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },

  pulseCircle: {
    position: 'absolute',
    width: '120px',
    height: '120px',
    borderRadius: '50%',
    background: `radial-gradient(circle, ${tokens.colors.primary[200]}20, transparent)`,
    animation: 'pulse 2s ease-in-out infinite',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },

  loadingEmoji: {
    fontSize: '48px',
    animation: 'rotate 3s linear infinite',
  },

  loadingSteps: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
    marginTop: tokens.spacing[6],
    maxWidth: '500px',
    width: '100%',
  },

  loadingStep: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.md,
    border: `1px solid var(--color-border)`,
  },

  stepDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.primary[400],
    animation: 'pulse 1.5s ease-in-out infinite',
  },

  stepText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
};

// Add keyframes for animations
const styleSheet = document.styleSheets[0];
try {
  styleSheet.insertRule(`
    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
        opacity: 0.5;
      }
      50% {
        transform: scale(1.1);
        opacity: 0.8;
      }
    }
  `, styleSheet.cssRules.length);

  styleSheet.insertRule(`
    @keyframes rotate {
      from {
        transform: rotate(0deg);
      }
      to {
        transform: rotate(360deg);
      }
    }
  `, styleSheet.cssRules.length);
} catch (e) {
  // Silently fail if rules already exist
}

export default EventModelTab;

/**
 * EventModelTimeline - Clean Event Model Visualization
 *
 * Follows Event Modeling conventions:
 * - Blue: Commands (user intentions)
 * - Orange: Events (facts that happened)
 * - Green: Read Models / Views (what users see)
 * - Yellow: Automations / Policies (system reactions)
 * - Purple: Deciders (business logic)
 *
 * Layout: Timeline flows left-to-right, grouped by chapters (workflows)
 */
import React, { useState, useMemo } from 'react';
import { Text, tokens } from '../design-system';

const EventModelTimeline = ({ task }) => {
  const [selectedItem, setSelectedItem] = useState(null);
  const [viewMode, setViewMode] = useState('flow'); // 'flow' or 'grid'

  // Extract data
  const chapters = task?.metadata?.chapters || [];
  const swimlanes = task?.metadata?.swimlanes || [];
  const commands = task?.metadata?.commands || [];
  const events = task?.metadata?.extracted_events || [];
  const readModels = task?.metadata?.read_models || [];
  const automations = task?.metadata?.automations || [];

  // Build enriched slices from chapters
  const allSlices = useMemo(() => {
    const slices = [];

    chapters.forEach((chapter, chapterIdx) => {
      (chapter.slices || []).forEach((slice, sliceIdx) => {
        // Find full objects
        const cmd = commands.find(c => c.name === slice.command);
        const rm = readModels.find(r => r.name === slice.read_model);
        const sliceEvents = (slice.events || []).map(eName =>
          events.find(e => (e.name || e) === eName) || { name: eName }
        );

        slices.push({
          ...slice,
          id: `${chapterIdx}-${sliceIdx}`,
          chapterName: chapter.name,
          chapterIdx,
          commandObj: cmd,
          readModelObj: rm,
          eventObjs: sliceEvents,
        });
      });
    });

    return slices;
  }, [chapters, commands, events, readModels]);

  // If no data, show helpful empty state
  if (chapters.length === 0 && commands.length === 0) {
    return (
      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>📋</div>
        <Text style={styles.emptyTitle}>Event Model</Text>
        <Text style={styles.emptyText}>
          The event model will appear here once analysis is complete
        </Text>

        {/* Show legend for reference */}
        <div style={styles.legendRow}>
          <LegendItem color={COLORS.command} label="Commands" icon="▶" />
          <LegendItem color={COLORS.event} label="Events" icon="●" />
          <LegendItem color={COLORS.readModel} label="Views" icon="◧" />
          <LegendItem color={COLORS.automation} label="Automations" icon="⚡" />
        </div>
      </div>
    );
  }

  // Fallback: if we have commands/events but no chapters, show flat view
  if (chapters.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <Text style={styles.title}>Event Model</Text>
          <div style={styles.stats}>
            <StatBadge count={commands.length} label="Commands" color={COLORS.command} />
            <StatBadge count={events.length} label="Events" color={COLORS.event} />
            <StatBadge count={readModels.length} label="Views" color={COLORS.readModel} />
          </div>
        </div>

        <div style={styles.flatFlow}>
          {/* Commands column */}
          <div style={styles.column}>
            <div style={styles.columnHeader}>
              <span style={{...styles.columnIcon, backgroundColor: COLORS.command}}>▶</span>
              <Text style={styles.columnTitle}>Commands</Text>
            </div>
            <div style={styles.columnItems}>
              {commands.slice(0, 12).map((cmd, i) => (
                <ItemCard
                  key={i}
                  item={cmd}
                  type="command"
                  isSelected={selectedItem?.name === cmd.name}
                  onClick={() => setSelectedItem(selectedItem?.name === cmd.name ? null : {...cmd, type: 'command'})}
                />
              ))}
              {commands.length > 12 && (
                <Text style={styles.moreText}>+{commands.length - 12} more</Text>
              )}
            </div>
          </div>

          {/* Arrow */}
          <div style={styles.flowArrow}>
            <div style={styles.arrowLine} />
            <Text style={styles.arrowLabel}>triggers</Text>
          </div>

          {/* Events column */}
          <div style={styles.column}>
            <div style={styles.columnHeader}>
              <span style={{...styles.columnIcon, backgroundColor: COLORS.event}}>●</span>
              <Text style={styles.columnTitle}>Events</Text>
            </div>
            <div style={styles.columnItems}>
              {events.slice(0, 12).map((evt, i) => (
                <ItemCard
                  key={i}
                  item={typeof evt === 'string' ? {name: evt} : evt}
                  type="event"
                  isSelected={selectedItem?.name === (evt.name || evt)}
                  onClick={() => setSelectedItem(selectedItem?.name === (evt.name || evt) ? null : {name: evt.name || evt, type: 'event'})}
                />
              ))}
              {events.length > 12 && (
                <Text style={styles.moreText}>+{events.length - 12} more</Text>
              )}
            </div>
          </div>

          {/* Arrow */}
          <div style={styles.flowArrow}>
            <div style={styles.arrowLine} />
            <Text style={styles.arrowLabel}>updates</Text>
          </div>

          {/* Read Models column */}
          <div style={styles.column}>
            <div style={styles.columnHeader}>
              <span style={{...styles.columnIcon, backgroundColor: COLORS.readModel}}>◧</span>
              <Text style={styles.columnTitle}>Views</Text>
            </div>
            <div style={styles.columnItems}>
              {readModels.slice(0, 12).map((rm, i) => (
                <ItemCard
                  key={i}
                  item={rm}
                  type="readModel"
                  isSelected={selectedItem?.name === rm.name}
                  onClick={() => setSelectedItem(selectedItem?.name === rm.name ? null : {...rm, type: 'readModel'})}
                />
              ))}
              {readModels.length > 12 && (
                <Text style={styles.moreText}>+{readModels.length - 12} more</Text>
              )}
            </div>
          </div>
        </div>

        {/* Detail panel */}
        {selectedItem && (
          <DetailPanel item={selectedItem} onClose={() => setSelectedItem(null)} />
        )}
      </div>
    );
  }

  // Full chapter-based timeline view
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <Text style={styles.title}>Event Model</Text>
        <div style={styles.stats}>
          <StatBadge count={chapters.length} label="Workflows" color={COLORS.chapter} />
          <StatBadge count={allSlices.length} label="Features" color={COLORS.command} />
          <StatBadge count={events.length} label="Events" color={COLORS.event} />
        </div>
      </div>

      {/* Legend */}
      <div style={styles.legendRow}>
        <LegendItem color={COLORS.command} label="Command" icon="▶" />
        <LegendItem color={COLORS.event} label="Event" icon="●" />
        <LegendItem color={COLORS.readModel} label="View" icon="◧" />
        <LegendItem color={COLORS.automation} label="Automation" icon="⚡" />
      </div>

      {/* Timeline */}
      <div style={styles.timeline}>
        {chapters.map((chapter, idx) => (
          <ChapterSection
            key={chapter.name}
            chapter={chapter}
            index={idx}
            slices={allSlices.filter(s => s.chapterName === chapter.name)}
            selectedItem={selectedItem}
            onSelectItem={setSelectedItem}
          />
        ))}
      </div>

      {/* Detail panel */}
      {selectedItem && (
        <DetailPanel item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
};

/**
 * Chapter section with its slices
 */
const ChapterSection = ({ chapter, index, slices, selectedItem, onSelectItem }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div style={styles.chapterSection}>
      {/* Chapter header */}
      <div
        style={styles.chapterHeader}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={styles.chapterNumber}>{index + 1}</div>
        <div style={styles.chapterInfo}>
          <Text style={styles.chapterName}>{chapter.name}</Text>
          {chapter.description && (
            <Text style={styles.chapterDesc}>{chapter.description}</Text>
          )}
        </div>
        <Text style={styles.chapterCount}>{slices.length} features</Text>
        <span style={styles.chevron}>{isExpanded ? '▼' : '▶'}</span>
      </div>

      {/* Slices */}
      {isExpanded && (
        <div style={styles.slicesContainer}>
          {slices.map((slice, idx) => (
            <SliceCard
              key={slice.id}
              slice={slice}
              isSelected={selectedItem?.id === slice.id}
              onClick={() => onSelectItem(selectedItem?.id === slice.id ? null : slice)}
            />
          ))}
          {slices.length === 0 && (
            <Text style={styles.noSlices}>No features defined</Text>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Individual slice showing command → event → view flow
 */
const SliceCard = ({ slice, isSelected, onClick }) => {
  const isCommand = slice.type === 'state_change' || slice.command;
  const isReadModel = slice.type === 'state_view' || (!slice.command && slice.read_model);
  const isAutomation = slice.type === 'automation';

  const name = slice.command || slice.read_model || slice.automation_name || slice.name;
  const events = slice.events || [];
  const gwtCount = slice.gwt_scenarios?.length || 0;

  return (
    <div
      style={{
        ...styles.sliceCard,
        ...(isSelected ? styles.sliceCardSelected : {}),
      }}
      onClick={onClick}
    >
      {/* Main element (command or read model) */}
      <div style={styles.sliceFlow}>
        {isCommand && (
          <>
            <div style={{...styles.flowNode, backgroundColor: COLORS.command}}>
              <span style={styles.nodeIcon}>▶</span>
              <Text style={styles.nodeName}>{slice.command}</Text>
            </div>

            {events.length > 0 && (
              <>
                <div style={styles.flowConnector}>→</div>
                <div style={styles.eventGroup}>
                  {events.slice(0, 2).map((evt, i) => (
                    <div key={i} style={{...styles.flowNode, ...styles.eventNode}}>
                      <span style={styles.nodeIcon}>●</span>
                      <Text style={styles.nodeName}>{evt}</Text>
                    </div>
                  ))}
                  {events.length > 2 && (
                    <Text style={styles.moreEvents}>+{events.length - 2}</Text>
                  )}
                </div>
              </>
            )}
          </>
        )}

        {isReadModel && (
          <>
            {slice.source_events?.length > 0 && (
              <>
                <div style={styles.eventGroup}>
                  {slice.source_events.slice(0, 2).map((evt, i) => (
                    <div key={i} style={{...styles.flowNode, ...styles.eventNode}}>
                      <span style={styles.nodeIcon}>●</span>
                      <Text style={styles.nodeName}>{evt}</Text>
                    </div>
                  ))}
                </div>
                <div style={styles.flowConnector}>→</div>
              </>
            )}
            <div style={{...styles.flowNode, backgroundColor: COLORS.readModel}}>
              <span style={styles.nodeIcon}>◧</span>
              <Text style={styles.nodeName}>{slice.read_model}</Text>
            </div>
          </>
        )}

        {isAutomation && (
          <>
            {slice.trigger_events?.length > 0 && (
              <div style={{...styles.flowNode, ...styles.eventNode}}>
                <span style={styles.nodeIcon}>●</span>
                <Text style={styles.nodeName}>{slice.trigger_events[0]}</Text>
              </div>
            )}
            <div style={styles.flowConnector}>→</div>
            <div style={{...styles.flowNode, backgroundColor: COLORS.automation}}>
              <span style={styles.nodeIcon}>⚡</span>
              <Text style={styles.nodeName}>{name}</Text>
            </div>
            {slice.result_events?.length > 0 && (
              <>
                <div style={styles.flowConnector}>→</div>
                <div style={{...styles.flowNode, ...styles.eventNode}}>
                  <span style={styles.nodeIcon}>●</span>
                  <Text style={styles.nodeName}>{slice.result_events[0]}</Text>
                </div>
              </>
            )}
          </>
        )}
      </div>

      {/* GWT indicator */}
      {gwtCount > 0 && (
        <div style={styles.gwtBadge}>
          <span style={styles.gwtIcon}>✓</span>
          <Text style={styles.gwtText}>{gwtCount} tests</Text>
        </div>
      )}
    </div>
  );
};

/**
 * Simple item card for flat view
 */
const ItemCard = ({ item, type, isSelected, onClick }) => {
  const color = type === 'command' ? COLORS.command
    : type === 'event' ? COLORS.event
    : COLORS.readModel;

  return (
    <div
      style={{
        ...styles.itemCard,
        borderLeftColor: color,
        ...(isSelected ? { backgroundColor: `${color}15` } : {}),
      }}
      onClick={onClick}
    >
      <Text style={styles.itemName}>{item.name}</Text>
    </div>
  );
};

/**
 * Detail panel for selected item
 */
const DetailPanel = ({ item, onClose }) => {
  const type = item.type || (item.command ? 'command' : item.read_model ? 'readModel' : 'slice');
  const color = type === 'command' ? COLORS.command
    : type === 'event' ? COLORS.event
    : type === 'readModel' ? COLORS.readModel
    : COLORS.command;

  return (
    <div style={styles.detailPanel}>
      <div style={styles.detailHeader}>
        <div style={{...styles.detailType, backgroundColor: color}}>
          {type === 'command' ? 'Command' : type === 'event' ? 'Event' : type === 'readModel' ? 'View' : 'Feature'}
        </div>
        <button style={styles.closeBtn} onClick={onClose}>×</button>
      </div>

      <Text style={styles.detailName}>{item.name || item.command || item.read_model}</Text>

      {(item.description || item.commandObj?.description || item.readModelObj?.description) && (
        <Text style={styles.detailDesc}>
          {item.description || item.commandObj?.description || item.readModelObj?.description}
        </Text>
      )}

      {/* Flow visualization for slices */}
      {item.command && item.events?.length > 0 && (
        <div style={styles.detailFlow}>
          <div style={{...styles.detailFlowNode, borderColor: COLORS.command}}>
            <Text style={styles.detailFlowLabel}>Command</Text>
            <Text style={styles.detailFlowName}>{item.command}</Text>
          </div>
          <div style={styles.detailFlowArrow}>→</div>
          <div style={{...styles.detailFlowNode, borderColor: COLORS.event}}>
            <Text style={styles.detailFlowLabel}>Events</Text>
            {item.events.map((e, i) => (
              <Text key={i} style={styles.detailFlowName}>{e}</Text>
            ))}
          </div>
        </div>
      )}

      {/* GWT Scenarios */}
      {item.gwt_scenarios?.length > 0 && (
        <div style={styles.gwtSection}>
          <Text style={styles.gwtSectionTitle}>Test Scenarios</Text>
          {item.gwt_scenarios.slice(0, 2).map((gwt, i) => (
            <div key={i} style={styles.gwtScenario}>
              {gwt.given && <div style={styles.gwtLine}><span style={styles.gwtKey}>Given</span> {gwt.given}</div>}
              {gwt.when && <div style={styles.gwtLine}><span style={styles.gwtKey}>When</span> {gwt.when}</div>}
              {gwt.then && <div style={styles.gwtLine}><span style={styles.gwtKey}>Then</span> {gwt.then}</div>}
            </div>
          ))}
          {item.gwt_scenarios.length > 2 && (
            <Text style={styles.gwtMore}>+{item.gwt_scenarios.length - 2} more scenarios</Text>
          )}
        </div>
      )}

      {/* Parameters for commands */}
      {item.commandObj?.parameters?.length > 0 && (
        <div style={styles.paramsSection}>
          <Text style={styles.paramsSectionTitle}>Parameters</Text>
          {item.commandObj.parameters.slice(0, 5).map((p, i) => (
            <div key={i} style={styles.paramRow}>
              <Text style={styles.paramName}>{p.name}</Text>
              <Text style={styles.paramType}>{p.type}</Text>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Stats badge
 */
const StatBadge = ({ count, label, color }) => (
  <div style={styles.statBadge}>
    <span style={{...styles.statDot, backgroundColor: color}} />
    <Text style={styles.statCount}>{count}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </div>
);

/**
 * Legend item
 */
const LegendItem = ({ color, label, icon }) => (
  <div style={styles.legendItem}>
    <span style={{...styles.legendDot, backgroundColor: color}}>{icon}</span>
    <Text style={styles.legendLabel}>{label}</Text>
  </div>
);

// Colors following Event Modeling conventions
const COLORS = {
  command: '#3B82F6',    // Blue
  event: '#F59E0B',      // Orange/Amber
  readModel: '#10B981',  // Green
  automation: '#EAB308', // Yellow
  decider: '#8B5CF6',    // Purple
  chapter: '#6366F1',    // Indigo
};

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    overflow: 'hidden',
  },

  // Header
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: `${tokens.spacing[4]} ${tokens.spacing[5]}`,
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
  },
  title: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[900],
  },
  stats: {
    display: 'flex',
    gap: tokens.spacing[4],
  },
  statBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
  },
  statDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  statCount: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[900],
  },
  statLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
  },

  // Legend
  legendRow: {
    display: 'flex',
    gap: tokens.spacing[5],
    padding: `${tokens.spacing[3]} ${tokens.spacing[5]}`,
    backgroundColor: tokens.colors.neutral[50],
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  legendDot: {
    width: '20px',
    height: '20px',
    borderRadius: tokens.borderRadius.sm,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '10px',
  },
  legendLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
  },

  // Timeline
  timeline: {
    padding: tokens.spacing[4],
  },

  // Chapter section
  chapterSection: {
    marginBottom: tokens.spacing[4],
    border: `1px solid ${tokens.colors.neutral[200]}`,
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
  },
  chapterHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[3],
    backgroundColor: tokens.colors.neutral[50],
    cursor: 'pointer',
    borderBottom: `1px solid ${tokens.colors.neutral[200]}`,
  },
  chapterNumber: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    backgroundColor: COLORS.chapter,
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.bold,
    flexShrink: 0,
  },
  chapterInfo: {
    flex: 1,
    minWidth: 0,
  },
  chapterName: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[900],
  },
  chapterDesc: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    marginTop: '2px',
  },
  chapterCount: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    backgroundColor: tokens.colors.neutral[100],
    borderRadius: tokens.borderRadius.full,
  },
  chevron: {
    color: tokens.colors.neutral[400],
    fontSize: '10px',
  },

  // Slices container
  slicesContainer: {
    padding: tokens.spacing[3],
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
    backgroundColor: 'white',
  },
  noSlices: {
    textAlign: 'center',
    color: tokens.colors.neutral[400],
    padding: tokens.spacing[4],
    fontSize: tokens.typography.fontSize.sm[0],
  },

  // Slice card
  sliceCard: {
    padding: tokens.spacing[3],
    border: `1px solid ${tokens.colors.neutral[200]}`,
    borderRadius: tokens.borderRadius.md,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  sliceCardSelected: {
    borderColor: COLORS.command,
    backgroundColor: `${COLORS.command}08`,
  },
  sliceFlow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
    flex: 1,
  },
  flowNode: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.md,
    color: 'white',
  },
  eventNode: {
    backgroundColor: COLORS.event,
  },
  nodeIcon: {
    fontSize: '8px',
  },
  nodeName: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'inherit',
    fontFamily: tokens.typography.fontFamily.mono,
  },
  flowConnector: {
    color: tokens.colors.neutral[400],
    fontSize: tokens.typography.fontSize.sm[0],
  },
  eventGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[1],
  },
  moreEvents: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    alignSelf: 'center',
  },
  gwtBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    backgroundColor: tokens.colors.success[50],
    borderRadius: tokens.borderRadius.full,
    flexShrink: 0,
  },
  gwtIcon: {
    color: tokens.colors.success[600],
    fontSize: '10px',
  },
  gwtText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.success[700],
  },

  // Flat flow view
  flatFlow: {
    display: 'flex',
    padding: tokens.spacing[5],
    gap: tokens.spacing[2],
    alignItems: 'flex-start',
  },
  column: {
    flex: 1,
    minWidth: 0,
  },
  columnHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },
  columnIcon: {
    width: '24px',
    height: '24px',
    borderRadius: tokens.borderRadius.md,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '10px',
  },
  columnTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
  },
  columnItems: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },
  flowArrow: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[1],
    paddingTop: '40px',
  },
  arrowLine: {
    width: '30px',
    height: '2px',
    backgroundColor: tokens.colors.neutral[300],
    position: 'relative',
  },
  arrowLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
  },

  // Item card
  itemCard: {
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    borderLeft: '3px solid',
    borderRadius: `0 ${tokens.borderRadius.md} ${tokens.borderRadius.md} 0`,
    backgroundColor: tokens.colors.neutral[50],
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  itemName: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: tokens.typography.fontFamily.mono,
    color: tokens.colors.neutral[700],
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  moreText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
    padding: tokens.spacing[2],
    textAlign: 'center',
  },

  // Detail panel
  detailPanel: {
    margin: tokens.spacing[4],
    marginTop: 0,
    padding: tokens.spacing[4],
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[2],
  },
  detailType: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'white',
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.md,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: tokens.colors.neutral[400],
    cursor: 'pointer',
    padding: 0,
    lineHeight: 1,
  },
  detailName: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    fontFamily: tokens.typography.fontFamily.mono,
    color: tokens.colors.neutral[900],
    marginBottom: tokens.spacing[2],
  },
  detailDesc: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    marginBottom: tokens.spacing[3],
    lineHeight: 1.5,
  },

  // Detail flow
  detailFlow: {
    display: 'flex',
    alignItems: 'stretch',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[3],
  },
  detailFlowNode: {
    flex: 1,
    padding: tokens.spacing[3],
    borderRadius: tokens.borderRadius.md,
    border: '2px solid',
    backgroundColor: 'white',
  },
  detailFlowLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    textTransform: 'uppercase',
    marginBottom: tokens.spacing[1],
  },
  detailFlowName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: tokens.typography.fontFamily.mono,
    color: tokens.colors.neutral[800],
  },
  detailFlowArrow: {
    display: 'flex',
    alignItems: 'center',
    color: tokens.colors.neutral[400],
    fontSize: tokens.typography.fontSize.xl[0],
  },

  // GWT section
  gwtSection: {
    marginBottom: tokens.spacing[3],
  },
  gwtSectionTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[2],
  },
  gwtScenario: {
    padding: tokens.spacing[3],
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.md,
    marginBottom: tokens.spacing[2],
    borderLeft: `3px solid ${tokens.colors.success[400]}`,
  },
  gwtLine: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
    marginBottom: tokens.spacing[1],
    lineHeight: 1.4,
  },
  gwtKey: {
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[700],
    marginRight: tokens.spacing[1],
  },
  gwtMore: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
    fontStyle: 'italic',
  },

  // Params section
  paramsSection: {
    marginBottom: tokens.spacing[3],
  },
  paramsSectionTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[2],
  },
  paramRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: `${tokens.spacing[1]} 0`,
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
  },
  paramName: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: tokens.typography.fontFamily.mono,
    color: tokens.colors.neutral[700],
  },
  paramType: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
  },

  // Empty state
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    textAlign: 'center',
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
  },
  emptyIcon: {
    fontSize: '40px',
    marginBottom: tokens.spacing[3],
  },
  emptyTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[2],
  },
  emptyText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
    marginBottom: tokens.spacing[4],
  },
};

export default EventModelTimeline;

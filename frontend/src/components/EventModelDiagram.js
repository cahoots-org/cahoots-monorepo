/**
 * EventModelDiagram - Visual diagram with nodes and arrows
 *
 * Renders an actual flowchart-style diagram showing:
 * - Commands (blue boxes) → Events (orange boxes) → Read Models (green boxes)
 * - Connected by arrows showing data flow
 * - Organized by chapters (horizontal swim lanes)
 */
import React, { useState, useMemo, useRef } from 'react';
import { Text, tokens } from '../design-system';

// Layout constants
const NODE = {
  width: 140,
  height: 44,
  spacing: 24,
  rowGap: 80,
};

const COLORS = {
  command: { bg: '#3B82F6', border: '#2563EB', text: '#FFFFFF' },
  event: { bg: '#F59E0B', border: '#D97706', text: '#FFFFFF' },
  readModel: { bg: '#10B981', border: '#059669', text: '#FFFFFF' },
  automation: { bg: '#8B5CF6', border: '#7C3AED', text: '#FFFFFF' },
  arrow: '#94A3B8',
  chapterBg: '#F8FAFC',
  chapterBorder: '#E2E8F0',
};

const EventModelDiagram = ({ task }) => {
  const containerRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [zoom, setZoom] = useState(1);

  // Extract data
  const chapters = task?.metadata?.chapters || [];
  const commands = task?.metadata?.commands || [];
  const events = task?.metadata?.extracted_events || [];
  const readModels = task?.metadata?.read_models || [];

  // Build diagram layout
  const { nodes, arrows, dimensions, chapterRects } = useMemo(() => {
    const allNodes = [];
    const allArrows = [];
    const chapRects = [];

    let currentY = 60;

    // If we have chapters with slices, use that structure
    if (chapters.length > 0 && chapters.some(c => c.slices?.length > 0)) {
      chapters.forEach((chapter, chapterIdx) => {
        const chapterStartY = currentY;
        const slices = chapter.slices || [];

        if (slices.length === 0) return;

        let maxRowWidth = 0;

        slices.forEach((slice, sliceIdx) => {
          const rowY = currentY + sliceIdx * NODE.rowGap;
          let currentX = 40;

          // Command node
          if (slice.command) {
            const cmdNode = {
              id: `cmd-${chapterIdx}-${sliceIdx}`,
              type: 'command',
              label: slice.command,
              x: currentX,
              y: rowY,
              data: commands.find(c => c.name === slice.command) || { name: slice.command },
            };
            allNodes.push(cmdNode);
            currentX += NODE.width + NODE.spacing;

            // Arrow to events
            const sliceEvents = slice.events || [];
            sliceEvents.forEach((eventName, eventIdx) => {
              const eventNode = {
                id: `evt-${chapterIdx}-${sliceIdx}-${eventIdx}`,
                type: 'event',
                label: eventName,
                x: currentX + eventIdx * (NODE.width + NODE.spacing / 2),
                y: rowY,
                data: events.find(e => (e.name || e) === eventName) || { name: eventName },
              };
              allNodes.push(eventNode);

              // Arrow from command to event
              allArrows.push({
                id: `arrow-${cmdNode.id}-${eventNode.id}`,
                from: cmdNode.id,
                to: eventNode.id,
              });
            });

            if (sliceEvents.length > 0) {
              currentX += sliceEvents.length * (NODE.width + NODE.spacing / 2);
            }
          }

          // Read model node (if present)
          if (slice.read_model) {
            const rmNode = {
              id: `rm-${chapterIdx}-${sliceIdx}`,
              type: 'readModel',
              label: slice.read_model,
              x: currentX,
              y: rowY,
              data: readModels.find(r => r.name === slice.read_model) || { name: slice.read_model },
            };
            allNodes.push(rmNode);

            // Connect from last event if exists
            const sliceEvents = slice.events || slice.source_events || [];
            if (sliceEvents.length > 0) {
              const lastEventId = `evt-${chapterIdx}-${sliceIdx}-${sliceEvents.length - 1}`;
              const lastEvent = allNodes.find(n => n.id === lastEventId);
              if (lastEvent) {
                allArrows.push({
                  id: `arrow-${lastEventId}-${rmNode.id}`,
                  from: lastEventId,
                  to: rmNode.id,
                });
              }
            }

            currentX += NODE.width + NODE.spacing;
          }

          maxRowWidth = Math.max(maxRowWidth, currentX);
        });

        const chapterHeight = slices.length * NODE.rowGap + 20;
        chapRects.push({
          name: chapter.name,
          x: 20,
          y: chapterStartY - 30,
          width: Math.max(maxRowWidth + 20, 400),
          height: chapterHeight,
        });

        currentY += slices.length * NODE.rowGap + 40;
      });
    } else if (commands.length > 0) {
      // Fallback: just show commands → events → read models in rows
      const cmdEventMap = {};

      commands.forEach((cmd, cmdIdx) => {
        const triggers = cmd.triggers_events || [];
        triggers.forEach(evtName => {
          if (!cmdEventMap[evtName]) cmdEventMap[evtName] = [];
          cmdEventMap[evtName].push(cmd.name);
        });
      });

      // Create a simple flow: commands on left, events in middle, read models on right
      const leftX = 40;
      const midX = 220;
      const rightX = 400;

      commands.slice(0, 10).forEach((cmd, idx) => {
        const y = currentY + idx * (NODE.height + 16);
        allNodes.push({
          id: `cmd-${idx}`,
          type: 'command',
          label: cmd.name,
          x: leftX,
          y,
          data: cmd,
        });
      });

      events.slice(0, 10).forEach((evt, idx) => {
        const evtName = typeof evt === 'string' ? evt : evt.name;
        const y = currentY + idx * (NODE.height + 16);
        allNodes.push({
          id: `evt-${idx}`,
          type: 'event',
          label: evtName,
          x: midX,
          y,
          data: typeof evt === 'string' ? { name: evt } : evt,
        });
      });

      readModels.slice(0, 10).forEach((rm, idx) => {
        const y = currentY + idx * (NODE.height + 16);
        allNodes.push({
          id: `rm-${idx}`,
          type: 'readModel',
          label: rm.name,
          x: rightX,
          y,
          data: rm,
        });
      });

      // Connect commands to events based on triggers_events
      commands.forEach((cmd, cmdIdx) => {
        const triggers = cmd.triggers_events || [];
        triggers.forEach(evtName => {
          const evtIdx = events.findIndex(e => (e.name || e) === evtName);
          if (evtIdx !== -1 && evtIdx < 10 && cmdIdx < 10) {
            allArrows.push({
              id: `arrow-cmd-${cmdIdx}-evt-${evtIdx}`,
              from: `cmd-${cmdIdx}`,
              to: `evt-${evtIdx}`,
            });
          }
        });
      });

      // Connect events to read models based on data_source
      readModels.forEach((rm, rmIdx) => {
        const sources = rm.data_source || [];
        sources.forEach(evtName => {
          const evtIdx = events.findIndex(e => (e.name || e) === evtName);
          if (evtIdx !== -1 && evtIdx < 10 && rmIdx < 10) {
            allArrows.push({
              id: `arrow-evt-${evtIdx}-rm-${rmIdx}`,
              from: `evt-${evtIdx}`,
              to: `rm-${rmIdx}`,
            });
          }
        });
      });

      currentY += Math.max(commands.length, events.length, readModels.length) * (NODE.height + 16) + 40;
    }

    // Calculate dimensions
    const maxX = Math.max(...allNodes.map(n => n.x + NODE.width), 600);
    const maxY = Math.max(...allNodes.map(n => n.y + NODE.height), currentY);

    return {
      nodes: allNodes,
      arrows: allArrows,
      dimensions: { width: maxX + 60, height: maxY + 60 },
      chapterRects: chapRects,
    };
  }, [chapters, commands, events, readModels]);

  // Get node position for arrow calculation
  const getNodeCenter = (nodeId, side) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };

    if (side === 'right') {
      return { x: node.x + NODE.width, y: node.y + NODE.height / 2 };
    }
    return { x: node.x, y: node.y + NODE.height / 2 };
  };

  // Handle zoom
  const handleWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom(z => Math.min(2, Math.max(0.5, z * delta)));
    }
  };

  // Empty state
  if (nodes.length === 0) {
    return (
      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>📊</div>
        <Text style={styles.emptyTitle}>Event Model Diagram</Text>
        <Text style={styles.emptyText}>
          No event model data to visualize yet
        </Text>
        <div style={styles.legend}>
          <LegendItem color={COLORS.command.bg} label="Commands" />
          <LegendItem color={COLORS.event.bg} label="Events" />
          <LegendItem color={COLORS.readModel.bg} label="Views" />
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <Text style={styles.title}>Event Model</Text>
        <div style={styles.legend}>
          <LegendItem color={COLORS.command.bg} label="Command" />
          <LegendItem color={COLORS.event.bg} label="Event" />
          <LegendItem color={COLORS.readModel.bg} label="View" />
        </div>
        <div style={styles.controls}>
          <button style={styles.zoomBtn} onClick={() => setZoom(z => Math.min(2, z + 0.1))}>+</button>
          <span style={styles.zoomLevel}>{Math.round(zoom * 100)}%</span>
          <button style={styles.zoomBtn} onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}>−</button>
        </div>
      </div>

      {/* Diagram canvas */}
      <div
        ref={containerRef}
        style={styles.canvas}
        onWheel={handleWheel}
      >
        <svg
          width={dimensions.width * zoom}
          height={dimensions.height * zoom}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
        >
          {/* Chapter backgrounds */}
          {chapterRects.map((rect, idx) => (
            <g key={`chapter-${idx}`}>
              <rect
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
                fill={COLORS.chapterBg}
                stroke={COLORS.chapterBorder}
                strokeWidth={1}
                rx={8}
              />
              <text
                x={rect.x + 12}
                y={rect.y + 20}
                fill="#64748B"
                fontSize="12"
                fontWeight="600"
              >
                {rect.name}
              </text>
            </g>
          ))}

          {/* Arrows */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill={COLORS.arrow} />
            </marker>
          </defs>
          {arrows.map(arrow => {
            const from = getNodeCenter(arrow.from, 'right');
            const to = getNodeCenter(arrow.to, 'left');

            // Create a curved path
            const midX = (from.x + to.x) / 2;
            const path = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;

            const isHighlighted = hoveredNode === arrow.from || hoveredNode === arrow.to;

            return (
              <path
                key={arrow.id}
                d={path}
                stroke={isHighlighted ? '#3B82F6' : COLORS.arrow}
                strokeWidth={isHighlighted ? 2 : 1.5}
                fill="none"
                markerEnd="url(#arrowhead)"
                style={{ transition: 'stroke 0.15s, stroke-width 0.15s' }}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map(node => {
            const colors = COLORS[node.type] || COLORS.command;
            const isHovered = hoveredNode === node.id;
            const isSelected = selectedNode?.id === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => setSelectedNode(isSelected ? null : node)}
              >
                <rect
                  width={NODE.width}
                  height={NODE.height}
                  fill={colors.bg}
                  stroke={isSelected ? '#1E40AF' : colors.border}
                  strokeWidth={isSelected ? 3 : isHovered ? 2 : 1}
                  rx={6}
                  style={{ transition: 'stroke-width 0.15s' }}
                />
                <text
                  x={NODE.width / 2}
                  y={NODE.height / 2 + 1}
                  fill={colors.text}
                  fontSize="11"
                  fontWeight="500"
                  fontFamily="ui-monospace, monospace"
                  textAnchor="middle"
                  dominantBaseline="middle"
                >
                  {truncateLabel(node.label, 18)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected node detail */}
      {selectedNode && (
        <div style={styles.detailPanel}>
          <div style={styles.detailHeader}>
            <span style={{
              ...styles.detailType,
              backgroundColor: COLORS[selectedNode.type]?.bg || COLORS.command.bg
            }}>
              {selectedNode.type === 'command' ? 'Command' :
               selectedNode.type === 'event' ? 'Event' : 'View'}
            </span>
            <button style={styles.closeBtn} onClick={() => setSelectedNode(null)}>×</button>
          </div>
          <Text style={styles.detailName}>{selectedNode.label}</Text>
          {selectedNode.data?.description && (
            <Text style={styles.detailDesc}>{selectedNode.data.description}</Text>
          )}
          {selectedNode.data?.triggers_events?.length > 0 && (
            <div style={styles.detailSection}>
              <Text style={styles.detailSectionTitle}>Triggers:</Text>
              <div style={styles.detailTags}>
                {selectedNode.data.triggers_events.map((e, i) => (
                  <span key={i} style={{...styles.tag, backgroundColor: COLORS.event.bg}}>{e}</span>
                ))}
              </div>
            </div>
          )}
          {selectedNode.data?.parameters?.length > 0 && (
            <div style={styles.detailSection}>
              <Text style={styles.detailSectionTitle}>Parameters:</Text>
              {selectedNode.data.parameters.slice(0, 4).map((p, i) => (
                <div key={i} style={styles.paramRow}>
                  <span style={styles.paramName}>{p.name}</span>
                  <span style={styles.paramType}>{p.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Truncate long labels
const truncateLabel = (label, maxLen) => {
  if (!label) return '';
  if (label.length <= maxLen) return label;
  return label.substring(0, maxLen - 2) + '…';
};

// Legend item
const LegendItem = ({ color, label }) => (
  <div style={styles.legendItem}>
    <div style={{ ...styles.legendDot, backgroundColor: color }} />
    <Text style={styles.legendLabel}>{label}</Text>
  </div>
);

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    borderBottom: `1px solid ${tokens.colors.neutral[200]}`,
    backgroundColor: tokens.colors.neutral[50],
  },
  title: {
    fontSize: tokens.typography.fontSize.base[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[900],
  },
  legend: {
    display: 'flex',
    gap: tokens.spacing[4],
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[1],
  },
  legendDot: {
    width: '12px',
    height: '12px',
    borderRadius: '3px',
  },
  legendLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  zoomBtn: {
    width: '28px',
    height: '28px',
    border: `1px solid ${tokens.colors.neutral[300]}`,
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'white',
    cursor: 'pointer',
    fontSize: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  zoomLevel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    minWidth: '40px',
    textAlign: 'center',
  },
  canvas: {
    overflow: 'auto',
    padding: tokens.spacing[4],
    minHeight: '400px',
    maxHeight: '600px',
    backgroundColor: '#FAFBFC',
  },
  detailPanel: {
    padding: tokens.spacing[4],
    borderTop: `1px solid ${tokens.colors.neutral[200]}`,
    backgroundColor: 'white',
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
    padding: `2px ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.sm,
    textTransform: 'uppercase',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: tokens.colors.neutral[400],
    cursor: 'pointer',
    padding: 0,
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
  },
  detailSection: {
    marginTop: tokens.spacing[3],
  },
  detailSectionTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[500],
    textTransform: 'uppercase',
    marginBottom: tokens.spacing[1],
  },
  detailTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacing[1],
  },
  tag: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'white',
    padding: `2px ${tokens.spacing[2]}`,
    borderRadius: tokens.borderRadius.sm,
    fontFamily: tokens.typography.fontFamily.mono,
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
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
  },
  emptyIcon: {
    fontSize: '48px',
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

export default EventModelDiagram;

/**
 * EventModelFlow - Dev Hero Component (Simplified)
 *
 * Clean visualization of Commands -> Events -> Read Models flow.
 */
import React, { useState, useMemo } from 'react';
import { Card, Text, Badge, tokens } from '../../../design-system';
import { extractEventModelComponents } from '../../../utils/personaDataTransforms';

const EventModelFlow = ({ task }) => {
  const [selectedItem, setSelectedItem] = useState(null);
  const components = useMemo(() => extractEventModelComponents(task), [task]);
  const { commands, events, readModels, summary } = components;

  return (
    <div style={styles.container}>
      {/* Summary Stats */}
      <div style={styles.statsRow}>
        <div style={styles.stat}>
          <Text style={{ ...styles.statValue, color: tokens.colors.primary[400] }}>
            {summary.commandCount}
          </Text>
          <Text style={styles.statLabel}>Commands</Text>
        </div>
        <div style={styles.arrow}>→</div>
        <div style={styles.stat}>
          <Text style={{ ...styles.statValue, color: tokens.colors.warning[500] }}>
            {summary.eventCount}
          </Text>
          <Text style={styles.statLabel}>Events</Text>
        </div>
        <div style={styles.arrow}>→</div>
        <div style={styles.stat}>
          <Text style={{ ...styles.statValue, color: tokens.colors.info[500] }}>
            {summary.readModelCount}
          </Text>
          <Text style={styles.statLabel}>Read Models</Text>
        </div>
      </div>

      {/* Flow Columns */}
      <Card style={styles.flowCard}>
        <div style={styles.flowContainer}>
          <FlowColumn
            title="Commands"
            items={commands}
            color={tokens.colors.primary[400]}
            selectedItem={selectedItem}
            onSelect={setSelectedItem}
          />
          <div style={styles.columnArrow}>→</div>
          <FlowColumn
            title="Events"
            items={events}
            color={tokens.colors.warning[500]}
            selectedItem={selectedItem}
            onSelect={setSelectedItem}
          />
          <div style={styles.columnArrow}>→</div>
          <FlowColumn
            title="Read Models"
            items={readModels}
            color={tokens.colors.info[500]}
            selectedItem={selectedItem}
            onSelect={setSelectedItem}
          />
        </div>
      </Card>

      {/* Selected Item Detail */}
      {selectedItem && (
        <Card style={styles.detailCard}>
          <div style={styles.detailHeader}>
            <Text style={styles.detailName}>{selectedItem.name}</Text>
            <button style={styles.closeBtn} onClick={() => setSelectedItem(null)}>×</button>
          </div>
          {selectedItem.description && (
            <Text style={styles.detailDesc}>{selectedItem.description}</Text>
          )}
        </Card>
      )}
    </div>
  );
};

const FlowColumn = ({ title, items, color, selectedItem, onSelect }) => (
  <div style={styles.column}>
    <Text style={styles.columnTitle}>{title}</Text>
    <div style={styles.itemList}>
      {items.slice(0, 8).map((item, i) => (
        <div
          key={i}
          style={{
            ...styles.flowItem,
            borderLeftColor: color,
            backgroundColor: selectedItem?.name === item.name ? `${color}15` : 'transparent',
          }}
          onClick={() => onSelect(item)}
        >
          <Text style={styles.itemName}>{item.name}</Text>
        </div>
      ))}
      {items.length > 8 && (
        <Text style={styles.moreText}>+{items.length - 8} more</Text>
      )}
    </div>
  </div>
);

const styles = {
  container: {
    marginBottom: tokens.spacing[6],
  },
  statsRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing[6],
    marginBottom: tokens.spacing[4],
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  stat: {
    textAlign: 'center',
  },
  statValue: {
    fontSize: tokens.typography.fontSize['3xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    lineHeight: 1,
  },
  statLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginTop: tokens.spacing[1],
  },
  arrow: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    color: 'var(--color-text-muted)',
  },
  flowCard: {
    padding: tokens.spacing[4],
  },
  flowContainer: {
    display: 'flex',
    gap: tokens.spacing[2],
  },
  column: {
    flex: 1,
    minWidth: 0,
  },
  columnTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[3],
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  columnArrow: {
    display: 'flex',
    alignItems: 'center',
    fontSize: tokens.typography.fontSize.xl[0],
    color: 'var(--color-text-muted)',
    padding: `0 ${tokens.spacing[2]}`,
  },
  itemList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
    maxHeight: '280px',
    overflowY: 'auto',
  },
  flowItem: {
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    borderLeft: '3px solid',
    borderRadius: `0 ${tokens.borderRadius.sm} ${tokens.borderRadius.sm} 0`,
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  itemName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontFamily: 'var(--font-mono)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  moreText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
    padding: tokens.spacing[2],
  },
  detailCard: {
    marginTop: tokens.spacing[4],
    padding: tokens.spacing[4],
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[2],
  },
  detailName: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    fontFamily: 'var(--font-mono)',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    padding: 0,
    lineHeight: 1,
  },
  detailDesc: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
  },
};

export default EventModelFlow;

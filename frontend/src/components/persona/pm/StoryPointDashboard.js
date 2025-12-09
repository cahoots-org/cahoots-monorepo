/**
 * StoryPointDashboard - PM Hero Component (Simplified)
 *
 * Clean display of story point totals and key project metrics.
 */
import React from 'react';
import { Text, tokens } from '../../../design-system';
import { calculateStoryPointMetrics } from '../../../utils/personaDataTransforms';

const StoryPointDashboard = ({ task, taskTree }) => {
  const metrics = calculateStoryPointMetrics(task, taskTree);

  return (
    <div style={styles.container}>
      <div style={styles.metricsRow}>
        <MetricCard
          value={metrics.totalPoints}
          label="Story Points"
          accent={tokens.colors.primary[400]}
        />
        <MetricCard
          value={metrics.epicCount}
          label="Epics"
          accent={tokens.colors.secondary[400]}
        />
        <MetricCard
          value={metrics.storyCount}
          label="Stories"
          accent={tokens.colors.info[500]}
        />
        <MetricCard
          value={metrics.atomicTasks}
          label="Tasks"
          accent={tokens.colors.success[500]}
        />
      </div>
    </div>
  );
};

const MetricCard = ({ value, label, accent }) => (
  <div style={styles.metricCard}>
    <Text style={{ ...styles.metricValue, color: accent }}>{value}</Text>
    <Text style={styles.metricLabel}>{label}</Text>
  </div>
);

const styles = {
  container: {
    marginBottom: tokens.spacing[6],
  },
  metricsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: tokens.spacing[4],
  },
  metricCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[5],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  metricValue: {
    fontSize: tokens.typography.fontSize['4xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    lineHeight: 1,
  },
  metricLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[2],
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
};

export default StoryPointDashboard;

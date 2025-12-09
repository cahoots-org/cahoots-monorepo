/**
 * ExecutiveSummary - Consultant Hero Component (Simplified)
 *
 * Clean scope overview without time estimates.
 */
import React from 'react';
import { Card, Text, Badge, tokens } from '../../../design-system';
import { calculateScopeMetrics } from '../../../utils/personaDataTransforms';

const ExecutiveSummary = ({ task, taskTree }) => {
  const metrics = calculateScopeMetrics(task, taskTree);

  const complexityColors = {
    Small: tokens.colors.success[500],
    Medium: tokens.colors.warning[500],
    Large: tokens.colors.error[500],
  };

  return (
    <div style={styles.container}>
      {/* Project Description */}
      <Card style={styles.descCard}>
        <Text style={styles.descLabel}>Project Scope</Text>
        <Text style={styles.descText}>
          {task?.description || 'No description provided.'}
        </Text>
        <Badge
          style={{
            ...styles.complexityBadge,
            backgroundColor: `${complexityColors[metrics.complexityRating]}20`,
            color: complexityColors[metrics.complexityRating],
          }}
        >
          {metrics.complexityRating} Project
        </Badge>
      </Card>

      {/* Metrics Row */}
      <div style={styles.metricsRow}>
        <MetricCard value={metrics.epicCount} label="Features" />
        <MetricCard value={metrics.storyCount} label="Stories" />
        <MetricCard value={metrics.totalTasks} label="Tasks" />
        <MetricCard value={metrics.commandCount} label="User Actions" />
      </div>
    </div>
  );
};

const MetricCard = ({ value, label }) => (
  <div style={styles.metricCard}>
    <Text style={styles.metricValue}>{value}</Text>
    <Text style={styles.metricLabel}>{label}</Text>
  </div>
);

const styles = {
  container: {
    marginBottom: tokens.spacing[6],
  },
  descCard: {
    padding: tokens.spacing[5],
    marginBottom: tokens.spacing[4],
  },
  descLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    marginBottom: tokens.spacing[2],
  },
  descText: {
    fontSize: tokens.typography.fontSize.lg[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
    marginBottom: tokens.spacing[4],
  },
  complexityBadge: {
    fontSize: tokens.typography.fontSize.sm[0],
    padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
    fontWeight: tokens.typography.fontWeight.medium,
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
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.lg,
    border: '1px solid var(--color-border)',
  },
  metricValue: {
    fontSize: tokens.typography.fontSize['3xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.info[500],
    lineHeight: 1,
  },
  metricLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[2],
  },
};

export default ExecutiveSummary;

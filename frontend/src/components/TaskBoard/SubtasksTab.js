import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  Text,
  Heading3,
  Badge,
  tokens,
} from '../../design-system';
import TreeVisualization from '../TreeVisualization';
import { formatDetailedDate } from '../../utils/dateUtils';

const SubtasksTab = ({
  taskTree,
  selectedSubtask,
  onSubtaskSelect,
  onStatusChange,
  onRefresh,
  updating
}) => {
  if (!taskTree) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>🎯</span>
        <h3 style={styles.emptyStateTitle}>No Subtasks</h3>
        <p style={styles.emptyStateDescription}>This task hasn't been decomposed into subtasks yet.</p>
      </div>
    );
  }

  const subtasksLayoutStyle = {
    display: 'grid',
    gridTemplateColumns: selectedSubtask ? '2fr 1fr' : '1fr',
    gap: tokens.spacing[4],
  };

  return (
    <div style={subtasksLayoutStyle}>
      <Card style={styles.treeCard}>
        <CardHeader>
          <Heading3>Task Hierarchy</Heading3>
        </CardHeader>
        <CardContent>
          <TreeVisualization
            taskTree={taskTree}
            onStatusChange={onStatusChange}
            updating={updating}
            onTaskSelect={onSubtaskSelect}
            onRefreshTree={onRefresh}
          />
        </CardContent>
      </Card>

      {selectedSubtask && (
        <Card style={styles.detailCard}>
          <CardHeader>
            <div style={styles.detailHeader}>
              <Heading3>Subtask Details</Heading3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSubtaskSelect(null)}
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <SubtaskDetails task={selectedSubtask} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

const SubtaskDetails = ({ task }) => (
  <div style={styles.subtaskDetails}>
    <InfoItem label="Description" value={task.description} />
    <InfoItem label="Status" value={
      <Badge variant={getStatusVariant(task.status)}>
        {task.status}
      </Badge>
    } />
    <InfoItem label="Created" value={formatDetailedDate(task.created_at)} />
    {task.story_points && (
      <InfoItem label="Story Points" value={task.story_points} />
    )}
    {task.implementation_details && (
      <InfoItem label="Implementation Details" value={task.implementation_details} />
    )}
  </div>
);

const InfoItem = ({ label, value }) => (
  <div style={styles.infoItem}>
    <Text style={styles.infoLabel}>{label}</Text>
    <div style={styles.infoValue}>{value}</div>
  </div>
);

const getStatusVariant = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'processing': return 'info';
    case 'failed': return 'error';
    default: return 'warning';
  }
};

const styles = {
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

  treeCard: {
    minHeight: '500px',
  },

  detailCard: {
    position: 'sticky',
    top: tokens.spacing[6],
    height: 'fit-content',
  },

  detailHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },

  subtaskDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  infoItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },

  infoLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },

  infoValue: {
    color: 'var(--color-text)',
  },
};

export default SubtasksTab;

import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Text,
  Heading3,
  Badge,
  tokens,
} from '../../design-system';
import { formatDetailedDate } from '../../utils/dateUtils';

const OverviewTab = ({ task, taskTree }) => {
  // Calculate statistics
  const epics = task.context?.epics || [];
  const userStories = task.context?.user_stories || [];
  const events = task.metadata?.extracted_events || [];
  const commands = task.metadata?.commands || [];
  const readModels = task.metadata?.read_models || [];
  const interactions = task.metadata?.user_interactions || [];
  const automations = task.metadata?.automations || [];

  const techStack = task.context?.tech_stack || {};
  const hasEventModeling = events.length > 0 || commands.length > 0 || readModels.length > 0;

  return (
    <div style={styles.overviewGrid}>
      {/* Task Status Card */}
      <Card>
        <CardHeader>
          <Heading3>📊 Task Status</Heading3>
        </CardHeader>
        <CardContent style={styles.infoGrid}>
          <InfoItem
            label="Status"
            value={
              <Badge variant={getStatusVariant(task.status)}>
                {task.status.replace('_', ' ')}
              </Badge>
            }
          />
          <InfoItem label="Created" value={formatDetailedDate(task.created_at)} />
          <InfoItem label="Last Updated" value={formatDetailedDate(task.updated_at)} />
          <InfoItem label="Depth" value={`Level ${task.depth}`} />
        </CardContent>
      </Card>

      {/* Decomposition Statistics */}
      <Card>
        <CardHeader>
          <Heading3>🎯 Task Breakdown</Heading3>
        </CardHeader>
        <CardContent style={styles.statsGrid}>
          <div style={styles.statItem}>
            <div style={styles.statValue}>{task.children_count || 0}</div>
            <div style={styles.statLabel}>Total Subtasks</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statValue}>{epics.length}</div>
            <div style={styles.statLabel}>Epics</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statValue}>{userStories.length}</div>
            <div style={styles.statLabel}>User Stories</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statValue}>
              {userStories.reduce((sum, s) => sum + (s.story_points || 0), 0)}
            </div>
            <div style={styles.statLabel}>Story Points</div>
          </div>
        </CardContent>
      </Card>

      {/* Event Modeling Statistics */}
      {hasEventModeling && (
        <Card>
          <CardHeader>
            <Heading3>⚡ Event Modeling</Heading3>
          </CardHeader>
          <CardContent style={styles.statsGrid}>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{events.length}</div>
              <div style={styles.statLabel}>Domain Events</div>
            </div>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{commands.length}</div>
              <div style={styles.statLabel}>Commands</div>
            </div>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{readModels.length}</div>
              <div style={styles.statLabel}>Read Models</div>
            </div>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{interactions.length}</div>
              <div style={styles.statLabel}>User Interactions</div>
            </div>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{automations.length}</div>
              <div style={styles.statLabel}>Automations</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Technology Stack */}
      {techStack.application_type && (
        <Card>
          <CardHeader>
            <Heading3>💻 Technology Stack</Heading3>
          </CardHeader>
          <CardContent>
            <div style={styles.techStackGrid}>
              <InfoItem
                label="Application Type"
                value={techStack.application_type || 'Not specified'}
              />

              {techStack.preferred_languages && techStack.preferred_languages.length > 0 && (
                <InfoItem
                  label="Languages"
                  value={techStack.preferred_languages.join(', ')}
                />
              )}

              {techStack.deployment_target && (
                <InfoItem
                  label="Deployment"
                  value={techStack.deployment_target}
                />
              )}

              {techStack.frameworks && Object.keys(techStack.frameworks).length > 0 && (
                <div style={styles.frameworksSection}>
                  <Text style={styles.techStackLabel}>Frameworks</Text>
                  {Object.entries(techStack.frameworks).map(([category, frameworks]) => (
                    frameworks && frameworks.length > 0 && (
                      <div key={category} style={styles.frameworkCategory}>
                        <Text style={styles.frameworkCategoryLabel}>
                          {category.charAt(0).toUpperCase() + category.slice(1)}:
                        </Text>
                        <Text style={styles.techStackValue}>
                          {frameworks.join(', ')}
                        </Text>
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Task Description */}
      <Card style={{ gridColumn: '1 / -1' }}>
        <CardHeader>
          <Heading3>📝 Description</Heading3>
        </CardHeader>
        <CardContent>
          <Text>{task.description}</Text>
        </CardContent>
      </Card>
    </div>
  );
};

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
  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: tokens.spacing[4],
  },

  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
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

  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
    gap: tokens.spacing[4],
  },

  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.md,
  },

  statValue: {
    display: 'block',
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    lineHeight: 1,
  },

  statLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
  },

  techStackGrid: {
    display: 'grid',
    gap: tokens.spacing[4],
  },

  techStackLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },

  techStackValue: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
  },

  frameworksSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  frameworkCategory: {
    display: 'flex',
    gap: tokens.spacing[2],
    alignItems: 'baseline',
  },

  frameworkCategoryLabel: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
    minWidth: '80px',
  },
};

export default OverviewTab;

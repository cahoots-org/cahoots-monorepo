import React, { useState } from 'react';
import {
  Card,
  IconButton,
  Button,
  Text,
  Heading3,
  Badge,
  ChevronDownIcon,
  ChevronRightIcon,
  tokens,
} from '../../design-system';

const StoriesTab = ({ task }) => {
  const [selectedStory, setSelectedStory] = useState(null);
  const [expandedEpics, setExpandedEpics] = useState(new Set());

  const epics = task.context?.epics || [];
  const userStories = task.context?.user_stories || [];

  // Group stories by epic
  const storiesByEpic = userStories.reduce((acc, story) => {
    const epicId = story.epic_id || 'unassigned';
    if (!acc[epicId]) {
      acc[epicId] = [];
    }
    acc[epicId].push(story);
    return acc;
  }, {});

  const toggleEpic = (epicId) => {
    const newExpanded = new Set(expandedEpics);
    if (newExpanded.has(epicId)) {
      newExpanded.delete(epicId);
    } else {
      newExpanded.add(epicId);
    }
    setExpandedEpics(newExpanded);
  };

  const expandAll = () => {
    const allEpicIds = epics.map(e => e.id);
    setExpandedEpics(new Set(allEpicIds));
  };

  const collapseAll = () => {
    setExpandedEpics(new Set());
  };

  if (epics.length === 0 && userStories.length === 0) {
    return (
      <div style={styles.emptyStateContainer}>
        <span style={styles.emptyStateIcon}>📝</span>
        <h3 style={styles.emptyStateTitle}>No User Stories</h3>
        <p style={styles.emptyStateDescription}>User stories will appear here once the task is processed.</p>
      </div>
    );
  }

  return (
    <div style={styles.storiesContainer}>
      {/* Controls */}
      <div style={styles.storiesControls}>
        <div style={styles.storiesSummary}>
          <Badge variant="secondary">{epics.length} Epics</Badge>
          <Badge variant="info">{userStories.length} Stories</Badge>
        </div>
        <div style={styles.expandControls}>
          <Button variant="ghost" size="sm" onClick={expandAll}>Expand All</Button>
          <Button variant="ghost" size="sm" onClick={collapseAll}>Collapse All</Button>
        </div>
      </div>

      {/* Epics and Stories */}
      <div style={styles.epicsContainer}>
        {epics.map(epic => {
          const isExpanded = expandedEpics.has(epic.id);
          const epicStories = storiesByEpic[epic.id] || [];

          return (
            <Card key={epic.id} style={styles.epicCard}>
              <div
                style={styles.epicHeader}
                onClick={() => toggleEpic(epic.id)}
              >
                <div style={styles.epicHeaderLeft}>
                  <IconButton
                    icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
                    size="sm"
                    variant="ghost"
                  />
                  <div>
                    <div style={styles.epicTitle}>
                      <Heading3 style={{ margin: 0 }}>{epic.title}</Heading3>
                      <Badge variant="primary" size="sm">{epic.id}</Badge>
                    </div>
                    <Text style={styles.epicDescription}>{epic.description}</Text>
                  </div>
                </div>
                <div style={styles.epicStats}>
                  <Badge variant="secondary">{epicStories.length} stories</Badge>
                  <Badge variant={epic.priority <= 2 ? 'error' : epic.priority <= 3 ? 'warning' : 'info'}>
                    Priority {epic.priority}
                  </Badge>
                </div>
              </div>

              {isExpanded && (
                <div style={styles.storiesList}>
                  {epicStories.length === 0 ? (
                    <Text style={styles.noStoriesText}>No stories in this epic</Text>
                  ) : (
                    epicStories.map(story => (
                      <div
                        key={story.id}
                        style={{
                          ...styles.storyItem,
                          ...(selectedStory?.id === story.id ? styles.selectedStory : {})
                        }}
                        onClick={() => setSelectedStory(story.id === selectedStory?.id ? null : story)}
                      >
                        <div style={styles.storyItemHeader}>
                          <div style={styles.storyItemLeft}>
                            <Text style={styles.storyId}>{story.id}</Text>
                            <Text style={styles.storyTitle}>
                              <strong>As a</strong> {story.actor},
                              <strong> I want to</strong> {story.action}
                            </Text>
                          </div>
                          <div style={styles.storyItemRight}>
                            <Badge
                              variant={
                                story.priority === 'must_have' ? 'error' :
                                story.priority === 'should_have' ? 'warning' :
                                'secondary'
                              }
                              size="sm"
                            >
                              {story.priority?.replace('_', ' ')}
                            </Badge>
                          </div>
                        </div>

                        {selectedStory?.id === story.id && (
                          <div style={styles.storyDetails}>
                            <Text style={styles.storyBenefit}>
                              <strong>So that</strong> {story.benefit}
                            </Text>
                            {story.acceptance_criteria?.length > 0 && (
                              <div style={styles.acceptanceCriteria}>
                                <Text style={styles.criteriaTitle}>Acceptance Criteria:</Text>
                                <ul style={styles.criteriaList}>
                                  {story.acceptance_criteria.map((criteria, idx) => (
                                    <li key={idx}>
                                      <Text style={styles.criteriaItem}>{criteria}</Text>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </Card>
          );
        })}

        {/* Unassigned stories (if any) */}
        {storiesByEpic.unassigned && storiesByEpic.unassigned.length > 0 && (
          <Card style={styles.epicCard}>
            <div style={styles.epicHeader}>
              <div style={styles.epicHeaderLeft}>
                <div>
                  <Heading3 style={{ margin: 0 }}>Unassigned Stories</Heading3>
                  <Text style={styles.epicDescription}>Stories not yet assigned to an epic</Text>
                </div>
              </div>
              <Badge variant="warning">{storiesByEpic.unassigned.length} stories</Badge>
            </div>
            <div style={styles.storiesList}>
              {storiesByEpic.unassigned.map(story => (
                <div
                  key={story.id}
                  style={{
                    ...styles.storyItem,
                    ...(selectedStory?.id === story.id ? styles.selectedStory : {})
                  }}
                  onClick={() => setSelectedStory(story.id === selectedStory?.id ? null : story)}
                >
                  <Text style={styles.storyTitle}>
                    <strong>As a</strong> {story.actor},
                    <strong> I want to</strong> {story.action}
                  </Text>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
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

  storiesContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  storiesControls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: tokens.spacing[3],
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.base,
    border: `1px solid var(--color-border)`,
  },

  storiesSummary: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  expandControls: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  epicsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[4],
  },

  epicCard: {
    overflow: 'hidden',
  },

  epicHeader: {
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

  epicHeaderLeft: {
    display: 'flex',
    gap: tokens.spacing[3],
    flex: 1,
  },

  epicTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },

  epicDescription: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  epicStats: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  storiesList: {
    borderTop: `1px solid var(--color-border)`,
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-background)',
  },

  storyItem: {
    padding: tokens.spacing[3],
    borderRadius: tokens.borderRadius.base,
    border: `1px solid var(--color-border)`,
    marginBottom: tokens.spacing[2],
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: 'var(--color-surface)',
    },
  },

  selectedStory: {
    backgroundColor: 'var(--color-surface)',
    borderColor: tokens.colors.primary[500],
  },

  storyItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: tokens.spacing[2],
  },

  storyItemLeft: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },

  storyItemRight: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  storyId: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    fontFamily: tokens.typography.fontFamily.mono.join(', '),
  },

  storyTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  storyDetails: {
    marginTop: tokens.spacing[3],
    paddingTop: tokens.spacing[3],
    borderTop: `1px solid var(--color-border)`,
  },

  storyBenefit: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[3],
    color: 'var(--color-text-muted)',
  },

  acceptanceCriteria: {
    marginTop: tokens.spacing[2],
  },

  criteriaTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[2],
  },

  criteriaList: {
    marginLeft: tokens.spacing[4],
    marginTop: 0,
  },

  criteriaItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[1],
  },

  noStoriesText: {
    textAlign: 'center',
    color: 'var(--color-text-muted)',
    padding: tokens.spacing[4],
  },
};

export default StoriesTab;

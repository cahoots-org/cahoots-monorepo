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
  EditIcon,
  tokens,
} from '../../design-system';

const StoriesTab = ({ task, onEditEpic, onEditStory }) => {
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
            <Card 
              key={epic.id} 
              style={styles.epicCard}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px) scale(1.01)';
                e.currentTarget.style.boxShadow = '0 12px 32px rgba(255, 140, 26, 0.3)';
                e.currentTarget.style.borderColor = 'rgba(255, 140, 26, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(255, 140, 26, 0.2)';
              }}
            >
              <div
                style={styles.epicHeader}
                onClick={() => toggleEpic(epic.id)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <div style={styles.epicHeaderLeft}>
                  <div style={{
                    transition: 'transform 0.3s ease',
                    transform: isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)',
                  }}>
                    <IconButton
                      icon={ChevronDownIcon}
                      size="sm"
                      variant="ghost"
                    />
                  </div>
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
                  <Badge 
                    variant={epic.priority === 1 || epic.priority === 2 ? 'error' : epic.priority === 3 ? 'warning' : 'info'}
                    style={{
                      backgroundColor: epic.priority === 1 || epic.priority === 2 ? 'rgba(239, 68, 68, 0.15)' : 
                                      epic.priority === 3 ? 'rgba(245, 158, 11, 0.15)' : 
                                      'rgba(59, 130, 246, 0.15)',
                      color: epic.priority === 1 || epic.priority === 2 ? tokens.colors.error[400] : 
                            epic.priority === 3 ? tokens.colors.warning[400] : 
                            tokens.colors.info[400],
                      border: `1px solid ${epic.priority === 1 || epic.priority === 2 ? tokens.colors.error[500] : 
                                          epic.priority === 3 ? tokens.colors.warning[500] : 
                                          tokens.colors.info[500]}`,
                    }}
                  >
                    Priority {epic.priority}
                  </Badge>
                  {onEditEpic && (
                    <IconButton
                      icon={EditIcon}
                      size="sm"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditEpic(epic);
                      }}
                    />
                  )}
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
                        onMouseEnter={(e) => {
                          if (selectedStory?.id !== story.id) {
                            e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
                            e.currentTarget.style.transform = 'translateX(4px)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (selectedStory?.id !== story.id) {
                            e.currentTarget.style.backgroundColor = 'var(--color-bg)';
                            e.currentTarget.style.transform = 'translateX(0)';
                          }
                        }}
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
                              style={{
                                backgroundColor: story.priority === 'must_have' ? 'rgba(239, 68, 68, 0.15)' : 
                                               story.priority === 'should_have' ? 'rgba(245, 158, 11, 0.15)' : 
                                               'rgba(59, 130, 246, 0.15)',
                                color: story.priority === 'must_have' ? tokens.colors.error[400] : 
                                      story.priority === 'should_have' ? tokens.colors.warning[400] : 
                                      tokens.colors.info[400],
                                border: `1px solid ${story.priority === 'must_have' ? tokens.colors.error[500] : 
                                                    story.priority === 'should_have' ? tokens.colors.warning[500] : 
                                                    tokens.colors.info[500]}`,
                              }}
                            >
                              {story.priority?.replace('_', ' ')}
                            </Badge>
                            {onEditStory && (
                              <IconButton
                                icon={EditIcon}
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onEditStory(story, epic.title || epic.name);
                                }}
                              />
                            )}
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
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid var(--color-border)`,
    marginBottom: tokens.spacing[1],
  },

  storiesSummary: {
    display: 'flex',
    gap: tokens.spacing[3],
    alignItems: 'center',
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
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
    transition: 'all 0.3s ease',
    border: '2px solid rgba(255, 140, 26, 0.2)',
    background: 'linear-gradient(135deg, rgba(255, 140, 26, 0.05) 0%, transparent 100%)',
  },

  epicHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: tokens.spacing[6],
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    borderBottom: '2px solid rgba(255, 140, 26, 0.1)',
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
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.md,
    border: `1px solid var(--color-border)`,
    marginBottom: tokens.spacing[3],
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    backgroundColor: 'var(--color-bg)',
  },

  selectedStory: {
    backgroundColor: 'rgba(255, 140, 26, 0.05)',
    borderColor: tokens.colors.primary[500],
    boxShadow: '0 0 0 1px ' + tokens.colors.primary[500],
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
    fontSize: tokens.typography.fontSize.base[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
    color: 'var(--color-text)',
  },

  storyDetails: {
    marginTop: tokens.spacing[4],
    paddingTop: tokens.spacing[4],
    borderTop: `2px solid var(--color-border)`,
    animation: 'slideIn 0.3s ease-out',
  },

  storyBenefit: {
    fontSize: tokens.typography.fontSize.base[0],
    marginBottom: tokens.spacing[4],
    color: 'var(--color-text)',
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  acceptanceCriteria: {
    marginTop: tokens.spacing[3],
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.md,
    border: '1px solid var(--color-border)',
  },

  criteriaTitle: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    marginBottom: tokens.spacing[3],
    color: 'var(--color-text)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  criteriaList: {
    marginLeft: tokens.spacing[5],
    marginTop: 0,
    marginBottom: 0,
  },

  criteriaItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[2],
    lineHeight: tokens.typography.lineHeight.relaxed,
    color: 'var(--color-text-muted)',
  },

  noStoriesText: {
    textAlign: 'center',
    color: 'var(--color-text-muted)',
    padding: tokens.spacing[4],
  },
};

export default StoriesTab;

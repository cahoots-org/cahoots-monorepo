/**
 * ChapterList - Expandable list of chapters with their slices/tasks
 *
 * Provides a clean drill-down interface for viewing the project breakdown
 */
import React, { useState } from 'react';
import {
  Card,
  Button,
  Text,
  Heading3,
  Badge,
  IconButton,
  ChevronDownIcon,
  ChevronRightIcon,
  EditIcon,
  tokens,
} from '../design-system';

const ChapterList = ({
  chapters = [],
  slices = [],
  onEditChapter,
  onEditSlice,
  onAddSlice,
}) => {
  const [expandedChapters, setExpandedChapters] = useState(new Set());

  const toggleChapter = (chapterName) => {
    setExpandedChapters(prev => {
      const next = new Set(prev);
      if (next.has(chapterName)) {
        next.delete(chapterName);
      } else {
        next.add(chapterName);
      }
      return next;
    });
  };

  const getChapterSlices = (chapterName) => {
    return slices.filter(s => s.chapter === chapterName);
  };

  const calculateChapterPoints = (chapterSlices) => {
    return chapterSlices.reduce((sum, slice) => {
      return sum + (slice.story_points || 2);
    }, 0);
  };

  if (chapters.length === 0) {
    return (
      <div style={styles.emptyState}>
        <Text style={styles.emptyStateText}>
          No chapters generated yet. Create a system blueprint to see the project breakdown.
        </Text>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {chapters.map((chapter, index) => {
        const isExpanded = expandedChapters.has(chapter.name);
        const chapterSlices = getChapterSlices(chapter.name);
        const storyPoints = calculateChapterPoints(chapterSlices);

        return (
          <Card key={chapter.name} style={styles.chapterCard}>
            {/* Chapter Header */}
            <div
              style={styles.chapterHeader}
              onClick={() => toggleChapter(chapter.name)}
            >
              <div style={styles.chapterLeft}>
                <IconButton
                  icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
                  size="sm"
                  variant="ghost"
                  style={styles.expandIcon}
                />
                <div style={styles.chapterInfo}>
                  <div style={styles.chapterTitleRow}>
                    <Badge variant="secondary" style={styles.chapterNumber}>
                      {index + 1}
                    </Badge>
                    <Heading3 style={styles.chapterTitle}>{chapter.name}</Heading3>
                  </div>
                  <Text style={styles.chapterDescription}>{chapter.description}</Text>
                </div>
              </div>

              <div style={styles.chapterRight}>
                <div style={styles.chapterStats}>
                  <Badge variant="info">{chapterSlices.length} {chapterSlices.length === 1 ? 'feature' : 'features'}</Badge>
                  <Badge variant="secondary">{storyPoints} pts</Badge>
                </div>
                <IconButton
                  icon={EditIcon}
                  size="sm"
                  variant="ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditChapter?.(chapter);
                  }}
                />
              </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div style={styles.chapterContent}>
                {chapterSlices.length === 0 ? (
                  <div style={styles.noSlices}>
                    <Text style={styles.noSlicesText}>No features in this chapter</Text>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onAddSlice?.(chapter.name)}
                    >
                      Add Feature
                    </Button>
                  </div>
                ) : (
                  <div style={styles.slicesList}>
                    {chapterSlices.map((slice, sliceIndex) => (
                      <SliceCard
                        key={slice.name || sliceIndex}
                        slice={slice}
                        index={sliceIndex}
                        onEdit={() => onEditSlice?.(slice, chapter.name)}
                      />
                    ))}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onAddSlice?.(chapter.name)}
                      style={styles.addSliceButton}
                    >
                      + Add Feature
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
};

/**
 * Individual slice card
 */
const SliceCard = ({ slice, index, onEdit }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div style={styles.sliceCard}>
      <div
        style={styles.sliceHeader}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={styles.sliceLeft}>
          <IconButton
            icon={isExpanded ? ChevronDownIcon : ChevronRightIcon}
            size="sm"
            variant="ghost"
            style={styles.sliceExpandIcon}
          />
          <div style={styles.sliceInfo}>
            <Text style={styles.sliceName}>
              {slice.name || slice.command || slice.read_model || `${slice.type} feature`}
            </Text>
            {slice.user_story && (
              <Text style={styles.sliceStory}>{slice.user_story}</Text>
            )}
            {!slice.user_story && slice.type && (
              <Text style={styles.sliceStory}>
                {slice.type === 'state_change' ? 'User Action' :
                 slice.type === 'state_view' ? 'Screen/View' :
                 slice.type === 'automation' ? 'Background Process' : slice.type}
              </Text>
            )}
          </div>
        </div>

        <div style={styles.sliceRight}>
          {slice.story_points && (
            <Badge variant="secondary">{slice.story_points} pts</Badge>
          )}
          <IconButton
            icon={EditIcon}
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onEdit?.();
            }}
          />
        </div>
      </div>

      {isExpanded && (
        <div style={styles.sliceContent}>
          {/* User Action */}
          {slice.command && (
            <div style={styles.sliceSection}>
              <Text style={styles.sectionLabel}>User Action</Text>
              <div style={styles.elementCard}>
                <Badge variant="primary" style={styles.elementBadge}>ACT</Badge>
                <Text style={styles.elementName}>
                  {typeof slice.command === 'string' ? slice.command : slice.command.name}
                </Text>
              </div>
            </div>
          )}

          {/* System Events */}
          {slice.events?.length > 0 && (
            <div style={styles.sliceSection}>
              <Text style={styles.sectionLabel}>System Events</Text>
              <div style={styles.elementsList}>
                {slice.events.map((event, i) => (
                  <div key={i} style={styles.elementCard}>
                    <Badge variant="warning" style={styles.elementBadge}>EVT</Badge>
                    <Text style={styles.elementName}>
                      {typeof event === 'string' ? event : event.name}
                    </Text>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Screen/View */}
          {slice.read_model && (
            <div style={styles.sliceSection}>
              <Text style={styles.sectionLabel}>Screen/View</Text>
              <div style={styles.elementCard}>
                <Badge variant="info" style={styles.elementBadge}>VIEW</Badge>
                <Text style={styles.elementName}>
                  {typeof slice.read_model === 'string' ? slice.read_model : slice.read_model.name}
                </Text>
              </div>
            </div>
          )}

          {/* Acceptance Criteria */}
          {slice.acceptance_criteria?.length > 0 && (
            <div style={styles.sliceSection}>
              <Text style={styles.sectionLabel}>Acceptance Criteria</Text>
              <ul style={styles.criteriaList}>
                {slice.acceptance_criteria.map((criterion, i) => (
                  <li key={i} style={styles.criteriaItem}>{criterion}</li>
                ))}
              </ul>
            </div>
          )}
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
  },

  emptyState: {
    padding: tokens.spacing[8],
    textAlign: 'center',
  },
  emptyStateText: {
    color: 'var(--color-text-muted)',
  },

  // Chapter card
  chapterCard: {
    overflow: 'hidden',
  },
  chapterHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    padding: tokens.spacing[4],
    cursor: 'pointer',
    transition: 'background-color 0.2s ease',
    '&:hover': {
      backgroundColor: 'var(--color-bg-secondary)',
    },
  },
  chapterLeft: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[2],
    flex: 1,
  },
  expandIcon: {
    flexShrink: 0,
    marginTop: tokens.spacing[1],
  },
  chapterInfo: {
    flex: 1,
  },
  chapterTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },
  chapterNumber: {
    fontSize: tokens.typography.fontSize.xs[0],
  },
  chapterTitle: {
    margin: 0,
    fontSize: tokens.typography.fontSize.lg[0],
  },
  chapterDescription: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    margin: 0,
  },
  chapterRight: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
  },
  chapterStats: {
    display: 'flex',
    gap: tokens.spacing[2],
  },
  chapterContent: {
    borderTop: `1px solid var(--color-border)`,
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
  },
  noSlices: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.md,
  },
  noSlicesText: {
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
  },

  // Slices
  slicesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  sliceCard: {
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.md,
    border: `1px solid var(--color-border)`,
    overflow: 'hidden',
  },
  sliceHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    padding: tokens.spacing[3],
    cursor: 'pointer',
    transition: 'background-color 0.2s ease',
  },
  sliceLeft: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[2],
    flex: 1,
  },
  sliceExpandIcon: {
    flexShrink: 0,
  },
  sliceInfo: {
    flex: 1,
  },
  sliceName: {
    fontWeight: tokens.typography.fontWeight.medium,
    marginBottom: tokens.spacing[1],
  },
  sliceStory: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
  sliceRight: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  sliceContent: {
    borderTop: `1px solid var(--color-border)`,
    padding: tokens.spacing[4],
    backgroundColor: 'var(--color-bg-secondary)',
  },
  sliceSection: {
    marginBottom: tokens.spacing[4],
    '&:last-child': {
      marginBottom: 0,
    },
  },
  sectionLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    textTransform: 'uppercase',
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
  },
  elementsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  elementCard: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: tokens.spacing[2],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.sm,
  },
  elementBadge: {
    fontSize: tokens.typography.fontSize.xs[0],
    padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
  },
  elementName: {
    fontSize: tokens.typography.fontSize.sm[0],
  },
  criteriaList: {
    margin: 0,
    paddingLeft: tokens.spacing[4],
  },
  criteriaItem: {
    fontSize: tokens.typography.fontSize.sm[0],
    marginBottom: tokens.spacing[1],
    color: 'var(--color-text)',
  },
  addSliceButton: {
    marginTop: tokens.spacing[2],
    alignSelf: 'flex-start',
  },
};

export default ChapterList;

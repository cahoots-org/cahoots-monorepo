/**
 * EventModelCarousel - Card-based slice browser
 *
 * Shows one slice at a time with its Command → Event → View flow.
 * Navigate with arrows or keyboard. Ordered by chapter.
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Text, tokens } from '../design-system';

const COLORS = {
  command: '#3B82F6',
  event: '#F59E0B',
  readModel: '#10B981',
  automation: '#8B5CF6',
};

const EventModelCarousel = ({ task }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Build ordered list of slices
  const slices = useMemo(() => {
    const chapters = task?.metadata?.chapters || [];
    const commands = task?.metadata?.commands || [];
    const events = task?.metadata?.extracted_events || [];
    const readModels = task?.metadata?.read_models || [];

    const result = [];

    chapters.forEach((chapter, chapterIdx) => {
      (chapter.slices || []).forEach((slice, sliceIdx) => {
        result.push({
          ...slice,
          id: `${chapterIdx}-${sliceIdx}`,
          chapterName: chapter.name,
          chapterIndex: chapterIdx + 1,
          totalChapters: chapters.length,
          commandObj: commands.find(c => c.name === slice.command),
          readModelObj: readModels.find(r => r.name === slice.read_model),
          eventObjs: (slice.events || []).map(e =>
            events.find(ev => (ev.name || ev) === e) || { name: e }
          ),
        });
      });
    });

    // Fallback if no chapters but we have commands
    if (result.length === 0 && commands.length > 0) {
      commands.forEach((cmd, idx) => {
        result.push({
          id: `cmd-${idx}`,
          command: cmd.name,
          events: cmd.triggers_events || [],
          chapterName: 'Commands',
          chapterIndex: 1,
          totalChapters: 1,
          commandObj: cmd,
          eventObjs: (cmd.triggers_events || []).map(e =>
            events.find(ev => (ev.name || ev) === e) || { name: e }
          ),
        });
      });
    }

    return result;
  }, [task]);

  const currentSlice = slices[currentIndex];
  const totalSlices = slices.length;

  // Navigation
  const goNext = useCallback(() => {
    if (currentIndex < totalSlices - 1) {
      setCurrentIndex(i => i + 1);
    }
  }, [currentIndex, totalSlices]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(i => i - 1);
    }
  }, [currentIndex]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        goNext();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        goPrev();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrev]);

  // Empty state
  if (slices.length === 0) {
    return (
      <div style={styles.empty}>
        <Text style={styles.emptyIcon}>📋</Text>
        <Text style={styles.emptyText}>No event model data yet</Text>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Progress bar */}
      <div style={styles.progressBar}>
        <div
          style={{
            ...styles.progressFill,
            width: `${((currentIndex + 1) / totalSlices) * 100}%`
          }}
        />
      </div>

      {/* Header */}
      <div style={styles.header}>
        <div style={styles.chapterBadge}>
          {currentSlice.chapterName}
        </div>
        <Text style={styles.counter}>
          {currentIndex + 1} / {totalSlices}
        </Text>
      </div>

      {/* Card */}
      <div style={styles.cardArea}>
        <button
          style={{...styles.navButton, ...styles.navLeft}}
          onClick={goPrev}
          disabled={currentIndex === 0}
        >
          ‹
        </button>

        <div style={styles.card} key={currentSlice.id}>
          {/* Flow visualization */}
          <div style={styles.flow}>
            {/* Command */}
            {currentSlice.command && (
              <div style={styles.flowStep}>
                <div style={{...styles.node, backgroundColor: COLORS.command}}>
                  <span style={styles.nodeIcon}>▶</span>
                  <Text style={styles.nodeName}>{currentSlice.command}</Text>
                </div>
                <Text style={styles.nodeType}>Command</Text>
              </div>
            )}

            {/* Arrow */}
            {currentSlice.command && currentSlice.events?.length > 0 && (
              <div style={styles.arrow}>
                <div style={styles.arrowLine} />
                <div style={styles.arrowHead} />
              </div>
            )}

            {/* Events */}
            {currentSlice.events?.length > 0 && (
              <div style={styles.flowStep}>
                <div style={styles.eventStack}>
                  {currentSlice.events.slice(0, 3).map((evt, i) => (
                    <div
                      key={i}
                      style={{
                        ...styles.node,
                        ...styles.eventNode,
                        transform: `translateY(${i * 4}px)`,
                        zIndex: 3 - i,
                      }}
                    >
                      <span style={styles.nodeIcon}>●</span>
                      <Text style={styles.nodeName}>{evt}</Text>
                    </div>
                  ))}
                </div>
                <Text style={styles.nodeType}>
                  {currentSlice.events.length === 1 ? 'Event' : `${currentSlice.events.length} Events`}
                </Text>
              </div>
            )}

            {/* Arrow to Read Model */}
            {currentSlice.read_model && (currentSlice.events?.length > 0 || currentSlice.source_events?.length > 0) && (
              <div style={styles.arrow}>
                <div style={styles.arrowLine} />
                <div style={styles.arrowHead} />
              </div>
            )}

            {/* Read Model */}
            {currentSlice.read_model && (
              <div style={styles.flowStep}>
                <div style={{...styles.node, backgroundColor: COLORS.readModel}}>
                  <span style={styles.nodeIcon}>◧</span>
                  <Text style={styles.nodeName}>{currentSlice.read_model}</Text>
                </div>
                <Text style={styles.nodeType}>View</Text>
              </div>
            )}
          </div>

          {/* Description */}
          {(currentSlice.commandObj?.description || currentSlice.readModelObj?.description) && (
            <div style={styles.description}>
              <Text style={styles.descText}>
                {currentSlice.commandObj?.description || currentSlice.readModelObj?.description}
              </Text>
            </div>
          )}

          {/* GWT Preview */}
          {currentSlice.gwt_scenarios?.length > 0 && (
            <div style={styles.gwtPreview}>
              <Text style={styles.gwtLabel}>Test Scenario</Text>
              <div style={styles.gwtContent}>
                <Text style={styles.gwtLine}>
                  <span style={styles.gwtKey}>Given</span> {currentSlice.gwt_scenarios[0].given}
                </Text>
                <Text style={styles.gwtLine}>
                  <span style={styles.gwtKey}>When</span> {currentSlice.gwt_scenarios[0].when}
                </Text>
                <Text style={styles.gwtLine}>
                  <span style={styles.gwtKey}>Then</span> {currentSlice.gwt_scenarios[0].then}
                </Text>
              </div>
              {currentSlice.gwt_scenarios.length > 1 && (
                <Text style={styles.gwtMore}>
                  +{currentSlice.gwt_scenarios.length - 1} more scenarios
                </Text>
              )}
            </div>
          )}
        </div>

        <button
          style={{...styles.navButton, ...styles.navRight}}
          onClick={goNext}
          disabled={currentIndex === totalSlices - 1}
        >
          ›
        </button>
      </div>

      {/* Dots */}
      <div style={styles.dots}>
        {slices.slice(
          Math.max(0, currentIndex - 4),
          Math.min(totalSlices, currentIndex + 5)
        ).map((_, i) => {
          const actualIndex = Math.max(0, currentIndex - 4) + i;
          return (
            <button
              key={actualIndex}
              style={{
                ...styles.dot,
                ...(actualIndex === currentIndex ? styles.dotActive : {}),
              }}
              onClick={() => setCurrentIndex(actualIndex)}
            />
          );
        })}
        {currentIndex + 5 < totalSlices && (
          <Text style={styles.dotMore}>...</Text>
        )}
      </div>

      {/* Keyboard hint */}
      <Text style={styles.hint}>Use ← → arrows to navigate</Text>
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    padding: tokens.spacing[4],
    userSelect: 'none',
  },
  progressBar: {
    height: '3px',
    backgroundColor: tokens.colors.neutral[100],
    borderRadius: '2px',
    marginBottom: tokens.spacing[4],
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.command,
    transition: 'width 0.3s ease',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[4],
  },
  chapterBadge: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[600],
    backgroundColor: tokens.colors.neutral[100],
    padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.full,
  },
  counter: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[400],
    fontFamily: tokens.typography.fontFamily.mono,
  },
  cardArea: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  navButton: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    border: `1px solid ${tokens.colors.neutral[200]}`,
    backgroundColor: 'white',
    fontSize: '24px',
    color: tokens.colors.neutral[600],
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all 0.15s ease',
  },
  navLeft: {},
  navRight: {},
  card: {
    flex: 1,
    minHeight: '280px',
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing[5],
    display: 'flex',
    flexDirection: 'column',
  },
  flow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[5],
    flexWrap: 'wrap',
  },
  flowStep: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },
  node: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    borderRadius: tokens.borderRadius.lg,
    color: 'white',
    minWidth: '120px',
    justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  eventNode: {
    backgroundColor: COLORS.event,
  },
  eventStack: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
  },
  nodeIcon: {
    fontSize: '12px',
  },
  nodeName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    fontFamily: tokens.typography.fontFamily.mono,
    color: 'inherit',
  },
  nodeType: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  arrow: {
    display: 'flex',
    alignItems: 'center',
    paddingTop: tokens.spacing[4],
  },
  arrowLine: {
    width: '32px',
    height: '2px',
    backgroundColor: tokens.colors.neutral[300],
  },
  arrowHead: {
    width: 0,
    height: 0,
    borderTop: '6px solid transparent',
    borderBottom: '6px solid transparent',
    borderLeft: `8px solid ${tokens.colors.neutral[300]}`,
  },
  description: {
    textAlign: 'center',
    marginBottom: tokens.spacing[4],
    paddingBottom: tokens.spacing[4],
    borderBottom: `1px solid ${tokens.colors.neutral[200]}`,
  },
  descText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    lineHeight: 1.5,
  },
  gwtPreview: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.md,
    padding: tokens.spacing[3],
    borderLeft: `3px solid ${tokens.colors.success[400]}`,
  },
  gwtLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[600],
    textTransform: 'uppercase',
    marginBottom: tokens.spacing[2],
  },
  gwtContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
  },
  gwtLine: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
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
    marginTop: tokens.spacing[2],
    fontStyle: 'italic',
  },
  dots: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginTop: tokens.spacing[4],
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    border: 'none',
    backgroundColor: tokens.colors.neutral[200],
    cursor: 'pointer',
    padding: 0,
    transition: 'all 0.15s ease',
  },
  dotActive: {
    backgroundColor: COLORS.command,
    transform: 'scale(1.25)',
  },
  dotMore: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
  },
  hint: {
    textAlign: 'center',
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
    marginTop: tokens.spacing[3],
  },
  empty: {
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
    fontSize: '40px',
    marginBottom: tokens.spacing[2],
  },
  emptyText: {
    color: tokens.colors.neutral[500],
  },
};

export default EventModelCarousel;

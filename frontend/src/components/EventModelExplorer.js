/**
 * EventModelExplorer - Query-based event model navigation
 *
 * Chapters are user journeys (e.g., "User Registration", "Booking an Appointment")
 * Each chapter contains slices - individual Command → Event → View paths.
 *
 * Cross-cutting concerns shown as connection hints.
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Text, tokens } from '../design-system';

const COLORS = {
  command: { bg: '#3B82F6', light: '#EFF6FF' },
  event: { bg: '#F59E0B', light: '#FFFBEB' },
  readModel: { bg: '#10B981', light: '#ECFDF5' },
  automation: { bg: '#8B5CF6', light: '#F5F3FF' },
  crossCut: { bg: '#EC4899', light: '#FDF2F8' },
};

const EventModelExplorer = ({ task }) => {
  const [query, setQuery] = useState('');
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [expandedSlice, setExpandedSlice] = useState(null);

  // Extract chapters early so we can auto-select
  const chapters = useMemo(() => task?.metadata?.chapters || [], [task]);

  // Auto-select first chapter when chapters are available
  useEffect(() => {
    if (chapters.length > 0 && !selectedChapter) {
      setSelectedChapter(chapters[0].name);
    }
  }, [chapters, selectedChapter]);

  // Extract other data (chapters already extracted above)
  const { commands, events, readModels } = useMemo(() => {
    return {
      commands: task?.metadata?.commands || [],
      events: task?.metadata?.extracted_events || [],
      readModels: task?.metadata?.read_models || [],
    };
  }, [task]);

  // Build search index and cross-reference map
  const { searchIndex, crossRefs } = useMemo(() => {
    const index = [];
    const refs = {
      events: {},      // eventName -> { producedBy: [], consumedBy: [], chapters: [] }
      commands: {},    // cmdName -> { triggers: [], chapters: [] }
      readModels: {},  // rmName -> { sources: [], chapters: [] }
    };

    // Index chapters and slices
    chapters.forEach((chapter, chapterIdx) => {
      // Add chapter to index
      index.push({
        type: 'chapter',
        name: chapter.name,
        description: chapter.description,
        keywords: `${chapter.name} ${chapter.description || ''}`.toLowerCase(),
        data: chapter,
        chapterIdx,
      });

      // Process slices
      (chapter.slices || []).forEach((slice, sliceIdx) => {
        // Index slice
        const sliceKeywords = [
          slice.command,
          slice.read_model,
          ...(slice.events || []),
          ...(slice.gwt_scenarios || []).map(g => `${g.given} ${g.when} ${g.then}`),
        ].filter(Boolean).join(' ').toLowerCase();

        index.push({
          type: 'slice',
          name: slice.command || slice.read_model || `Slice ${sliceIdx + 1}`,
          keywords: sliceKeywords,
          data: { ...slice, chapterName: chapter.name, chapterIdx, sliceIdx },
          chapterIdx,
        });

        // Build cross-references
        if (slice.command) {
          if (!refs.commands[slice.command]) {
            refs.commands[slice.command] = { triggers: [], chapters: new Set() };
          }
          refs.commands[slice.command].triggers.push(...(slice.events || []));
          refs.commands[slice.command].chapters.add(chapter.name);
        }

        (slice.events || []).forEach(evt => {
          if (!refs.events[evt]) {
            refs.events[evt] = { producedBy: [], consumedBy: [], chapters: new Set() };
          }
          if (slice.command) {
            refs.events[evt].producedBy.push(slice.command);
          }
          refs.events[evt].chapters.add(chapter.name);
        });

        if (slice.read_model) {
          if (!refs.readModels[slice.read_model]) {
            refs.readModels[slice.read_model] = { sources: [], chapters: new Set() };
          }
          refs.readModels[slice.read_model].sources.push(...(slice.events || slice.source_events || []));
          refs.readModels[slice.read_model].chapters.add(chapter.name);
        }
      });
    });

    // Index standalone commands
    commands.forEach(cmd => {
      if (!index.find(i => i.type === 'slice' && i.data.command === cmd.name)) {
        index.push({
          type: 'command',
          name: cmd.name,
          description: cmd.description,
          keywords: `${cmd.name} ${cmd.description || ''} ${(cmd.triggers_events || []).join(' ')}`.toLowerCase(),
          data: cmd,
        });
      }
    });

    // Index standalone events
    events.forEach(evt => {
      const evtName = typeof evt === 'string' ? evt : evt.name;
      index.push({
        type: 'event',
        name: evtName,
        keywords: evtName.toLowerCase(),
        data: evt,
      });
    });

    // Convert Sets to Arrays
    Object.values(refs.events).forEach(r => r.chapters = Array.from(r.chapters));
    Object.values(refs.commands).forEach(r => r.chapters = Array.from(r.chapters));
    Object.values(refs.readModels).forEach(r => r.chapters = Array.from(r.chapters));

    return { searchIndex: index, crossRefs: refs };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapters, commands, events]);

  // Search results
  const searchResults = useMemo(() => {
    if (!query.trim()) return null;

    const q = query.toLowerCase().trim();
    const results = {
      chapters: [],
      slices: [],
      elements: [],
    };

    searchIndex.forEach(item => {
      if (item.keywords.includes(q) || item.name.toLowerCase().includes(q)) {
        if (item.type === 'chapter') {
          results.chapters.push(item);
        } else if (item.type === 'slice') {
          results.slices.push(item);
        } else {
          results.elements.push(item);
        }
      }
    });

    // Sort by relevance (name match > keyword match)
    const sortByRelevance = (a, b) => {
      const aNameMatch = a.name.toLowerCase().includes(q);
      const bNameMatch = b.name.toLowerCase().includes(q);
      if (aNameMatch && !bNameMatch) return -1;
      if (!aNameMatch && bNameMatch) return 1;
      return 0;
    };

    results.chapters.sort(sortByRelevance);
    results.slices.sort(sortByRelevance);
    results.elements.sort(sortByRelevance);

    return results;
  }, [query, searchIndex]);

  // Get slices for selected chapter
  const chapterSlices = useMemo(() => {
    if (!selectedChapter) return [];
    const chapter = chapters.find(c => c.name === selectedChapter);
    if (!chapter) return [];

    return (chapter.slices || []).map((slice, idx) => ({
      ...slice,
      chapterName: chapter.name,
      sliceIdx: idx,
      commandObj: commands.find(c => c.name === slice.command),
      readModelObj: readModels.find(r => r.name === slice.read_model),
    }));
  }, [selectedChapter, chapters, commands, readModels]);

  // Get cross-cutting info for an element
  const getCrossRefs = useCallback((type, name) => {
    if (type === 'event') {
      return crossRefs.events[name] || { producedBy: [], consumedBy: [], chapters: [] };
    }
    if (type === 'command') {
      return crossRefs.commands[name] || { triggers: [], chapters: [] };
    }
    if (type === 'readModel') {
      return crossRefs.readModels[name] || { sources: [], chapters: [] };
    }
    return {};
  }, [crossRefs]);

  // Handle search input
  const handleSearch = (e) => {
    setQuery(e.target.value);
    setSelectedChapter(null);
  };

  // Handle chapter selection
  const handleSelectChapter = (chapterName) => {
    setSelectedChapter(chapterName);
    setQuery('');
    setExpandedSlice(null);
  };

  // Handle search result click
  const handleResultClick = (result) => {
    if (result.type === 'chapter') {
      handleSelectChapter(result.name);
    } else if (result.type === 'slice') {
      handleSelectChapter(result.data.chapterName);
      setTimeout(() => setExpandedSlice(result.data.sliceIdx), 100);
    } else {
      // For standalone elements, find which chapter(s) they belong to
      const refs = getCrossRefs(result.type, result.name);
      if (refs.chapters?.length > 0) {
        handleSelectChapter(refs.chapters[0]);
      }
    }
  };

  // Empty state
  if (chapters.length === 0 && commands.length === 0) {
    return (
      <div style={styles.empty}>
        <Text style={styles.emptyIcon}>🔍</Text>
        <Text style={styles.emptyTitle}>Event Model Explorer</Text>
        <Text style={styles.emptyText}>
          No event model data yet. Once analysis completes, you can explore the system design here.
        </Text>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Search bar */}
      <div style={styles.searchSection}>
        <div style={styles.searchBar}>
          <span style={styles.searchIcon}>🔍</span>
          <input
            type="text"
            value={query}
            onChange={handleSearch}
            placeholder="Search... try 'register', 'book', 'payment'"
            style={styles.searchInput}
          />
          {query && (
            <button style={styles.clearBtn} onClick={() => setQuery('')}>×</button>
          )}
        </div>
      </div>

      {/* Search results */}
      {searchResults && (
        <div style={styles.results}>
          {searchResults.chapters.length === 0 &&
           searchResults.slices.length === 0 &&
           searchResults.elements.length === 0 ? (
            <Text style={styles.noResults}>No results for "{query}"</Text>
          ) : (
            <>
              {searchResults.chapters.length > 0 && (
                <div style={styles.resultGroup}>
                  <Text style={styles.resultGroupTitle}>Chapters</Text>
                  {searchResults.chapters.map((r, i) => (
                    <button
                      key={i}
                      style={styles.resultItem}
                      onClick={() => handleResultClick(r)}
                    >
                      <span style={styles.resultIcon}>📖</span>
                      <div style={styles.resultInfo}>
                        <Text style={styles.resultName}>{r.name}</Text>
                        {r.description && (
                          <Text style={styles.resultDesc}>{r.description}</Text>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {searchResults.slices.length > 0 && (
                <div style={styles.resultGroup}>
                  <Text style={styles.resultGroupTitle}>Commands & Views</Text>
                  {searchResults.slices.slice(0, 8).map((r, i) => (
                    <button
                      key={i}
                      style={styles.resultItem}
                      onClick={() => handleResultClick(r)}
                    >
                      <span style={styles.resultIcon}>→</span>
                      <div style={styles.resultInfo}>
                        <Text style={styles.resultName}>{r.name}</Text>
                        <Text style={styles.resultDesc}>in {r.data.chapterName}</Text>
                      </div>
                    </button>
                  ))}
                  {searchResults.slices.length > 8 && (
                    <Text style={styles.moreResults}>
                      +{searchResults.slices.length - 8} more
                    </Text>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Chapter tabs (when not searching) */}
      {!searchResults && (
        <div style={styles.chapterTabs}>
          {chapters.map((chapter, idx) => (
            <button
              key={chapter.name}
              style={{
                ...styles.chapterTab,
                ...(selectedChapter === chapter.name ? styles.chapterTabActive : {}),
              }}
              onClick={() => handleSelectChapter(chapter.name)}
            >
              <span style={styles.chapterNum}>{idx + 1}</span>
              <Text style={styles.chapterTabName}>{chapter.name}</Text>
            </button>
          ))}
        </div>
      )}

      {/* Flow visualization */}
      {selectedChapter && !searchResults && (
        <div style={styles.flowSection}>
          <div style={styles.flowHeader}>
            <Text style={styles.flowTitle}>{selectedChapter}</Text>
            <Text style={styles.flowCount}>{chapterSlices.length} {chapterSlices.length === 1 ? 'slice' : 'slices'}</Text>
          </div>

          <div style={styles.flowList}>
            {chapterSlices.map((slice, idx) => (
              <FlowCard
                key={idx}
                slice={slice}
                index={idx}
                isExpanded={expandedSlice === idx}
                onToggle={() => setExpandedSlice(expandedSlice === idx ? null : idx)}
                getCrossRefs={getCrossRefs}
                currentChapter={selectedChapter}
                onNavigateChapter={handleSelectChapter}
              />
            ))}
          </div>
        </div>
      )}

      {/* Loading state - should rarely show since we auto-select */}
      {!selectedChapter && !searchResults && chapters.length > 0 && (
        <div style={styles.prompt}>
          <Text style={styles.promptText}>Loading...</Text>
        </div>
      )}
    </div>
  );
};

/**
 * FlowCard - Single slice shown as a narrative flow
 */
const FlowCard = ({
  slice,
  index,
  isExpanded,
  onToggle,
  getCrossRefs,
  currentChapter,
  onNavigateChapter
}) => {
  const hasCommand = !!slice.command;
  const hasEvents = slice.events?.length > 0;
  const hasReadModel = !!slice.read_model;
  const hasGWT = slice.gwt_scenarios?.length > 0;

  // Get cross-references for events
  const eventCrossRefs = useMemo(() => {
    if (!hasEvents) return [];
    return slice.events.map(evt => {
      const refs = getCrossRefs('event', evt);
      const otherChapters = refs.chapters?.filter(c => c !== currentChapter) || [];
      return { name: evt, otherChapters };
    });
  }, [slice.events, hasEvents, getCrossRefs, currentChapter]);

  const hasCrossRefs = eventCrossRefs.some(e => e.otherChapters.length > 0);

  return (
    <div style={styles.flowCard}>
      {/* Flow visualization */}
      <div style={styles.flowViz} onClick={onToggle}>
        <div style={styles.flowNum}>{index + 1}</div>

        <div style={styles.flowNodes}>
          {/* Command */}
          {hasCommand && (
            <>
              <div style={{...styles.flowNode, backgroundColor: COLORS.command.bg}}>
                <Text style={styles.flowNodeText}>{slice.command}</Text>
              </div>
              {hasEvents && <div style={styles.flowArrow}>→</div>}
            </>
          )}

          {/* Events */}
          {hasEvents && (
            <>
              <div style={styles.eventGroup}>
                {slice.events.map((evt, i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.flowNode,
                      ...styles.eventNode,
                      marginTop: i > 0 ? '-8px' : 0,
                      zIndex: slice.events.length - i,
                    }}
                  >
                    <Text style={styles.flowNodeText}>{evt}</Text>
                  </div>
                ))}
              </div>
              {hasReadModel && <div style={styles.flowArrow}>→</div>}
            </>
          )}

          {/* Read Model */}
          {hasReadModel && (
            <div style={{...styles.flowNode, backgroundColor: COLORS.readModel.bg}}>
              <Text style={styles.flowNodeText}>{slice.read_model}</Text>
            </div>
          )}
        </div>

        {/* Cross-ref indicator */}
        {hasCrossRefs && (
          <div style={styles.crossRefBadge} title="Connected to other chapters">
            ↗
          </div>
        )}

        <div style={styles.expandIcon}>{isExpanded ? '−' : '+'}</div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div style={styles.flowDetails}>
          {/* Description */}
          {(slice.commandObj?.description || slice.readModelObj?.description) && (
            <div style={styles.detailSection}>
              <Text style={styles.detailText}>
                {slice.commandObj?.description || slice.readModelObj?.description}
              </Text>
            </div>
          )}

          {/* Cross-cutting connections */}
          {hasCrossRefs && (
            <div style={styles.crossRefSection}>
              <Text style={styles.crossRefTitle}>Also used in:</Text>
              <div style={styles.crossRefList}>
                {eventCrossRefs
                  .filter(e => e.otherChapters.length > 0)
                  .map((e, i) => (
                    <div key={i} style={styles.crossRefItem}>
                      <span style={styles.crossRefEvent}>{e.name}</span>
                      <span style={styles.crossRefArrow}>→</span>
                      {e.otherChapters.map((ch, j) => (
                        <button
                          key={j}
                          style={styles.crossRefChapter}
                          onClick={(ev) => {
                            ev.stopPropagation();
                            onNavigateChapter(ch);
                          }}
                        >
                          {ch}
                        </button>
                      ))}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* GWT Scenarios */}
          {hasGWT && (
            <div style={styles.gwtSection}>
              <Text style={styles.gwtTitle}>
                Test Scenarios ({slice.gwt_scenarios.length})
              </Text>
              {slice.gwt_scenarios.slice(0, 2).map((gwt, i) => (
                <div key={i} style={styles.gwtCard}>
                  <div style={styles.gwtLine}>
                    <span style={styles.gwtKey}>Given</span>
                    <Text style={styles.gwtValue}>{gwt.given}</Text>
                  </div>
                  <div style={styles.gwtLine}>
                    <span style={styles.gwtKey}>When</span>
                    <Text style={styles.gwtValue}>{gwt.when}</Text>
                  </div>
                  <div style={styles.gwtLine}>
                    <span style={styles.gwtKey}>Then</span>
                    <Text style={styles.gwtValue}>{gwt.then}</Text>
                  </div>
                </div>
              ))}
              {slice.gwt_scenarios.length > 2 && (
                <Text style={styles.gwtMore}>
                  +{slice.gwt_scenarios.length - 2} more scenarios
                </Text>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    overflow: 'hidden',
  },

  // Search
  searchSection: {
    padding: tokens.spacing[4],
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
  },
  searchIcon: {
    marginRight: tokens.spacing[2],
    fontSize: '16px',
  },
  searchInput: {
    flex: 1,
    border: 'none',
    background: 'none',
    fontSize: tokens.typography.fontSize.base[0],
    outline: 'none',
    color: tokens.colors.neutral[900],
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: tokens.colors.neutral[400],
    cursor: 'pointer',
    padding: 0,
    marginLeft: tokens.spacing[2],
  },

  // Results
  results: {
    padding: tokens.spacing[4],
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
    maxHeight: '300px',
    overflowY: 'auto',
  },
  noResults: {
    color: tokens.colors.neutral[500],
    textAlign: 'center',
    padding: tokens.spacing[4],
  },
  resultGroup: {
    marginBottom: tokens.spacing[4],
  },
  resultGroupTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[500],
    textTransform: 'uppercase',
    marginBottom: tokens.spacing[2],
  },
  resultItem: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    width: '100%',
    padding: tokens.spacing[3],
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.neutral[200]}`,
    borderRadius: tokens.borderRadius.md,
    cursor: 'pointer',
    marginBottom: tokens.spacing[2],
    textAlign: 'left',
    transition: 'background-color 0.15s',
  },
  resultIcon: {
    fontSize: '16px',
  },
  resultInfo: {
    flex: 1,
    minWidth: 0,
  },
  resultName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[900],
  },
  resultDesc: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[500],
    marginTop: '2px',
  },
  moreResults: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
    fontStyle: 'italic',
    padding: tokens.spacing[2],
  },

  // Chapter tabs
  chapterTabs: {
    display: 'flex',
    gap: tokens.spacing[2],
    padding: tokens.spacing[4],
    overflowX: 'auto',
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
  },
  chapterTab: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    backgroundColor: 'white',
    border: `1px solid ${tokens.colors.neutral[200]}`,
    borderRadius: tokens.borderRadius.full,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s',
  },
  chapterTabActive: {
    backgroundColor: COLORS.command.bg,
    borderColor: COLORS.command.bg,
    color: 'white',
  },
  chapterNum: {
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.neutral[200],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.bold,
  },
  chapterTabName: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },

  // Flow section
  flowSection: {
    padding: tokens.spacing[4],
  },
  flowHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing[4],
  },
  flowTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[900],
  },
  flowCount: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
  },
  flowList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  // Flow card
  flowCard: {
    border: `1px solid ${tokens.colors.neutral[200]}`,
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
  },
  flowViz: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  flowNum: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.neutral[100],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.neutral[600],
    flexShrink: 0,
  },
  flowNodes: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flex: 1,
    flexWrap: 'wrap',
  },
  flowNode: {
    padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.md,
    color: 'white',
  },
  eventNode: {
    backgroundColor: COLORS.event.bg,
  },
  eventGroup: {
    display: 'flex',
    flexDirection: 'column',
  },
  flowNodeText: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    fontFamily: tokens.typography.fontFamily.mono,
    color: 'inherit',
  },
  flowArrow: {
    color: tokens.colors.neutral[400],
    fontSize: tokens.typography.fontSize.lg[0],
  },
  crossRefBadge: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: COLORS.crossCut.light,
    color: COLORS.crossCut.bg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    flexShrink: 0,
  },
  expandIcon: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.neutral[100],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    color: tokens.colors.neutral[500],
    flexShrink: 0,
  },

  // Flow details
  flowDetails: {
    padding: tokens.spacing[4],
    paddingTop: 0,
    borderTop: `1px solid ${tokens.colors.neutral[100]}`,
    backgroundColor: tokens.colors.neutral[50],
  },
  detailSection: {
    paddingTop: tokens.spacing[4],
  },
  detailText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[600],
    lineHeight: 1.5,
  },

  // Cross-references
  crossRefSection: {
    paddingTop: tokens.spacing[4],
  },
  crossRefTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: COLORS.crossCut.bg,
    marginBottom: tokens.spacing[2],
  },
  crossRefList: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  crossRefItem: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    flexWrap: 'wrap',
  },
  crossRefEvent: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontFamily: tokens.typography.fontFamily.mono,
    color: COLORS.event.bg,
  },
  crossRefArrow: {
    color: tokens.colors.neutral[400],
    fontSize: tokens.typography.fontSize.xs[0],
  },
  crossRefChapter: {
    fontSize: tokens.typography.fontSize.xs[0],
    padding: `2px ${tokens.spacing[2]}`,
    backgroundColor: COLORS.crossCut.light,
    color: COLORS.crossCut.bg,
    border: 'none',
    borderRadius: tokens.borderRadius.sm,
    cursor: 'pointer',
    fontWeight: tokens.typography.fontWeight.medium,
  },

  // GWT
  gwtSection: {
    paddingTop: tokens.spacing[4],
  },
  gwtTitle: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[600],
    marginBottom: tokens.spacing[2],
  },
  gwtCard: {
    backgroundColor: 'white',
    borderRadius: tokens.borderRadius.md,
    padding: tokens.spacing[3],
    marginBottom: tokens.spacing[2],
    borderLeft: `3px solid ${tokens.colors.success[400]}`,
  },
  gwtLine: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },
  gwtKey: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[700],
    minWidth: '45px',
  },
  gwtValue: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[600],
    lineHeight: 1.4,
  },
  gwtMore: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: tokens.colors.neutral[400],
    fontStyle: 'italic',
  },

  // Prompt
  prompt: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[8],
    textAlign: 'center',
  },
  promptIcon: {
    fontSize: '32px',
    marginBottom: tokens.spacing[2],
  },
  promptText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
  },

  // Empty
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
  emptyTitle: {
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[2],
  },
  emptyText: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: tokens.colors.neutral[500],
    textAlign: 'center',
  },
};

export default EventModelExplorer;

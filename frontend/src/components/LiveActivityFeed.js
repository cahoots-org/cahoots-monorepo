/**
 * LiveActivityFeed - Real-time activity stream during task processing
 *
 * Shows a live feed of what's happening on the backend:
 * - LLM calls and responses
 * - Tasks being created
 * - Events/commands being discovered
 * - Stage transitions
 *
 * Makes the wait feel productive and engaging.
 */
import React, { useState, useEffect, useRef } from 'react';
import { Text, tokens } from '../design-system';
import { useWebSocket } from '../contexts/WebSocketContext';

const LiveActivityFeed = ({ taskId }) => {
  const [activities, setActivities] = useState([]);
  const feedRef = useRef(null);
  const { subscribe, connected } = useWebSocket();

  // Auto-scroll to bottom when new activities arrive
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [activities]);

  // Subscribe to WebSocket events for this task
  useEffect(() => {
    if (!connected || !taskId) return;

    const unsubscribe = subscribe((event) => {
      // Filter for events related to this task
      if (event.task_id !== taskId && event.root_task_id !== taskId) return;

      const activity = mapEventToActivity(event);
      if (activity) {
        setActivities(prev => [...prev.slice(-50), activity]); // Keep last 50
      }
    });

    return () => unsubscribe?.();
  }, [connected, subscribe, taskId]);

  // Add initial activity
  useEffect(() => {
    setActivities([{
      id: 'start',
      type: 'info',
      icon: '🚀',
      message: 'Starting project analysis...',
      timestamp: new Date(),
    }]);
  }, [taskId]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.liveIndicator}>
          <div style={styles.liveDot} />
          <Text style={styles.liveText}>Live</Text>
        </div>
        <Text style={styles.title}>Activity</Text>
      </div>

      <div ref={feedRef} style={styles.feed}>
        {activities.map((activity, index) => (
          <ActivityItem key={activity.id || index} activity={activity} />
        ))}
        <TypingIndicator />
      </div>
    </div>
  );
};

const ActivityItem = ({ activity }) => {
  const timeAgo = getTimeAgo(activity.timestamp);

  return (
    <div style={{
      ...styles.activityItem,
      ...(activity.type === 'success' && styles.activitySuccess),
      ...(activity.type === 'milestone' && styles.activityMilestone),
    }}>
      <span style={styles.activityIcon}>{activity.icon}</span>
      <div style={styles.activityContent}>
        <Text style={styles.activityMessage}>{activity.message}</Text>
        {activity.detail && (
          <Text style={styles.activityDetail}>{activity.detail}</Text>
        )}
      </div>
      <Text style={styles.activityTime}>{timeAgo}</Text>
    </div>
  );
};

const TypingIndicator = () => (
  <div style={styles.typingIndicator}>
    <div style={styles.typingDots}>
      <div style={{ ...styles.typingDot, animationDelay: '0ms' }} />
      <div style={{ ...styles.typingDot, animationDelay: '150ms' }} />
      <div style={{ ...styles.typingDot, animationDelay: '300ms' }} />
    </div>
    <Text style={styles.typingText}>AI is thinking...</Text>
  </div>
);

// Map WebSocket events to activity items
function mapEventToActivity(event) {
  const type = event.type || event.event_type;
  const data = event.data || event;

  switch (type) {
    case 'task.created':
      return {
        id: `task-${Date.now()}-${Math.random()}`,
        type: 'success',
        icon: '✨',
        message: 'Created task',
        detail: data.description?.substring(0, 60) + (data.description?.length > 60 ? '...' : ''),
        timestamp: new Date(),
      };

    case 'task.updated':
      return {
        id: `update-${Date.now()}-${Math.random()}`,
        type: 'info',
        icon: '📝',
        message: 'Updated task data',
        timestamp: new Date(),
      };

    case 'task.status_changed':
      if (data.new_status === 'completed') {
        return {
          id: `complete-${Date.now()}`,
          type: 'success',
          icon: '🎉',
          message: 'Processing complete!',
          timestamp: new Date(),
        };
      } else if (data.new_status === 'processing') {
        return {
          id: `processing-${Date.now()}`,
          type: 'info',
          icon: '⚙️',
          message: 'Started processing...',
          timestamp: new Date(),
        };
      }
      return null;

    case 'decomposition.started':
      return {
        id: `decomp-start-${Date.now()}`,
        type: 'milestone',
        icon: '🔨',
        message: 'Starting task decomposition',
        timestamp: new Date(),
      };

    case 'decomposition.completed':
      return {
        id: `decomp-done-${Date.now()}`,
        type: 'success',
        icon: '✅',
        message: 'Task decomposition complete',
        detail: data.subtasks_count ? `${data.subtasks_count} subtasks created` : null,
        timestamp: new Date(),
      };

    case 'context.updated':
      const contextMessages = {
        'tech_stack': { icon: '🔧', message: 'Analyzed tech stack' },
        'epics_and_stories': { icon: '📚', message: 'Created epics and user stories' },
        'decomposed_tasks': { icon: '📋', message: 'Decomposed into tasks' },
      };
      const ctx = contextMessages[data.data_key] || { icon: '📊', message: data.message || 'Updated project context' };
      return {
        id: `ctx-${Date.now()}-${Math.random()}`,
        type: 'info',
        icon: ctx.icon,
        message: ctx.message,
        timestamp: new Date(),
      };

    case 'event_modeling.started':
      return {
        id: `em-start-${Date.now()}`,
        type: 'milestone',
        icon: '⚡',
        message: 'Starting event modeling analysis',
        timestamp: new Date(),
      };

    case 'event_modeling.progress':
      const events = data.events || 0;
      const commands = data.commands || 0;
      return {
        id: `em-progress-${Date.now()}-${Math.random()}`,
        type: 'info',
        icon: '🔄',
        message: 'Building event model...',
        detail: events || commands ? `${events} events, ${commands} commands` : null,
        timestamp: new Date(),
      };

    case 'event_modeling.completed':
      return {
        id: `em-done-${Date.now()}`,
        type: 'success',
        icon: '✅',
        message: 'Event model complete!',
        detail: `${data.events || 0} events, ${data.commands || 0} commands, ${data.read_models || 0} read models`,
        timestamp: new Date(),
      };

    case 'event_modeling.error':
      return {
        id: `em-error-${Date.now()}`,
        type: 'error',
        icon: '❌',
        message: 'Event modeling error',
        detail: data.error || data.message,
        timestamp: new Date(),
      };

    case 'task.processing_update':
      return {
        id: `proc-${Date.now()}-${Math.random()}`,
        type: 'info',
        icon: '🔄',
        message: data.message || 'Processing...',
        timestamp: new Date(),
      };

    default:
      // Log unknown events for debugging (but not pings/heartbeats)
      if (type && !type.includes('ping') && !type.includes('heartbeat') && !type.includes('connection')) {
        console.log('[ActivityFeed] Event:', type, data);
      }
      return null;
  }
}

function getTimeAgo(date) {
  if (!date) return '';
  const seconds = Math.floor((new Date() - new Date(date)) / 1000);
  if (seconds < 5) return 'now';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m`;
}

const styles = {
  container: {
    backgroundColor: 'var(--color-bg-secondary)',
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    height: '300px',
  },

  header: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    borderBottom: '1px solid var(--color-border)',
  },

  liveIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
  },

  liveDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.success[500],
    animation: 'pulse 2s infinite',
  },

  liveText: {
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.success[500],
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  title: {
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--color-text-muted)',
  },

  feed: {
    flex: 1,
    overflowY: 'auto',
    padding: tokens.spacing[3],
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },

  activityItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacing[3],
    padding: tokens.spacing[2],
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'var(--color-bg)',
    animation: 'slideIn 0.2s ease-out',
  },

  activitySuccess: {
    backgroundColor: `${tokens.colors.success[500]}15`,
    borderLeft: `3px solid ${tokens.colors.success[500]}`,
  },

  activityMilestone: {
    backgroundColor: `${tokens.colors.primary[500]}15`,
    borderLeft: `3px solid ${tokens.colors.primary[500]}`,
  },

  activityIcon: {
    fontSize: '16px',
    flexShrink: 0,
    marginTop: '2px',
  },

  activityContent: {
    flex: 1,
    minWidth: 0,
  },

  activityMessage: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    lineHeight: 1.4,
  },

  activityDetail: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginTop: tokens.spacing[1],
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },

  activityTime: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    flexShrink: 0,
  },

  typingIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[2],
    opacity: 0.7,
  },

  typingDots: {
    display: 'flex',
    gap: '4px',
  },

  typingDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-text-muted)',
    animation: 'bounce 1s infinite',
  },

  typingText: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
};

// Add keyframe animations
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes bounce {
      0%, 60%, 100% {
        transform: translateY(0);
      }
      30% {
        transform: translateY(-4px);
      }
    }

    @keyframes pulse {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
    }
  `;
  document.head.appendChild(styleSheet);
}

export default LiveActivityFeed;

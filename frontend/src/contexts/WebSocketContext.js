// Simplified WebSocket Context - Replaces complex per-task WebSocket connections
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys, invalidateQueries } from '../lib/query-client';
import { useAuth } from './AuthContext';
import { useApp } from './AppContext';
import { getQueryDebouncer } from '../utils/queryDebounce';

const WebSocketContext = createContext();

// WebSocket connection manager
class WebSocketManager {
  constructor() {
    this.ws = null;
    this.subscribers = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.isConnecting = false;
    this.shouldReconnect = true;
  }

  connect(url, token) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    if (this.isConnecting) {
      return Promise.resolve();
    }

    this.isConnecting = true;
    this.shouldReconnect = true;

    return new Promise((resolve, reject) => {
      try {
        // Add auth token to WebSocket URL
        const wsUrl = new URL(url);
        wsUrl.searchParams.set('token', token);
        
        this.ws = new WebSocket(wsUrl.toString());

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;
          this.notifySubscribers('connected', { connected: true });
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Received message:', data);
            this.notifySubscribers('message', data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          this.isConnecting = false;
          this.notifySubscribers('disconnected', { connected: false });
          
          if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(url, token);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnecting = false;
          this.notifySubscribers('error', error);
          reject(error);
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  scheduleReconnect(url, token) {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    
    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect(url, token).catch(error => {
          console.error('Reconnect failed:', error);
        });
      }
    }, delay);
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscribers.clear();
  }

  subscribe(id, callback) {
    this.subscribers.set(id, callback);
    
    // Return unsubscribe function
    return () => {
      this.subscribers.delete(id);
    };
  }

  notifySubscribers(type, data) {
    this.subscribers.forEach(callback => {
      try {
        callback(type, data);
      } catch (error) {
        console.error('Error in WebSocket subscriber:', error);
      }
    });
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  send(data) {
    if (this.isConnected()) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }
}

// Create singleton instance
const wsManager = new WebSocketManager();

export const WebSocketProvider = ({ children }) => {
  const [connectionState, setConnectionState] = useState({
    connected: false,
    connecting: false,
    error: null,
  });
  
  const { user, isAuthenticated } = useAuth();
  const { showError, showSuccess } = useApp();
  const queryClient = useQueryClient();
  const subscriptionRef = useRef(null);
  const debouncerRef = useRef(null);
  const shouldConnectRef = useRef(false);

  // WebSocket URL construction
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
    
    return `${protocol}//${host}${port !== '80' && port !== '443' ? ':' + port : ''}/ws/global`;
  };

  // Handle WebSocket messages
  const handleWebSocketMessage = (type, data) => {
    switch (type) {
      case 'connected':
        setConnectionState({ connected: true, connecting: false, error: null });
        break;
        
      case 'disconnected':
        setConnectionState({ connected: false, connecting: false, error: null });
        break;
        
      case 'error':
        setConnectionState({ connected: false, connecting: false, error: data });
        showError('WebSocket connection error');
        break;
        
      case 'message':
        handleTaskMessage(data);
        break;
    }
  };

  // Handle task-related messages
  const handleTaskMessage = (data) => {
    console.log('[WebSocket] handleTaskMessage called with:', data);
    if (!data.type) return;


    switch (data.type) {
      case 'task.created':
      case 'task.updated':
      case 'task.status_changed':
        // Invalidate task list and stats
        invalidateQueries.tasks.list();
        invalidateQueries.tasks.stats();

        // Update specific task if we have the ID
        if (data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.task_id)
          });
        }

        // Also invalidate parent task tree if this is a subtask
        if (data.parent_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.parent_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.parent_id)
          });
        }

        // Also invalidate root task tree if provided
        if (data.root_task_id && data.root_task_id !== data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.root_task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.root_task_id)
          });
        }
        break;
        
      case 'decomposition.started':
      case 'decomposition.completed':
      case 'decomposition.error':
        // These events indicate changes to the task tree structure
        if (data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.task_id)
          });
        }
        break;

      case 'task.approved':
        // Show success notification
        showSuccess(`Task approved: ${data.task_id} by ${data.approved_by}`);
        
        // Invalidate task list and stats to refresh pending approvals
        invalidateQueries.tasks.list();
        invalidateQueries.tasks.stats();
        
        // Update specific task
        if (data.task_id) {
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.tasks.detail(data.task_id) 
          });
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.tasks.tree(data.task_id) 
          });
        }
        break;
        
      case 'task.rejected':
        // Show rejection notification
        const message = data.new_description 
          ? `Task rejected and resubmitted: ${data.task_id} by ${data.rejected_by}`
          : `Task rejected: ${data.task_id} by ${data.rejected_by}`;
        showError(message);
        
        // Invalidate task list and stats to refresh pending approvals
        invalidateQueries.tasks.list();
        invalidateQueries.tasks.stats();
        
        // Update specific task
        if (data.task_id) {
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.tasks.detail(data.task_id) 
          });
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.tasks.tree(data.task_id) 
          });
        }
        break;
        
      case 'task.completed':
        // Don't show notification - too noisy for task completions

        // Just invalidate related queries
        invalidateQueries.tasks.list();
        invalidateQueries.tasks.stats();

        if (data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.task_id)
          });
        }
        break;
        
      case 'task.deleted':
        // Remove from cache immediately for the specific task
        if (data.task_id) {
          queryClient.removeQueries({ 
            queryKey: queryKeys.tasks.detail(data.task_id) 
          });
          queryClient.removeQueries({ 
            queryKey: queryKeys.tasks.tree(data.task_id) 
          });
        }
        
        // Debounce list and stats invalidations to prevent flooding
        if (!debouncerRef.current) {
          debouncerRef.current = getQueryDebouncer(queryClient, 500);
        }
        
        debouncerRef.current.invalidate('tasks.list', () => {
          invalidateQueries.tasks.list();
        });
        
        debouncerRef.current.invalidate('tasks.stats', () => {
          invalidateQueries.tasks.stats();
        });
        break;
        
      case 'operator.status':
        // Handle operator status updates
        // Could show loading states based on operator progress
        break;
        
      case 'service.status':
        // Handle detailed service status updates

        // Don't show notifications - let individual components handle service.status events
        // This allows DecompositionStatus to display them as status messages instead

        // Still invalidate queries to refresh UI if needed
        if (data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.task_id)
          });
        }
        break;

      case 'event_modeling.started':
      case 'event_modeling.progress':
        // Let EventModelTab handle these via subscribe - don't show notifications
        break;

      case 'event_modeling.completed':
        // Show success notification
        showSuccess(data.message || 'Event model generated successfully');

        // Invalidate task queries to refresh the event model data
        if (data.task_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.detail(data.task_id)
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.tree(data.task_id)
          });
        }
        break;

      case 'event_modeling.error':
        // Show error notification
        showError(data.message || 'Event model generation failed');
        break;
    }
  };

  // Manual connection control - only connect when explicitly requested
  const connect = React.useCallback(() => {
    if (!isAuthenticated() || !user) {
      console.log('Cannot connect WebSocket: not authenticated');
      return Promise.reject(new Error('Not authenticated'));
    }

    if (connectionState.connected || connectionState.connecting) {
      console.log('WebSocket already connected or connecting');
      return Promise.resolve();
    }

    const token = localStorage.getItem('token') || 'dev-bypass-token';
    setConnectionState({ connected: false, connecting: true, error: null });
    
    // Subscribe to WebSocket events
    subscriptionRef.current = wsManager.subscribe(
      'app-context',
      handleWebSocketMessage
    );
    
    // Connect
    return wsManager.connect(getWebSocketUrl(), token)
      .then(() => {
        setConnectionState({ connected: true, connecting: false, error: null });
        shouldConnectRef.current = true;
      })
      .catch(error => {
        console.error('WebSocket connection failed:', error);
        setConnectionState({ connected: false, connecting: false, error });
        if (subscriptionRef.current) {
          subscriptionRef.current();
          subscriptionRef.current = null;
        }
        throw error;
      });
  }, [isAuthenticated, user, connectionState.connected, connectionState.connecting, getWebSocketUrl, handleWebSocketMessage]);

  const disconnect = React.useCallback(() => {
    if (subscriptionRef.current) {
      subscriptionRef.current();
      subscriptionRef.current = null;
    }
    
    // Flush any pending debounced invalidations
    if (debouncerRef.current) {
      debouncerRef.current.flush();
    }
    
    wsManager.disconnect();
    setConnectionState({ connected: false, connecting: false, error: null });
    shouldConnectRef.current = false;
  }, []);

  // Only disconnect when user logs out (don't auto-connect)
  useEffect(() => {
    if (!isAuthenticated() && shouldConnectRef.current) {
      disconnect();
    }

    // Cleanup on unmount
    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current();
      }
      if (debouncerRef.current) {
        debouncerRef.current.cancel();
      }
    };
  }, [isAuthenticated, disconnect]);

  // Context value
  const contextValue = {
    // Connection state
    ...connectionState,
    
    // Actions
    connect,
    disconnect,
    send: (data) => wsManager.send(data),
    reconnect: () => {
      if (isAuthenticated() && user) {
        const token = localStorage.getItem('token') || 'dev-bypass-token';
        return wsManager.connect(getWebSocketUrl(), token);
      }
    },
    
    // Subscribe to specific message types
    subscribe: (callback) => wsManager.subscribe(`subscriber-${Date.now()}`, (type, data) => {
      // For 'message' events, forward the actual message data
      // For other events (connected, disconnected, error), forward the event info
      if (type === 'message') {
        callback(data);
      } else {
        callback(type);
      }
    }),
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Custom hook to use WebSocket context
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export default WebSocketContext;
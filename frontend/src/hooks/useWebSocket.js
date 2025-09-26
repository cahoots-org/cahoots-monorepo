import { useState, useEffect, useCallback, useRef } from 'react';

// WebSocket connection states
export const WS_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected'
};

/**
 * Custom hook for managing WebSocket connections
 * @param {string|Function} urlOrGetter - Base URL or function that returns URL for WebSocket connection
 * @param {Function} onMessage - Callback for handling incoming messages
 * @returns {Object} WebSocket connection utilities
 */
const useWebSocket = (urlOrGetter, onMessage) => {
  const [wsState, setWsState] = useState(WS_STATES.DISCONNECTED);
  const wsStateRef = useRef(WS_STATES.DISCONNECTED);
  
  // WebSocket connection management refs
  const socketRef = useRef(null);
  const taskIdRef = useRef(null);
  const connectionTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const lastConnectionAttemptRef = useRef(0);

  // Update message handler ref when it changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Update both state and ref when state changes
  const updateWsState = useCallback((newState) => {
    setWsState(newState);
    wsStateRef.current = newState;
  }, []);

  // Clean up any existing connection timers
  const cleanupConnectionTimers = useCallback(() => {
    // Clear any pending connection timers
    if (connectionTimerRef.current) {
      clearTimeout(connectionTimerRef.current);
      connectionTimerRef.current = null;
    }
    
    // Clear any pending reconnection timers
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  // Safely clean up a WebSocket instance
  const cleanupWebSocket = useCallback((ws) => {
    if (!ws) return;
    
    try {
      // Clear all intervals
      if (ws.heartbeatInterval) {
        clearInterval(ws.heartbeatInterval);
        ws.heartbeatInterval = null;
      }
      if (ws.monitorInterval) {
        clearInterval(ws.monitorInterval);
        ws.monitorInterval = null;
      }
      
      // Close the connection if it's still open
      if (ws.readyState === WebSocket.OPEN) {
        // Close the socket
        try {
          ws.close();
        } catch (e) {
          // Ignore errors during close
        }
      }
    } catch (err) {
      console.error('Error cleaning up WebSocket:', err);
    }
  }, []);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    // If already disconnected, do nothing
    if (wsStateRef.current === WS_STATES.DISCONNECTED && !socketRef.current) {
      return;
    }
    
    console.log(`Disconnecting WebSocket for task ${taskIdRef.current}`);
    
    // Clean up any existing timers
    cleanupConnectionTimers();
    
    // Get the current socket
    const ws = socketRef.current;
    if (!ws) {
      // No socket, so just reset state
      updateWsState(WS_STATES.DISCONNECTED);
      taskIdRef.current = null;
      return;
    }
    
    try {
      // Clean up the WebSocket
      cleanupWebSocket(ws);
      
      // Reset state immediately
      socketRef.current = null;
      updateWsState(WS_STATES.DISCONNECTED);
      // Don't clear taskIdRef here - let the caller decide
    } catch (err) {
      console.error('Error disconnecting WebSocket:', err);
      // Force reset even on error
      socketRef.current = null;
      updateWsState(WS_STATES.DISCONNECTED);
    }
  }, [cleanupConnectionTimers, cleanupWebSocket, updateWsState]);

  // Set up WebSocket event handlers
  const setupWebSocketHandlers = useCallback((ws, taskId) => {
    if (!ws) return;
    
    // Set up event handlers
    ws.onopen = () => {
      console.log(`WebSocket connection opened for task ${taskId}`);
      updateWsState(WS_STATES.CONNECTED);
      
      // Set up heartbeat interval
      ws.heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: 'heartbeat' }));
          } catch (e) {
            console.error('Error sending heartbeat:', e);
          }
        }
      }, 30000); // 30 seconds - less frequent heartbeats
      
      // Set up connection monitor
      ws.monitorInterval = setInterval(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          console.warn('WebSocket connection lost, clearing intervals');
          clearInterval(ws.heartbeatInterval);
          clearInterval(ws.monitorInterval);
          
          // Try to reconnect
          if (wsStateRef.current !== WS_STATES.DISCONNECTED) {
            console.log('Attempting to reconnect...');
            updateWsState(WS_STATES.DISCONNECTED);
            
            // Reconnect immediately
            if (taskIdRef.current) {
              console.log(`Reconnecting to WebSocket for task: ${taskIdRef.current}`);
              initializeWebSocket(taskIdRef.current);
            }
          }
        }
      }, 3000); // 3 seconds - check connection more frequently
    };
    
    ws.onclose = () => {
      console.log(`WebSocket connection closed for task ${taskId}`);
      if (wsStateRef.current !== WS_STATES.DISCONNECTED) {
        updateWsState(WS_STATES.DISCONNECTED);
        
        // Try to reconnect after a delay
        reconnectTimerRef.current = setTimeout(() => {
          if (wsStateRef.current === WS_STATES.DISCONNECTED && taskIdRef.current) {
            console.log(`Attempting to reconnect to WebSocket for task: ${taskIdRef.current}`);
            initializeWebSocket(taskIdRef.current);
          }
        }, 5000);
      }
    };
    
    ws.onerror = (error) => {
      console.error(`WebSocket error for task ${taskId}:`, error);
      if (wsStateRef.current !== WS_STATES.DISCONNECTED) {
        updateWsState(WS_STATES.DISCONNECTED);
        
        // Try to reconnect after a delay
        reconnectTimerRef.current = setTimeout(() => {
          if (wsStateRef.current === WS_STATES.DISCONNECTED && taskIdRef.current) {
            console.log(`Attempting to reconnect after error for task: ${taskIdRef.current}`);
            initializeWebSocket(taskIdRef.current);
          }
        }, 5000);
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log(`WebSocket message received for task ${taskId}:`, data);
        
        // Call the provided message handler for all messages
        if (onMessageRef.current) {
          onMessageRef.current(data);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
      }
    };
  }, [updateWsState]);

  // Initialize WebSocket connection with retry logic
  const initializeWebSocket = useCallback((taskId) => {
    try {
      // Only start if we're disconnected
      if (wsStateRef.current !== WS_STATES.DISCONNECTED) {
        return;
      }

      // Rate limiting: prevent too many rapid connection attempts
      const now = Date.now();
      if (now - lastConnectionAttemptRef.current < 1000) {
        console.log('Rate limiting: Too many connection attempts, waiting...');
        return;
      }
      lastConnectionAttemptRef.current = now;

      updateWsState(WS_STATES.CONNECTING);
      
      // Get the WebSocket URL
      let wsUrl;
      if (typeof urlOrGetter === 'function') {
        wsUrl = urlOrGetter(taskId);
      } else {
        // For backward compatibility
        wsUrl = taskId ? `${urlOrGetter}/${taskId}` : urlOrGetter;
      }
      
      if (!wsUrl) {
        console.warn('No WebSocket URL available');
        updateWsState(WS_STATES.DISCONNECTED);
        return;
      }
      
      console.log(`Connecting to WebSocket URL: ${wsUrl}`);
      // Store the task ID for reconnection
      taskIdRef.current = taskId;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      // Set up all event handlers
      setupWebSocketHandlers(ws, taskId);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      updateWsState(WS_STATES.DISCONNECTED);
      
      // Try to reconnect after a delay
      reconnectTimerRef.current = setTimeout(() => {
        if (wsStateRef.current === WS_STATES.DISCONNECTED && taskIdRef.current) {
          initializeWebSocket(taskIdRef.current);
        }
      }, 5000);
    }
  }, [urlOrGetter, updateWsState, setupWebSocketHandlers]);

  // Connect to WebSocket
  const connect = useCallback((taskId) => {
    // Don't attempt to connect if taskId is null, undefined, or not a valid UUID
    if (!taskId || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(taskId)) {
      console.warn('Not connecting WebSocket: Invalid or missing task ID');
      disconnect();
      return;
    }
    
    // If already connected to this task, do nothing
    if (socketRef.current && 
        wsStateRef.current === WS_STATES.CONNECTED && 
        taskIdRef.current === taskId) {
      console.log(`Already connected to task ${taskId}, skipping connection`);
      return;
    }
    
    // If we're already trying to connect to this task, wait
    if (wsStateRef.current === WS_STATES.CONNECTING && taskIdRef.current === taskId) {
      console.log(`Already connecting to task ${taskId}, waiting...`);
      return;
    }
    
    // Store the task ID
    taskIdRef.current = taskId;
    
    // Clean up any existing connection and wait for it to close
    if (socketRef.current) {
      console.log(`Switching from ${taskIdRef.current} to ${taskId}, cleaning up old connection`);
      disconnect();
      
      // Wait a bit before creating new connection to ensure cleanup is complete
      setTimeout(() => {
        if (taskIdRef.current === taskId) {
          initializeWebSocket(taskId);
        }
      }, 100);
    } else {
      // No existing connection, initialize immediately
      initializeWebSocket(taskId);
    }
  }, [disconnect, initializeWebSocket]);
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    wsState,
    connect,
    disconnect,
    isConnected: wsState === WS_STATES.CONNECTED,
    currentTaskId: taskIdRef.current
  };
};

export default useWebSocket;

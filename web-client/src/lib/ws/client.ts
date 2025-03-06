import { config } from '../../config/config';

/**
 * Project update types for WebSocket messages
 */
export type ProjectUpdate = {
  project_id: string;
  type: 'status' | 'resource' | 'task' | 'comment';
  data: any;
};

/**
 * WebSocket client for real-time communication with the backend
 */
class WebSocketClient {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private eventHandlers: Record<string, Array<(data: any) => void>> = {};
  private baseUrl: string;
  private projectSubscriptions: Record<string, Array<(update: ProjectUpdate) => void>> = {};
  
  constructor() {
    // Using the correct property name from the config
    this.baseUrl = config.ws.url;
  }

  /**
   * Connect to the WebSocket server
   * @param token The authentication token
   */
  connect(token: string): void {
    // Close existing connection if any
    if (this.socket) {
      this.socket.close();
    }

    // Clear any pending reconnect timer
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    try {
      // Create a new WebSocket connection with the auth token
      this.socket = new WebSocket(`${this.baseUrl}?token=${token}`);
      
      // Set up event handlers
      this.socket.onopen = () => {
        console.log('WebSocket connection established');
        this.trigger('connection', { status: 'connected' });
        
        // Re-subscribe to projects after reconnecting
        this.resubscribeToProjects();
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type && message.data) {
            this.trigger(message.type, message.data);
            
            // Handle project updates
            if (message.type === 'project_update' && message.data.project_id) {
              this.handleProjectUpdate(message.data as ProjectUpdate);
            }
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.socket = null;
        this.trigger('connection', { status: 'disconnected', code: event.code, reason: event.reason });
        
        // Attempt to reconnect after a delay
        this.scheduleReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.trigger('error', { message: 'WebSocket connection error' });
      };
    } catch (error) {
      console.error('Failed to establish WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Close the WebSocket connection
   */
  disconnect(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  /**
   * Send data to the WebSocket server
   * @param type Event type
   * @param data Event data
   */
  send(type: string, data: any): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error('Cannot send message: WebSocket is not connected');
      return false;
    }

    try {
      this.socket.send(JSON.stringify({ type, data }));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }

  /**
   * Register an event handler
   * @param event Event name
   * @param callback Callback function
   */
  on(event: string, callback: (data: any) => void): void {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(callback);
  }

  /**
   * Remove an event handler
   * @param event Event name
   * @param callback Callback function
   */
  off(event: string, callback: (data: any) => void): void {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event] = this.eventHandlers[event].filter(cb => cb !== callback);
    }
  }

  /**
   * Subscribe to updates for a specific project
   * @param projectId The ID of the project to subscribe to
   * @param callback The callback function to call when an update is received
   * @returns A function to unsubscribe
   */
  subscribeToProject(projectId: string, callback: (update: ProjectUpdate) => void): () => void {
    if (!this.projectSubscriptions[projectId]) {
      this.projectSubscriptions[projectId] = [];
      
      // Send subscription request to the server if we're connected
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.send('subscribe', { project_id: projectId });
      }
    }
    
    this.projectSubscriptions[projectId].push(callback);
    
    // Return unsubscribe function
    return () => {
      this.unsubscribeFromProject(projectId, callback);
    };
  }
  
  /**
   * Unsubscribe from project updates
   * @param projectId The ID of the project
   * @param callback The callback function to remove
   */
  unsubscribeFromProject(projectId: string, callback: (update: ProjectUpdate) => void): void {
    if (this.projectSubscriptions[projectId]) {
      this.projectSubscriptions[projectId] = this.projectSubscriptions[projectId].filter(
        cb => cb !== callback
      );
      
      // If no more subscriptions for this project, send unsubscribe message
      if (this.projectSubscriptions[projectId].length === 0) {
        delete this.projectSubscriptions[projectId];
        
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.send('unsubscribe', { project_id: projectId });
        }
      }
    }
  }
  
  /**
   * Handle project update messages
   * @param update The project update data
   */
  private handleProjectUpdate(update: ProjectUpdate): void {
    const projectId = update.project_id;
    if (this.projectSubscriptions[projectId]) {
      this.projectSubscriptions[projectId].forEach(callback => {
        try {
          callback(update);
        } catch (error) {
          console.error(`Error in project update handler for project ${projectId}:`, error);
        }
      });
    }
  }
  
  /**
   * Re-subscribe to all projects after reconnecting
   */
  private resubscribeToProjects(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      Object.keys(this.projectSubscriptions).forEach(projectId => {
        this.send('subscribe', { project_id: projectId });
      });
    }
  }

  /**
   * Trigger an event
   * @param event Event name
   * @param data Event data
   */
  private trigger(event: string, data: any): void {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${event} event handler:`, error);
        }
      });
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) {
      return;
    }
    
    // Reconnect after 5 seconds
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      const token = localStorage.getItem(config.auth.tokenKey);
      if (token) {
        this.connect(token);
      }
    }, 5000);
  }
}

export const wsClient = new WebSocketClient();
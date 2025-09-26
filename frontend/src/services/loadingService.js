/**
 * Centralized loading state management service
 */

/**
 * Loading state types for different operations
 */
export const LoadingTypes = {
  // Task operations
  TASKS_FETCH: 'tasks_fetch',
  TASK_CREATE: 'task_create',
  TASK_UPDATE: 'task_update',
  TASK_DELETE: 'task_delete',
  TASK_TREE_FETCH: 'task_tree_fetch',
  TASK_STATS_FETCH: 'task_stats_fetch',
  
  // Authentication operations
  AUTH_LOGIN: 'auth_login',
  AUTH_REGISTER: 'auth_register',
  AUTH_OAUTH: 'auth_oauth',
  AUTH_REFRESH: 'auth_refresh',
  
  // Content generation
  GENERATE_DETAILS: 'generate_details',
  DECOMPOSE_TASK: 'decompose_task',
  
  // Export operations
  EXPORT_TRELLO: 'export_trello',
  EXPORT_JSON: 'export_json',
  
  // General operations
  SAVE: 'save',
  SUBMIT: 'submit',
  PROCESS: 'process'
};

/**
 * Loading state manager class
 */
class LoadingStateManager {
  constructor() {
    this.loadingStates = new Map();
    this.subscribers = new Set();
  }

  /**
   * Set loading state for a specific operation
   */
  setLoading(type, isLoading, message = null) {
    const currentState = this.loadingStates.get(type) || {};
    const newState = {
      ...currentState,
      isLoading,
      message: isLoading ? (message || this.getDefaultMessage(type)) : null,
      timestamp: Date.now()
    };

    this.loadingStates.set(type, newState);
    this.notifySubscribers(type, newState);
  }

  /**
   * Get loading state for a specific operation
   */
  getLoading(type) {
    return this.loadingStates.get(type) || { isLoading: false, message: null };
  }

  /**
   * Check if any loading operation is active
   */
  isAnyLoading() {
    return Array.from(this.loadingStates.values()).some(state => state.isLoading);
  }

  /**
   * Get all active loading operations
   */
  getActiveLoadings() {
    const active = [];
    this.loadingStates.forEach((state, type) => {
      if (state.isLoading) {
        active.push({ type, ...state });
      }
    });
    return active;
  }

  /**
   * Clear all loading states
   */
  clearAll() {
    this.loadingStates.clear();
    this.notifySubscribers('*', { cleared: true });
  }

  /**
   * Subscribe to loading state changes
   */
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  /**
   * Notify all subscribers of state changes
   */
  notifySubscribers(type, state) {
    this.subscribers.forEach(callback => {
      try {
        callback(type, state);
      } catch (error) {
        console.error('Error in loading state subscriber:', error);
      }
    });
  }

  /**
   * Get default loading message for operation type
   */
  getDefaultMessage(type) {
    const messages = {
      [LoadingTypes.TASKS_FETCH]: 'Loading tasks...',
      [LoadingTypes.TASK_CREATE]: 'Creating task...',
      [LoadingTypes.TASK_UPDATE]: 'Updating task...',
      [LoadingTypes.TASK_DELETE]: 'Deleting task...',
      [LoadingTypes.TASK_TREE_FETCH]: 'Loading task tree...',
      [LoadingTypes.TASK_STATS_FETCH]: 'Loading statistics...',
      [LoadingTypes.AUTH_LOGIN]: 'Signing in...',
      [LoadingTypes.AUTH_REGISTER]: 'Creating account...',
      [LoadingTypes.AUTH_OAUTH]: 'Completing authentication...',
      [LoadingTypes.AUTH_REFRESH]: 'Refreshing session...',
      [LoadingTypes.GENERATE_DETAILS]: 'Generating implementation details...',
      [LoadingTypes.DECOMPOSE_TASK]: 'Decomposing task...',
      [LoadingTypes.EXPORT_TRELLO]: 'Exporting to Trello...',
      [LoadingTypes.EXPORT_JSON]: 'Preparing download...',
      [LoadingTypes.SAVE]: 'Saving...',
      [LoadingTypes.SUBMIT]: 'Submitting...',
      [LoadingTypes.PROCESS]: 'Processing...'
    };

    return messages[type] || 'Loading...';
  }
}

// Create singleton instance
const loadingManager = new LoadingStateManager();

/**
 * Hook-like interface for React components
 */
export const useLoadingState = (type) => {
  return {
    setLoading: (isLoading, message) => loadingManager.setLoading(type, isLoading, message),
    isLoading: loadingManager.getLoading(type).isLoading,
    message: loadingManager.getLoading(type).message
  };
};

/**
 * Wrapper for async operations with automatic loading state management
 */
export const withLoading = async (type, asyncOperation, customMessage = null) => {
  loadingManager.setLoading(type, true, customMessage);
  
  try {
    const result = await asyncOperation();
    return result;
  } finally {
    loadingManager.setLoading(type, false);
  }
};

/**
 * Export the manager instance for direct access
 */
export default loadingManager;
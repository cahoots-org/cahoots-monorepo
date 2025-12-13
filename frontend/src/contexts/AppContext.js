// Simplified App Context - Replaces complex multiple context providers
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useAuth } from './AuthContext';

// App state shape
const initialState = {
  // UI state
  sidebarOpen: false,
  theme: 'dark',
  
  // Current selections
  currentTaskId: null,
  
  // UI feedback
  notifications: [],
  
  // Loading states for global operations
  globalLoading: false,
  
  // Error state
  globalError: null,
};

// Action types
const ActionTypes = {
  SET_SIDEBAR_OPEN: 'SET_SIDEBAR_OPEN',
  SET_CURRENT_TASK_ID: 'SET_CURRENT_TASK_ID',
  SET_THEME: 'SET_THEME',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  SET_GLOBAL_LOADING: 'SET_GLOBAL_LOADING',
  SET_GLOBAL_ERROR: 'SET_GLOBAL_ERROR',
  CLEAR_GLOBAL_ERROR: 'CLEAR_GLOBAL_ERROR',
};

// Reducer function
function appReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_SIDEBAR_OPEN:
      return {
        ...state,
        sidebarOpen: action.payload,
      };

    case ActionTypes.SET_CURRENT_TASK_ID:
      return {
        ...state,
        currentTaskId: action.payload,
      };

    case ActionTypes.SET_THEME:
      return {
        ...state,
        theme: action.payload,
      };

    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, {
          id: Date.now() + Math.random(),
          timestamp: new Date(),
          ...action.payload,
        }],
      };

    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(
          notification => notification.id !== action.payload
        ),
      };

    case ActionTypes.SET_GLOBAL_LOADING:
      return {
        ...state,
        globalLoading: action.payload,
      };

    case ActionTypes.SET_GLOBAL_ERROR:
      return {
        ...state,
        globalError: action.payload,
        globalLoading: false,
      };

    case ActionTypes.CLEAR_GLOBAL_ERROR:
      return {
        ...state,
        globalError: null,
      };

    default:
      return state;
  }
}

// Create context
const AppContext = createContext();

// Context provider
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const { user } = useAuth();

  // Auto-clear notifications after 5 seconds
  useEffect(() => {
    state.notifications.forEach(notification => {
      if (notification.autoHide !== false) {
        setTimeout(() => {
          dispatch({
            type: ActionTypes.REMOVE_NOTIFICATION,
            payload: notification.id,
          });
        }, 5000);
      }
    });
  }, [state.notifications]);

  // Action creators
  const actions = {
    // UI actions
    setSidebarOpen: (open) => {
      dispatch({
        type: ActionTypes.SET_SIDEBAR_OPEN,
        payload: open,
      });
    },

    setCurrentTaskId: (taskId) => {
      dispatch({
        type: ActionTypes.SET_CURRENT_TASK_ID,
        payload: taskId,
      });
    },

    setTheme: (theme) => {
      dispatch({
        type: ActionTypes.SET_THEME,
        payload: theme,
      });
      // Persist theme preference
      localStorage.setItem('theme', theme);
    },

    // Notification actions
    addNotification: (notification) => {
      dispatch({
        type: ActionTypes.ADD_NOTIFICATION,
        payload: notification,
      });
    },

    showSuccess: (message, options = {}) => {
      actions.addNotification({
        type: 'success',
        message,
        ...options,
      });
    },

    showError: (message, options = {}) => {
      actions.addNotification({
        type: 'error',
        message,
        autoHide: false, // Errors don't auto-hide
        ...options,
      });
    },

    showWarning: (message, options = {}) => {
      actions.addNotification({
        type: 'warning',
        message,
        ...options,
      });
    },

    showInfo: (message, options = {}) => {
      actions.addNotification({
        type: 'info',
        message,
        ...options,
      });
    },

    removeNotification: (id) => {
      dispatch({
        type: ActionTypes.REMOVE_NOTIFICATION,
        payload: id,
      });
    },

    // Global state actions
    setGlobalLoading: (loading) => {
      dispatch({
        type: ActionTypes.SET_GLOBAL_LOADING,
        payload: loading,
      });
    },

    setGlobalError: (error) => {
      dispatch({
        type: ActionTypes.SET_GLOBAL_ERROR,
        payload: error,
      });
    },

    clearGlobalError: () => {
      dispatch({
        type: ActionTypes.CLEAR_GLOBAL_ERROR,
      });
    },
  };

  // Initialize theme from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme && savedTheme !== state.theme) {
      actions.setTheme(savedTheme);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Context value
  const contextValue = {
    // State
    ...state,
    
    // Actions
    ...actions,
    
    // Computed values
    isAuthenticated: !!user,
    hasNotifications: state.notifications.length > 0,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use the app context
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;
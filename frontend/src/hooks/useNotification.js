import { useApp } from '../contexts/AppContext';

// Simple notification hook that works with the AppContext
export const useNotification = () => {
  const { showNotification } = useApp();

  return {
    showNotification: (message, type = 'info') => {
      // For now, just log to console since we don't have notification system yet
      console.log(`${type.toUpperCase()}: ${message}`);
      
      // If AppContext has showNotification, use it
      if (showNotification) {
        showNotification(message, type);
      }
    },
  };
};
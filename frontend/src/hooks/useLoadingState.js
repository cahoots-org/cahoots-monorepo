/**
 * React hook for loading state management with proper lifecycle
 */
import { useState, useEffect, useCallback } from 'react';
import loadingManager from '../services/loadingService';

export const useLoadingState = (type) => {
  const [state, setState] = useState(() => loadingManager.getLoading(type));

  useEffect(() => {
    // Subscribe to loading state changes
    const unsubscribe = loadingManager.subscribe((loadingType, newState) => {
      if (loadingType === type || loadingType === '*') {
        setState(loadingManager.getLoading(type));
      }
    });

    // Cleanup subscription on unmount
    return unsubscribe;
  }, [type]);

  const setLoading = useCallback((isLoading, message) => {
    loadingManager.setLoading(type, isLoading, message);
  }, [type]);

  return {
    isLoading: state.isLoading,
    message: state.message,
    setLoading
  };
};

export default useLoadingState;
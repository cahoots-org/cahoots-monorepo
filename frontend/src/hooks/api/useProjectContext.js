/**
 * Project Context Hook - Fetches real-time project context from Contex
 *
 * This hook provides access to all the context data for a project,
 * including tech stack, decomposed tasks, epics, events, commands, etc.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { queryKeys } from '../../lib/query-client';
import { useWebSocket } from '../../contexts/WebSocketContext';
import apiClient from '../../services/unifiedApiClient';

/**
 * Fetch project context from the API
 * @param {string} projectId - The project/task ID
 * @returns {Promise<Object>} Project context data
 */
const fetchProjectContext = async (projectId) => {
  const response = await apiClient.get(`/projects/${projectId}/context`);
  return response;
};

/**
 * Hook to fetch and subscribe to project context updates
 *
 * @param {string} projectId - The project/task ID
 * @param {Object} options - Query options
 * @param {boolean} options.enabled - Whether to enable the query (default: true)
 * @param {number} options.refetchInterval - Auto-refetch interval in ms (default: disabled)
 * @returns {Object} Query result with context data
 */
export const useProjectContext = (projectId, options = {}) => {
  const queryClient = useQueryClient();
  const { subscribe, connected } = useWebSocket();

  const {
    enabled = true,
    refetchInterval = false,
    ...queryOptions
  } = options;

  // Subscribe to WebSocket updates for this project
  useEffect(() => {
    if (!connected || !projectId) return;

    const unsubscribe = subscribe((data) => {
      // Refetch context when we get updates for this project
      if (data.task_id === projectId || data.root_task_id === projectId) {
        // Only refetch on certain event types
        const relevantEvents = [
          'task.created',
          'task.updated',
          'decomposition.completed',
          'event_modeling.completed',
          'context.updated',
        ];

        if (relevantEvents.includes(data.type)) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.projects.context(projectId),
          });
        }
      }
    });

    return () => unsubscribe();
  }, [connected, subscribe, projectId, queryClient]);

  return useQuery({
    queryKey: queryKeys.projects.context(projectId),
    queryFn: () => fetchProjectContext(projectId),
    enabled: enabled && !!projectId,
    refetchInterval,
    // Keep previous data while fetching new data
    placeholderData: (previousData) => previousData,
    ...queryOptions,
  });
};

/**
 * Hook to get just the processing status of a project
 * Useful for showing loading states during decomposition
 */
export const useProjectStatus = (projectId) => {
  const { data, isLoading, error } = useProjectContext(projectId, {
    // Poll every 2 seconds while processing
    refetchInterval: (data) => {
      return data?.is_processing ? 2000 : false;
    },
  });

  return {
    isProcessing: data?.is_processing ?? true,
    status: data?.task_status ?? 'unknown',
    stats: data?.stats ?? {},
    isLoading,
    error,
  };
};

export default useProjectContext;

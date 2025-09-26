// Task API Hooks - Simplified replacement for complex TaskService hook
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys, invalidateQueries } from '../../lib/query-client';
import apiClient from '../../services/unifiedApiClient';

// Fetch tasks with pagination
export const useTasks = (options = {}) => {
  const {
    page = 1,
    pageSize = 10,
    topLevelOnly = true,
    ...queryOptions
  } = options;

  return useQuery({
    queryKey: queryKeys.tasks.list({ page, pageSize, topLevelOnly }),
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      
      if (topLevelOnly) {
        params.append('top_level_only', 'true');
      }

      const response = await apiClient.get(`/tasks?${params.toString()}`);
      
      // Normalize response structure
      if (response && typeof response === 'object') {
        if (response.tasks && Array.isArray(response.tasks)) {
          return {
            items: response.tasks,
            total: response.total || response.tasks.length,
            page: response.page || page,
            pageSize: response.page_size || pageSize,
            totalPages: Math.ceil((response.total || response.tasks.length) / pageSize),
          };
        } else if (response.task_id) {
          // Single task response
          return {
            items: [response],
            total: 1,
            page: 1,
            pageSize: 1,
            totalPages: 1,
          };
        }
      } else if (Array.isArray(response)) {
        // Legacy array response
        return {
          items: response,
          total: response.length,
          page: 1,
          pageSize: response.length,
          totalPages: 1,
        };
      }

      // Fallback empty response
      return {
        items: [],
        total: 0,
        page: 1,
        pageSize: pageSize,
        totalPages: 0,
      };
    },
    ...queryOptions,
  });
};

// Fetch single task
export const useTask = (taskId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.tasks.detail(taskId),
    queryFn: async () => {
      if (!taskId) return null;
      return await apiClient.get(`/tasks/${taskId}`);
    },
    enabled: !!taskId,
    ...options,
  });
};

// Fetch task tree
export const useTaskTree = (taskId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.tasks.tree(taskId),
    queryFn: async () => {
      if (!taskId) return null;
      
      const response = await apiClient.get(`/tasks/${taskId}/tree`);
      
      // Validate response
      if (!response || !response.task_id) {
        throw new Error('Invalid task tree data received');
      }
      
      return response;
    },
    enabled: !!taskId,
    staleTime: 2 * 60 * 1000, // Task trees are more stable, cache for 2 minutes
    ...options,
  });
};

// Fetch task statistics
export const useTaskStats = (topLevelOnly = true, options = {}) => {
  return useQuery({
    queryKey: queryKeys.tasks.stats(),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('top_level_only', topLevelOnly.toString());
      
      const response = await apiClient.get(`/tasks/stats?${params.toString()}`);
      
      return {
        total: response.total || 0,
        completed: response.completed || 0,
        inProgress: response.in_progress || 0,
        pending: response.pending || 0,
      };
    },
    staleTime: 30 * 1000, // Stats change frequently, cache for 30 seconds
    ...options,
  });
};

// Create task mutation
export const useCreateTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskData) => {
      return await apiClient.post('/tasks', taskData);
    },
    onSuccess: () => {
      // Invalidate and refetch tasks list and stats
      invalidateQueries.tasks.list();
      invalidateQueries.tasks.stats();
    },
    onError: (error) => {
      console.error('Failed to create task:', error);
    },
  });
};

// Update task mutation
export const useUpdateTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ taskId, updates }) => {
      return await apiClient.patch(`/tasks/${taskId}`, updates);
    },
    onSuccess: (data, { taskId }) => {
      // Update the specific task in cache
      queryClient.setQueryData(queryKeys.tasks.detail(taskId), data);
      
      // Invalidate related queries
      invalidateQueries.tasks.list();
      invalidateQueries.tasks.tree(taskId);
      invalidateQueries.tasks.stats();
    },
    onError: (error) => {
      console.error('Failed to update task:', error);
    },
  });
};

// Complete task mutation
export const useCompleteTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId) => {
      return await apiClient.post(`/tasks/${taskId}/complete`);
    },
    onSuccess: (data, taskId) => {
      // Update task status in cache
      queryClient.setQueryData(queryKeys.tasks.detail(taskId), (oldData) => 
        oldData ? { ...oldData, status: 'completed' } : oldData
      );
      
      // Invalidate related queries
      invalidateQueries.tasks.list();
      invalidateQueries.tasks.tree(taskId);
      invalidateQueries.tasks.stats();
    },
    onError: (error) => {
      console.error('Failed to complete task:', error);
    },
  });
};

// Delete task mutation
export const useDeleteTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId) => {
      return await apiClient.deleteTask(taskId);
    },
    onMutate: async (taskId) => {
      // Cancel any outgoing refetches to prevent optimistic update being overwritten
      await queryClient.cancelQueries({ queryKey: queryKeys.tasks.lists() });
      
      // Get all task list queries in the cache
      const queries = queryClient.getQueriesData({ queryKey: queryKeys.tasks.lists() });
      
      // Save snapshots and update all matching queries
      const previousData = {};
      
      queries.forEach(([queryKey, data]) => {
        if (data) {
          // Save the snapshot
          previousData[JSON.stringify(queryKey)] = data;
          
          // Optimistically update the cache by removing the deleted task
          queryClient.setQueryData(queryKey, (old) => {
            if (!old) return old;
            
            // Handle paginated response structure
            if (old.tasks && Array.isArray(old.tasks)) {
              return {
                ...old,
                tasks: old.tasks.filter(task => task.task_id !== taskId),
                total: Math.max(0, (old.total || 0) - 1)
              };
            }
            
            // Handle simple array structure
            if (Array.isArray(old)) {
              return old.filter(task => task.task_id !== taskId);
            }
            
            return old;
          });
        }
      });
      
      // Return context with all snapshots
      return { previousData };
    },
    onError: (error, taskId, context) => {
      console.error('Failed to delete task:', error);
      // If mutation fails, roll back to all previous values
      if (context?.previousData) {
        Object.entries(context.previousData).forEach(([queryKeyString, data]) => {
          const queryKey = JSON.parse(queryKeyString);
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSettled: (data, error, taskId) => {
      // Always refetch after error or success to ensure cache is in sync
      queryClient.removeQueries({ queryKey: queryKeys.tasks.detail(taskId) });
      queryClient.removeQueries({ queryKey: queryKeys.tasks.tree(taskId) });
      invalidateQueries.tasks.list();
      invalidateQueries.tasks.stats();
    },
  });
};
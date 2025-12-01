// React Query Configuration - Replaces complex Recoil state management
import { QueryClient } from '@tanstack/react-query';

// Default query configuration
const queryConfig = {
  defaultOptions: {
    queries: {
      // Stale time - data is considered fresh for this duration
      staleTime: 1 * 60 * 1000, // 1 minute
      
      // Cache time - how long to keep unused data in cache
      cacheTime: 5 * 60 * 1000, // 5 minutes
      
      // Retry configuration
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (client errors)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      
      // Refetch configuration
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      
      // Error handling
      onError: (error) => {
        console.error('Query error:', error);
      },
    },
    mutations: {
      // Retry configuration for mutations
      retry: (failureCount, error) => {
        // Don't retry mutations on client errors
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      
      // Error handling
      onError: (error) => {
        console.error('Mutation error:', error);
      },
    },
  },
};

// Create query client instance
export const queryClient = new QueryClient(queryConfig);

// Query keys factory - centralized query key management
export const queryKeys = {
  // Task-related queries
  tasks: {
    all: ['tasks'],
    lists: () => [...queryKeys.tasks.all, 'list'],
    list: (filters) => [...queryKeys.tasks.lists(), filters],
    details: () => [...queryKeys.tasks.all, 'detail'],
    detail: (id) => [...queryKeys.tasks.details(), id],
    trees: () => [...queryKeys.tasks.all, 'tree'],
    tree: (id) => [...queryKeys.tasks.trees(), id],
    stats: () => [...queryKeys.tasks.all, 'stats'],
  },

  // Project context queries (from Contex)
  projects: {
    all: ['projects'],
    contexts: () => [...queryKeys.projects.all, 'context'],
    context: (id) => [...queryKeys.projects.contexts(), id],
  },

  // User-related queries
  user: {
    all: ['user'],
    profile: () => [...queryKeys.user.all, 'profile'],
    preferences: () => [...queryKeys.user.all, 'preferences'],
  },

  // Auth-related queries
  auth: {
    all: ['auth'],
    session: () => [...queryKeys.auth.all, 'session'],
  },
};

// Utility function to invalidate related queries
export const invalidateQueries = {
  tasks: {
    all: () => queryClient.invalidateQueries({ queryKey: queryKeys.tasks.all }),
    list: () => queryClient.invalidateQueries({ queryKey: queryKeys.tasks.lists() }),
    detail: (id) => queryClient.invalidateQueries({ queryKey: queryKeys.tasks.detail(id) }),
    tree: (id) => queryClient.invalidateQueries({ queryKey: queryKeys.tasks.tree(id) }),
    stats: () => queryClient.invalidateQueries({ queryKey: queryKeys.tasks.stats() }),
  },
  projects: {
    all: () => queryClient.invalidateQueries({ queryKey: queryKeys.projects.all }),
    context: (id) => queryClient.invalidateQueries({ queryKey: queryKeys.projects.context(id) }),
  },
  user: {
    all: () => queryClient.invalidateQueries({ queryKey: queryKeys.user.all }),
    profile: () => queryClient.invalidateQueries({ queryKey: queryKeys.user.profile() }),
  },
};

export default queryClient;
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
    endpoints: {
      auth: {
        login: '/api/v1/auth/login',
        register: '/api/v1/auth/register',
        verify: '/api/v1/auth/verify',
        resetPassword: '/api/v1/auth/reset-password',
      },
      projects: {
        list: '/api/v1/projects',
        create: '/api/v1/projects',
        details: (id: string) => `/api/v1/projects/${id}`,
        resources: (id: string) => `/api/v1/projects/${id}/resources`,
        stories: (id: string) => `/api/v1/projects/${id}/stories`,
      },
      tasks: {
        list: (projectId: string) => `/api/v1/projects/${projectId}/tasks`,
        create: (projectId: string) => `/api/v1/projects/${projectId}/tasks`,
        update: (projectId: string, taskId: string) => 
          `/api/v1/projects/${projectId}/tasks/${taskId}`,
      },
    },
  },
  auth: {
    tokenKey: 'cahoots_token',
    refreshTokenKey: 'cahoots_refresh_token',
  },
  ui: {
    theme: {
      primaryColor: '#0070f3',
      secondaryColor: '#7928ca',
      errorColor: '#ff0000',
      successColor: '#00ff00',
      warningColor: '#ff9800',
    },
    toast: {
      duration: 5000,
    },
  },
} as const;

export type Config = typeof config; 
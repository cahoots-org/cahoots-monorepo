export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_URL || 'https://test.cahoots.cc',
    wsUrl: import.meta.env.VITE_WS_URL || 'wss://test.cahoots.cc',
    endpoints: {
      auth: {
        login: '/api/v1/auth/login',
        register: '/api/v1/auth/register',
        verify: '/api/v1/auth/verify',
        resetPassword: '/api/v1/auth/reset-password',
        social: (provider: string) => `/api/v1/auth/social/${provider}`,
        refresh: '/api/v1/auth/refresh',
        me: '/api/v1/auth/me'
      },
      projects: {
        list: '/api/v1/projects',
        create: '/api/v1/projects',
        details: (id: string) => `/api/v1/projects/${id}`,
        update: (id: string) => `/api/v1/projects/${id}`,
        delete: (id: string) => `/api/v1/projects/${id}`,
        status: (id: string) => `/api/v1/projects/${id}/status`,
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
      primaryColor: '#FF8C1A', // Vibrant orange
      secondaryColor: '#FF4D1C', // Orange-red
      tertiaryColor: '#D94167', // Accent red
      backgroundColor: '#1A1B1E', // Dark background
      surfaceColor: '#25262B', // Slightly lighter surface
      textColor: '#FFFFFF', // White text
      mutedTextColor: '#909296', // Muted text
      borderColor: '#373A40', // Dark border
      errorColor: '#FF4444', // Error red
      successColor: '#71F0A9', // Success green
      warningColor: '#FFB224', // Warning orange
      infoColor: '#87CEEB', // Info blue
      gradients: {
        primary: 'linear-gradient(135deg, #E67300 0%, #CC3300 100%)', // Darker orange gradient
        surface: 'linear-gradient(180deg, #25262B 0%, #1A1B1E 100%)', // Surface gradient
      },
      shadows: {
        card: '0 4px 8px rgba(0, 0, 0, 0.5)',
        button: '0 2px 4px rgba(0, 0, 0, 0.3)',
      },
    },
    toast: {
      duration: 5000,
    },
  },
  ws: {
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
  }
} as const;

export type Config = typeof config; 
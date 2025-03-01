import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';
import { config } from '../config/config';
import { apiClient } from '../lib/api/client';
import { wsClient } from '../lib/ws/client';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

interface UserResponse {
  user: User;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  name: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  socialLogin: (provider: string, userData: any) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  checkAuth: () => Promise<void>;
  refreshToken: () => Promise<string>;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        login: async (credentials) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.post<{ success: boolean; data: AuthResponse }>(
              config.api.endpoints.auth.login,
              credentials
            );

            if (!response.success || !response.data) {
              throw new Error('Invalid response from server');
            }

            const { access_token, refresh_token, user } = response.data;

            localStorage.setItem(config.auth.tokenKey, access_token);
            localStorage.setItem(config.auth.refreshTokenKey, refresh_token);

            // Connect WebSocket with the new token
            wsClient.connect(access_token);

            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch (error: any) {
            set({
              error: error.response?.data?.error?.message || error.message || 'Failed to login',
              isLoading: false,
            });
          }
        },

        register: async (data) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(config.api.endpoints.auth.register, data);
            set({ isLoading: false });
          } catch (error: any) {
            set({
              error: error.message || 'Failed to register',
              isLoading: false,
            });
          }
        },

        socialLogin: async (provider, userData) => {
          set({ isLoading: true, error: null });
          try {
            const endpoint = config.api.endpoints.auth.social(provider);
            console.log('[OAUTH_FLOW] Starting backend request:', {
              endpoint,
              provider,
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              }
            });
            
            // Ensure userData matches SocialLoginRequest schema
            if (!userData.provider || !userData.user_data || !userData.access_token) {
              throw new Error('Invalid social login data format');
            }
            
            const response = await apiClient.post<{ success: boolean; data: AuthResponse }>(endpoint, userData);
            console.log('[OAUTH_FLOW] Backend response received:', {
              success: response.success,
              hasData: !!response.data,
              hasAccessToken: !!response.data?.access_token,
              hasRefreshToken: !!response.data?.refresh_token,
              hasUser: !!response.data?.user
            });

            if (!response.success || !response.data) {
              throw new Error('Invalid response from server');
            }

            const { access_token, refresh_token, user } = response.data;

            // Verify we received the required data
            if (!access_token || !refresh_token || !user) {
              console.error('Invalid response data:', { 
                hasAccessToken: !!access_token,
                hasRefreshToken: !!refresh_token,
                hasUser: !!user 
              });
              throw new Error('Invalid response from server');
            }

            localStorage.setItem(config.auth.tokenKey, access_token);
            localStorage.setItem(config.auth.refreshTokenKey, refresh_token);

            wsClient.connect(access_token);

            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch (error: any) {
            console.error('[OAUTH_FLOW] Social login error:', {
              message: error.message,
              status: error.response?.status,
              statusText: error.response?.statusText,
              data: error.response?.data,
              stack: error.stack,
              config: {
                url: error.config?.url,
                method: error.config?.method,
                headers: error.config?.headers,
                data: error.config?.data
              }
            });
            
            // Set a more descriptive error message
            const errorDetail = error.response?.data?.error?.message || error.message;
            const errorMessage = `Social login failed: ${errorDetail}`;
            
            set({
              error: errorMessage,
              isLoading: false,
              isAuthenticated: false,
              user: null
            });
            
            // Re-throw the error so the component can handle it
            throw new Error(errorMessage);
          }
        },

        logout: () => {
          localStorage.removeItem(config.auth.tokenKey);
          localStorage.removeItem(config.auth.refreshTokenKey);
          wsClient.disconnect();
          set({
            user: null,
            isAuthenticated: false,
          });
        },

        clearError: () => {
          set({ error: null });
        },

        checkAuth: async () => {
          const token = localStorage.getItem(config.auth.tokenKey);
          if (!token) {
            set({ isAuthenticated: false, user: null });
            return;
          }

          try {
            const decoded: any = jwtDecode(token);
            const currentTime = Date.now() / 1000;

            if (decoded.exp < currentTime) {
              // Token expired, try to refresh
              const newToken = await get().refreshToken();
              if (!newToken) {
                get().logout();
                set({ isAuthenticated: false, user: null });
                return;
              }
            }

            // Token still valid, fetch user info
            const response = await apiClient.get<UserResponse>(config.api.endpoints.auth.me);
            set({
              user: response.user,
              isAuthenticated: true,
            });
          } catch (error) {
            get().logout();
            set({ isAuthenticated: false, user: null });
          }
        },

        refreshToken: async () => {
          const refreshToken = localStorage.getItem(config.auth.refreshTokenKey);
          if (!refreshToken) {
            set({ isAuthenticated: false, user: null });
            return '';
          }

          try {
            const response = await apiClient.post<{ success: boolean; data: AuthResponse }>(
              config.api.endpoints.auth.refresh,
              { refresh_token: refreshToken }
            );

            if (!response.success || !response.data) {
              throw new Error('Invalid response from server');
            }

            const { access_token, refresh_token } = response.data;

            localStorage.setItem(config.auth.tokenKey, access_token);
            localStorage.setItem(config.auth.refreshTokenKey, refresh_token);

            return access_token;
          } catch (error) {
            get().logout();
            set({ isAuthenticated: false, user: null });
            return '';
          }
        },
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({
          user: state.user,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    )
  )
); 
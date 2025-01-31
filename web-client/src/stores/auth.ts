import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import jwtDecode from 'jwt-decode';
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
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        login: async (credentials) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.post<AuthResponse>(
              config.api.endpoints.auth.login,
              credentials
            );

            const { access_token, refresh_token, user } = response;

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
              error: error.message || 'Failed to login',
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
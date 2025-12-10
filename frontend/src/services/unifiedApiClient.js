import axios from 'axios';
import loadingManager from './loadingService';

// Get API URL from runtime config or fallback to relative URL
const API_URL = window.CAHOOTS_CONFIG?.API_URL || '/api';

class UnifiedApiClient {
  constructor() {
    // Create Axios instance with base configuration
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      withCredentials: true, // Important: Always send cookies with requests
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor - add auth headers
    this.client.interceptors.request.use(
      (config) => {
        // Get token from httpOnly cookie via API call if needed
        // For now, fallback to localStorage but migrate to cookies
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add user context header if available
        const user = this.getCurrentUser();
        if (user?.id) {
          config.headers['X-User-ID'] = user.id;
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            await this.refreshToken();
            const token = this.getAuthToken();
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            this.handleAuthError();
            return Promise.reject(error);
          }
        }

        return Promise.reject(this.enhanceError(error));
      }
    );
  }

  // Enhanced error with user-friendly messages
  enhanceError(error) {
    const enhanced = { ...error };
    
    if (error.response) {
      // Server responded with error status
      enhanced.userMessage = this.getErrorMessage(error.response.status, error.response.data);
    } else if (error.request) {
      // Network error
      enhanced.userMessage = 'Network error. Please check your connection.';
    } else {
      // Request setup error
      enhanced.userMessage = 'Request failed. Please try again.';
    }
    
    return enhanced;
  }

  getErrorMessage(status, data) {
    const statusMessages = {
      400: 'Invalid request. Please check your input.',
      401: 'Please log in to continue.',
      403: 'You don\'t have permission to perform this action.',
      404: 'The requested resource was not found.',
      500: 'Server error. Please try again later.',
      503: 'Service temporarily unavailable. Please try again later.'
    };
    
    return data?.detail || data?.message || statusMessages[status] || 'An error occurred.';
  }

  // Auth token management (to be migrated to httpOnly cookies)
  getAuthToken() {
    const token = localStorage.getItem('token');
    if (token) {
      return token;
    }
    
    // Check if user has explicitly logged out
    const hasLoggedOut = localStorage.getItem('has_logged_out') === 'true';
    if (hasLoggedOut) {
      return null;
    }

    // Development bypass for when no real token is available
    if (process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost') {
      // Store dev-bypass-token so it persists across page refreshes
      localStorage.setItem('token', 'dev-bypass-token');
      return 'dev-bypass-token';
    }

    return null;
  }

  setAuthToken(token) {
    if (token) {
      localStorage.setItem('token', token);
      // Update the axios client default headers immediately
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      localStorage.removeItem('token');
      // Remove authorization header
      delete this.client.defaults.headers.common['Authorization'];
    }
  }

  getCurrentUser() {
    try {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  async refreshToken() {
    // Use a separate axios instance to avoid interceptor loops
    const refreshClient = axios.create({
      baseURL: API_URL,
      withCredentials: true, // Important for cookies
      timeout: 10000
    });
    
    try {
      
      // In development, include the dev-bypass-token in the header
      const headers = {};
      const currentToken = this.getAuthToken();
      if (currentToken === 'dev-bypass-token') {
        headers.Authorization = `Bearer ${currentToken}`;
      }
      
      // Get refresh token from localStorage
      const storedRefreshToken = localStorage.getItem('refresh_token');
      
      // Make request to refresh token endpoint with refresh token in body
      const response = await refreshClient.post('/auth/refresh-token', 
        { refresh_token: storedRefreshToken }, 
        { headers }
      );
      const { access_token, refresh_token: newRefreshToken } = response.data;
      
      if (!access_token) {
        throw new Error('No access token returned');
      }
      
      this.setAuthToken(access_token);
      
      // Store new refresh token if provided
      if (newRefreshToken) {
        localStorage.setItem('refresh_token', newRefreshToken);
      }
      
      // Fetch user data with new token to ensure auth context is updated
      try {
        const userResponse = await this.client.get('/auth/me');
        if (userResponse.data) {
          localStorage.setItem('user', JSON.stringify(userResponse.data));
        }
      } catch (userError) {
        // Failed to refresh user data
      }
      
      return access_token;
    } catch (error) {
      // Token refresh failed
      // Clear invalid tokens
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      throw error;
    }
  }

  handleAuthError() {
    this.setAuthToken(null);
    localStorage.removeItem('user');
    
    // Use React Router navigation instead of direct window.location
    // This will be handled by the auth context
    if (window.__CAHOOTS_NAVIGATE) {
      window.__CAHOOTS_NAVIGATE('/login');
    } else {
      // Fallback for cases where navigate is not available
      window.location.href = '/login';
    }
  }

  // HTTP Methods with consistent error handling
  async get(url, config = {}) {
    try {
      const response = await this.client.get(url, config);
      return response.data;
    } catch (error) {
      throw this.enhanceError(error);
    }
  }

  async post(url, data, config = {}) {
    try {
      const response = await this.client.post(url, data, config);
      return response.data;
    } catch (error) {
      throw this.enhanceError(error);
    }
  }

  async patch(url, data, config = {}) {
    try {
      const response = await this.client.patch(url, data, config);
      return response.data;
    } catch (error) {
      throw this.enhanceError(error);
    }
  }

  async put(url, data, config = {}) {
    try {
      const response = await this.client.put(url, data, config);
      return response.data;
    } catch (error) {
      throw this.enhanceError(error);
    }
  }

  async delete(url, config = {}) {
    try {
      const response = await this.client.delete(url, config);
      return response.data;
    } catch (error) {
      throw this.enhanceError(error);
    }
  }

  // Methods with loading state management
  async getWithLoading(url, loadingType, config = {}) {
    loadingManager.setLoading(loadingType, true);
    try {
      return await this.get(url, config);
    } finally {
      loadingManager.setLoading(loadingType, false);
    }
  }

  async postWithLoading(url, data, loadingType, config = {}) {
    loadingManager.setLoading(loadingType, true);
    try {
      return await this.post(url, data, config);
    } finally {
      loadingManager.setLoading(loadingType, false);
    }
  }

  async patchWithLoading(url, data, loadingType, config = {}) {
    loadingManager.setLoading(loadingType, true);
    try {
      return await this.patch(url, data, config);
    } finally {
      loadingManager.setLoading(loadingType, false);
    }
  }

  // Specialized methods for common operations
  async getTasks(params = {}) {
    return this.get('/tasks', { params });
  }

  async getTask(taskId) {
    return this.get(`/tasks/${taskId}`);
  }

  async getTaskTree(taskId) {
    return this.get(`/tasks/${taskId}/tree`);
  }

  async createTask(taskData) {
    return this.post('/tasks', taskData);
  }

  async updateTask(taskId, updates) {
    return this.patch(`/tasks/${taskId}`, updates);
  }

  async deleteTask(taskId) {
    return this.delete(`/tasks/${taskId}`);
  }

  async deleteSubtask(taskId) {
    return this.delete(`/tasks/${taskId}/subtask`);
  }

  async restartDecomposition(taskId, restartData) {
    return this.post(`/tasks/${taskId}/restart-decomposition`, restartData);
  }

  async getTaskStats(topLevelOnly = true) {
    return this.get('/tasks/stats', {
      params: { top_level_only: topLevelOnly }
    });
  }

  // Code Generation Methods
  async getTechStacks() {
    return this.get('/codegen/tech-stacks');
  }

  async getTechStackDetails(stackName) {
    return this.get(`/codegen/tech-stacks/${stackName}`);
  }

  async startCodeGeneration(projectId, techStack, repoName = null) {
    return this.post(`/codegen/projects/${projectId}/generate`, {
      tech_stack: techStack,
      repo_name: repoName,
    });
  }

  async getGenerationStatus(projectId) {
    return this.get(`/codegen/projects/${projectId}/generate/status`);
  }

  async cancelGeneration(projectId) {
    return this.post(`/codegen/projects/${projectId}/generate/cancel`);
  }

  async retryGeneration(projectId) {
    return this.post(`/codegen/projects/${projectId}/generate/retry`);
  }

  async addGenerationRetries(projectId) {
    return this.post(`/codegen/projects/${projectId}/generate/keep-trying`);
  }

  // Edit Methods with Cascade Support
  /**
   * Analyze an edit to get cascade effects before applying
   * @param {string} taskId - The task ID
   * @param {object} editRequest - { artifact_type, artifact_id, changes }
   * @returns {Promise<object>} - { direct_change, cascade_effects, total_affected }
   */
  async analyzeEdit(taskId, editRequest) {
    return this.post(`/edit/tasks/${taskId}/analyze`, editRequest);
  }

  /**
   * Apply an edit with selected cascade changes
   * @param {string} taskId - The task ID
   * @param {object} applyRequest - { direct_change, cascade_changes_to_apply }
   * @returns {Promise<object>} - { success, changes_applied, updated_task }
   */
  async applyEdit(taskId, applyRequest) {
    return this.post(`/edit/tasks/${taskId}/apply`, applyRequest);
  }

  /**
   * Get supported artifact types for editing
   * @returns {Promise<object>} - List of artifact types with metadata
   */
  async getEditableArtifactTypes() {
    return this.get('/edit/artifact-types');
  }
}

// Export singleton instance
const apiClient = new UnifiedApiClient();
export default apiClient;
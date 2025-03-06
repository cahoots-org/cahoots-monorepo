import axios from 'axios';
import { config } from '../../config/config';

/**
 * API client for making HTTP requests to the backend
 */
class ApiClient {
  private baseUrl: string;
  
  constructor() {
    this.baseUrl = config.api.baseUrl;
  }

  /**
   * Get the authorization header using the token from localStorage
   */
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem(config.auth.tokenKey);
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * Make a GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    try {
      const response = await axios.get(`${this.baseUrl}${endpoint}`, {
        headers: {
          ...this.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Make a POST request
   */
  async post<T>(endpoint: string, data: any): Promise<T> {
    try {
      const response = await axios.post(`${this.baseUrl}${endpoint}`, data, {
        headers: {
          ...this.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Make a PUT request
   */
  async put<T>(endpoint: string, data: any): Promise<T> {
    try {
      const response = await axios.put(`${this.baseUrl}${endpoint}`, data, {
        headers: {
          ...this.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Make a PATCH request
   */
  async patch<T>(endpoint: string, data: any): Promise<T> {
    try {
      const response = await axios.patch(`${this.baseUrl}${endpoint}`, data, {
        headers: {
          ...this.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Make a DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    try {
      const response = await axios.delete(`${this.baseUrl}${endpoint}`, {
        headers: {
          ...this.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Handle error responses
   */
  private handleError(error: any): void {
    if (error.response?.status === 401) {
      // Handle unauthorized error (e.g., redirect to login)
      localStorage.removeItem(config.auth.tokenKey);
      localStorage.removeItem(config.auth.refreshTokenKey);
      // You might want to redirect to login page here or handle it in your auth store
    }
  }
}

export const apiClient = new ApiClient();
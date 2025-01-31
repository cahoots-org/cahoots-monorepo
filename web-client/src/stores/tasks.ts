import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { config } from '../config/config';
import { apiClient } from '../lib/api/client';

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'review' | 'testing' | 'done';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee?: string;
  created_at: string;
  updated_at: string;
  project_id: string;
}

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  isLoading: boolean;
  error: string | null;
  fetchTasks: (projectId: string) => Promise<void>;
  createTask: (projectId: string, data: Partial<Task>) => Promise<void>;
  updateTask: (projectId: string, taskId: string, data: Partial<Task>) => Promise<void>;
  setCurrentTask: (task: Task | null) => void;
  clearError: () => void;
}

export const useTaskStore = create<TaskState>()(
  devtools((set) => ({
    tasks: [],
    currentTask: null,
    isLoading: false,
    error: null,

    fetchTasks: async (projectId) => {
      set({ isLoading: true, error: null });
      try {
        const tasks = await apiClient.get<Task[]>(
          config.api.endpoints.tasks.list(projectId)
        );
        set({ tasks, isLoading: false });
      } catch (error: any) {
        set({
          error: error.message || 'Failed to fetch tasks',
          isLoading: false,
        });
      }
    },

    createTask: async (projectId, data) => {
      set({ isLoading: true, error: null });
      try {
        const task = await apiClient.post<Task>(
          config.api.endpoints.tasks.create(projectId),
          data
        );
        set((state) => ({
          tasks: [...state.tasks, task],
          isLoading: false,
        }));
      } catch (error: any) {
        set({
          error: error.message || 'Failed to create task',
          isLoading: false,
        });
      }
    },

    updateTask: async (projectId, taskId, data) => {
      set({ isLoading: true, error: null });
      try {
        const updated = await apiClient.patch<Task>(
          config.api.endpoints.tasks.update(projectId, taskId),
          data
        );
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === taskId ? updated : t)),
          currentTask: state.currentTask?.id === taskId ? updated : state.currentTask,
          isLoading: false,
        }));
      } catch (error: any) {
        set({
          error: error.message || 'Failed to update task',
          isLoading: false,
        });
      }
    },

    setCurrentTask: (task) => {
      set({ currentTask: task });
    },

    clearError: () => {
      set({ error: null });
    },
  }))
); 
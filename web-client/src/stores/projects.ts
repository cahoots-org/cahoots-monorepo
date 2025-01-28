import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { config } from '../config/config';
import { apiClient } from '../lib/api/client';
import { wsClient } from '../lib/ws/client';
import type { ProjectUpdate } from '../lib/ws/client';

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'initializing' | 'active' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  task_board_url?: string;
  repository_url?: string;
}

interface ProjectResources {
  task_board_url: string;
  repository_url: string;
}

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  createProject: (data: { name: string; description: string }) => Promise<void>;
  fetchProjectDetails: (id: string) => Promise<void>;
  fetchProjectResources: (id: string) => Promise<ProjectResources>;
  updateProject: (id: string, data: Partial<Project>) => Promise<void>;
  handleProjectUpdate: (update: ProjectUpdate) => void;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>()(
  devtools((set, get) => ({
    projects: [],
    currentProject: null,
    isLoading: false,
    error: null,

    fetchProjects: async () => {
      set({ isLoading: true, error: null });
      try {
        const projects = await apiClient.get<Project[]>(config.api.endpoints.projects.list);
        set({ projects, isLoading: false });
      } catch (error: any) {
        set({
          error: error.message || 'Failed to fetch projects',
          isLoading: false,
        });
      }
    },

    createProject: async (data) => {
      set({ isLoading: true, error: null });
      try {
        const project = await apiClient.post<Project>(
          config.api.endpoints.projects.create,
          data
        );
        set((state) => ({
          projects: [...state.projects, project],
          currentProject: project,
          isLoading: false,
        }));
      } catch (error: any) {
        set({
          error: error.message || 'Failed to create project',
          isLoading: false,
        });
      }
    },

    fetchProjectDetails: async (id) => {
      set({ isLoading: true, error: null });
      try {
        const project = await apiClient.get<Project>(
          config.api.endpoints.projects.details(id)
        );
        set({ currentProject: project, isLoading: false });

        // Subscribe to project updates
        const unsubscribe = wsClient.subscribeToProject(id, get().handleProjectUpdate);
        return () => unsubscribe();
      } catch (error: any) {
        set({
          error: error.message || 'Failed to fetch project details',
          isLoading: false,
        });
      }
    },

    fetchProjectResources: async (id) => {
      try {
        return await apiClient.get<ProjectResources>(
          config.api.endpoints.projects.resources(id)
        );
      } catch (error: any) {
        set({
          error: error.message || 'Failed to fetch project resources',
        });
        throw error;
      }
    },

    updateProject: async (id, data) => {
      set({ isLoading: true, error: null });
      try {
        const updated = await apiClient.patch<Project>(
          config.api.endpoints.projects.details(id),
          data
        );
        set((state) => ({
          projects: state.projects.map((p) => (p.id === id ? updated : p)),
          currentProject: state.currentProject?.id === id ? updated : state.currentProject,
          isLoading: false,
        }));
      } catch (error: any) {
        set({
          error: error.message || 'Failed to update project',
          isLoading: false,
        });
      }
    },

    handleProjectUpdate: (update) => {
      const { currentProject } = get();
      if (currentProject?.id === update.project_id) {
        switch (update.type) {
          case 'status':
            set((state) => ({
              currentProject: state.currentProject
                ? { ...state.currentProject, ...update.data }
                : null,
            }));
            break;
          // Handle other update types as needed
        }
      }
    },

    clearError: () => {
      set({ error: null });
    },
  }))
); 
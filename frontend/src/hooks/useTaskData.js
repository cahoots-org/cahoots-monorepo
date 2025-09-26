import { useState, useEffect } from 'react';
import apiClient from '../services/unifiedApiClient';
import { withErrorHandling } from '../services/errorHandler';
import { LoadingTypes } from '../services/loadingService';
import { logger } from '../utils/logger';

export const useTaskData = (task, isOpen) => {
  const [implementationDetails, setImplementationDetails] = useState('');
  const [storyPoints, setStoryPoints] = useState(1);
  const [projectStandards, setProjectStandards] = useState({});
  const [techStack, setTechStack] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Simple operator status update (removed Recoil dependency)
  const updateOperatorStatus = (taskId, operator, status, progress) => {
    logger.debug(`Operator ${operator} status: ${status} (${progress}%)`);
  };

  // Initialize task details when task changes
  useEffect(() => {
    if (!isOpen || !task) return;

    logger.debug(`useTaskData: Loading task details for ${task.task_id}`);
    
    // Set initial values from task data
    setImplementationDetails(task.implementation_details || '');
    setStoryPoints(task.story_points || 1);
    
    // Extract project standards and tech stack from context
    const context = task.context || {};
    const standards = context.project_standards || context.standards || {};
    const technologies = context.tech_stack || context.technologies || {};
    
    setProjectStandards(standards);
    setTechStack(technologies);
    
    // Auto-generate implementation details for atomic tasks without them
    const isAtomic = task.is_atomic;
    const hasImplementationDetails = task.implementation_details && task.implementation_details.trim().length > 0;
    
    if (isAtomic && !hasImplementationDetails) {
      logger.debug('useTaskData: Atomic task detected without implementation details, generating them...');
      generateImplementationDetails();
    }
  }, [isOpen, task]);

  // Generate implementation details
  const generateImplementationDetails = async () => {
    if (!task) return;
    
    setIsGenerating(true);
    updateOperatorStatus(task.task_id, 'details_generator', 'processing', 0);
    
    const { data, error } = await withErrorHandling(
      () => apiClient.postWithLoading(`/tasks/${task.task_id}/generate-details`, {
        task_description: task.description,
        complexity_score: task.complexity_score || 0
      }, LoadingTypes.GENERATE_DETAILS),
      {
        customMessages: {
          SERVER_ERROR: 'Failed to generate implementation details. Please try again.',
          NOT_FOUND: 'Task not found. Please refresh and try again.',
          VALIDATION_ERROR: 'Invalid task data. Please check the task details.'
        }
      }
    );
    
    if (error) {
      console.error('Failed to generate implementation details:', error);
      updateOperatorStatus(task.task_id, 'details_generator', 'failed', 0);
      throw error;
    } else {
      if (data && data.implementation_details) {
        setImplementationDetails(data.implementation_details);
      }
      
      if (data && data.story_points) {
        setStoryPoints(data.story_points);
        updateOperatorStatus(task.task_id, 'details_generator', 'processing', 50);
      }
      
      // Update the task with new details
      const { error: updateError } = await withErrorHandling(
        () => apiClient.patch(`/tasks/${task.task_id}`, {
          implementation_details: data.implementation_details || implementationDetails,
          story_points: data.story_points || storyPoints
        }),
        {
          customMessages: {
            SERVER_ERROR: 'Failed to save generated details. Please try saving manually.'
          }
        }
      );
      
      if (updateError) {
        console.error('Failed to update task with generated details:', updateError);
        updateOperatorStatus(task.task_id, 'details_generator', 'failed', 0);
      } else {
        updateOperatorStatus(task.task_id, 'details_generator', 'completed', 100);
      }
    }
    
    setIsGenerating(false);
  };

  // Save task details
  const handleSave = async () => {
    if (!task) return { success: false };
    
    setIsSaving(true);
    
    try {
      // First, save the task details
      const { data, error } = await withErrorHandling(
        () => apiClient.patchWithLoading(`/tasks/${task.task_id}/details`, {
          implementation_details: implementationDetails,
          story_points: storyPoints
        }, LoadingTypes.SAVE),
        {
          customMessages: {
            VALIDATION_ERROR: 'Please check your task details and try again.',
            SERVER_ERROR: 'Unable to save task details. Please try again later.'
          }
        }
      );
      
      if (error) {
        throw error;
      }
      
      // If the server adjusted the story points (to match Fibonacci), update our local state
      if (data && data.story_points && data.story_points !== storyPoints) {
        logger.debug(`Server adjusted story points from ${storyPoints} to ${data.story_points}`);
        setStoryPoints(data.story_points);
      }
      
      // If the server generated implementation details for an atomic task, update our local state
      if (data && data.implementation_details && 
          (!implementationDetails || implementationDetails.trim() === '') && 
          data.implementation_details.trim() !== '') {
        logger.debug('Server generated implementation details for atomic task');
        setImplementationDetails(data.implementation_details);
      }
      
      return { 
        success: true, 
        adjustedStoryPoints: data?.story_points,
        generatedDetails: data?.implementation_details
      };
    } catch (err) {
      logger.error('Error saving task details:', err);
      return { success: false, error: err };
    } finally {
      setIsSaving(false);
    }
  };

  return {
    implementationDetails,
    setImplementationDetails,
    storyPoints,
    setStoryPoints,
    projectStandards,
    techStack,
    isSaving,
    isGenerating,
    generateImplementationDetails,
    handleSave
  };
};
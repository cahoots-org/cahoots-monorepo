import { useState, useCallback } from 'react';
import unifiedApiClient from '../services/unifiedApiClient';

/**
 * useCascadeEdits - Hook for managing cascade edit workflow
 *
 * Handles:
 * 1. Analyzing cascade changes via API
 * 2. Showing change preview modal
 * 3. Applying accepted changes
 * 4. Error handling and loading states
 */
export const useCascadeEdits = (taskId, currentState) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [previewChanges, setPreviewChanges] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Analyze what cascade changes are needed for an edit
   */
  const analyzeCascade = useCallback(async (editType, editId, changes) => {
    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await unifiedApiClient.post(
        `/cascade/tasks/${taskId}/analyze`,
        {
          edit_type: editType,
          edit_id: editId,
          changes: changes,
          current_state: currentState,
        }
      );

      if (response.changes && response.changes.length > 0) {
        // Show preview modal
        setPreviewChanges(response);
        return response;
      } else {
        // No cascade changes needed, can apply directly
        return null;
      }
    } catch (err) {
      console.error('[CascadeEdits] Analysis failed:', err);
      setError(err.message || 'Failed to analyze cascade changes');
      throw err;
    } finally {
      setIsAnalyzing(false);
    }
  }, [taskId, currentState]);

  /**
   * Apply selected cascade changes
   */
  const applyCascade = useCallback(async (changes) => {
    setIsApplying(true);
    setError(null);

    try {
      const response = await unifiedApiClient.post(
        `/cascade/tasks/${taskId}/apply`,
        {
          task_id: taskId,
          changes: changes,
        }
      );

      // Close preview modal
      setPreviewChanges(null);

      return response;
    } catch (err) {
      console.error('[CascadeEdits] Apply failed:', err);
      setError(err.message || 'Failed to apply cascade changes');
      throw err;
    } finally {
      setIsApplying(false);
    }
  }, [taskId]);

  /**
   * Cancel cascade preview
   */
  const cancelCascade = useCallback(() => {
    setPreviewChanges(null);
    setError(null);
  }, []);

  /**
   * Handle an edit with cascade analysis
   */
  const handleEdit = useCallback(async ({ type, id, field, oldValue, newValue }) => {
    try {
      // Build changes object
      const changes = {
        [field]: newValue,
      };

      // Analyze cascade
      const cascadeResult = await analyzeCascade(type, id, changes);

      if (!cascadeResult) {
        // No cascade changes, apply directly
        // This would typically update local state
        return { success: true, cascadeChanges: [] };
      }

      // Cascade changes will be shown in preview modal
      // User will need to accept/reject them
      return { success: true, cascadeChanges: cascadeResult.changes };
    } catch (err) {
      console.error('[CascadeEdits] handleEdit failed:', err);
      return { success: false, error: err.message };
    }
  }, [analyzeCascade]);

  return {
    isAnalyzing,
    isApplying,
    previewChanges,
    error,
    analyzeCascade,
    applyCascade,
    cancelCascade,
    handleEdit,
  };
};

export default useCascadeEdits;

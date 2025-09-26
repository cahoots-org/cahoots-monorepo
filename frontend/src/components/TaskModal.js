import React, { useState } from 'react';
import TreeVisualization from './TreeVisualization';
import { useModalStack } from '../contexts/ModalContext';
import apiClient from '../services/unifiedApiClient';
import { withErrorHandling } from '../services/errorHandler';
import { logger } from '../utils/logger';
import FeedbackModal from './FeedbackModal';
import TaskEditForm from './TaskEditForm';
import TaskModalHeader from './TaskModalHeader';
import ConfirmationModal from './ConfirmationModal';
import { useTaskData } from '../hooks/useTaskData';
import { useTaskTree } from '../hooks/useTaskTree';
import { useToast } from '../hooks/useToast';

const TaskModal = () => {
  // Use modal stack context
  const { modalStack, popModal, clearModalStack, getCurrentTask } = useModalStack();
  
  // Get the current modal object from the modal stack
  const modalObject = getCurrentTask();
  const isOpen = !!modalObject;
  
  // Determine modal type and extract task if it's a regular task modal
  const modalType = modalObject?.type || 'task';
  const task = modalType === 'task' ? modalObject?.task : null;
  
  // Debug logging
  console.log('TaskModal rendered with modalObject:', modalObject);
  console.log('TaskModal modalType:', modalType);
  console.log('TaskModal task:', task);
  
  // Local loading state instead of Recoil
  const [loading, setLoading] = useState(false);
  
  // Custom hooks for managing component state
  const { showToast, ToastComponent } = useToast();
  const {
    implementationDetails,
    setImplementationDetails,
    storyPoints,
    setStoryPoints,
    projectStandards,
    techStack,
    isSaving,
    isGenerating,
    generateImplementationDetails,
    handleSave: handleSaveTask
  } = useTaskData(task, isOpen);
  
  const {
    localTaskTree,
    isLoadingTaskTree,
    taskTreeError,
    isRootTask,
    showDecompositionTree,
    loadTaskTree,
    updateTaskTree,
    lastUpdated
  } = useTaskTree(task, isOpen);

  // Handle closing non-task modals (just pop from stack)
  const onCloseNonTaskModal = () => {
    popModal();
  };

  // Handle closing the modal
  const onClose = async (shouldRefresh = false) => {
    // If this is a subtask modal and we're refreshing, refresh the parent task data
    if (shouldRefresh && task && task.parent_id) {
      logger.debug(`Refreshing parent task ${task.parent_id} after subtask update`);
      // Show loading state while refreshing
      setLoading(true);
      
      try {
        // Get the full parent task data with context
        const { data: parentTask } = await withErrorHandling(
          () => apiClient.get(`/tasks/${task.parent_id}`)
        );
        
        // Then refresh the parent task's tree view
        await withErrorHandling(
          () => apiClient.get(`/tasks/${task.parent_id}/tree`)
        );
        
        logger.debug('Parent task tree refreshed successfully');
        
        // If there's an onClose callback in the modal object, call it with refresh flag
        if (modalObject && modalObject.onClose) {
          modalObject.onClose(true);
        }
      } catch (error) {
        logger.error('Failed to refresh parent task tree:', error);
        showToast('Failed to refresh parent task data', 'error');
      } finally {
        setLoading(false);
      }
    } else {
      // If there's an onClose callback in the modal object, call it
      if (modalObject && modalObject.onClose) {
        modalObject.onClose(shouldRefresh);
      }
    }
    
    // Reset loading state to ensure dashboard doesn't show spinner
    setLoading(false);
    // Always clear the entire modal stack when closing
    clearModalStack();
  };
  
  // State for delete confirmation modal
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  
  
  const calculateStoryPoints = (complexity) => {
    // Convert complexity score (0-10) to story points (1-5)
    if (complexity >= 8) return 5;
    if (complexity >= 6) return 4;
    if (complexity >= 4) return 3;
    if (complexity >= 2) return 2;
    return 1;
  };
  
  // Handle save button click and close modal
  const handleSaveAndClose = async () => {
    try {
      const result = await handleSaveTask();
      if (result.success) {
        // Show appropriate success message
        if (result.adjustedStoryPoints) {
          showToast(`Task details saved. Story points adjusted to ${result.adjustedStoryPoints}`, 'success');
        } else if (result.generatedDetails) {
          showToast('Task details saved. Implementation details were auto-generated for this atomic task', 'success');
        } else {
          showToast('Task details saved successfully', 'success');
        }
        
        // Close the modal and refresh the parent task tree
        onClose(true);
      }
    } catch (error) {
      showToast(error.message || 'Failed to save task details', 'error');
    }
  };

  // Delete handler for confirmation modal
  const handleDeleteConfirm = async () => {
    const { error } = await withErrorHandling(
      () => apiClient.delete(`/tasks/${task.task_id}`),
      {
        customMessages: {
          NOT_FOUND: 'Task not found. It may have already been deleted.',
          AUTHORIZATION: 'You do not have permission to delete this task.',
          SERVER_ERROR: 'Failed to delete task. Please try again later.'
        }
      }
    );
    
    if (error) {
      console.error('Failed to delete task:', error);
      showToast(error.message, 'error');
    } else {
      onClose(true); // Close with refresh flag
    }
  };
  
  // Render helper functions for different modal types
  const renderTreeStatsModal = () => {
    const stats = modalObject.stats;
    return (
      <>
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center">
            {modalStack.length > 1 && (
              <button
                onClick={onCloseNonTaskModal}
                className="mr-3 px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                ← Back
              </button>
            )}
            <h2 className="text-xl font-semibold">Tree Statistics</h2>
          </div>
          <button 
            onClick={onCloseNonTaskModal} 
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
            <div className="text-blue-600 dark:text-blue-400 text-2xl font-bold">{stats.total_nodes}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Tasks</div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
            <div className="text-green-600 dark:text-green-400 text-2xl font-bold">{stats.atomic_nodes}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Atomic Tasks</div>
          </div>
          <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
            <div className="text-purple-600 dark:text-purple-400 text-2xl font-bold">{stats.max_depth}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Max Depth</div>
          </div>
          <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
            <div className="text-orange-600 dark:text-orange-400 text-2xl font-bold">{stats.total_story_points}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Story Points</div>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
            <div className="text-yellow-600 dark:text-yellow-400 text-2xl font-bold">{stats.completed_nodes}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Completed</div>
          </div>
          <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
            <div className="text-red-600 dark:text-red-400 text-2xl font-bold">{stats.error_nodes}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Errors</div>
          </div>
        </div>
        
        {stats.avg_complexity_score > 0 && (
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">Average Complexity Score</div>
            <div className="text-lg font-semibold">{stats.avg_complexity_score.toFixed(2)}</div>
          </div>
        )}
      </>
    );
  };

  const renderDspyStatusModal = () => {
    const status = modalObject.status;
    const optimizationStatus = status.optimization_status || {};
    const feedbackCount = optimizationStatus.feedback_count || 0;
    const threshold = status.feedback_collection?.optimization_threshold || 50;
    const progress = Math.min((feedbackCount / threshold) * 100, 100);
    const readyForOptimization = optimizationStatus.ready_for_optimization || false;
    const externalExamplesCount = optimizationStatus.external_examples_count || 0;
    const pretrainingThreshold = optimizationStatus.pretraining_threshold || 100;
    const externalProgress = Math.min((externalExamplesCount / pretrainingThreshold) * 100, 100);
    
    return (
      <>
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center">
            {modalStack.length > 1 && (
              <button
                onClick={onCloseNonTaskModal}
                className="mr-3 px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                ← Back
              </button>
            )}
            <h2 className="text-xl font-semibold">AI Model Feedback & Training Status</h2>
          </div>
          <button 
            onClick={onCloseNonTaskModal} 
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-6">
          {/* Feedback Collection Progress */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-6 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">User Feedback Collection</h3>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                readyForOptimization 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
              }`}>
                {readyForOptimization ? 'Ready for Retraining' : 'Collecting Feedback'}
              </div>
            </div>
            
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-2">
                <span>Feedback collected: {feedbackCount} / {threshold}</span>
                <span className="font-medium">{progress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div 
                  className={`h-3 rounded-full transition-all duration-500 ${
                    readyForOptimization 
                      ? 'bg-green-500' 
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Collection Status:</span>
                <div className="font-medium">{status.feedback_collection?.enabled ? '🟢 Active' : '🔴 Disabled'}</div>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Feedback Sources:</span>
                <div className="font-medium">{status.feedback_collection?.sources?.join(', ') || 'None'}</div>
              </div>
            </div>
          </div>

          {/* External Training Data Progress */}
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-6 rounded-lg border border-purple-200 dark:border-purple-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-purple-900 dark:text-purple-100">External Training Data</h3>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                optimizationStatus.ready_for_pretraining
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
              }`}>
                {optimizationStatus.ready_for_pretraining ? 'Ready for Pretraining' : 'Gathering Data'}
              </div>
            </div>
            
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-2">
                <span>External examples: {externalExamplesCount} / {pretrainingThreshold}</span>
                <span className="font-medium">{externalProgress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div 
                  className="h-3 rounded-full bg-purple-500 transition-all duration-500"
                  style={{ width: `${externalProgress}%` }}
                ></div>
              </div>
            </div>
            
            {optimizationStatus.external_datasets && (
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Available Datasets:</span>
                <div className="mt-1 space-y-1">
                  {Object.entries(optimizationStatus.external_datasets).map(([name, info]) => (
                    <div key={name} className="flex justify-between">
                      <span className="font-medium">{name}</span>
                      <span className="text-gray-500">{info.status || 'Unknown'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Optimization History */}
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 p-6 rounded-lg border border-emerald-200 dark:border-emerald-800">
            <h3 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100 mb-4">Model Training History</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Last Optimization:</span>
                <div className="font-medium">
                  {optimizationStatus.last_optimization 
                    ? new Date(optimizationStatus.last_optimization).toLocaleString()
                    : 'Never'
                  }
                </div>
              </div>
              
              {optimizationStatus.metrics && (
                <>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Model Accuracy:</span>
                    <div className="font-medium">
                      {optimizationStatus.metrics.correct_predictions} / {optimizationStatus.metrics.total_predictions}
                      {optimizationStatus.metrics.total_predictions > 0 && 
                        ` (${((optimizationStatus.metrics.correct_predictions / optimizationStatus.metrics.total_predictions) * 100).toFixed(1)}%)`
                      }
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Avg Confidence:</span>
                    <div className="font-medium">{optimizationStatus.metrics.average_confidence?.toFixed(2) || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Improvement Rate:</span>
                    <div className="font-medium">{optimizationStatus.metrics.improvement_rate?.toFixed(1) || 'N/A'}%</div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Next Steps */}
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 p-6 rounded-lg border border-amber-200 dark:border-amber-800">
            <h3 className="text-lg font-semibold text-amber-900 dark:text-amber-100 mb-4">What Happens Next?</h3>
            
            <div className="space-y-3 text-sm">
              {readyForOptimization ? (
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mt-0.5">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  </div>
                  <div>
                    <div className="font-medium text-green-800 dark:text-green-300">Ready for Automatic Retraining</div>
                    <div className="text-gray-600 dark:text-gray-400">The system will automatically retrain AI models using collected feedback (max once per day).</div>
                  </div>
                </div>
              ) : (
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mt-0.5">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  </div>
                  <div>
                    <div className="font-medium text-blue-800 dark:text-blue-300">Continue Providing Feedback</div>
                    <div className="text-gray-600 dark:text-gray-400">Help improve the AI by providing feedback on task decompositions. Need {threshold - feedbackCount} more feedbacks for next training.</div>
                  </div>
                </div>
              )}
              
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                </div>
                <div>
                  <div className="font-medium text-purple-800 dark:text-purple-300">Enhanced with External Data</div>
                  <div className="text-gray-600 dark:text-gray-400">Training combines your feedback with external datasets (JIRA estimations, etc.) for better performance.</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  };


  if (!isOpen) return null;

  // For non-task modals, render them directly
  if (modalType !== 'task') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className={`bg-white dark:bg-gray-800 rounded-lg w-full max-h-[90vh] overflow-y-auto ${
          modalType === 'dspy-status' ? 'max-w-4xl' : 'max-w-2xl'
        }`}>
          <div className="p-6">
            {modalType === 'tree-stats' && renderTreeStatsModal()}
            {modalType === 'dspy-status' && renderDspyStatusModal()}
            {modalType === 'feedback' && <FeedbackModal modalObject={modalObject} onClose={onClose} />}
          </div>
        </div>
      </div>
    );
  }

  // For task modals, ensure we have a task
  if (!task) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <TaskModalHeader 
            task={task}
            localTaskTree={localTaskTree}
            modalStack={modalStack}
            popModal={popModal}
            onClose={onClose}
            onShowToast={showToast}
          />
          
          <div className="mb-6">
            <h3 className="text-lg font-medium mb-2">
              {task.description && task.description.trim() 
                ? task.description.split('\n')[0] 
                : `Task ${task.task_id ? task.task_id.substring(0, 8) : 'Details'}`
              }
            </h3>
            <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
              {task.description && task.description.trim() 
                ? task.description 
                : 'No description available. This task may not have loaded completely.'
              }
            </p>
            {(!task.description || !task.description.trim()) && (
              <div className="mt-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <div className="text-sm text-yellow-800 dark:text-yellow-200">
                  <strong>Data Loading Issue:</strong> This task appears to have incomplete data. 
                  Try refreshing the page or check the browser console for errors.
                </div>
              </div>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h4 className="font-medium mb-2">Task Information</h4>
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-500 dark:text-gray-400">Status:</div>
                  <div className="font-medium capitalize">{task.status?.replace('_', ' ') || 'pending'}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">Created:</div>
                  <div>{task.created_at ? new Date(task.created_at).toLocaleString() : 'Unknown'}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">Complexity:</div>
                  <div>{task.complexity_score !== undefined && task.complexity_score !== null ? task.complexity_score.toFixed(1) : 'N/A'}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">Subtasks:</div>
                  <div>{task.children_count !== undefined ? task.children_count : 0}</div>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Context Information</h4>
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-500 dark:text-gray-400">Is Atomic:</div>
                  <div className="font-medium">{task.is_atomic ? 'Yes' : 'No'}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">Depth:</div>
                  <div>{task.depth !== undefined ? task.depth : 0}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">Parent ID:</div>
                  <div className="text-xs break-all">{task.parent_id || 'Root Task'}</div>
                  
                  <div className="text-gray-500 dark:text-gray-400">User ID:</div>
                  <div className="text-xs break-all">{task.user_id || 'Unknown'}</div>
                </div>
              </div>
            </div>
          </div>
          
          {showDecompositionTree && (
            <div className="mb-6">
              <div className="flex items-center mb-2">
                <h4 className="font-medium mr-2">Decomposition Tree</h4>
                <button
                  className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 flex items-center"
                  onClick={() => {
                    logger.debug(`TaskModal: Manually refreshing task tree for ${task.task_id}`);
                    loadTaskTree(task.task_id);
                  }}
                  disabled={isLoadingTaskTree}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {isLoadingTaskTree ? 'Loading...' : 'Refresh Tree'}
                </button>
              </div>
              <div className="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 p-3 max-h-96 overflow-auto">
                {isLoadingTaskTree ? (
                  <div className="text-gray-500 italic p-4 flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p>Loading decomposition tree...</p>
                  </div>
                ) : taskTreeError ? (
                  <div className="text-red-500 italic p-4 border border-red-200 rounded-md">
                    <p>Error loading task tree: {taskTreeError}</p>
                    <button 
                      className="mt-2 px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                      onClick={() => loadTaskTree(task.task_id)}
                    >
                      Retry
                    </button>
                  </div>
                ) : localTaskTree ? (
                  <TreeVisualization 
                    taskTree={localTaskTree} 
                    operatorStatus={{}} 
                    key={`tree-${task.task_id}-${Date.now()}`}
                    onRefresh={() => loadTaskTree(task.task_id)}
                    onTaskTreeUpdate={(updatedTree) => {
                      logger.debug('Task tree updated from subtask changes');
                      // Update the local task tree with the refreshed data
                      if (updatedTree) {
                        updateTaskTree(updatedTree);
                      }
                    }}
                  />
                ) : (
                  <div className="text-gray-500 italic p-4">
                    <p>No decomposition tree available</p>
                    <p className="text-xs mt-2">The task may not have been decomposed yet</p>
                    <button 
                      className="mt-2 px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                      onClick={() => loadTaskTree(task.task_id)}
                    >
                      Retry Loading
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
          
          <TaskEditForm 
            task={task}
            showDecompositionTree={showDecompositionTree}
            implementationDetails={implementationDetails}
            setImplementationDetails={setImplementationDetails}
            projectStandards={projectStandards}
            techStack={techStack}
            storyPoints={storyPoints}
            setStoryPoints={setStoryPoints}
            onShowToast={showToast}
          />
          
          <div className="flex justify-between items-center w-full">
            {/* Left side - Delete button */}
            <div>
              {!isRootTask && (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="px-4 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                >
                  Delete Task
                </button>
              )}
            </div>
            
            {/* Right side - Other buttons */}
            <div className="flex space-x-3">
              <button
                onClick={() => onClose(false)}
                className="btn-secondary px-4 py-2"
              >
                {isRootTask ? 'Close' : 'Cancel'}
              </button>
              {!showDecompositionTree && (
                <>
                  {task.is_atomic && (
                    <button
                      onClick={async () => {
                        try {
                          await generateImplementationDetails();
                        } catch (error) {
                          showToast(error.message, 'error');
                        }
                      }}
                      className="px-4 py-2 ml-auto text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={isGenerating}
                    >
                      {isGenerating ? 'Generating...' : 'Auto-Generate Details'}
                    </button>
                  )}
                  <button 
                    type="button" 
                    className="btn btn-primary" 
                    onClick={handleSaveAndClose}
                    disabled={isSaving || isGenerating}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDeleteConfirm}
        title="Delete Task"
        message={`Are you sure you want to delete "${task?.description}"? This will also delete all subtasks.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />
      
      <ToastComponent />
    </div>
  );
};

export default TaskModal;

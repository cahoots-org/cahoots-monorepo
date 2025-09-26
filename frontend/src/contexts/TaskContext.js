import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
import useWebSocket from '../hooks/useWebSocket';
import apiClient from '../services/unifiedApiClient';

// Get API URL from runtime config (same as unifiedApiClient)
const API_URL = window.CAHOOTS_CONFIG?.API_URL || '/api';

// Function to get WebSocket URL for a specific task
const getWebSocketUrl = (taskId) => {
  if (!taskId) {
    console.error('No task ID provided for WebSocket connection');
    return null;
  }
  
  // Use the same logic as other WebSocket connections
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  
  // In production (HTTPS), don't include port
  if (window.location.protocol === 'https:') {
    return `${protocol}//${host}/ws/tasks/${taskId}`;
  }
  
  // In development, use port 8080
  const port = process.env.REACT_APP_API_URL ? 
    new URL(process.env.REACT_APP_API_URL).port || '8080' : 
    '8080';
  return `${protocol}//${host}:${port}/ws/tasks/${taskId}`;
};


export const TaskContext = createContext();

export const TaskProvider = ({ children }) => {
  // Core state
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentTask, setCurrentTask] = useState({});
  const [taskTree, setTaskTree] = useState({});
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [operatorStatus, setOperatorStatus] = useState({});

  // Create refs for functions that will be used in the WebSocket callback
  const getTaskRef = useRef(null);
  const updateTaskStatusRef = useRef(null);
  const fetchTasksRef = useRef(null);
  const fetchTaskTreeRef = useRef(null);

  // Function to fetch a specific task
  const getTask = useCallback(async (taskId) => {
    if (!taskId) return null;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(`/tasks/${taskId}`);
      return response;
    } catch (err) {
      console.error(`Error fetching task ${taskId}:`, err);
      setError(`Failed to fetch task: ${err.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Store getTask in ref
  useEffect(() => {
    getTaskRef.current = getTask;
  }, [getTask]);

  // Function to fetch the task tree for a specific task
  const fetchTaskTree = useCallback(async (taskId) => {
    if (!taskId) {
      // fetchTaskTree called without taskId
      return;
    }
    
    
    try {
      setLoading(true);
      setError(null);
      
      const treeData = await apiClient.get(`/tasks/${taskId}/tree`);
      
      if (!treeData) {
        console.error('Received null or undefined tree data for taskId:', taskId);
        setError('Failed to load task tree: No data received');
        setLoading(false);
        return null;
      }
      
      console.log('Successfully fetched task tree:', treeData);
      
      // Create a completely new object reference to ensure React detects the change
      setTaskTree((prev) => {
        const newState = { ...prev };
        // Create a deep copy of the tree data to ensure React detects the change
        newState[taskId] = JSON.parse(JSON.stringify(treeData));
        console.log('Updated task tree state with new reference:', taskId, newState[taskId]);
        return newState;
      });
      
      setLoading(false);
      return treeData;
    } catch (err) {
      console.error('Error fetching task tree:', err);
      setLoading(false);
      setError(`Failed to load task tree: ${err.message}`);
      throw err;
    }
  }, []);

  // Store fetchTaskTree in ref
  useEffect(() => {
    fetchTaskTreeRef.current = fetchTaskTree;
  }, [fetchTaskTree]);

  // Function to fetch all tasks
  const fetchTasks = useCallback(async (topLevelOnly = true) => {
    console.log('fetchTasks called with topLevelOnly:', topLevelOnly);
    
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (topLevelOnly) {
        params.append('top_level_only', 'true');
      }
      
      const response = await apiClient.get(`/tasks?${params.toString()}`);
      const tasksData = Array.isArray(response) ? response : response.tasks || [];
      
      setTasks(tasksData);
      setLoading(false);
      return tasksData;
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setLoading(false);
      setError(`Failed to load tasks: ${err.message}`);
      throw err;
    }
  }, []);

  // Store fetchTasks in ref
  useEffect(() => {
    fetchTasksRef.current = fetchTasks;
  }, [fetchTasks]);

  // Update task status
  const updateTaskStatus = useCallback(async (taskId, status) => {
    try {
      setLoading(true);
      setError(null);
      
      await apiClient.patch(`/tasks/${taskId}`, { status });
      
      // Refresh task list after updating task status
      if (fetchTasksRef.current) {
        await fetchTasksRef.current();
      }
      
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Error updating task status:', err);
      setLoading(false);
      setError(`Failed to update task status: ${err.message}`);
      throw err;
    }
  }, []);

  // Store updateTaskStatus in ref
  useEffect(() => {
    updateTaskStatusRef.current = updateTaskStatus;
  }, [updateTaskStatus]);

  // Function to directly refresh a task tree (for future use)
  // eslint-disable-next-line no-unused-vars
  const _refreshTaskTree = useCallback(async (taskId) => {
    try {
      if (!fetchTaskTreeRef.current) return;
      
      console.log(`Directly refreshing task tree for ${taskId}`);
      const updatedTree = await fetchTaskTreeRef.current(taskId);
      
      if (updatedTree) {
        console.log(`Got updated task tree for ${taskId}:`, updatedTree);
        
        // Force a re-render by creating a completely new object reference
        setTaskTree(prevTrees => {
          const newTrees = JSON.parse(JSON.stringify(prevTrees)); // Deep clone
          newTrees[taskId] = updatedTree;
          console.log(`Updated task tree state for ${taskId}`);
          return newTrees;
        });
      }
    } catch (err) {
      console.error(`Error refreshing task tree for ${taskId}:`, err);
    }
  }, []);
  
  // Initialize WebSocket hook with message handler
  const onMessageCallback = useCallback((data) => {
      try {
        console.log('WebSocket message received:', data);
        
        // Handle connection test messages
        if (data.type === 'connection_test' || data.type === 'connection_established') {
          return;
        }
        
        // Handle event history
        if (data.type === 'event_history' && Array.isArray(data.events)) {
          console.log(`Received event history with ${data.events.length} events for task ${data.task_id}`);
          
          // Process each event in the history
          data.events.forEach(event => {
            console.log(`Processing historical event: ${event.channel}`, event.data);
            
            // Create a synthetic message from the historical event
            const eventData = {
              ...event.data,
              type: event.channel,  // Use the channel as the message type
              timestamp: event.timestamp
            };
            
            // Process the event by calling this same callback recursively
            // but skip event_history to prevent infinite recursion
            if (eventData.type !== 'event_history') {
              onMessageCallback(eventData);
            }
          });
        }
        
        // Handle operator status updates
        else if (data.type === 'operator.status') {
          console.log(`Operator status update for task ${data.task_id}:`, data);
          
          // Update operator status in state
          setOperatorStatus(prev => ({
            ...prev,
            [data.operator_id]: {
              status: data.status,
              message: data.message,
              timestamp: data.timestamp,
              task_id: data.task_id
            }
          }));
          
          // If this is a completion message, check if the task is atomic
          if (data.status === 'completed' && data.task_id) {
            if (apiClient) {
              console.log(`Checking if task ${data.task_id} is atomic after operator completion`);
              apiClient.get(`/tasks/${data.task_id}`)
              .then(response => {
                const task = response.data;
                // If task is atomic and not completed, auto-complete it
                if (task && task.is_atomic && task.status !== 'completed') {
                  console.log(`Auto-completing atomic task ${data.task_id}`);
                  apiClient.patch(`/tasks/${data.task_id}`, { 
                    status: 'completed',
                    is_atomic: true // Ensure is_atomic is set
                  })
                    .then(() => {
                      console.log(`Task ${data.task_id} marked as completed`);
                      // Force refresh the task tree to reflect changes
                      if (getTaskRef.current) {
                        setTimeout(() => getTaskRef.current(data.task_id), 200);
                      }
                    })
                    .catch(err => console.error('Error auto-completing atomic task:', err));
                }
              }).catch(err => {
                console.error('Error checking if task is atomic:', err);
              });
            }
          }
        }
        // Handle task update messages
        else if (data.type && data.type.startsWith('task.')) {
          console.log(`Received ${data.type} event for task ${data.task_id}`, data);
          
          // Update current task if it matches
          if (currentTask && currentTask.id === data.task_id) {
            console.log(`Updating current task ${data.task_id} with new data`);
            setCurrentTask(prev => {
              const updatedTask = {
                ...prev,
                status: data.status || prev.status,
                is_atomic: data.is_atomic !== undefined ? data.is_atomic : prev.is_atomic
              };
              
              // If task is marked as completed, update UI immediately
              if (data.status === 'completed' && prev.status !== 'completed') {
                console.log(`Task ${data.task_id} marked as completed`);
              }
              
              // If task is marked as atomic, update UI immediately
              if (data.is_atomic && !prev.is_atomic) {
                console.log(`Task ${data.task_id} marked as atomic`);
              }
              
              return updatedTask;
            });
          }
          
          // Function to refresh task tree and its ancestors
          const refreshTaskAndAncestors = async (taskId) => {
            try {
              if (!getTaskRef.current) return;
              
              console.log(`Refreshing task tree for ${taskId}`);
              // First refresh this task's tree
              const updatedTask = await getTaskRef.current(taskId);
              
              // Update tasks in state if this task is loaded
              if (updatedTask) {
                setTasks(prevTasks => {
                  // Find and update the task in the tasks array
                  return prevTasks.map(task => {
                    if (task.id === taskId) {
                      return {
                        ...task,
                        status: updatedTask.status,
                        is_atomic: updatedTask.is_atomic,
                        predictions: updatedTask.predictions || task.predictions
                      };
                    }
                    return task;
                  });
                });
              }
              
              // Then refresh all ancestor tasks
              if (updatedTask && updatedTask.parent_id) {
                await refreshTaskAndAncestors(updatedTask.parent_id);
              }
            } catch (err) {
              console.error(`Error refreshing task ${taskId} and ancestors:`, err);
            }
          };
          
          // Always refresh task data regardless of whether it's the current task
          // This ensures we update the task list even if the user isn't viewing the task
          if (data.task_id) {
            console.log(`Refreshing task data for ${data.task_id} due to ${data.type} event`);
            // Use a small delay to ensure the backend has processed the update
            setTimeout(() => refreshTaskAndAncestors(data.task_id), 100);
          }
          
          // Refresh the main tasks list for any task event
          if (fetchTasksRef.current) {
            fetchTasksRef.current().catch(err => {
              console.error('Error refreshing tasks list after event:', err);
            });
          }
        }
      } catch (err) {
        console.error('Error handling WebSocket message:', err);
      }
  }, []);

  // Initialize WebSocket hook with a function to get the URL
  const { wsState, connect, disconnect } = useWebSocket(
    (taskId) => getWebSocketUrl(taskId), 
    onMessageCallback
  );

  // Debug WebSocket state changes
  useEffect(() => {
    console.log('WebSocket state changed:', wsState);
  }, [wsState]);

  // Connect to WebSocket ONLY when currentTaskId changes AND is valid
  useEffect(() => {
    // Only connect if we have a valid task ID (UUID format)
    const isValidTaskId = currentTaskId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(currentTaskId);
    
    if (isValidTaskId) {
      console.log('Connecting to WebSocket for task:', currentTaskId);
      connect(currentTaskId);
    } else {
      console.log('Not connecting WebSocket: No valid task ID');
      disconnect();
    }
    
    // Cleanup on unmount or when currentTaskId changes
    return () => {
      console.log('Cleaning up WebSocket connection');
      disconnect();
    };
  }, [currentTaskId]); // Remove connect/disconnect from dependencies to prevent render loop

  // Initial data fetch
  useEffect(() => {
    // Check if user is authenticated before fetching tasks
    const token = localStorage.getItem('token');
    if (token) {
      console.log('TaskContext: User authenticated, fetching initial tasks');
      fetchTasks().catch(err => {
        console.error('Error in initial tasks fetch:', err);
      });
    } else {
      console.log('TaskContext: No authentication token found, skipping initial task fetch');
    }
  }, []); // Remove fetchTasks from dependencies to prevent render loop

  // Create a task
  const createTask = useCallback(async (taskData) => {
    try {
      setLoading(true);
      setError(null);
      
      const newTask = await apiClient.post('/tasks', taskData);
      console.log('Task created successfully:', newTask);
      
      // Refresh task list after creating a new task
      fetchTasks();
      
      // Immediately fetch the task tree for the new task
      if (newTask && newTask.task_id) {
        try {
          console.log('Pre-fetching task tree for newly created task:', newTask.task_id);
          await fetchTaskTree(newTask.task_id);
        } catch (treeErr) {
          console.error('Failed to pre-fetch task tree, but continuing:', treeErr);
          // Don't rethrow - we still want to return the created task
        }
      }
      
      setLoading(false);
      return newTask;
    } catch (err) {
      console.error('Error creating task:', err);
      setLoading(false);
      setError(`Failed to create task: ${err.message}`);
      throw err;
    }
  }, [fetchTasks, fetchTaskTree]);

  // Delete a task
  const deleteTask = useCallback(async (taskId) => {
    try {
      setLoading(true);
      setError(null);
      
      await apiClient.delete(`/tasks/${taskId}`);
      
      // Refresh task list after deleting a task
      await fetchTasks();
      
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Error deleting task:', err);
      setLoading(false);
      setError(`Failed to delete task: ${err.message}`);
      throw err;
    }
  }, [fetchTasks]);

  return (
    <TaskContext.Provider
      value={{
        tasks,
        loading,
        error,
        currentTask,
        taskTree,
        operatorStatus,
        currentTaskId,
        fetchTasks,
        getTask,
        fetchTaskTree,
        createTask,
        deleteTask,
        updateTaskStatus,
        connectWebSocket: connect,
        disconnectWebSocket: disconnect,
        wsState,
        setError,
        setCurrentTaskId,
      }}
    >
      {children}
    </TaskContext.Provider>
  );
};

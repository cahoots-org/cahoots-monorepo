import React, { useState, useEffect, useRef, useCallback } from 'react';
import ApprovalReviewModal from './ApprovalReviewModal';
import apiClient from '../services/unifiedApiClient';
import { Card, tokens } from '../design-system';
import './PendingApprovalsPanel.css';

const PendingApprovalsPanel = ({ refreshTrigger = 0, parentTaskId }) => {
  console.log('DEBUG: PendingApprovalsPanel mounted with parentTaskId:', parentTaskId);
  const [pendingTasks, setPendingTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [processedTasks, setProcessedTasks] = useState(new Set());
  
  // WebSocket connection for real-time approval notifications
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [wsConnected, setWsConnected] = useState(false);
  const fetchTasksRef = useRef(null);

  // Get WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    
    // In production (HTTPS), don't include port in WebSocket URL
    if (window.location.protocol === 'https:') {
      return `${protocol}//${host}/ws/global`;
    }
    
    // In development, use the appropriate port
    const port = process.env.REACT_APP_API_URL ? 
      new URL(process.env.REACT_APP_API_URL).port || '8080' : 
      '8080';
    return `${protocol}//${host}:${port}/ws/global`;
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('Approval panel received WebSocket message:', data);
      
      // Check if this is a task.updated event with awaiting_approval status
      if (data.type === 'task.updated' && data.status === 'awaiting_approval') {
        console.log('Task requires approval, refreshing pending tasks list');
        // Refresh the pending tasks list using ref
        if (fetchTasksRef.current) {
          fetchTasksRef.current();
        }
      }
      
      // Also refresh if a task status changed from awaiting_approval (approved/rejected)
      if (data.type === 'task.updated' && 
          (data.status === 'approved' || data.status === 'rejected' || data.status === 'processing')) {
        console.log('Task approval status changed, refreshing pending tasks list');
        if (fetchTasksRef.current) {
          fetchTasksRef.current();
        }
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }, []);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      const wsUrl = getWebSocketUrl();
      console.log('Connecting to approval WebSocket:', wsUrl);
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('Approval WebSocket connected');
        setWsConnected(true);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
      
      wsRef.current.onmessage = handleWebSocketMessage;
      
      wsRef.current.onclose = (event) => {
        console.log('Approval WebSocket disconnected:', event.code, event.reason);
        setWsConnected(false);
        
        // Reconnect after a delay if not a normal closure
        if (event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect approval WebSocket...');
            connectWebSocket();
          }, 3000);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('Approval WebSocket error:', error);
        setWsConnected(false);
      };
    } catch (error) {
      console.error('Error creating approval WebSocket connection:', error);
    }
  }, [getWebSocketUrl, handleWebSocketMessage]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, []);

  // Connect WebSocket on mount
  useEffect(() => {
    connectWebSocket();
  }, [connectWebSocket]);

  const fetchPendingTasks = useCallback(async () => {
    try {
      setLoading(true);
      const url = parentTaskId 
        ? `/tasks/pending-approval?parent_task_id=${parentTaskId}`
        : '/tasks/pending-approval';
      console.log('DEBUG: PendingApprovalsPanel fetching from URL:', url);
      console.log('DEBUG: parentTaskId:', parentTaskId);
      const response = await apiClient.get(url);
      console.log('DEBUG: PendingApprovalsPanel response:', response);
      setPendingTasks(response.tasks || []);
      console.log('DEBUG: Set pending tasks:', response.tasks || []);
    } catch (error) {
      console.error('Error fetching pending approval tasks:', error);
      setPendingTasks([]);
    } finally {
      setLoading(false);
    }
  }, [parentTaskId]);

  // Store the function in ref for WebSocket handler
  useEffect(() => {
    fetchTasksRef.current = fetchPendingTasks;
  }, [fetchPendingTasks]);

  useEffect(() => {
    fetchPendingTasks();
  }, [refreshTrigger]);

  const handleReviewTask = (task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleApprove = async (taskId) => {
    try {
      await apiClient.post(`/tasks/${taskId}/approve`);
      setProcessedTasks(prev => new Set([...prev, taskId]));
      // Refresh the list after approval
      await fetchPendingTasks();
    } catch (error) {
      console.error('Error approving task:', error);
      throw error;
    }
  };

  const handleReject = async (taskId, rejectionData) => {
    try {
      await apiClient.post(`/tasks/${taskId}/reject`, rejectionData);
      setProcessedTasks(prev => new Set([...prev, taskId]));
      // Refresh the list after rejection
      await fetchPendingTasks();
    } catch (error) {
      console.error('Error rejecting task:', error);
      throw error;
    }
  };

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'Unknown';
    
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 60) {
        return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
      } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
      } else {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
      }
    } catch (error) {
      return 'Unknown';
    }
  };

  const truncateText = (text, maxLength = 150) => {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  const getComplexityColor = (score) => {
    if (score > 0.7) return 'high';
    if (score > 0.4) return 'medium';
    return 'low';
  };

  if (loading) {
    return (
      <div className="pending-approvals-loading">
        <div className="spinner"></div>
        <p>Loading pending approvals...</p>
      </div>
    );
  }

  if (pendingTasks.length === 0) {
    return null; // Hide the entire component when no approvals are needed
  }

  return (
    <Card style={{ marginBottom: tokens.spacing[6] }}>
      <div className="pending-approvals-panel" style={{ padding: tokens.spacing[4] }}>
        <div className="pending-approvals-header" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: tokens.spacing[3], 
          marginBottom: tokens.spacing[4] 
        }}>
          <h2 style={{ 
            margin: 0, 
            fontSize: tokens.typography.fontSize.lg[0], 
            fontWeight: tokens.typography.fontWeight.semibold, 
            color: tokens.colors.dark.text 
          }}>
            Pending Approvals
          </h2>
          <span style={{ 
            background: `${tokens.colors.error[500]}20`, 
            color: tokens.colors.error[500], 
            padding: '4px 8px', 
            borderRadius: tokens.borderRadius.xl, 
            fontSize: tokens.typography.fontSize.xs[0], 
            fontWeight: tokens.typography.fontWeight.semibold, 
            minWidth: '20px', 
            textAlign: 'center' 
          }}>
            {pendingTasks.length}
          </span>
          <button 
            style={{ 
              background: 'none', 
              border: `1px solid ${tokens.colors.dark.border}`, 
              color: tokens.colors.dark.muted, 
              padding: '4px 8px', 
              borderRadius: tokens.borderRadius.base, 
              cursor: 'pointer', 
              transition: tokens.transitions.colors,
              opacity: loading ? 0.5 : 1
            }}
            onClick={fetchPendingTasks}
            disabled={loading}
            title="Refresh pending approvals"
          >
            ↻
          </button>
        </div>

        <div className="pending-tasks-list" style={{ display: 'flex', flexDirection: 'column', gap: tokens.spacing[4] }}>
          {pendingTasks.map((decomposition) => (
            <div
              key={decomposition.task_id}
              style={{
                border: `1px solid ${tokens.colors.dark.border}`,
                borderRadius: tokens.borderRadius.lg,
                padding: tokens.spacing[4],
                backgroundColor: tokens.colors.dark.surface,
                opacity: processedTasks.has(decomposition.task_id) ? 0.6 : 1,
                transition: tokens.transitions.all
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: tokens.spacing[3] }}>
                <div style={{ display: 'flex', gap: tokens.spacing[2], flexWrap: 'wrap' }}>
                  <span style={{ 
                    background: `${tokens.colors.warning[500]}20`, 
                    color: tokens.colors.warning[500], 
                    padding: '4px 8px', 
                    borderRadius: tokens.borderRadius.base, 
                    fontSize: tokens.typography.fontSize.xs[0], 
                    fontWeight: tokens.typography.fontWeight.medium 
                  }}>
                    Decomposition Awaiting Approval
                  </span>
                  {decomposition.story_points > 0 && (
                    <span style={{ 
                      background: `${tokens.colors.info[500]}20`, 
                      color: tokens.colors.info[500], 
                      padding: '4px 8px', 
                      borderRadius: tokens.borderRadius.base, 
                      fontSize: tokens.typography.fontSize.xs[0], 
                      fontWeight: tokens.typography.fontWeight.medium 
                    }}>
                      {decomposition.story_points} points
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[1], color: tokens.colors.dark.muted, fontSize: tokens.typography.fontSize.xs[0] }}>
                  <span>🕒</span>
                  <span>{formatTimeAgo(decomposition.created_at)}</span>
                </div>
              </div>

              <div className="task-card-body">
                <div className="task-description-section">
                  <h4>Original Task:</h4>
                  <h5 style={{ color: '#FFFFFF', fontSize: '16px', margin: '4px 0' }}>
                    {decomposition.parent_task.title || 'Task'}
                  </h5>
                  <p style={{ color: '#A3A3A3' }}>
                    {truncateText(decomposition.parent_task.description)}
                  </p>
                </div>

                <div className="proposed-subtasks-section" style={{ marginTop: '16px' }}>
                  <h4 style={{ color: '#FFFFFF' }}>
                    Proposed Subtasks ({decomposition.proposed_subtasks.length}):
                  </h4>
                  <div className="subtasks-preview" style={{ marginTop: '8px' }}>
                    {decomposition.proposed_subtasks.slice(0, 3).map((subtask, index) => (
                      <div key={index} className="subtask-preview-item" style={{ 
                        display: 'flex', 
                        marginBottom: '6px',
                        color: '#A3A3A3',
                        fontSize: '14px'
                      }}>
                        <span style={{ color: '#FF8C1A', marginRight: '8px', fontWeight: 'bold' }}>
                          {index + 1}.
                        </span>
                        <span>
                          {truncateText(subtask.description || subtask.title || 'Untitled subtask', 80)}
                        </span>
                      </div>
                    ))}
                    {decomposition.proposed_subtasks.length > 3 && (
                      <div style={{ 
                        color: '#737373', 
                        fontSize: '12px', 
                        fontStyle: 'italic',
                        marginTop: '4px'
                      }}>
                        ... and {decomposition.proposed_subtasks.length - 3} more subtasks
                      </div>
                    )}
                  </div>
                </div>

                {decomposition.implementation_details && (
                  <div className="implementation-details-section" style={{ marginTop: '16px' }}>
                    <h4 style={{ color: '#FFFFFF' }}>Implementation Approach:</h4>
                    <p style={{ color: '#A3A3A3' }}>
                      {truncateText(decomposition.implementation_details)}
                    </p>
                  </div>
                )}

                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  marginTop: tokens.spacing[4], 
                  paddingTop: tokens.spacing[3], 
                  borderTop: `1px solid ${tokens.colors.dark.border}` 
                }}>
                  <span style={{ color: tokens.colors.dark.muted, fontSize: tokens.typography.fontSize.xs[0] }}>
                    ID: {decomposition.task_id.substring(0, 8)}...
                  </span>
                  <button
                    style={{
                      background: tokens.colors.primary[500],
                      color: tokens.colors.neutral[0],
                      border: 'none',
                      padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
                      borderRadius: tokens.borderRadius.base,
                      fontSize: tokens.typography.fontSize.sm[0],
                      fontWeight: tokens.typography.fontWeight.medium,
                      cursor: 'pointer',
                      transition: tokens.transitions.all,
                      opacity: processedTasks.has(decomposition.task_id) ? 0.5 : 1,
                      pointerEvents: processedTasks.has(decomposition.task_id) ? 'none' : 'auto'
                    }}
                    onClick={() => handleReviewTask(decomposition)}
                    disabled={processedTasks.has(decomposition.task_id)}
                    onMouseEnter={(e) => !processedTasks.has(decomposition.task_id) && (e.target.style.background = tokens.colors.primary[600])}
                    onMouseLeave={(e) => !processedTasks.has(decomposition.task_id) && (e.target.style.background = tokens.colors.primary[500])}
                    title="Review and approve/reject the proposed task decomposition"
                  >
                    👁 Review Decomposition
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <ApprovalReviewModal
        isOpen={isModalOpen}
        onClose={() => {
          setSelectedTask(null);
          setIsModalOpen(false);
        }}
        task={selectedTask}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </Card>
  );
};

export default PendingApprovalsPanel;
import React, { useState } from 'react';
import './ApprovalReviewModal.css';

const ApprovalReviewModal = ({ 
  isOpen, 
  onClose, 
  task, 
  onApprove, 
  onReject,
  isProcessing = false 
}) => {
  const [rejectionReason, setRejectionReason] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [includeNewDescription, setIncludeNewDescription] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(task.task_id);
      onClose();
    } catch (error) {
      console.error('Failed to approve task:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      alert('Please provide a reason for rejecting this task.');
      return;
    }

    if (includeNewDescription && !newDescription.trim()) {
      alert('Please provide a new description for resubmission or uncheck the option.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onReject(task.task_id, {
        reason: rejectionReason,
        new_description: includeNewDescription ? newDescription : null
      });
      onClose();
    } catch (error) {
      console.error('Failed to reject task:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setRejectionReason('');
    setNewDescription('');
    setIncludeNewDescription(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!task || !isOpen) return null;

  return (
    <div className="approval-modal-overlay">
      <div className="approval-modal-container">
        <div className="approval-modal-header">
          <h2>Decomposition Approval Review</h2>
          <span className="approval-status-badge">Awaiting Approval</span>
          <button 
            className="approval-modal-close"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            ×
          </button>
        </div>
        
        <div className="approval-modal-body">
          <div className="approval-section">
            <h3>Original Task:</h3>
            <div className="approval-task-description">
              <h4>{task.parent_task?.title || 'Task'}</h4>
              <p>{task.parent_task?.description || 'No description available'}</p>
            </div>
          </div>

          <div className="approval-section">
            <h3>Proposed Subtasks ({task.proposed_subtasks?.length || 0}):</h3>
            <div className="approval-subtasks-list">
              {task.proposed_subtasks?.map((subtask, index) => (
                <div key={index} className="subtask-item">
                  <div className="subtask-header">
                    <span className="subtask-number">{index + 1}.</span>
                    <h5 className="subtask-title">
                      {subtask.title || `Subtask ${index + 1}`}
                    </h5>
                  </div>
                  <div className="subtask-description">
                    {subtask.description || 'No description provided'}
                  </div>
                  {subtask.story_points && (
                    <div className="subtask-story-points">
                      Story Points: {subtask.story_points}
                    </div>
                  )}
                </div>
              )) || <p>No subtasks available</p>}
            </div>
          </div>

          {task.implementation_details && (
            <div className="approval-section">
              <h3>Implementation Approach:</h3>
              <div className="approval-implementation-details">
                {task.implementation_details}
              </div>
            </div>
          )}

          <div className="approval-section">
            <h3>Summary:</h3>
            <div className="approval-task-details">
              <div className="detail-row">
                <span className="detail-label">Task ID:</span>
                <span className="detail-value">{task.task_id}</span>
              </div>
              {task.story_points > 0 && (
                <div className="detail-row">
                  <span className="detail-label">Total Story Points:</span>
                  <span className="detail-value">{task.story_points}</span>
                </div>
              )}
              <div className="detail-row">
                <span className="detail-label">Number of Subtasks:</span>
                <span className="detail-value">{task.proposed_subtasks?.length || 0}</span>
              </div>
            </div>
          </div>

          <div className="approval-divider"></div>

          <div className="approval-instructions">
            <h3>Review Instructions</h3>
            <p>
              Please review this task carefully. You can approve it to continue decomposition, 
              or reject it with feedback. If rejecting, you can optionally provide a new 
              description to resubmit the task.
            </p>
          </div>

          <div className="approval-section">
            <label htmlFor="rejection-reason">Rejection Reason (if rejecting):</label>
            <textarea
              id="rejection-reason"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Explain why this task needs revision..."
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          <div className="approval-section">
            <label className="approval-checkbox">
              <input
                type="checkbox"
                checked={includeNewDescription}
                onChange={(e) => setIncludeNewDescription(e.target.checked)}
                disabled={isSubmitting}
              />
              Provide new description for resubmission
            </label>
            
            {includeNewDescription && (
              <div className="approval-new-description">
                <label htmlFor="new-description">New Task Description:</label>
                <textarea
                  id="new-description"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Enter the revised task description..."
                  rows={4}
                  disabled={isSubmitting}
                />
              </div>
            )}
          </div>

          <div className="approval-divider"></div>

          <div className="approval-actions">
            <button 
              className="approval-btn approval-btn-cancel" 
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              className="approval-btn approval-btn-reject"
              onClick={handleReject}
              disabled={isSubmitting || !rejectionReason.trim() || (includeNewDescription && !newDescription.trim())}
            >
              {isSubmitting ? 'Rejecting...' : 'Reject'}
            </button>
            <button
              className="approval-btn approval-btn-approve"
              onClick={handleApprove}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Approving...' : 'Approve'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApprovalReviewModal;
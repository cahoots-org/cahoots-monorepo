import React from 'react';
import { useModalStack } from '../contexts/ModalContext';

const BoardCard = ({ task, isProcessing = false, operatorProgress = null, onStatusChange }) => {
  // Use modal stack context
  const { pushModal } = useModalStack();
  
  // Handle click to open task modal
  const handleCardClick = () => {
    pushModal(task);
  };

  // Handle status change button click
  const handleStatusChange = (newStatus, e) => {
    e.stopPropagation(); // Prevent card click
    if (onStatusChange) {
      onStatusChange(task.task_id, newStatus);
    }
  };
  // Ecosystem icons based on complexity
  const getEcosystemIcon = (complexity) => {
    if (complexity >= 8) return '🌳'; // Tree for high complexity (stability needed)
    if (complexity >= 5) return '🍄'; // Mushroom for medium complexity (innovation)
    return '🌿'; // Vine for low complexity (simple linking)
  };

  // Complexity color
  const getComplexityColor = (complexity) => {
    if (complexity >= 8) return 'text-error-500';
    if (complexity >= 5) return 'text-warning-500';
    return 'text-success-500';
  };
  
  // Status badge
  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">✓ Completed</span>;
      case 'in_progress':
        return <span className="badge badge-warning">⏳ In Progress</span>;
      case 'failed':
        return <span className="badge badge-error">✗ Failed</span>;
      default:
        return <span className="badge badge-info">📋 Pending</span>;
    }
  };
  
  return (
    <div 
      className={`task-card group ${isProcessing ? 'border-brand-vibrant-blue border' : ''} ${isProcessing && !operatorProgress ? 'animate-pulse' : ''} cursor-pointer`}
      onClick={handleCardClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-xl">{getEcosystemIcon(task.complexity_score || 0)}</span>
          <h3 className="font-semibold text-brand-text group-hover:text-brand-vibrant-orange transition-colors duration-200">
            {task.description.split('\n')[0].substring(0, 60)}
            {task.description.split('\n')[0].length > 60 ? '...' : ''}
          </h3>
        </div>
        {getStatusBadge(task.status)}
      </div>

      <p className="text-secondary text-sm mb-4 line-clamp-2">
        {task.description}
      </p>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4 text-brand-muted-text" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
            </svg>
            <span className="text-xs text-brand-muted-text">
              {new Date(task.created_at).toLocaleDateString()}
            </span>
          </div>
          
          {task.complexity_score && (
            <div className="flex items-center space-x-1">
              <svg className="w-4 h-4 text-brand-muted-text" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <span className={`text-xs font-medium ${getComplexityColor(task.complexity_score)}`}>
                {task.complexity_score.toFixed(1)}
              </span>
            </div>
          )}
        </div>

        {task.is_atomic && (
          <div className="flex items-center space-x-1">
            <span className="text-xs text-brand-muted-text">🧩</span>
            <span className="text-xs text-brand-muted-text">
              Atomic
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`status-dot ${
            task.status === 'completed' ? 'status-success' :
            task.status === 'in_progress' ? 'status-warning' :
            task.status === 'failed' ? 'status-error' : 'status-info'
          }`}></div>
          <span className="text-xs text-brand-muted-text capitalize">
            {task.status?.replace('_', ' ') || 'pending'}
          </span>
        </div>

        {/* Status change buttons */}
        {onStatusChange && !isProcessing && (
          <div className="flex items-center space-x-1">
            {task.status !== 'completed' && (
              <button
                onClick={(e) => handleStatusChange('completed', e)}
                className="text-xs px-2 py-1 bg-success-500 text-white rounded hover:bg-success-600 transition-colors"
                title="Mark as completed"
              >
                ✓
              </button>
            )}
            {task.status !== 'in_progress' && task.status !== 'completed' && (
              <button
                onClick={(e) => handleStatusChange('in_progress', e)}
                className="text-xs px-2 py-1 bg-warning-500 text-white rounded hover:bg-warning-600 transition-colors"
                title="Mark as in progress"
              >
                ⏳
              </button>
            )}
          </div>
        )}

        {/* Processing indicator */}
        {isProcessing && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-brand-vibrant-blue font-medium">
              Processing {operatorProgress !== null && `(${Math.round(operatorProgress * 100)}%)`}
            </span>
          </div>
        )}
      </div>
      
      {/* Progress bar for tasks being processed */}
      {isProcessing && operatorProgress !== null && (
        <div className="mt-3">
          <div className="w-full h-1 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-brand-vibrant-blue transition-all duration-500 ease-in-out"
              style={{ width: `${Math.round(operatorProgress * 100)}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Mycelial network pattern overlay on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 pointer-events-none">
        <div className="w-full h-full bg-brand-vibrant-orange rounded-lg"></div>
      </div>
    </div>
  );
};

export default BoardCard;
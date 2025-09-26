import React from 'react';
import ExportModal from './ExportModal';

const TaskModalHeader = ({ 
  task,
  localTaskTree,
  modalStack,
  popModal,
  onClose,
  onShowToast
}) => {
  if (!task) return null;

  return (
    <div className="flex flex-col mb-4">
      {/* Breadcrumb navigation */}
      {modalStack.length > 1 && (
        <div className="flex items-center text-sm text-gray-500 mb-2 overflow-x-auto">
          {modalStack.slice(0, -1).map((stackTask, index) => (
            <div key={stackTask.task?.task_id || stackTask.task_id || index} className="flex items-center">
              <span 
                className="truncate max-w-xs hover:text-brand-vibrant-orange cursor-pointer"
                onClick={() => {
                  // Navigate back to this task in the stack
                  while (modalStack.length > index + 1) {
                    popModal();
                  }
                }}
              >
                {stackTask.task?.description ? stackTask.task.description.split('\n')[0].substring(0, 30) : 
                 stackTask.description ? stackTask.description.split('\n')[0].substring(0, 30) : 'Task'}
                {((stackTask.task?.description || stackTask.description) && 
                  (stackTask.task?.description || stackTask.description).split('\n')[0].length > 30) ? '...' : ''}
              </span>
              <svg className="w-4 h-4 mx-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          ))}
          <span className="font-medium text-brand-text truncate max-w-xs">
            {task?.description ? task.description.split('\n')[0].substring(0, 30) : 'Task'}
            {task?.description && task.description.split('\n')[0].length > 30 ? '...' : ''}
          </span>
        </div>
      )}
      
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-brand-text">
          Task Details
        </h2>
        <div className="flex items-center">
          {modalStack.length > 1 && (
            <button
              onClick={() => popModal()}
              className="mr-2 px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              Back
            </button>
          )}
          <ExportModal 
            task={task}
            localTaskTree={localTaskTree}
            onShowToast={onShowToast}
          />
          <button 
            onClick={() => onClose(false)} 
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TaskModalHeader;
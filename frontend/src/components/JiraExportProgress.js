import React, { useState, useEffect } from 'react';

const JiraExportProgress = ({ 
  isOpen, 
  onClose, 
  exportId,
  onSuccess,
  onError 
}) => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [currentMessage, setCurrentMessage] = useState('Initializing export...');
  const [isComplete, setIsComplete] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [resultData, setResultData] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    
    // If no exportId yet, wait for it
    if (!exportId) {
      setCurrentMessage('Initializing export...');
      return;
    }

    // Reset state when modal opens
    setProgress(0);
    setCurrentStep('');
    setCurrentMessage('Connecting to export service...');
    setIsComplete(false);
    setHasError(false);
    setErrorMessage('');
    setResultData(null);

    // Set up WebSocket connection for progress updates
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/jira-export/${exportId}`);

    ws.onopen = () => {
      console.log('WebSocket connected for JIRA export progress');
      setCurrentMessage('Connected to export service...');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        
        if (data.type === 'connection_established') {
          setCurrentMessage('Export service connected, starting export...');
        } else if (data.type === 'jira.export.progress') {
          const { step, progress: newProgress, message } = data.payload;
          
          setCurrentStep(step);
          setProgress(newProgress);
          setCurrentMessage(message);
          
          if (step === 'completion' && newProgress === 100) {
            setIsComplete(true);
          }
        } else if (data.type === 'jira.export.success') {
          setResultData(data.payload);
          setIsComplete(true);
          setProgress(100);
          setCurrentMessage('Export completed successfully!');
          
          if (onSuccess) {
            setTimeout(() => onSuccess(data.payload), 1000);
          }
        } else if (data.type === 'jira.export.error') {
          setHasError(true);
          setErrorMessage(data.payload.message || 'Export failed');
          
          if (onError) {
            onError(data.payload);
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setHasError(true);
      setErrorMessage('Connection error during export');
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };

    // Cleanup on unmount or when modal closes
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [isOpen, exportId, onSuccess, onError]);

  const getStepDescription = (step) => {
    switch (step) {
      case 'project_creation':
        return 'Creating JIRA Project';
      case 'issue_creation':
        return 'Creating Issues';
      case 'label_update':
        return 'Updating Labels';
      case 'completion':
        return 'Finalizing Export';
      default:
        return 'Processing';
    }
  };

  const getStepIcon = (step) => {
    if (hasError) return '❌';
    if (isComplete) return '✅';
    
    switch (step) {
      case 'project_creation':
        return '🏗️';
      case 'issue_creation':
        return '📋';
      case 'label_update':
        return '🏷️';
      case 'completion':
        return '🎉';
      default:
        return '⚙️';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-medium">JIRA Export Progress</h2>
            <span className="text-2xl">{getStepIcon(currentStep)}</span>
          </div>
        </div>
        
        {/* Body */}
        <div className="p-6">
          <div className="space-y-6">
            {hasError ? (
              <div className="p-4 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-md">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <span className="text-red-400">❌</span>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                      Export Failed
                    </h3>
                    <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                      {errorMessage}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Progress Bar */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {getStepDescription(currentStep)}
                    </span>
                    <span className="text-sm text-gray-500">
                      {progress}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div 
                      className={`h-3 rounded-full transition-all duration-300 ${
                        isComplete ? 'bg-green-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Current Status */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-md">
                  <div className="flex items-center space-x-3">
                    {!isComplete && !hasError && (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                    )}
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {currentMessage}
                    </span>
                  </div>
                </div>

                {/* Success Message */}
                {isComplete && resultData && (
                  <div className="p-4 bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-md">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <span className="text-green-400">✅</span>
                      </div>
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                          Export Completed!
                        </h3>
                        <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                          Created {resultData.issues_created} issues in project {resultData.project_key}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3">
              {isComplete && resultData?.project_url && (
                <a
                  href={resultData.project_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  Open JIRA Project
                </a>
              )}
              <button
                onClick={onClose}
                className={`px-4 py-2 text-sm rounded-md ${
                  isComplete || hasError
                    ? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-500 cursor-not-allowed'
                }`}
                disabled={!isComplete && !hasError}
              >
                {isComplete || hasError ? 'Close' : 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JiraExportProgress;
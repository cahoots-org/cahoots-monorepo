// Decomposition Status - Real-time feedback during task decomposition
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
  Card,
  Text,
  Badge,
  Progress,
  LoadingSpinner,
  CheckIcon,
  ClockIcon,
  CogIcon,
  ExclamationCircleIcon,
  tokens,
} from '../design-system';

const DecompositionStatus = ({ taskId, isDecomposing, onDecompositionComplete }) => {
  const { connected, subscribe } = useWebSocket();
  const [decompositionSteps, setDecompositionSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const stageLabels = {
    source: 'Source Processing',
    context_fetch: 'Context Analysis',
    complexity_scorer: 'Complexity Analysis',
    root_processor: 'Technical Planning',
    decomposer: 'Task Decomposition',
    composer: 'Final Composition'
  };

  const getProgressForStage = (stage) => {
    const stageProgress = {
      source: 10,
      context_fetch: 25,
      complexity_scorer: 40,
      root_processor: 55,
      decomposer: 75,
      composer: 90
    };
    return stageProgress[stage] || 0;
  };

  const handleDecompositionEvent = (event) => {
    switch (event.type) {
      // Handle real-time service status events
      case 'service.status':
        if (event.task_id === taskId) {
          const { stage, status, message, timestamp } = event;
          const stepTitle = stageLabels[stage] || stage;
          const stepId = `${stage}-${status}`;
          
          // Update current step and progress
          setCurrentStep(message);
          
          if (status === 'started') {
            setProgress(getProgressForStage(stage));
            // Add or update the step
            const existingStepIndex = decompositionSteps.findIndex(s => s.id.startsWith(stage));
            if (existingStepIndex >= 0) {
              updateStep(stepTitle, 'in_progress', message);
            } else {
              addStep(stepTitle, 'in_progress', message);
            }
          } else if (status === 'processing') {
            setCurrentStep(message);
            updateStepDescription(stepTitle, message);
          } else if (status === 'completed') {
            updateStep(stepTitle, 'completed', message);
            setProgress(getProgressForStage(stage) + 10);
          } else if (status === 'error') {
            updateStep(stepTitle, 'error', message);
            setError(message);
          }
        }
        break;

      // Handle task completion
      case 'task.updated':
        if (event.task_id === taskId && event.task?.status === 'completed') {
          setCurrentStep('Task processing completed successfully!');
          setProgress(100);
          setTimeout(() => {
            if (onDecompositionComplete) {
              onDecompositionComplete();
            }
          }, 2000);
        }
        break;
        
      // Handle task decomposition completed
      case 'task.decomposed':
        if (event.task_id === taskId) {
          setCurrentStep('Task decomposed into subtasks successfully!');
          setProgress(85);
        }
        break;

      // Handle event modeling started
      case 'event_modeling.started':
        if (event.task_id === taskId) {
          addStep('Event Model Generation', 'in_progress', 'Analyzing events, commands, and read models...');
          setCurrentStep('Generating event model...');
          setProgress(85);
        }
        break;

      // Handle event modeling completed
      case 'event_modeling.completed':
        if (event.task_id === taskId) {
          const { events, commands, read_models } = event.data || {};
          updateStep(
            'Event Model Generation',
            'completed',
            `Generated ${events || 0} events, ${commands || 0} commands, ${read_models || 0} read models`
          );
          setCurrentStep('Task processing completed successfully!');
          setProgress(100);
          setTimeout(() => {
            if (onDecompositionComplete) {
              onDecompositionComplete();
            }
          }, 2000);
        }
        break;

      default:
        break;
    }
  };

  useEffect(() => {
    if (taskId && connected) {
      const unsubscribe = subscribe((event) => {
        // Listen to events for this task or its subtasks
        if (event.task_id === taskId || event.task?.parent_id === taskId) {
          handleDecompositionEvent(event);
        }
      });

      return unsubscribe;
    }
  }, [taskId, connected, subscribe, handleDecompositionEvent]);

  // Fallback: If decomposing but no progress after 5 seconds, simulate progress
  useEffect(() => {
    if (isDecomposing && progress === 0 && decompositionSteps.length === 0) {
      const timer = setTimeout(() => {
        if (progress === 0) {
          setCurrentStep('AI is analyzing your task...');
          setProgress(15);
          addStep('Task Analysis', 'in_progress', 'Breaking down the task requirements');
        }
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [isDecomposing, progress, decompositionSteps.length]);

  const addStep = (title, status, description) => {
    setDecompositionSteps(prev => [...prev, {
      id: title.toLowerCase().replace(/\s+/g, '-'),
      title,
      status,
      description,
      timestamp: new Date().toLocaleTimeString(),
    }]);
  };

  const updateStep = (title, status, description) => {
    setDecompositionSteps(prev => 
      prev.map(step => 
        step.title === title 
          ? { ...step, status, description: description || step.description, timestamp: new Date().toLocaleTimeString() }
          : step
      )
    );
  };

  const updateStepDescription = (title, description) => {
    setDecompositionSteps(prev => 
      prev.map(step => 
        step.title === title 
          ? { ...step, description }
          : step
      )
    );
  };

  const getStepIcon = (status) => {
    switch (status) {
      case 'completed':
        return CheckIcon;
      case 'in_progress':
        return CogIcon;
      case 'error':
        return ExclamationCircleIcon;
      default:
        return ClockIcon;
    }
  };

  const getStepColor = (status) => {
    switch (status) {
      case 'completed':
        return tokens.colors.success[500];
      case 'in_progress':
        return tokens.colors.primary[500];
      case 'error':
        return tokens.colors.error[500];
      default:
        return tokens.colors.dark.muted;
    }
  };

  // Show component only if actively decomposing OR if there's an error
  // Hide the component if decomposition is complete (not decomposing and no error)
  if (!isDecomposing && !error) {
    return null;
  }

  // If decomposing but no steps yet, show waiting message
  // But don't show the waiting state if we're not actually decomposing (prevents showing after page refresh)
  const showWaitingState = isDecomposing && decompositionSteps.length === 0 && !currentStep;

  return (
    <Card>
      <div style={{ padding: tokens.spacing[1] }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: tokens.spacing[4],
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[3],
          }}>
            {isDecomposing && <LoadingSpinner size="sm" />}
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.semibold,
              color: tokens.colors.dark.text,
              margin: 0,
            }}>
              {isDecomposing ? 'Decomposing Task' : 'Decomposition Complete'}
            </Text>
          </div>
          
          <Badge variant={error ? 'danger' : isDecomposing ? 'info' : 'success'}>
            {error ? 'Failed' : isDecomposing ? 'Running' : 'Complete'}
          </Badge>
        </div>

        {/* Progress Bar */}
        <div style={{ marginBottom: tokens.spacing[4] }}>
          <Text style={{
            fontSize: tokens.typography.fontSize.sm[0],
            color: tokens.colors.dark.muted,
            margin: 0,
            marginBottom: tokens.spacing[2],
          }}>
            {showWaitingState ? 'Waiting for AI to start decomposition...' : currentStep}
          </Text>
          <Progress 
            value={showWaitingState ? 10 : progress}
            variant={showWaitingState ? 'info' : (error ? 'error' : 'primary')}
          />
          {showWaitingState && (
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
              marginTop: tokens.spacing[1],
              fontStyle: 'italic',
            }}>
              The AI is analyzing your task and will start creating subtasks shortly...
            </Text>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div style={{
            padding: tokens.spacing[3],
            backgroundColor: `${tokens.colors.error[500]}10`,
            border: `1px solid ${tokens.colors.error[500]}30`,
            borderRadius: tokens.borderRadius.md,
            marginBottom: tokens.spacing[4],
          }}>
            <Text style={{
              color: tokens.colors.error[500],
              fontSize: tokens.typography.fontSize.sm[0],
              margin: 0,
            }}>
              {error}
            </Text>
          </div>
        )}

        {/* Step List */}
        {decompositionSteps.length > 0 && (
          <div>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.semibold,
              color: tokens.colors.dark.text,
              margin: 0,
              marginBottom: tokens.spacing[3],
            }}>
              Process Steps
            </Text>
            
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: tokens.spacing[2],
            }}>
              {decompositionSteps.map((step, index) => {
                const StepIcon = getStepIcon(step.status);
                
                return (
                  <div
                    key={step.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: tokens.spacing[3],
                      backgroundColor: tokens.colors.dark.surface,
                      borderRadius: tokens.borderRadius.md,
                      border: `1px solid ${tokens.colors.dark.border}`,
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginRight: tokens.spacing[3],
                    }}>
                      {step.status === 'in_progress' ? (
                        <LoadingSpinner size="xs" />
                      ) : (
                        <StepIcon 
                          size={16} 
                          style={{ color: getStepColor(step.status) }} 
                        />
                      )}
                    </div>
                    
                    <div style={{ flex: 1 }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: tokens.spacing[1],
                      }}>
                        <Text style={{
                          fontSize: tokens.typography.fontSize.sm[0],
                          fontWeight: tokens.typography.fontWeight.medium,
                          color: tokens.colors.dark.text,
                          margin: 0,
                        }}>
                          {step.title}
                        </Text>
                        
                        <Text style={{
                          fontSize: tokens.typography.fontSize.xs[0],
                          color: tokens.colors.dark.muted,
                          margin: 0,
                        }}>
                          {step.timestamp}
                        </Text>
                      </div>
                      
                      <Text style={{
                        fontSize: tokens.typography.fontSize.xs[0],
                        color: tokens.colors.dark.muted,
                        margin: 0,
                      }}>
                        {step.description}
                      </Text>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

export default DecompositionStatus;
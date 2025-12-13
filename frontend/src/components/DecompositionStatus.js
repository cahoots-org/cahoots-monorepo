// Decomposition Status - Real-time feedback during task decomposition
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
  Card,
  Text,
  Badge,
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
  const [error, setError] = useState(null);

  // User-friendly stage labels with descriptions
  const stageLabels = {
    source: 'Reading Your Request',
    context_fetch: 'Understanding Context',
    complexity_scorer: 'Estimating Work',
    root_processor: 'Planning Architecture',
    decomposer: 'Creating Tasks',
    composer: 'Finalizing Plan'
  };

  useEffect(() => {
    if (taskId && connected) {
      const handleDecompositionEvent = (event) => {
        switch (event.type) {
          // Handle real-time service status events
          case 'service.status':
            if (event.task_id === taskId) {
              const { stage, status, message } = event;
              const stepTitle = stageLabels[stage] || stage;

              // Update current step
              setCurrentStep(message);

              if (status === 'started') {
                // Add or update the step
                setDecompositionSteps(prev => {
                  const existingStepIndex = prev.findIndex(s => s.id.startsWith(stage));
                  if (existingStepIndex >= 0) {
                    return prev.map(step =>
                      step.title === stepTitle
                        ? { ...step, status: 'in_progress', description: message || step.description, timestamp: new Date().toLocaleTimeString() }
                        : step
                    );
                  } else {
                    return [...prev, {
                      id: stepTitle.toLowerCase().replace(/\s+/g, '-'),
                      title: stepTitle,
                      status: 'in_progress',
                      description: message,
                      timestamp: new Date().toLocaleTimeString(),
                    }];
                  }
                });
              } else if (status === 'processing') {
                setCurrentStep(message);
                setDecompositionSteps(prev =>
                  prev.map(step =>
                    step.title === stepTitle
                      ? { ...step, description: message }
                      : step
                  )
                );
              } else if (status === 'completed') {
                setDecompositionSteps(prev =>
                  prev.map(step =>
                    step.title === stepTitle
                      ? { ...step, status: 'completed', description: message || step.description, timestamp: new Date().toLocaleTimeString() }
                      : step
                  )
                );
              } else if (status === 'error') {
                setDecompositionSteps(prev =>
                  prev.map(step =>
                    step.title === stepTitle
                      ? { ...step, status: 'error', description: message || step.description, timestamp: new Date().toLocaleTimeString() }
                      : step
                  )
                );
                setError(message);
              }
            }
            break;

          // Handle task decomposition completed
          case 'task.decomposed':
            if (event.task_id === taskId) {
              setCurrentStep('Task decomposed into subtasks successfully!');
            }
            break;

          // Handle event modeling started
          case 'event_modeling.started':
            if (event.task_id === taskId) {
              setDecompositionSteps(prev => [...prev, {
                id: 'designing-system-blueprint',
                title: 'Designing System Blueprint',
                status: 'in_progress',
                description: 'Mapping out how users will interact with your app...',
                timestamp: new Date().toLocaleTimeString(),
              }]);
              setCurrentStep('Creating your system blueprint...');
            }
            break;

          // Handle event modeling progress
          case 'event_modeling.progress':
            if (event.task_id === taskId) {
              const { events, commands, read_models } = event;
              const totalItems = (events || 0) + (commands || 0) + (read_models || 0);
              setDecompositionSteps(prev =>
                prev.map(step =>
                  step.title === 'Designing System Blueprint'
                    ? { ...step, status: 'in_progress', description: `Found ${totalItems} elements: ${commands || 0} user actions, ${read_models || 0} screens, ${events || 0} background processes...`, timestamp: new Date().toLocaleTimeString() }
                    : step
                )
              );
              setCurrentStep(`Discovered ${totalItems} features so far`);
            }
            break;

          // Handle event modeling completed
          case 'event_modeling.completed':
            if (event.task_id === taskId) {
              const { events, commands, read_models } = event;
              setDecompositionSteps(prev =>
                prev.map(step =>
                  step.title === 'Designing System Blueprint'
                    ? { ...step, status: 'completed', description: `Complete: ${commands || 0} user actions, ${read_models || 0} screens, ${events || 0} background processes`, timestamp: new Date().toLocaleTimeString() }
                    : step
                )
              );
              setCurrentStep('System blueprint complete! Wrapping up...');
              setTimeout(() => {
                if (onDecompositionComplete) {
                  onDecompositionComplete();
                }
              }, 2000);
            }
            break;

          // Handle task completion (final fallback)
          case 'task.updated':
            if (event.task_id === taskId && event.status === 'completed') {
              setCurrentStep('Task processing completed!');
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

      const unsubscribe = subscribe((event) => {
        // Listen to events for this task or its subtasks
        if (event.task_id === taskId || event.task?.parent_id === taskId) {
          handleDecompositionEvent(event);
        }
      });

      return unsubscribe;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, connected, subscribe, onDecompositionComplete]);

  // Fallback: If decomposing but no steps after 5 seconds, show initial step
  useEffect(() => {
    if (isDecomposing && decompositionSteps.length === 0 && !currentStep) {
      const timer = setTimeout(() => {
        if (decompositionSteps.length === 0) {
          setCurrentStep('AI is analyzing your task...');
          addStep('Task Analysis', 'in_progress', 'Breaking down the task requirements');
        }
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [isDecomposing, decompositionSteps.length, currentStep]);

  const addStep = (title, status, description) => {
    setDecompositionSteps(prev => [...prev, {
      id: title.toLowerCase().replace(/\s+/g, '-'),
      title,
      status,
      description,
      timestamp: new Date().toLocaleTimeString(),
    }]);
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
              {isDecomposing ? 'Building Your Project Plan' : 'Project Plan Ready'}
            </Text>
          </div>
          
          <Badge variant={error ? 'danger' : isDecomposing ? 'info' : 'success'}>
            {error ? 'Failed' : isDecomposing ? 'Running' : 'Complete'}
          </Badge>
        </div>

        {/* Current Status */}
        {currentStep && (
          <div style={{
            marginBottom: tokens.spacing[4],
            padding: tokens.spacing[3],
            backgroundColor: tokens.colors.dark.surface,
            borderRadius: tokens.borderRadius.md,
            border: `1px solid ${tokens.colors.dark.border}`,
          }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              color: tokens.colors.dark.text,
              margin: 0,
              fontWeight: tokens.typography.fontWeight.medium,
            }}>
              {currentStep}
            </Text>
            {showWaitingState && (
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                margin: 0,
                marginTop: tokens.spacing[2],
                fontStyle: 'italic',
              }}>
                We're reading through your requirements and will start building your plan shortly...
              </Text>
            )}
          </div>
        )}

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
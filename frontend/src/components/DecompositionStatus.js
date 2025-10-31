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

  const stageLabels = {
    source: 'Source Processing',
    context_fetch: 'Context Analysis',
    complexity_scorer: 'Complexity Analysis',
    root_processor: 'Technical Planning',
    decomposer: 'Task Decomposition',
    composer: 'Final Composition'
  };

  const handleDecompositionEvent = (event) => {
    switch (event.type) {
      // Handle real-time service status events
      case 'service.status':
        if (event.task_id === taskId) {
          const { stage, status, message, timestamp } = event;
          const stepTitle = stageLabels[stage] || stage;
          const stepId = `${stage}-${status}`;

          // Update current step
          setCurrentStep(message);

          if (status === 'started') {
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
          } else if (status === 'error') {
            updateStep(stepTitle, 'error', message);
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
          addStep('Event Model Generation', 'in_progress', 'Analyzing events, commands, and read models...');
          setCurrentStep('Generating event model...');
        }
        break;

      // Handle event modeling progress
      case 'event_modeling.progress':
        if (event.task_id === taskId) {
          const { events, commands, read_models, user_interactions, automations } = event;
          const totalItems = (events || 0) + (commands || 0) + (read_models || 0) + (user_interactions || 0) + (automations || 0);
          updateStep(
            'Event Model Generation',
            'in_progress',
            `Identified ${totalItems} elements (${events || 0} events, ${commands || 0} commands, ${read_models || 0} read models)...`
          );
          setCurrentStep(`Processing event model: ${totalItems} elements identified`);
        }
        break;

      // Handle event modeling completed
      case 'event_modeling.completed':
        if (event.task_id === taskId) {
          const { events, commands, read_models, user_interactions, automations } = event;
          updateStep(
            'Event Model Generation',
            'completed',
            `Generated ${events || 0} events, ${commands || 0} commands, ${read_models || 0} read models`
          );
          setCurrentStep('Event model complete! Finalizing...');
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
                The AI is analyzing your task and will start creating subtasks shortly...
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
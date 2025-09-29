import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, SparklesIcon, CodeBracketIcon } from '@heroicons/react/24/outline';
import Button from '../design-system/components/Button';
import { Heading1, Text } from '../design-system/components/Typography';
import Card from '../design-system/components/Card';
import { tokens } from '../design-system/tokens';
import { useCreateTask } from '../hooks/api/useTasks';
import { useApp } from '../contexts/AppContext';
import { getApplicationTypes, getTechStacksForType } from '../config/techStacks';

const CreateTask = () => {
  const navigate = useNavigate();
  const { showSuccess, showError } = useApp();
  const { mutate: createTask, isPending: isCreating } = useCreateTask();
  
  const [description, setDescription] = useState('');
  const [applicationType, setApplicationType] = useState('');
  const [techStackId, setTechStackId] = useState('');
  const [githubRepo, setGithubRepo] = useState('');

  const applicationTypes = getApplicationTypes();
  const availableTechStacks = applicationType ? getTechStacksForType(applicationType) : [];

  const handleSubmit = () => {
    console.log('handleSubmit called');
    console.log('Description:', description);
    console.log('isCreating:', isCreating);

    if (!description.trim()) {
      showError('Please enter a task description');
      return;
    }

    const taskData = {
      description: description.trim(),
      // Use sensible defaults - no user configuration needed
      max_depth: 4,
      max_subtasks: 7,
      complexity_threshold: 0.7,
      use_context: true,
      requires_approval: false,
      tech_preferences: {
        application_type: applicationType,
        tech_stack_id: techStackId,
        github_repo: githubRepo.trim(),
        additional_requirements: ''
      }
    };

    console.log('Calling createTask with data:', taskData);

    createTask(taskData, {
      onSuccess: (response) => {
        console.log('Create task response:', response);
        showSuccess('Task created successfully!');
        // Navigate to the created task's detail page
        // The response has the structure: { data: { task_id: "...", ... } }
        const taskId = response?.data?.task_id || response?.task_id;
        if (taskId) {
          navigate(`/tasks/${taskId}`);
        } else {
          console.warn('No task_id in response, navigating to dashboard', response);
          // Fallback to dashboard if no task_id
          navigate('/dashboard');
        }
      },
      onError: (error) => {
        console.error('Create task error:', error);
        showError(error?.userMessage || error?.message || 'Failed to create task');
      }
    });
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div style={{ 
      padding: tokens.spacing[6],
      maxWidth: '800px',
      margin: '0 auto'
    }}>
      {/* Header */}
      <header style={{ marginBottom: tokens.spacing[6] }}>
        <button
          onClick={() => navigate('/dashboard')}
          style={{ 
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: tokens.spacing[3],
            padding: '6px',
            background: 'transparent',
            border: 'none',
            color: tokens.colors.neutral[600],
            cursor: 'pointer',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = tokens.colors.primary[500];
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = tokens.colors.neutral[600];
          }}
          aria-label="Back to Dashboard"
        >
          <ArrowLeftIcon style={{ width: '18px', height: '18px' }} />
        </button>
        
        <div style={{ textAlign: 'center' }}>
          <Heading1 style={{ 
            margin: 0, 
            color: tokens.colors.primary[500],
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: tokens.spacing[3]
          }}>
            <SparklesIcon style={{ width: '40px', height: '40px' }} />
            Create New Task
          </Heading1>
          <Text style={{ 
            color: tokens.colors.neutral[500],
            marginTop: tokens.spacing[2],
          }}>
            Describe what you want to build and let AI handle the decomposition
          </Text>
        </div>
      </header>

      {/* Simple Form */}
      <Card style={{ padding: tokens.spacing[6] }}>
        {/* Task Description */}
        <div style={{ marginBottom: tokens.spacing[5] }}>
          <label style={{
            display: 'block',
            fontSize: '16px',
            fontWeight: '500',
            color: tokens.colors.neutral[700],
            marginBottom: tokens.spacing[2],
          }}>
            What would you like to build?
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="E.g., Build an e-commerce platform with product catalog, shopping cart, and payment processing"
            style={{
              width: '100%',
              minHeight: '120px',
              padding: tokens.spacing[3],
              borderRadius: tokens.borderRadius.lg,
              border: `1px solid ${tokens.colors.neutral[300]}`,
              backgroundColor: tokens.colors.neutral[0],
              color: tokens.colors.neutral[900],
              fontSize: '16px',
              fontFamily: tokens.typography.fontFamily.sans.join(', '),
              resize: 'vertical',
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = tokens.colors.primary[500];
            }}
            onBlur={(e) => {
              e.target.style.borderColor = tokens.colors.neutral[300];
            }}
            autoFocus
          />
        </div>

        {/* Tech Stack and GitHub Repo Row */}
        <div style={{ 
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: tokens.spacing[4],
          marginBottom: tokens.spacing[5]
        }}>
          {/* Application Type */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: tokens.colors.neutral[700],
              marginBottom: tokens.spacing[2],
            }}>
              Application Type (Optional)
            </label>
            <select
              value={applicationType}
              onChange={(e) => {
                setApplicationType(e.target.value);
                setTechStackId(''); // Reset tech stack when type changes
              }}
              style={{
                width: '100%',
                padding: tokens.spacing[2],
                borderRadius: tokens.borderRadius.md,
                border: `1px solid ${tokens.colors.neutral[300]}`,
                backgroundColor: tokens.colors.neutral[0],
                color: tokens.colors.neutral[900],
                fontSize: '14px',
                fontFamily: tokens.typography.fontFamily.sans.join(', '),
                outline: 'none',
                cursor: 'pointer',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => {
                e.target.style.borderColor = tokens.colors.primary[500];
              }}
              onBlur={(e) => {
                e.target.style.borderColor = tokens.colors.neutral[300];
              }}
            >
              <option value="">Select application type...</option>
              {applicationTypes.map(type => (
                <option key={type.id} value={type.id}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Tech Stack */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: tokens.colors.neutral[700],
              marginBottom: tokens.spacing[2],
            }}>
              Tech Stack (Optional)
            </label>
            <select
              value={techStackId}
              onChange={(e) => setTechStackId(e.target.value)}
              disabled={!applicationType}
              style={{
                width: '100%',
                padding: tokens.spacing[2],
                borderRadius: tokens.borderRadius.md,
                border: `1px solid ${tokens.colors.neutral[300]}`,
                backgroundColor: applicationType ? tokens.colors.neutral[0] : tokens.colors.neutral[100],
                color: tokens.colors.neutral[900],
                fontSize: '14px',
                fontFamily: tokens.typography.fontFamily.sans.join(', '),
                outline: 'none',
                cursor: applicationType ? 'pointer' : 'not-allowed',
                opacity: applicationType ? 1 : 0.6,
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => {
                if (applicationType) {
                  e.target.style.borderColor = tokens.colors.primary[500];
                }
              }}
              onBlur={(e) => {
                e.target.style.borderColor = tokens.colors.neutral[300];
              }}
            >
              <option value="">
                {applicationType ? 'Select tech stack...' : 'Select application type first'}
              </option>
              {availableTechStacks.map(stack => (
                <option key={stack.id} value={stack.id}>
                  {stack.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* GitHub Repository */}
        <div style={{ marginBottom: tokens.spacing[5] }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[2],
            fontSize: '14px',
            fontWeight: '500',
            color: tokens.colors.neutral[700],
            marginBottom: tokens.spacing[2],
          }}>
            <CodeBracketIcon style={{ width: '16px', height: '16px' }} />
            GitHub Repository (Optional)
          </label>
          <input
            type="text"
            value={githubRepo}
            onChange={(e) => setGithubRepo(e.target.value)}
            placeholder="e.g., https://github.com/username/repository"
            style={{
              width: '100%',
              padding: tokens.spacing[2],
              borderRadius: tokens.borderRadius.md,
              border: `1px solid ${tokens.colors.neutral[300]}`,
              backgroundColor: tokens.colors.neutral[0],
              color: tokens.colors.neutral[900],
              fontSize: '14px',
              fontFamily: tokens.typography.fontFamily.sans.join(', '),
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = tokens.colors.primary[500];
            }}
            onBlur={(e) => {
              e.target.style.borderColor = tokens.colors.neutral[300];
            }}
          />
        </div>

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: tokens.spacing[3],
          justifyContent: 'flex-end',
        }}>
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate('/dashboard')}
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleSubmit}
            disabled={!description.trim() || isCreating}
            icon={SparklesIcon}
          >
            {isCreating ? 'Creating...' : 'Create Task'}
          </Button>
        </div>

        <Text style={{
          fontSize: '13px',
          color: tokens.colors.neutral[500],
          marginTop: tokens.spacing[3],
          textAlign: 'center',
        }}>
          Tip: Press Ctrl+Enter to create task
        </Text>
      </Card>

      {/* Info Section */}
      <div style={{
        marginTop: tokens.spacing[6],
        padding: tokens.spacing[4],
        backgroundColor: tokens.colors.primary[50],
        borderRadius: tokens.borderRadius.lg,
        border: `1px solid ${tokens.colors.primary[200]}`,
      }}>
        <Text style={{
          fontSize: '14px',
          color: tokens.colors.primary[700],
          lineHeight: 1.6,
        }}>
          <strong>How it works:</strong> Our AI will automatically analyze your task and break it down into manageable subtasks. 
          The system intelligently determines the structure based on the complexity of your project.
        </Text>
      </div>
    </div>
  );
};

export default CreateTask;
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, SparklesIcon, CodeBracketIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import Button from '../design-system/components/Button';
import { Heading1, Text } from '../design-system/components/Typography';
import Card from '../design-system/components/Card';
import { tokens } from '../design-system/tokens';
import { useCreateTask } from '../hooks/api/useTasks';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/unifiedApiClient';

const CreateTask = () => {
  const navigate = useNavigate();
  const { showSuccess, showError } = useApp();
  const { mutate: createTask, isPending: isCreating } = useCreateTask();

  const [description, setDescription] = useState('');
  const [githubRepo, setGithubRepo] = useState('');
  const [isGitHubConnected, setIsGitHubConnected] = useState(false);
  const [checkingGitHub, setCheckingGitHub] = useState(true);

  // Check GitHub connection status on mount
  useEffect(() => {
    const checkGitHubStatus = async () => {
      try {
        const data = await apiClient.get('/github/status');
        setIsGitHubConnected(data?.connected || false);
      } catch (error) {
        console.error('Failed to check GitHub status:', error);
        setIsGitHubConnected(false);
      } finally {
        setCheckingGitHub(false);
      }
    };

    checkGitHubStatus();
  }, []);

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
      // Include GitHub repo URL if provided (backend expects github_repo_url at top level)
      ...(githubRepo.trim() && {
        github_repo_url: githubRepo.trim()
      })
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
          // Navigate to new ProjectView for better UX
          navigate(`/projects/${taskId}`);
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
            placeholder={
              !isGitHubConnected
                ? "Connect GitHub in Settings to enable this feature"
                : "e.g., https://github.com/username/repository"
            }
            disabled={!isGitHubConnected}
            style={{
              width: '100%',
              padding: tokens.spacing[2],
              borderRadius: tokens.borderRadius.md,
              border: `1px solid ${tokens.colors.neutral[300]}`,
              backgroundColor: !isGitHubConnected ? tokens.colors.neutral[100] : tokens.colors.neutral[0],
              color: !isGitHubConnected ? tokens.colors.neutral[400] : tokens.colors.neutral[900],
              fontSize: '14px',
              fontFamily: tokens.typography.fontFamily.sans.join(', '),
              outline: 'none',
              transition: 'border-color 0.2s, background-color 0.2s',
              cursor: !isGitHubConnected ? 'not-allowed' : 'text',
            }}
            onFocus={(e) => {
              if (isGitHubConnected) {
                e.target.style.borderColor = tokens.colors.primary[500];
              }
            }}
            onBlur={(e) => {
              e.target.style.borderColor = tokens.colors.neutral[300];
            }}
          />
          {!isGitHubConnected && !checkingGitHub && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: tokens.spacing[2],
              marginTop: tokens.spacing[2],
              padding: tokens.spacing[2],
              backgroundColor: tokens.colors.warning[50],
              border: `1px solid ${tokens.colors.warning[200]}`,
              borderRadius: tokens.borderRadius.md,
            }}>
              <InformationCircleIcon style={{
                width: '16px',
                height: '16px',
                color: tokens.colors.warning[600],
                flexShrink: 0,
              }} />
              <Text style={{
                fontSize: '12px',
                color: tokens.colors.warning[800],
              }}>
                To use GitHub repository context, please{' '}
                <button
                  onClick={() => navigate('/settings')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: tokens.colors.primary[600],
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    padding: 0,
                    font: 'inherit',
                  }}
                >
                  connect your GitHub account in Settings
                </button>
                .
              </Text>
            </div>
          )}
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
          <strong>How it works:</strong> Our AI will automatically analyze your task, select the best technology stack,
          and break it down into manageable subtasks. The system intelligently determines the structure and technologies
          based on your project requirements.
        </Text>
      </div>
    </div>
  );
};

export default CreateTask;
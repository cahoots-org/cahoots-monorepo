import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeftIcon, SparklesIcon, CodeBracketIcon, InformationCircleIcon, ChevronDownIcon, ChevronRightIcon, AdjustmentsHorizontalIcon, ChevronUpDownIcon, CheckIcon, XMarkIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import Button from '../design-system/components/Button';
import { Heading1, Text } from '../design-system/components/Typography';
import Card from '../design-system/components/Card';
import { tokens } from '../design-system/tokens';
// Removed useCreateTask - using direct API call for immediate navigation
import { useApp } from '../contexts/AppContext';
import { useSubscription } from '../contexts/SubscriptionContext';
import apiClient from '../services/unifiedApiClient';
import GranularitySelector from '../components/GranularitySelector';

const CreateTask = () => {
  const navigate = useNavigate();
  const { showError } = useApp();
  const { isPro, isEnterprise } = useSubscription();
  const canUseGitHub = isPro || isEnterprise;
  // Using direct API call instead of mutation for immediate navigation
  // const { mutate: createTask, isPending: isCreating } = useCreateTask();

  const [description, setDescription] = useState('');
  const [githubRepo, setGithubRepo] = useState('');
  const [isGitHubConnected, setIsGitHubConnected] = useState(false);
  const [checkingGitHub, setCheckingGitHub] = useState(true);
  const [granularity, setGranularity] = useState('medium');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Repository dropdown state
  const [repositories, setRepositories] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [showRepoDropdown, setShowRepoDropdown] = useState(false);
  const [repoSearchQuery, setRepoSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState(null);
  const dropdownRef = useRef(null);

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

  // Fetch repositories when GitHub is connected
  useEffect(() => {
    const fetchRepositories = async () => {
      if (!isGitHubConnected) return;

      setLoadingRepos(true);
      try {
        const repos = await apiClient.get('/github/user/repos');
        setRepositories(repos || []);
      } catch (error) {
        console.error('Failed to fetch repositories:', error);
        setRepositories([]);
      } finally {
        setLoadingRepos(false);
      }
    };

    fetchRepositories();
  }, [isGitHubConnected]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowRepoDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter repositories based on search
  const filteredRepos = repositories.filter(repo => {
    const searchLower = repoSearchQuery.toLowerCase();
    const fullName = repo.full_name || `${repo.owner}/${repo.name}`;
    return fullName.toLowerCase().includes(searchLower) ||
           (repo.description && repo.description.toLowerCase().includes(searchLower));
  });

  // Handle repository selection
  const handleSelectRepo = (repo) => {
    const repoUrl = repo.html_url || `https://github.com/${repo.full_name || `${repo.owner}/${repo.name}`}`;
    setGithubRepo(repoUrl);
    setSelectedRepo(repo);
    setShowRepoDropdown(false);
    setRepoSearchQuery('');
  };

  // Handle manual URL entry
  const handleManualUrlEntry = () => {
    if (repoSearchQuery.trim()) {
      setGithubRepo(repoSearchQuery.trim());
      setSelectedRepo(null);
      setShowRepoDropdown(false);
    }
  };

  // Clear repository selection
  const handleClearRepo = () => {
    setGithubRepo('');
    setSelectedRepo(null);
    setRepoSearchQuery('');
  };

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!description.trim()) {
      showError('Please enter a task description');
      return;
    }

    if (isSubmitting) return;
    setIsSubmitting(true);

    const taskData = {
      description: description.trim(),
      max_depth: 4,
      max_subtasks: 7,
      complexity_threshold: 0.7,
      use_context: true,
      requires_approval: false,
      granularity,
      ...(githubRepo.trim() && {
        github_repo_url: githubRepo.trim()
      })
    };

    try {
      // Make API call directly for immediate response
      const response = await apiClient.post('/tasks', taskData);

      const taskId = response?.data?.task_id
        || response?.task_id
        || response?.data?.id
        || response?.id;

      if (taskId) {
        // Navigate immediately to project view - processing happens in background
        navigate(`/projects/${taskId}`);
      } else {
        throw new Error('No task ID returned');
      }
    } catch (error) {
      console.error('Create task error:', error);
      // Handle Pydantic validation errors (422) which come as array of objects
      let errorMessage = 'Failed to create task';
      if (error?.userMessage) {
        if (Array.isArray(error.userMessage)) {
          // Extract message from validation error objects
          errorMessage = error.userMessage
            .map(e => e.msg || e.message || JSON.stringify(e))
            .join(', ');
        } else if (typeof error.userMessage === 'string') {
          errorMessage = error.userMessage;
        }
      } else if (error?.message) {
        errorMessage = error.message;
      }
      showError(errorMessage);
      setIsSubmitting(false);
    }
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
            {!canUseGitHub && (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontWeight: '500',
                color: tokens.colors.primary[600],
                backgroundColor: tokens.colors.primary[50],
                padding: '2px 8px',
                borderRadius: tokens.borderRadius.full,
              }}>
                <LockClosedIcon style={{ width: '10px', height: '10px' }} />
                Pro
              </span>
            )}
          </label>

          {/* Pro+ feature gate */}
          {!canUseGitHub ? (
            <div style={{
              padding: tokens.spacing[3],
              backgroundColor: tokens.colors.neutral[50],
              border: `1px solid ${tokens.colors.neutral[200]}`,
              borderRadius: tokens.borderRadius.md,
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: tokens.spacing[2],
                marginBottom: tokens.spacing[2],
              }}>
                <LockClosedIcon style={{
                  width: '16px',
                  height: '16px',
                  color: tokens.colors.neutral[400],
                }} />
                <Text style={{
                  fontSize: '14px',
                  color: tokens.colors.neutral[600],
                  margin: 0,
                }}>
                  GitHub integration is a Pro feature
                </Text>
              </div>
              <Text style={{
                fontSize: '13px',
                color: tokens.colors.neutral[500],
                margin: 0,
                marginBottom: tokens.spacing[2],
              }}>
                Upgrade to Pro to connect your GitHub repositories and use existing code as context for better task decomposition.
              </Text>
              <Link
                to="/pricing"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '13px',
                  fontWeight: '500',
                  color: tokens.colors.primary[600],
                  textDecoration: 'none',
                }}
              >
                Upgrade to Pro →
              </Link>
            </div>
          ) : selectedRepo || githubRepo ? (
            // Selected repository display
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: tokens.spacing[2],
              borderRadius: tokens.borderRadius.md,
              border: `1px solid ${tokens.colors.neutral[300]}`,
              backgroundColor: tokens.colors.neutral[50],
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
                <CodeBracketIcon style={{ width: '16px', height: '16px', color: tokens.colors.neutral[500] }} />
                <div>
                  <Text style={{
                    fontSize: '14px',
                    fontWeight: '500',
                    color: tokens.colors.neutral[800],
                    margin: 0,
                  }}>
                    {selectedRepo
                      ? (selectedRepo.full_name || `${selectedRepo.owner}/${selectedRepo.name}`)
                      : githubRepo.replace('https://github.com/', '')
                    }
                  </Text>
                  {selectedRepo?.description && (
                    <Text style={{
                      fontSize: '12px',
                      color: tokens.colors.neutral[500],
                      margin: 0,
                    }}>
                      {selectedRepo.description.substring(0, 60)}{selectedRepo.description.length > 60 ? '...' : ''}
                    </Text>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={handleClearRepo}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '4px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: tokens.colors.neutral[400],
                  borderRadius: tokens.borderRadius.sm,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = tokens.colors.neutral[600];
                  e.currentTarget.style.backgroundColor = tokens.colors.neutral[200];
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = tokens.colors.neutral[400];
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
                aria-label="Clear repository"
              >
                <XMarkIcon style={{ width: '16px', height: '16px' }} />
              </button>
            </div>
          ) : isGitHubConnected ? (
            // Repository dropdown/combobox
            <div ref={dropdownRef} style={{ position: 'relative' }}>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  value={repoSearchQuery}
                  onChange={(e) => setRepoSearchQuery(e.target.value)}
                  onFocus={() => setShowRepoDropdown(true)}
                  placeholder={loadingRepos ? "Loading repositories..." : "Search your repositories or enter a URL..."}
                  disabled={loadingRepos}
                  style={{
                    width: '100%',
                    padding: tokens.spacing[2],
                    paddingRight: '36px',
                    borderRadius: tokens.borderRadius.md,
                    border: `1px solid ${showRepoDropdown ? tokens.colors.primary[500] : tokens.colors.neutral[300]}`,
                    backgroundColor: tokens.colors.neutral[0],
                    color: tokens.colors.neutral[900],
                    fontSize: '14px',
                    fontFamily: tokens.typography.fontFamily.sans.join(', '),
                    outline: 'none',
                    transition: 'border-color 0.2s',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowRepoDropdown(!showRepoDropdown)}
                  style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                    color: tokens.colors.neutral[400],
                  }}
                  aria-label="Toggle dropdown"
                >
                  <ChevronUpDownIcon style={{ width: '16px', height: '16px' }} />
                </button>
              </div>

              {/* Dropdown menu */}
              {showRepoDropdown && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '4px',
                  maxHeight: '280px',
                  overflowY: 'auto',
                  backgroundColor: tokens.colors.neutral[0],
                  border: `1px solid ${tokens.colors.neutral[300]}`,
                  borderRadius: tokens.borderRadius.md,
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                  zIndex: 100,
                }}>
                  {/* Repository list */}
                  {filteredRepos.length > 0 ? (
                    filteredRepos.slice(0, 20).map((repo) => {
                      const fullName = repo.full_name || `${repo.owner}/${repo.name}`;
                      return (
                        <button
                          key={repo.id || fullName}
                          type="button"
                          onClick={() => handleSelectRepo(repo)}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: tokens.spacing[2],
                            width: '100%',
                            padding: tokens.spacing[2],
                            textAlign: 'left',
                            backgroundColor: 'transparent',
                            border: 'none',
                            borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
                            cursor: 'pointer',
                            transition: 'background-color 0.15s',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = tokens.colors.neutral[50];
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'transparent';
                          }}
                        >
                          <CodeBracketIcon style={{
                            width: '16px',
                            height: '16px',
                            color: tokens.colors.neutral[400],
                            marginTop: '2px',
                            flexShrink: 0,
                          }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <Text style={{
                              fontSize: '14px',
                              fontWeight: '500',
                              color: tokens.colors.neutral[800],
                              margin: 0,
                            }}>
                              {fullName}
                            </Text>
                            <div style={{ display: 'flex', gap: tokens.spacing[2], flexWrap: 'wrap' }}>
                              {repo.private && (
                                <Text style={{
                                  fontSize: '11px',
                                  color: tokens.colors.warning[600],
                                  margin: 0,
                                }}>
                                  Private
                                </Text>
                              )}
                              {repo.language && (
                                <Text style={{
                                  fontSize: '11px',
                                  color: tokens.colors.neutral[500],
                                  margin: 0,
                                }}>
                                  {repo.language}
                                </Text>
                              )}
                            </div>
                            {repo.description && (
                              <Text style={{
                                fontSize: '12px',
                                color: tokens.colors.neutral[500],
                                margin: 0,
                                marginTop: '2px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}>
                                {repo.description}
                              </Text>
                            )}
                          </div>
                        </button>
                      );
                    })
                  ) : repoSearchQuery && !loadingRepos ? (
                    <div style={{ padding: tokens.spacing[3], textAlign: 'center' }}>
                      <Text style={{ fontSize: '13px', color: tokens.colors.neutral[500], margin: 0 }}>
                        No matching repositories found
                      </Text>
                    </div>
                  ) : null}

                  {/* Use as URL option */}
                  {repoSearchQuery && repoSearchQuery.includes('/') && (
                    <button
                      type="button"
                      onClick={handleManualUrlEntry}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: tokens.spacing[2],
                        width: '100%',
                        padding: tokens.spacing[2],
                        textAlign: 'left',
                        backgroundColor: tokens.colors.primary[50],
                        border: 'none',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = tokens.colors.primary[100];
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = tokens.colors.primary[50];
                      }}
                    >
                      <CheckIcon style={{ width: '16px', height: '16px', color: tokens.colors.primary[600] }} />
                      <Text style={{
                        fontSize: '13px',
                        fontWeight: '500',
                        color: tokens.colors.primary[700],
                        margin: 0,
                      }}>
                        Use "{repoSearchQuery}" as repository URL
                      </Text>
                    </button>
                  )}

                  {/* Hint text */}
                  <div style={{
                    padding: tokens.spacing[2],
                    backgroundColor: tokens.colors.neutral[50],
                    borderTop: `1px solid ${tokens.colors.neutral[200]}`,
                  }}>
                    <Text style={{
                      fontSize: '11px',
                      color: tokens.colors.neutral[500],
                      margin: 0,
                    }}>
                      Type to search or enter a full GitHub URL
                    </Text>
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Not connected - show disabled input with message
            <input
              type="text"
              placeholder="Connect GitHub in Settings to enable this feature"
              disabled
              style={{
                width: '100%',
                padding: tokens.spacing[2],
                borderRadius: tokens.borderRadius.md,
                border: `1px solid ${tokens.colors.neutral[300]}`,
                backgroundColor: tokens.colors.neutral[100],
                color: tokens.colors.neutral[400],
                fontSize: '14px',
                fontFamily: tokens.typography.fontFamily.sans.join(', '),
                outline: 'none',
                cursor: 'not-allowed',
              }}
            />
          )}

          {/* GitHub not connected warning - only show for Pro+ users */}
          {canUseGitHub && !isGitHubConnected && !checkingGitHub && (
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

        {/* Advanced Options (Collapsible) */}
        <div style={{ marginBottom: tokens.spacing[5] }}>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: tokens.spacing[2],
              padding: `${tokens.spacing[2]} 0`,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              color: tokens.colors.neutral[600],
              width: '100%',
              textAlign: 'left',
            }}
          >
            {showAdvanced ? (
              <ChevronDownIcon style={{ width: '16px', height: '16px' }} />
            ) : (
              <ChevronRightIcon style={{ width: '16px', height: '16px' }} />
            )}
            <AdjustmentsHorizontalIcon style={{ width: '16px', height: '16px' }} />
            Advanced Options
          </button>

          {showAdvanced && (
            <div style={{
              marginTop: tokens.spacing[3],
              padding: tokens.spacing[4],
              backgroundColor: tokens.colors.neutral[50],
              borderRadius: tokens.borderRadius.lg,
              border: `1px solid ${tokens.colors.neutral[200]}`,
            }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: tokens.colors.neutral[700],
                marginBottom: tokens.spacing[3],
              }}>
                Task Granularity
              </label>
              <Text style={{
                fontSize: '13px',
                color: tokens.colors.neutral[500],
                marginBottom: tokens.spacing[3],
              }}>
                Control how tasks are sized based on your team's preferences
              </Text>
              <GranularitySelector
                value={granularity}
                onChange={setGranularity}
              />
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
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleSubmit}
            disabled={!description.trim() || isSubmitting}
            icon={SparklesIcon}
          >
            {isSubmitting ? 'Creating...' : 'Create Task'}
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
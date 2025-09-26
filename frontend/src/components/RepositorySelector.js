import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  Card,
  Button,
  Text,
  LoadingSpinner,
  Badge,
  tokens,
} from '../design-system';
import { FaGithub, FaLink } from 'react-icons/fa';
import apiClient from '../services/unifiedApiClient';

const RepositorySelector = ({ value, onChange }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const { isAuthenticated } = useAuth();

  // Check GitHub connection status
  useEffect(() => {
    const checkConnection = async () => {
      if (!isAuthenticated) return;
      
      try {
        const response = await apiClient.get('/github/status');
        setIsConnected(response.connected || false);
      } catch (error) {
        console.error('Failed to check GitHub connection:', error);
        setIsConnected(false);
      }
    };

    checkConnection();
  }, [isAuthenticated]);

  // Fetch repositories when connected
  useEffect(() => {
    const fetchRepos = async () => {
      if (!isConnected) return;
      
      setLoading(true);
      try {
        const response = await apiClient.get('/github/user/repos');
        setRepos(response || []);
      } catch (error) {
        console.error('Failed to fetch repositories:', error);
        setRepos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRepos();
  }, [isConnected]);

  // Filter repositories based on search
  const filteredRepos = repos.filter(repo => 
    repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleSelectRepo = (repo) => {
    onChange({
      type: 'github',
      url: repo.html_url || `https://github.com/${repo.full_name}`,  // Use html_url or construct it
      branch: repo.default_branch || 'main',
      name: repo.full_name
    });
    setShowDropdown(false);
    setSearchQuery('');
  };

  const handleCustomUrl = () => {
    if (customUrl) {
      onChange({
        type: 'custom',
        url: customUrl,
        branch: 'main',  // Default to main branch
        name: customUrl.split('/').slice(-2).join('/')
      });
      setShowCustomInput(false);
      setCustomUrl('');
    }
  };

  const handleClear = () => {
    onChange(null);
    setSearchQuery('');
    setCustomUrl('');
    setShowCustomInput(false);
  };

  // If user has no GitHub connection, show connection prompt
  if (!isConnected) {
    return (
      <div style={{
        padding: tokens.spacing[4],
        borderRadius: tokens.borderRadius.lg,
        backgroundColor: tokens.colors.warning[50],
        border: `1px solid ${tokens.colors.warning[200]}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3] }}>
          <FaGithub size={24} style={{ color: tokens.colors.warning[500] }} />
          <div style={{ flex: 1 }}>
            <Text weight="semibold">GitHub Not Connected</Text>
            <Text size="sm" style={{ color: tokens.colors.dark.muted, margin: 0 }}>
              Connect your GitHub account in Settings to select from your repositories, or enter a public repository URL.
            </Text>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => setShowCustomInput(true)}
          >
            <FaLink size={14} style={{ marginRight: tokens.spacing[1] }} />
            Use URL
          </Button>
        </div>

        {showCustomInput && (
          <div style={{ marginTop: tokens.spacing[3] }}>
            <input
              type="url"
              placeholder="https://github.com/owner/repository"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              style={{
                width: '100%',
                padding: tokens.spacing[2],
                border: `1px solid ${tokens.colors.dark.border}`,
                borderRadius: tokens.borderRadius.md,
                backgroundColor: tokens.colors.dark.bg,
                color: tokens.colors.dark.text,
                fontSize: tokens.typography.fontSize.sm[0],
              }}
            />
            <div style={{ 
              display: 'flex', 
              gap: tokens.spacing[2], 
              marginTop: tokens.spacing[2] 
            }}>
              <Button
                type="button"
                size="sm"
                variant="primary"
                onClick={handleCustomUrl}
                disabled={!customUrl}
              >
                Add Repository
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setShowCustomInput(false);
                  setCustomUrl('');
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // If value is already selected, show it
  if (value) {
    return (
      <div style={{
        padding: tokens.spacing[3],
        borderRadius: tokens.borderRadius.lg,
        backgroundColor: tokens.colors.dark.surface,
        border: `1px solid ${tokens.colors.dark.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
          <FaGithub size={18} />
          <div>
            <Text weight="medium" style={{ margin: 0 }}>
              {value.repo_name}
            </Text>
            {value.type === 'url' && (
              <Badge size="sm" variant="secondary">Public URL</Badge>
            )}
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={handleClear}
        >
          Change
        </Button>
      </div>
    );
  }

  // Repository selector
  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        display: 'flex',
        gap: tokens.spacing[2],
      }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            type="text"
            placeholder={loading ? "Loading repositories..." : "Search your repositories..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setShowDropdown(true)}
            disabled={loading}
            style={{
              width: '100%',
              padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
              paddingLeft: '36px',
              border: `1px solid ${tokens.colors.dark.border}`,
              borderRadius: tokens.borderRadius.md,
              backgroundColor: tokens.colors.dark.surface,
              color: tokens.colors.dark.text,
              fontSize: tokens.typography.fontSize.sm[0],
            }}
          />
          <FaGithub 
            size={16} 
            style={{ 
              position: 'absolute',
              left: tokens.spacing[3],
              top: '50%',
              transform: 'translateY(-50%)',
              color: tokens.colors.dark.muted,
            }} 
          />
          
          {/* Dropdown */}
          {showDropdown && !loading && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: tokens.spacing[1],
              maxHeight: '300px',
              overflowY: 'auto',
              backgroundColor: tokens.colors.dark.surface,
              border: `1px solid ${tokens.colors.dark.border}`,
              borderRadius: tokens.borderRadius.md,
              boxShadow: tokens.boxShadow.lg,
              zIndex: 100,
            }}>
              {filteredRepos.length > 0 ? (
                filteredRepos.map((repo) => (
                  <button
                    key={repo.id}
                    type="button"
                    onClick={() => handleSelectRepo(repo)}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: tokens.spacing[3],
                      textAlign: 'left',
                      backgroundColor: 'transparent',
                      border: 'none',
                      borderBottom: `1px solid ${tokens.colors.dark.border}`,
                      cursor: 'pointer',
                      transition: tokens.transitions.colors,
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = tokens.colors.dark.hover;
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
                      <div style={{ flex: 1 }}>
                        <Text weight="medium" style={{ margin: 0 }}>
                          {repo.name}
                        </Text>
                        <Text size="xs" style={{ 
                          color: tokens.colors.dark.muted, 
                          margin: 0 
                        }}>
                          {repo.owner} {repo.private && '• Private'} {repo.language && `• ${repo.language}`}
                        </Text>
                        {repo.description && (
                          <Text size="xs" style={{ 
                            color: tokens.colors.dark.muted,
                            margin: `${tokens.spacing[1]} 0 0 0`,
                          }}>
                            {repo.description}
                          </Text>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <div style={{ padding: tokens.spacing[4], textAlign: 'center' }}>
                  <Text size="sm" style={{ color: tokens.colors.dark.muted }}>
                    {searchQuery ? 'No matching repositories found' : 'No repositories found'}
                  </Text>
                </div>
              )}
              
              {/* Add custom URL option */}
              <button
                type="button"
                onClick={() => {
                  setShowDropdown(false);
                  setShowCustomInput(true);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: tokens.spacing[2],
                  width: '100%',
                  padding: tokens.spacing[3],
                  backgroundColor: tokens.colors.primary[50],
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <FaLink size={14} />
                <Text weight="medium" style={{ margin: 0 }}>
                  Use Public Repository URL
                </Text>
              </button>
            </div>
          )}
        </div>

        {loading && <LoadingSpinner size="sm" />}
      </div>

      {/* Custom URL input */}
      {showCustomInput && (
        <div style={{ marginTop: tokens.spacing[3] }}>
          <input
            type="url"
            placeholder="https://github.com/owner/repository"
            value={customUrl}
            onChange={(e) => setCustomUrl(e.target.value)}
            style={{
              width: '100%',
              padding: tokens.spacing[2],
              border: `1px solid ${tokens.colors.dark.border}`,
              borderRadius: tokens.borderRadius.md,
              backgroundColor: tokens.colors.dark.bg,
              color: tokens.colors.dark.text,
              fontSize: tokens.typography.fontSize.sm[0],
            }}
          />
          <div style={{ 
            display: 'flex', 
            gap: tokens.spacing[2], 
            marginTop: tokens.spacing[2] 
          }}>
            <Button
              type="button"
              size="sm"
              variant="primary"
              onClick={handleCustomUrl}
              disabled={!customUrl}
            >
              Add Repository
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => {
                setShowCustomInput(false);
                setCustomUrl('');
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 99,
          }}
          onClick={() => setShowDropdown(false)}
        />
      )}
    </div>
  );
};

export default RepositorySelector;
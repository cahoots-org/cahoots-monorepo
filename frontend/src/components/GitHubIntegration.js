import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../hooks/useNotification';
import {
  Card,
  Button,
  Text,
  LoadingSpinner,
  Modal,
  CheckIcon,
  ExclamationCircleIcon,
  tokens,
} from '../design-system';
import { FaGithub } from 'react-icons/fa';
import apiClient from '../services/unifiedApiClient';

const GitHubIntegration = () => {
  const [loading, setLoading] = useState(false);
  const [accessToken, setAccessToken] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [userData, setUserData] = useState(null);
  const { isAuthenticated } = useAuth();
  const { showNotification } = useNotification();

  // Check if user has a GitHub token stored
  const checkConnection = async () => {
    if (!isAuthenticated()) return;
    
    setLoading(true);
    try {
      const data = await apiClient.get('/github/status');
      if (data) {
        setIsConnected(data.connected || false);
        setUserData(data.user || null);
      } else {
        setIsConnected(false);
        setUserData(null);
      }
    } catch (error) {
      console.error('Failed to check GitHub connection:', error);
      setIsConnected(false);
      setUserData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  // Connect GitHub account
  const connectGitHub = async () => {
    if (!accessToken) {
      showNotification({
        type: 'error',
        message: 'Please enter your GitHub access token'
      });
      return;
    }

    setLoading(true);
    try {
      const data = await apiClient.post('/github/connect', {
        access_token: accessToken
      });
      
      showNotification({
        type: 'success',
        message: `Connected to GitHub as ${data.username || 'your account'}`
      });

      setIsConnected(true);
      setUserData(data.user || null);
      setAccessToken(''); // Clear the token from form
      setShowModal(false);
      
      // Also refresh connection status
      await checkConnection();
      
    } catch (error) {
      console.error('GitHub connect error:', error);
      showNotification({
        type: 'error',
        message: error.response?.data?.detail || error.userMessage || error.message || 'Failed to connect to GitHub'
      });
    } finally {
      setLoading(false);
    }
  };

  // Disconnect GitHub account
  const disconnectGitHub = async () => {
    if (!window.confirm('Are you sure you want to disconnect your GitHub account?')) {
      return;
    }

    setLoading(true);
    try {
      await apiClient.delete('/github/disconnect');

      showNotification({
        type: 'success',
        message: 'GitHub account disconnected'
      });

      setIsConnected(false);
      setUserData(null);
      
    } catch (error) {
      showNotification({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to disconnect GitHub account'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: tokens.spacing[4]
      }}>
        <div>
          <Text size="lg" weight="bold" style={{ marginBottom: tokens.spacing[1] }}>
            GitHub Integration
          </Text>
          <Text size="sm" style={{ color: tokens.colors.dark.muted }}>
            Connect your GitHub account to provide repository context during task creation
          </Text>
        </div>
        
        {!isConnected ? (
          <Button
            type="button"
            onClick={() => setShowModal(true)}
            disabled={!isAuthenticated() || loading}
            size="sm"
            style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}
          >
            <FaGithub />
            Connect
          </Button>
        ) : (
          <Button
            type="button"
            variant="secondary"
            onClick={disconnectGitHub}
            disabled={loading}
            size="sm"
          >
            Disconnect
          </Button>
        )}
      </div>

      {!isAuthenticated() && (
        <Card style={{
          backgroundColor: tokens.colors.warning[50],
          border: `1px solid ${tokens.colors.warning[200]}`,
          marginBottom: tokens.spacing[4]
        }}>
          <Text weight="semibold">Authentication Required</Text>
          <Text>Please log in to connect your GitHub account</Text>
        </Card>
      )}

      {loading && !isConnected ? (
        <div style={{ textAlign: 'center', padding: tokens.spacing[10] }}>
          <LoadingSpinner size="lg" />
          <Text style={{ marginTop: tokens.spacing[4] }}>Checking connection...</Text>
        </div>
      ) : isConnected && userData ? (
        <Card style={{
          backgroundColor: tokens.colors.success[50],
          border: `1px solid ${tokens.colors.success[200]}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3] }}>
            <CheckIcon size={24} style={{ color: tokens.colors.success[500] }} />
            <div>
              <Text weight="semibold">Connected to GitHub</Text>
              <Text size="sm" style={{ color: tokens.colors.dark.muted }}>
                Logged in as {userData.login || userData.username}
                {userData.public_repos && ` • ${userData.public_repos} public repositories`}
              </Text>
            </div>
          </div>
        </Card>
      ) : !isConnected ? (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3] }}>
            <ExclamationCircleIcon size={24} style={{ color: tokens.colors.warning[500] }} />
            <div>
              <Text weight="semibold">Not Connected</Text>
              <Text size="sm" style={{ color: tokens.colors.dark.muted }}>
                Connect your GitHub account to enable repository context in task creation
              </Text>
            </div>
          </div>
        </Card>
      ) : null}

      {/* Connect GitHub Modal */}
      <Modal 
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Connect GitHub Account"
      >
        <div style={{ marginBottom: tokens.spacing[4] }}>
          <Text weight="semibold" style={{ marginBottom: tokens.spacing[2] }}>
            Personal Access Token
          </Text>
          <input
            type="password"
            placeholder="ghp_..."
            value={accessToken}
            onChange={(e) => setAccessToken(e.target.value)}
            style={{
              width: '100%',
              padding: tokens.spacing[2],
              border: `1px solid ${tokens.colors.dark.border}`,
              borderRadius: tokens.borderRadius.md,
              backgroundColor: tokens.colors.dark.bg,
              color: tokens.colors.dark.text
            }}
          />
          <Text size="sm" style={{ 
            color: tokens.colors.dark.muted,
            marginTop: tokens.spacing[1]
          }}>
            Create a{' '}
            <a 
              href="https://github.com/settings/tokens/new?scopes=repo,read:user" 
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: tokens.colors.primary[500] }}
            >
              personal access token
            </a>{' '}
            with 'repo' and 'read:user' scopes.
          </Text>
        </div>

        <Card style={{ 
          backgroundColor: tokens.colors.info[50],
          border: `1px solid ${tokens.colors.info[200]}`,
          marginBottom: tokens.spacing[4]
        }}>
          <Text weight="semibold" size="sm">How it works</Text>
          <Text size="xs" style={{ marginTop: tokens.spacing[1] }}>
            Once connected, you'll be able to select any of your repositories when creating tasks.
            The system will analyze your selected repository to provide relevant context and patterns
            during task decomposition.
          </Text>
        </Card>

        <Card style={{ 
          backgroundColor: tokens.colors.warning[50],
          border: `1px solid ${tokens.colors.warning[200]}`,
          marginBottom: tokens.spacing[4]
        }}>
          <Text weight="semibold" size="sm">Security Note</Text>
          <Text size="xs" style={{ marginTop: tokens.spacing[1] }}>
            Your token is stored securely and only used to access repositories you explicitly select.
            We never modify your code or repositories.
          </Text>
        </Card>

        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end',
          gap: tokens.spacing[3]
        }}>
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowModal(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={connectGitHub}
            disabled={loading || !accessToken}
            style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}
          >
            {loading ? <LoadingSpinner size="sm" /> : <FaGithub />}
            Connect Account
          </Button>
        </div>
      </Modal>
    </Card>
  );
};

export default GitHubIntegration;
import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useSettings } from '../contexts/SettingsContext';
import apiClient from '../services/unifiedApiClient';
import { withErrorHandling } from '../services/errorHandler';
import { LoadingTypes } from '../services/loadingService';
import JiraExportProgress from './JiraExportProgress';
import TrelloExportProgress from './TrelloExportProgress';
import { Button, DocumentDuplicateIcon } from '../design-system';

// Constants for export functionality
const EXPORT_FILENAME_MAX_LENGTH = 30;
const BOARD_NAME_MAX_LENGTH = 30;

const ExportModal = ({ 
  task, 
  localTaskTree, 
  onShowToast 
}) => {
  const [isTrelloModalOpen, setIsTrelloModalOpen] = useState(false);
  const [isJiraModalOpen, setIsJiraModalOpen] = useState(false);
  const [isJiraProgressOpen, setIsJiraProgressOpen] = useState(false);
  const [isTrelloProgressOpen, setIsTrelloProgressOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [boardName, setBoardName] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [currentExportId, setCurrentExportId] = useState(null);
  const [currentTrelloExportId, setCurrentTrelloExportId] = useState(null);
  const [exportResult, setExportResult] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, right: 0 });
  const buttonRef = useRef(null);
  const [jiraConfig, setJiraConfig] = useState({
    projectName: '',
    projectKey: '',
    jiraUrl: '',
    apiToken: '',
    userEmail: '',
    accountId: '',
    users: [{ username: '', email: '' }]
  });
  const { settings } = useSettings();

  // Update dropdown position when opened
  useEffect(() => {
    if (isDropdownOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right
      });
    }
  }, [isDropdownOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isDropdownOpen && buttonRef.current && !buttonRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isDropdownOpen]);

  const onTrelloModalOpen = () => {
    // Pre-fill board name from task description
    if (task?.description) {
      setBoardName(`Cahoots: ${task.description.split('\n')[0].substring(0, BOARD_NAME_MAX_LENGTH)}`);
    }
    setIsTrelloModalOpen(true);
  };
  const onTrelloModalClose = () => setIsTrelloModalOpen(false);
  const onJiraModalOpen = () => {
    // Always show the modal for project configuration, but pre-fill credentials if available
    setJiraConfig({
      projectName: task?.description ? `Cahoots: ${task.description.split('\n')[0].substring(0, 30)}` : 'Cahoots Project',
      projectKey: 'CAHOOTS',
      jiraUrl: settings.jiraIntegration?.jiraUrl || 'https://your-domain.atlassian.net',
      apiToken: settings.jiraIntegration?.apiToken || '',
      userEmail: settings.jiraIntegration?.userEmail || '',
      accountId: settings.jiraIntegration?.accountId || '',
      users: [{ username: 'project-admin', email: settings.jiraIntegration?.userEmail || '' }]
    });
    setIsJiraModalOpen(true);
  };
  const onJiraModalClose = () => setIsJiraModalOpen(false);

  // Function to handle exporting to JSON
  const handleExportToJson = () => {
    if (!task) return;
    
    // Create a JSON file from the task tree
    const dataStr = JSON.stringify(localTaskTree, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    // Create a download link and trigger the download
    const exportFileDefaultName = `${task.description.split('\n')[0].substring(0, EXPORT_FILENAME_MAX_LENGTH)}-task-tree.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  // Function to handle exporting to JIRA via backend API
  const handleExportToJira = async () => {
    if (!task || !localTaskTree) return;
    
    setIsExporting(true);
    
    // Close config modal and open progress modal immediately  
    onJiraModalClose();
    setIsJiraProgressOpen(true);
    
    try {
      // Prepare the request payload
      const exportRequest = {
        config: {
          jira_url: jiraConfig.jiraUrl,
          user_email: jiraConfig.userEmail,
          api_token: jiraConfig.apiToken,
          account_id: jiraConfig.accountId,
          project_name: jiraConfig.projectName,
          project_key: jiraConfig.projectKey,
          users: jiraConfig.users
        },
        task_tree: localTaskTree
      };

      // Make request to start export and get export ID
      const response = await fetch('/api/jira/start-export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || 'dev-bypass-token'}`
        },
        body: JSON.stringify(exportRequest)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update the export ID with the real one from backend
      setCurrentExportId(result.export_id);
      
    } catch (error) {
      console.error('Error exporting to JIRA:', error);
      handleJiraExportError({ message: error.message });
    } finally {
      setIsExporting(false);
    }
  };

  // Handle successful JIRA export
  const handleJiraExportSuccess = (result) => {
    onShowToast(`Successfully created JIRA project with ${result.issues_created} issues`, 'success');
    
    // Open the project in a new tab
    if (result.project_url) {
      window.open(result.project_url, '_blank');
    }
    
    // Keep the progress modal open - user can close it manually
    // The progress modal will show completion status and allow manual closure
  };

  // Handle JIRA export error
  const handleJiraExportError = (error) => {
    onShowToast(`JIRA export failed: ${error.message || 'Unknown error'}`, 'error');
    setIsJiraProgressOpen(false);
    setCurrentExportId(null);
  };

  // Handle successful Trello export
  const handleTrelloExportSuccess = (result) => {
    onShowToast(`Successfully created Trello board with ${result.cards_created} cards`, 'success');
    
    // Open the board in a new tab
    if (result.board_url) {
      window.open(result.board_url, '_blank');
    }
    
    // Keep the progress modal open - user can close it manually
    // The progress modal will show completion status and allow manual closure
  };

  // Handle Trello export error
  const handleTrelloExportError = (error) => {
    onShowToast(`Trello export failed: ${error.message || 'Unknown error'}`, 'error');
    setIsTrelloProgressOpen(false);
    setCurrentTrelloExportId(null);
  };

  // Function to handle adding a new user to JIRA config
  const handleAddUser = () => {
    setJiraConfig(prev => ({
      ...prev,
      users: [...prev.users, { username: '', email: '' }]
    }));
  };

  // Function to handle removing a user from JIRA config
  const handleRemoveUser = (index) => {
    setJiraConfig(prev => ({
      ...prev,
      users: prev.users.filter((_, i) => i !== index)
    }));
  };

  // Function to handle updating user data
  const handleUpdateUser = (index, field, value) => {
    setJiraConfig(prev => ({
      ...prev,
      users: prev.users.map((user, i) => 
        i === index ? { ...user, [field]: value } : user
      )
    }));
  };

  // Function to validate email format
  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Function to validate project key format
  const isValidProjectKey = (key) => {
    // JIRA project key requirements: 2-10 uppercase alphanumeric characters
    const keyRegex = /^[A-Z0-9]{2,10}$/;
    return keyRegex.test(key);
  };

  // Function to validate JIRA configuration
  const validateJiraConfig = () => {
    if (!jiraConfig.projectName.trim()) {
      onShowToast('Project name is required', 'error');
      return false;
    }
    if (!jiraConfig.projectKey.trim()) {
      onShowToast('Project key is required', 'error');
      return false;
    }
    if (!isValidProjectKey(jiraConfig.projectKey)) {
      onShowToast('Project key must be 2-10 uppercase alphanumeric characters (e.g., PROJ, TEST123)', 'error');
      return false;
    }
    if (!jiraConfig.jiraUrl.trim()) {
      onShowToast('JIRA URL is required', 'error');
      return false;
    }
    if (!jiraConfig.userEmail.trim()) {
      onShowToast('Your email is required', 'error');
      return false;
    }
    if (!isValidEmail(jiraConfig.userEmail)) {
      onShowToast('Invalid email format', 'error');
      return false;
    }
    if (!jiraConfig.apiToken.trim()) {
      onShowToast('API token is required', 'error');
      return false;
    }
    if (!jiraConfig.accountId.trim()) {
      onShowToast('Account ID is required', 'error');
      return false;
    }
    
    // Validate URL format
    try {
      new URL(jiraConfig.jiraUrl);
    } catch {
      onShowToast('Invalid JIRA URL format', 'error');
      return false;
    }
    
    return true;
  };

  // Function to handle exporting to Trello
  const handleExportToTrello = async () => {
    if (!task || !localTaskTree) return;
    
    // Get Trello API key and token from settings
    const trelloApiKey = settings.trelloIntegration?.apiKey;
    const trelloToken = settings.trelloIntegration?.token;
    
    // Check if Trello credentials are available
    if (!trelloApiKey || !trelloToken) {
      onShowToast('Please add your Trello API key and token in the Settings page first.', 'warning');
      return;
    }
    
    // Validate board name
    if (!boardName.trim()) {
      onShowToast('Board name is required', 'error');
      return;
    }
    
    setIsExporting(true);
    
    // Close config modal and open progress modal immediately
    onTrelloModalClose();
    setIsTrelloProgressOpen(true);
    
    try {
      // Prepare the request payload
      const exportRequest = {
        config: {
          trello_api_key: trelloApiKey,
          trello_token: trelloToken,
          board_name: boardName || `Cahoots: ${task.description.substring(0, BOARD_NAME_MAX_LENGTH)}`
        },
        task_tree: localTaskTree
      };

      // Make request to start export and get export ID
      const response = await fetch('/api/trello/start-export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || 'dev-bypass-token'}`
        },
        body: JSON.stringify(exportRequest)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update the export ID with the real one from backend
      setCurrentTrelloExportId(result.export_id);
      
    } catch (error) {
      console.error('Error exporting to Trello:', error);
      handleTrelloExportError({ message: error.message });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      {/* Export Dropdown */}
      <div className="relative inline-block text-left" ref={buttonRef}>
        <Button
          variant="outline"
          size="sm"
          icon={DocumentDuplicateIcon}
          onClick={(e) => {
            e.preventDefault();
            setIsDropdownOpen(!isDropdownOpen);
          }}
          aria-expanded={isDropdownOpen}
          aria-haspopup="true"
        >
          Export
        </Button>
        {isDropdownOpen && createPortal(
          <div
            className="fixed w-56 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 focus:outline-none"
            style={{
              top: `${dropdownPosition.top}px`,
              right: `${dropdownPosition.right}px`,
              zIndex: 99999
            }}
            role="menu"
            aria-orientation="vertical"
            aria-labelledby="export-menu-button"
            tabIndex="-1"
          >
            <div className="py-1" role="none">
              <button
                className="text-gray-700 dark:text-gray-200 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600"
                role="menuitem"
                tabIndex="-1"
                onClick={() => {
                  handleExportToJson();
                  setIsDropdownOpen(false);
                }}
              >
                Export to JSON
              </button>
              <button
                className={`${!settings.jiraIntegration?.enabled ? 'opacity-50 cursor-not-allowed' : ''} text-gray-700 dark:text-gray-200 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600`}
                role="menuitem"
                tabIndex="-1"
                onClick={() => {
                  if (settings.jiraIntegration?.enabled) {
                    onJiraModalOpen();
                    setIsDropdownOpen(false);
                  }
                }}
                title={!settings.jiraIntegration?.enabled ? "Enable JIRA integration in Settings" : ""}
              >
                Export to JIRA
              </button>
              <button
                className={`${!settings.trelloIntegration?.enabled ? 'opacity-50 cursor-not-allowed' : ''} text-gray-700 dark:text-gray-200 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600`}
                role="menuitem"
                tabIndex="-1"
                onClick={() => {
                  if (settings.trelloIntegration?.enabled) {
                    onTrelloModalOpen();
                    setIsDropdownOpen(false);
                  }
                }}
                title={!settings.trelloIntegration?.enabled ? "Enable Trello integration in Settings" : ""}
              >
                Export to Trello
              </button>
            </div>
          </div>,
          document.body
        )}
      </div>

      {/* Export to Trello Modal */}
      {isTrelloModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-medium">Export to Trello</h2>
              <button onClick={onTrelloModalClose} className="text-gray-500 hover:text-gray-700">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Trello Connection Status */}
              {settings.trelloIntegration?.enabled && settings.trelloIntegration?.apiKey && 
               settings.trelloIntegration?.token ? (
                <div className="space-y-4">
                  <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">Trello Connection</h3>
                  <div className="p-3 bg-green-50 dark:bg-green-900 rounded-md">
                    <p className="text-sm text-green-800 dark:text-green-200">
                      <strong>✅ Using saved Trello credentials</strong><br/>
                      API Key: {settings.trelloIntegration.apiKey.substring(0, 8)}...<br/>
                      Token: {settings.trelloIntegration.token.substring(0, 8)}...
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900 rounded-md">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    <strong>⚠️ Trello credentials not configured</strong><br/>
                    Please add your Trello API key and token in the Settings page first.
                  </p>
                </div>
              )}
              
              {/* Board Name Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Board Name
                </label>
                <input
                  type="text"
                  value={boardName}
                  onChange={(e) => setBoardName(e.target.value)}
                  placeholder="Enter board name"
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  maxLength={BOARD_NAME_MAX_LENGTH}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Maximum {BOARD_NAME_MAX_LENGTH} characters
                </p>
              </div>
              
              {/* Export Details */}
              <div className="space-y-2">
                <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">What will be created:</h3>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>• Trello board with your specified name</li>
                  <li>• Lists for task organization (To Do, In Progress, Done)</li>
                  <li>• Cards for each task with descriptions and story points</li>
                  <li>• Labels for different task types and priorities</li>
                  <li>• Checklists for subtasks within parent cards</li>
                </ul>
              </div>
            </div>
            <div className="flex justify-end p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                className="px-4 py-2 mr-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                onClick={onTrelloModalClose}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleExportToTrello}
                disabled={isExporting || !boardName.trim() || !settings.trelloIntegration?.apiKey || !settings.trelloIntegration?.token}
              >
                {isExporting ? 'Creating Trello Board...' : 'Export to Trello'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export to JIRA Configuration Modal */}
      {isJiraModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-medium">Configure JIRA Export</h2>
              <button onClick={onJiraModalClose} className="text-gray-500 hover:text-gray-700">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* JIRA Connection */}
              {settings.jiraIntegration?.enabled && settings.jiraIntegration?.jiraUrl && 
               settings.jiraIntegration?.userEmail && settings.jiraIntegration?.apiToken && 
               settings.jiraIntegration?.accountId ? (
                <div className="space-y-4">
                  <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">JIRA Connection</h3>
                  <div className="p-3 bg-green-50 dark:bg-green-900 rounded-md">
                    <p className="text-sm text-green-800 dark:text-green-200">
                      <strong>Using saved JIRA credentials:</strong><br/>
                      URL: {settings.jiraIntegration.jiraUrl}<br/>
                      Email: {settings.jiraIntegration.userEmail}<br/>
                      Account ID: {settings.jiraIntegration.accountId}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">JIRA Connection</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        JIRA URL
                      </label>
                      <input
                        type="url"
                        value={jiraConfig.jiraUrl}
                        onChange={(e) => setJiraConfig(prev => ({ ...prev, jiraUrl: e.target.value }))}
                        placeholder="https://your-domain.atlassian.net"
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Your Email
                        </label>
                        <input
                          type="email"
                          value={jiraConfig.userEmail}
                          onChange={(e) => setJiraConfig(prev => ({ ...prev, userEmail: e.target.value }))}
                          placeholder="your.email@example.com"
                          className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          API Token
                        </label>
                        <input
                          type="password"
                          value={jiraConfig.apiToken}
                          onChange={(e) => setJiraConfig(prev => ({ ...prev, apiToken: e.target.value }))}
                          placeholder="Your JIRA API token"
                          className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Atlassian Account ID
                      </label>
                      <input
                        type="text"
                        value={jiraConfig.accountId}
                        onChange={(e) => setJiraConfig(prev => ({ ...prev, accountId: e.target.value }))}
                        placeholder="Your Atlassian account ID"
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Find your account ID at{' '}
                        <a href="https://id.atlassian.com/manage-profile/profile-and-visibility" target="_blank" rel="noopener noreferrer" className="underline">
                          Atlassian Account Settings
                        </a>
                        {' '}(usually starts with "5" and is 24 characters long)
                      </p>
                    </div>
                    
                    <div className="p-3 bg-blue-50 dark:bg-blue-900 rounded-md">
                      <p className="text-xs text-blue-800 dark:text-blue-200">
                        <strong>How to get your API token:</strong><br/>
                        1. Go to <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noopener noreferrer" className="underline">Atlassian Account Settings</a><br/>
                        2. Click "Create API token"<br/>
                        3. Copy the token and paste it above
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Project Configuration */}
              <div className="space-y-4">
                <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">Project Configuration</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Project Name
                    </label>
                    <input
                      type="text"
                      value={jiraConfig.projectName}
                      onChange={(e) => setJiraConfig(prev => ({ ...prev, projectName: e.target.value }))}
                      placeholder="Enter project name"
                      className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Project Key
                    </label>
                    <input
                      type="text"
                      value={jiraConfig.projectKey}
                      onChange={(e) => {
                        const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').substring(0, 10);
                        setJiraConfig(prev => ({ ...prev, projectKey: value }));
                      }}
                      placeholder="PROJ"
                      className={`w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                        jiraConfig.projectKey && !isValidProjectKey(jiraConfig.projectKey) 
                          ? 'border-red-500 dark:border-red-400' 
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                      maxLength="10"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      2-10 uppercase alphanumeric characters (e.g., PROJ, TEST123)
                    </p>
                    {jiraConfig.projectKey && !isValidProjectKey(jiraConfig.projectKey) && (
                      <p className="text-xs text-red-500 mt-1">
                        Invalid format: use only uppercase letters and numbers
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Export Details */}
              <div className="space-y-4">
                <h3 className="text-md font-medium text-gray-900 dark:text-gray-100">What will be created:</h3>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>• JIRA project with your specified name and key</li>
                  <li>• Epics for each non-atomic first-level subtask</li>
                  <li>• Stories for each atomic first-level subtask</li>
                  <li>• Sub-tasks for all child tasks, linked to their parents</li>
                  <li>• Story point estimates included in issue details</li>
                  <li>• Confluence pages for tech stack, best practices, and project standards</li>
                </ul>
              </div>
            </div>
            
            <div className="flex justify-end p-4 border-t border-gray-200 dark:border-gray-700 space-x-2">
              <button
                className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                onClick={onJiraModalClose}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={() => {
                  if (validateJiraConfig()) {
                    handleExportToJira();
                  }
                }}
                disabled={isExporting}
              >
                {isExporting ? 'Creating JIRA Project...' : 'Export to JIRA'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* JIRA Export Progress Modal */}
      <JiraExportProgress
        isOpen={isJiraProgressOpen}
        onClose={() => setIsJiraProgressOpen(false)}
        exportId={currentExportId}
        onSuccess={handleJiraExportSuccess}
        onError={handleJiraExportError}
      />

      {/* Trello Export Progress Modal */}
      <TrelloExportProgress
        isOpen={isTrelloProgressOpen}
        onClose={() => setIsTrelloProgressOpen(false)}
        exportId={currentTrelloExportId}
        onSuccess={handleTrelloExportSuccess}
        onError={handleTrelloExportError}
      />
    </>
  );
};

export default ExportModal;
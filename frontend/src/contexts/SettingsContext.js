import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import apiClient from '../services/unifiedApiClient';

const defaultSettings = {
  darkMode: false,
  notifications: true,
  trelloIntegration: {
    enabled: false,
    apiKey: '',
    token: ''
  },
  jiraIntegration: {
    enabled: false,
    jiraUrl: '',
    userEmail: '',
    apiToken: '',
    accountId: ''
  }
};

const SettingsContext = createContext({
  settings: defaultSettings,
  updateSettings: () => {},
  loadUserSettings: () => {},
  settingsLoaded: false,
});

export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState(defaultSettings);
  const [currentUserId, setCurrentUserId] = useState(null);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  // Load user-specific settings from backend
  const loadUserSettings = useCallback(async (userId) => {
    console.log('[SettingsContext] loadUserSettings called with userId:', userId);

    if (!userId) {
      // No user - use default settings
      console.log('[SettingsContext] No user, resetting to default settings');
      setSettings(defaultSettings);
      setCurrentUserId(null);
      setSettingsLoaded(false);
      return;
    }

    if (userId === currentUserId && settingsLoaded) {
      // Same user and settings already loaded, no need to reload
      console.log('[SettingsContext] Same user and settings loaded, no reload needed');
      return;
    }

    try {
      // Fetch settings from backend API
      console.log('[SettingsContext] Fetching settings from API for user:', userId);
      const response = await apiClient.get('/settings');

      if (response.data && response.data.data) {
        const backendSettings = response.data.data;
        console.log('[SettingsContext] Settings loaded from backend:', backendSettings);

        // Transform backend format to frontend format
        const transformedSettings = {
          darkMode: backendSettings.dark_mode || false,
          notifications: backendSettings.notifications !== undefined ? backendSettings.notifications : true,
          trelloIntegration: {
            enabled: backendSettings.trello_integration?.enabled || false,
            apiKey: backendSettings.trello_integration?.api_key || '',
            token: backendSettings.trello_integration?.token || ''
          },
          jiraIntegration: {
            enabled: backendSettings.jira_integration?.enabled || false,
            jiraUrl: backendSettings.jira_integration?.jira_url || '',
            userEmail: backendSettings.jira_integration?.user_email || '',
            apiToken: backendSettings.jira_integration?.api_token || '',
            accountId: backendSettings.jira_integration?.account_id || ''
          }
        };

        setSettings(transformedSettings);
        setCurrentUserId(userId);
        setSettingsLoaded(true);
      } else {
        // No settings in backend, use defaults
        console.log('[SettingsContext] No settings in backend, using defaults');
        setSettings(defaultSettings);
        setCurrentUserId(userId);
        setSettingsLoaded(true);
      }
    } catch (error) {
      console.error('[SettingsContext] Error loading settings from backend:', error);

      // Fallback to localStorage
      const userSettingsKey = `userSettings:${userId}`;
      const saved = localStorage.getItem(userSettingsKey);

      if (saved) {
        try {
          const parsedSettings = JSON.parse(saved);
          const mergedSettings = {
            ...defaultSettings,
            ...parsedSettings,
            trelloIntegration: {
              ...defaultSettings.trelloIntegration,
              ...parsedSettings.trelloIntegration
            },
            jiraIntegration: {
              ...defaultSettings.jiraIntegration,
              ...parsedSettings.jiraIntegration
            }
          };
          setSettings(mergedSettings);
        } catch (parseError) {
          console.error('[SettingsContext] Error parsing localStorage settings:', parseError);
          setSettings(defaultSettings);
        }
      } else {
        setSettings(defaultSettings);
      }

      setCurrentUserId(userId);
      setSettingsLoaded(true);
    }
  }, [currentUserId, settingsLoaded]);

  // Save settings when they change (only if we have a current user and settings are loaded)
  useEffect(() => {
    // Skip saving during initial load
    if (!currentUserId || !settingsLoaded) {
      console.log('[SettingsContext] Skipping save - no user or settings not loaded yet');
      return;
    }

    // Transform frontend format to backend format
    const backendSettings = {
      dark_mode: settings.darkMode,
      notifications: settings.notifications,
      trello_integration: {
        enabled: settings.trelloIntegration.enabled,
        api_key: settings.trelloIntegration.apiKey,
        token: settings.trelloIntegration.token
      },
      jira_integration: {
        enabled: settings.jiraIntegration.enabled,
        jira_url: settings.jiraIntegration.jiraUrl,
        user_email: settings.jiraIntegration.userEmail,
        api_token: settings.jiraIntegration.apiToken,
        account_id: settings.jiraIntegration.accountId
      }
    };

    console.log('[SettingsContext] Saving settings to backend:', backendSettings);

    // Save to backend API
    apiClient.put('/settings', backendSettings)
      .then(() => {
        console.log('[SettingsContext] Settings saved to backend successfully');

        // Also save to localStorage as backup
        const userSettingsKey = `userSettings:${currentUserId}`;
        localStorage.setItem(userSettingsKey, JSON.stringify(settings));
      })
      .catch((error) => {
        console.error('[SettingsContext] Failed to save settings to backend:', error);

        // Fallback: save to localStorage only
        const userSettingsKey = `userSettings:${currentUserId}`;
        localStorage.setItem(userSettingsKey, JSON.stringify(settings));
      });
  }, [settings, currentUserId, settingsLoaded]);

  const updateSettings = useCallback((newSettings) => {
    console.log('[SettingsContext] updateSettings called with:', newSettings);
    setSettings(newSettings);
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, loadUserSettings, settingsLoaded }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => useContext(SettingsContext);

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

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

  // Load user-specific settings
  const loadUserSettings = useCallback((userId) => {
    console.log('[SettingsContext] loadUserSettings called with userId:', userId, 'currentUserId:', currentUserId, 'settingsLoaded:', settingsLoaded);
    
    if (!userId) {
      // No user - use default settings
      console.log('[SettingsContext] No user, resetting to default settings');
      setSettings(defaultSettings);
      setCurrentUserId(null);
      setSettingsLoaded(true);
      return;
    }

    if (userId === currentUserId && settingsLoaded) {
      // Same user and settings already loaded, no need to reload
      console.log('[SettingsContext] Same user and settings loaded, no reload needed');
      return;
    }

    const userSettingsKey = `userSettings:${userId}`;
    const saved = localStorage.getItem(userSettingsKey);
    console.log('[SettingsContext] Loading settings for key:', userSettingsKey);
    console.log('[SettingsContext] Saved settings:', saved);
    
    if (saved) {
      try {
        const parsedSettings = JSON.parse(saved);
        console.log('[SettingsContext] Parsed settings:', parsedSettings);
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
        console.log('[SettingsContext] Merged settings:', mergedSettings);
        setSettings(mergedSettings);
      } catch (error) {
        console.error('[SettingsContext] Error parsing user settings:', error);
        setSettings(defaultSettings);
      }
    } else {
      // First time user - use default settings
      console.log('[SettingsContext] No saved settings, using defaults');
      setSettings(defaultSettings);
    }
    
    setCurrentUserId(userId);
    setSettingsLoaded(true);
  }, [currentUserId, settingsLoaded]);

  // Save settings when they change (only if we have a current user)
  useEffect(() => {
    if (currentUserId) {
      const userSettingsKey = `userSettings:${currentUserId}`;
      console.log('[SettingsContext] Saving settings to key:', userSettingsKey);
      console.log('[SettingsContext] Settings being saved:', settings);
      localStorage.setItem(userSettingsKey, JSON.stringify(settings));
      
      // Handle email notifications preference change
      if (settings.notifications !== undefined) {
        console.log(`[SettingsContext] Email notifications preference changed for user ${currentUserId}:`, settings.notifications ? 'enabled' : 'disabled');
        
        // Here you could integrate with a backend API to update user preferences
        // For now, we'll just log the change and store it locally
        
        // Future integration example:
        // apiClient.updateUserPreferences({ emailNotifications: settings.notifications });
      }
    } else {
      console.log('[SettingsContext] No currentUserId, not saving settings');
    }
  }, [settings, currentUserId]);

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

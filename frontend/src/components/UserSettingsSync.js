import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';

/**
 * Component that syncs user authentication state with settings context
 * This bridges the AuthContext and SettingsContext to enable user-specific settings
 */
export const UserSettingsSync = () => {
  const { user, loading } = useAuth();
  const { loadUserSettings } = useSettings();
  const location = useLocation();

  // Sync settings whenever user, loading state, or location changes
  useEffect(() => {
    
    // Only sync after auth has finished loading
    if (loading) {
      // Auth still loading, waiting...
      return;
    }

    // Auth loaded, syncing settings
    
    // Load settings for the current user (or reset to defaults if no user)
    loadUserSettings(user?.id || null);
  }, [user?.id, loading, loadUserSettings, location.pathname, user]);

  // This component doesn't render anything
  return null;
};
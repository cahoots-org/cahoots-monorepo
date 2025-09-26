import React, { createContext, useContext, useEffect } from 'react';
import { useSettings } from './SettingsContext';
import { useAuth } from './AuthContext';
import { tokens } from '../design-system/tokens';

const ThemeContext = createContext();

// Light theme color overrides
const lightTheme = {
  bg: '#FFFFFF',
  surface: '#F8F9FA',
  border: '#D1D5DB',  // More visible border for light theme
  text: '#111827',
  muted: '#6B7280',
  body: '#374151',
};

// Dark theme (default from tokens)
const darkTheme = {
  bg: tokens.colors.dark.bg,
  surface: tokens.colors.dark.surface,
  border: tokens.colors.dark.border,
  text: tokens.colors.dark.text,
  muted: tokens.colors.dark.muted,
  body: tokens.colors.dark.text,
};

export const ThemeProvider = ({ children }) => {
  const { settings, settingsLoaded } = useSettings();
  const { isAuthenticated, loading } = useAuth();
  
  // For unauthenticated users, always use light mode
  // Wait for both auth and settings to finish loading before applying theme
  const shouldUseDarkMode = !loading && settingsLoaded && isAuthenticated() && settings.darkMode;

  useEffect(() => {
    // Apply theme to CSS custom properties
    const theme = shouldUseDarkMode ? darkTheme : lightTheme;
    const root = document.documentElement;

    // Update CSS custom properties
    root.style.setProperty('--color-bg', theme.bg);
    root.style.setProperty('--color-surface', theme.surface);
    root.style.setProperty('--color-border', theme.border);
    root.style.setProperty('--color-text', theme.text);
    root.style.setProperty('--color-text-muted', theme.muted);
    root.style.setProperty('--color-text-body', theme.body);

    // Update body background
    document.body.style.backgroundColor = theme.bg;
    document.body.style.color = theme.text;

    // Add/remove dark theme class
    if (shouldUseDarkMode) {
      document.documentElement.classList.add('dark-theme');
      document.documentElement.classList.remove('light-theme');
    } else {
      document.documentElement.classList.add('light-theme');
      document.documentElement.classList.remove('dark-theme');
    }
  }, [shouldUseDarkMode]);

  const contextValue = {
    isDark: shouldUseDarkMode,
    theme: shouldUseDarkMode ? darkTheme : lightTheme,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
// Redesigned Settings - Professional replacement using design system
import React, { useState } from 'react';
import { useSettings } from '../contexts/SettingsContext';
import { useAuth } from '../contexts/AuthContext';
import { useApp } from '../contexts/AppContext';
import { useNavigate } from 'react-router-dom';
import { useNotification } from '../hooks/useNotification';
import {
  Card,
  Button,
  Text,
  Heading1,
  Badge,
  Modal,
  CogIcon,
  CheckIcon,
  ExclamationCircleIcon,
  ArrowRightIcon,
  CreditCardIcon,
  tokens,
} from '../design-system';
import apiClient from '../services/unifiedApiClient';
import GitHubIntegration from '../components/GitHubIntegration';
import { useSubscription } from '../contexts/SubscriptionContext';

const Settings = () => {
  const { settings, updateSettings } = useSettings();
  const { logout, user } = useAuth();
  const { subscription, openBillingPortal, isPro, isEnterprise, isFree, loading: billingLoading } = useSubscription();
  const { setGlobalLoading } = useApp();
  const { showNotification } = useNotification();
  const navigate = useNavigate();
  
  // Local state
  const [localSettings, setLocalSettings] = useState(settings);
  const [isSaving, setIsSaving] = useState(false);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [activeSection, setActiveSection] = useState('general');

  const handleChange = (section, field, value) => {
    if (section === 'trelloIntegration' || section === 'jiraIntegration') {
      setLocalSettings((prev) => ({
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      }));
    } else {
      setLocalSettings((prev) => ({
        ...prev,
        [field]: value
      }));
      
      // Show immediate feedback for general settings changes and update settings context
      if (field === 'darkMode') {
        showNotification(value ? 'Dark mode enabled' : 'Light mode enabled', 'success');
        // Apply dark mode change immediately
        const updatedSettings = { ...localSettings, [field]: value };
        updateSettings(updatedSettings);
      } else if (field === 'notifications') {
        showNotification(value ? 'Email notifications enabled' : 'Email notifications disabled', 'success');
        // Apply notification preference immediately
        const updatedSettings = { ...localSettings, [field]: value };
        updateSettings(updatedSettings);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    
    try {
      // Save Trello credentials if enabled
      if (localSettings.trelloIntegration.enabled && 
          localSettings.trelloIntegration.apiKey && 
          localSettings.trelloIntegration.token) {
        await apiClient.post('/trello/credentials', {
          api_key: localSettings.trelloIntegration.apiKey,
          token: localSettings.trelloIntegration.token
        });
      }

      // Save JIRA credentials if enabled
      if (localSettings.jiraIntegration.enabled && 
          localSettings.jiraIntegration.jiraUrl && 
          localSettings.jiraIntegration.userEmail &&
          localSettings.jiraIntegration.apiToken &&
          localSettings.jiraIntegration.accountId) {
        await apiClient.post('/jira/credentials', {
          jira_url: localSettings.jiraIntegration.jiraUrl,
          user_email: localSettings.jiraIntegration.userEmail,
          api_token: localSettings.jiraIntegration.apiToken,
          account_id: localSettings.jiraIntegration.accountId
        });
      }
      
      updateSettings(localSettings);
      showNotification('Settings saved successfully!', 'success');
    } catch (error) {
      console.error('Failed to save settings:', error);
      showNotification('Failed to save settings. Please try again.', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    setGlobalLoading(true);
    try {
      await logout();
      navigate('/');
    } catch (error) {
      showNotification('Logout failed. Please try again.', 'error');
    } finally {
      setGlobalLoading(false);
      setShowLogoutModal(false);
    }
  };

  const sections = [
    { id: 'general', label: 'General', icon: CogIcon },
    { id: 'billing', label: 'Billing', icon: CreditCardIcon },
    { id: 'integrations', label: 'Integrations', icon: ArrowRightIcon },
    { id: 'account', label: 'Account', icon: user?.id ? CheckIcon : ExclamationCircleIcon },
  ];

  return (
    <div className="container" style={{ paddingTop: tokens.spacing[6] }}>
      {/* Header */}
      <div style={{ marginBottom: tokens.spacing[8] }}>
        <Heading1 style={{
          fontSize: tokens.typography.fontSize['3xl'][0],
          lineHeight: tokens.typography.lineHeight.tight,
          fontWeight: tokens.typography.fontWeight.bold,
          marginBottom: tokens.spacing[2],
          color: tokens.colors.primary[500],
        }}>
          Settings
        </Heading1>
        
        <Text style={{ 
          color: tokens.colors.dark.muted,
          fontSize: tokens.typography.fontSize.lg[0],
          margin: 0,
        }}>
          Manage your preferences and integrations
        </Text>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: tokens.spacing[6],
        alignItems: 'flex-start',
      }}
      className="settings-layout"
      >
        {/* Sidebar Navigation */}
        <Card style={{
          position: 'sticky',
          top: tokens.spacing[6],
        }}>
          <div style={{ padding: tokens.spacing[4] }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.semibold,
              color: tokens.colors.dark.muted,
              textTransform: 'uppercase',
              letterSpacing: tokens.typography.letterSpacing.wide,
              margin: 0,
              marginBottom: tokens.spacing[4],
            }}>
              Settings
            </Text>
            
            <nav>
              {sections.map(section => {
                const isActive = activeSection === section.id;
                const Icon = section.icon;
                
                return (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: tokens.spacing[3],
                      width: '100%',
                      padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
                      border: 'none',
                      borderRadius: tokens.borderRadius.md,
                      background: isActive ? tokens.colors.primary[500] : 'transparent',
                      color: isActive ? tokens.colors.neutral[0] : tokens.colors.dark.text,
                      cursor: 'pointer',
                      transition: tokens.transitions.colors,
                      fontSize: tokens.typography.fontSize.sm[0],
                      fontWeight: tokens.typography.fontWeight.medium,
                      textAlign: 'left',
                      marginBottom: tokens.spacing[1],
                    }}
                  >
                    <Icon size={18} />
                    {section.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </Card>

        {/* Main Content */}
        <div>
          <form onSubmit={handleSubmit}>
            {/* General Settings */}
            {activeSection === 'general' && (
              <Card title="General Preferences">
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: tokens.spacing[6],
                }}>
                  <ToggleField
                    label="Dark Mode"
                    description="Use dark theme throughout the application"
                    checked={localSettings.darkMode}
                    onChange={(checked) => handleChange('general', 'darkMode', checked)}
                  />
                  
                </div>
              </Card>
            )}

            {/* Billing */}
            {activeSection === 'billing' && (
              <Card title="Subscription & Billing">
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: tokens.spacing[6],
                }}>
                  {/* Current Plan */}
                  <div>
                    <Text style={{
                      fontSize: tokens.typography.fontSize.sm[0],
                      fontWeight: tokens.typography.fontWeight.semibold,
                      color: tokens.colors.dark.text,
                      margin: 0,
                      marginBottom: tokens.spacing[2],
                    }}>
                      Current Plan
                    </Text>

                    <div style={{
                      padding: tokens.spacing[4],
                      backgroundColor: tokens.colors.dark.surface,
                      borderRadius: tokens.borderRadius.md,
                      border: `1px solid ${tokens.colors.dark.border}`,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2], marginBottom: tokens.spacing[1] }}>
                          <Text style={{
                            fontSize: tokens.typography.fontSize.lg[0],
                            fontWeight: tokens.typography.fontWeight.bold,
                            color: tokens.colors.dark.text,
                            margin: 0,
                          }}>
                            {isEnterprise ? 'Enterprise' : isPro ? 'Pro' : 'Free'}
                          </Text>
                          {(isPro || isEnterprise) && (
                            <Badge variant="success" size="sm">Active</Badge>
                          )}
                        </div>
                        <Text style={{
                          fontSize: tokens.typography.fontSize.sm[0],
                          color: tokens.colors.dark.muted,
                          margin: 0,
                        }}>
                          {isEnterprise
                            ? 'Full access to all features including SSO and priority support'
                            : isPro
                            ? 'Code generation, GitHub integration, and exports'
                            : 'Task decomposition and event modeling'}
                        </Text>
                      </div>
                      {isFree && (
                        <Button
                          variant="primary"
                          onClick={() => navigate('/pricing')}
                        >
                          Upgrade
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Billing Management - Only for Pro users */}
                  {(isPro || isEnterprise) && subscription?.stripe_subscription_id && (
                    <div>
                      <Text style={{
                        fontSize: tokens.typography.fontSize.sm[0],
                        fontWeight: tokens.typography.fontWeight.semibold,
                        color: tokens.colors.dark.text,
                        margin: 0,
                        marginBottom: tokens.spacing[2],
                      }}>
                        Billing Management
                      </Text>

                      <div style={{
                        padding: tokens.spacing[4],
                        backgroundColor: tokens.colors.dark.surface,
                        borderRadius: tokens.borderRadius.md,
                        border: `1px solid ${tokens.colors.dark.border}`,
                      }}>
                        <Text style={{
                          fontSize: tokens.typography.fontSize.sm[0],
                          color: tokens.colors.dark.muted,
                          margin: 0,
                          marginBottom: tokens.spacing[3],
                        }}>
                          Manage your subscription, update payment methods, and view invoices.
                        </Text>
                        <Button
                          variant="secondary"
                          onClick={() => openBillingPortal()}
                          disabled={billingLoading}
                        >
                          {billingLoading ? 'Loading...' : 'Manage Subscription'}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Feature Comparison - For Free users */}
                  {isFree && (
                    <div>
                      <Text style={{
                        fontSize: tokens.typography.fontSize.sm[0],
                        fontWeight: tokens.typography.fontWeight.semibold,
                        color: tokens.colors.dark.text,
                        margin: 0,
                        marginBottom: tokens.spacing[2],
                      }}>
                        Upgrade to Pro for More Features
                      </Text>

                      <div style={{
                        padding: tokens.spacing[4],
                        backgroundColor: `${tokens.colors.primary[500]}10`,
                        borderRadius: tokens.borderRadius.md,
                        border: `1px solid ${tokens.colors.primary[500]}30`,
                      }}>
                        <ul style={{
                          margin: 0,
                          padding: 0,
                          paddingLeft: tokens.spacing[4],
                          color: tokens.colors.dark.text,
                        }}>
                          <li style={{ marginBottom: tokens.spacing[2] }}>Code Generation from Event Models</li>
                          <li style={{ marginBottom: tokens.spacing[2] }}>GitHub Integration</li>
                          <li style={{ marginBottom: tokens.spacing[2] }}>Export to JSON, Markdown, YAML</li>
                        </ul>
                        <div style={{ marginTop: tokens.spacing[4] }}>
                          <Button
                            variant="primary"
                            onClick={() => navigate('/pricing')}
                          >
                            View Pricing
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Integrations */}
            {activeSection === 'integrations' && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: tokens.spacing[6],
              }}>
                {/* GitHub Integration */}
                <GitHubIntegration />
                
                {/* Trello Integration */}
                <IntegrationCard
                  title="Trello Integration"
                  description="Export tasks as Trello boards and cards"
                  enabled={localSettings.trelloIntegration.enabled}
                  onToggle={(enabled) => handleChange('trelloIntegration', 'enabled', enabled)}
                  badge={localSettings.trelloIntegration.enabled ? 'Connected' : 'Available'}
                  badgeVariant={localSettings.trelloIntegration.enabled ? 'success' : 'secondary'}
                >
                  {localSettings.trelloIntegration.enabled && (
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: tokens.spacing[4],
                      marginTop: tokens.spacing[4],
                    }}>
                      <InputField
                        label="Trello API Key"
                        value={localSettings.trelloIntegration.apiKey}
                        onChange={(value) => handleChange('trelloIntegration', 'apiKey', value)}
                        placeholder="Enter your Trello API Key"
                        helpText={
                          <a 
                            href="https://trello.com/app-key" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: tokens.colors.primary[500], 
                              textDecoration: 'none' 
                            }}
                          >
                            Get your API key from Trello →
                          </a>
                        }
                      />
                      
                      <InputField
                        label="Trello Token"
                        type="password"
                        value={localSettings.trelloIntegration.token}
                        onChange={(value) => handleChange('trelloIntegration', 'token', value)}
                        placeholder="Enter your Trello Token"
                        helpText="Generate a token from the same API key page"
                      />
                    </div>
                  )}
                </IntegrationCard>

                {/* JIRA Integration */}
                <IntegrationCard
                  title="JIRA Integration"
                  description="Export tasks as JIRA projects and issues"
                  enabled={localSettings.jiraIntegration?.enabled || false}
                  onToggle={(enabled) => handleChange('jiraIntegration', 'enabled', enabled)}
                  badge={localSettings.jiraIntegration?.enabled ? 'Connected' : 'Available'}
                  badgeVariant={localSettings.jiraIntegration?.enabled ? 'success' : 'secondary'}
                >
                  {localSettings.jiraIntegration?.enabled && (
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: tokens.spacing[4],
                      marginTop: tokens.spacing[4],
                    }}>
                      <InputField
                        label="JIRA URL"
                        type="url"
                        value={localSettings.jiraIntegration?.jiraUrl || ''}
                        onChange={(value) => handleChange('jiraIntegration', 'jiraUrl', value)}
                        placeholder="https://your-domain.atlassian.net"
                        helpText="Your Atlassian Cloud instance URL"
                      />
                      
                      <InputField
                        label="Email Address"
                        type="email"
                        value={localSettings.jiraIntegration?.userEmail || ''}
                        onChange={(value) => handleChange('jiraIntegration', 'userEmail', value)}
                        placeholder="your.email@example.com"
                        helpText="Your JIRA account email address"
                      />
                      
                      <InputField
                        label="API Token"
                        type="password"
                        value={localSettings.jiraIntegration?.apiToken || ''}
                        onChange={(value) => handleChange('jiraIntegration', 'apiToken', value)}
                        placeholder="Enter your JIRA API token"
                        helpText={
                          <a 
                            href="https://id.atlassian.com/manage-profile/security/api-tokens" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: tokens.colors.primary[500], 
                              textDecoration: 'none' 
                            }}
                          >
                            Generate an API token from Atlassian →
                          </a>
                        }
                      />
                      
                      <InputField
                        label="Atlassian Account ID"
                        value={localSettings.jiraIntegration?.accountId || ''}
                        onChange={(value) => handleChange('jiraIntegration', 'accountId', value)}
                        placeholder="Your Atlassian account ID"
                        helpText={
                          <>
                            Find your account ID at{' '}
                            <a 
                              href="https://id.atlassian.com/manage-profile/profile-and-visibility" 
                              target="_blank" 
                              rel="noopener noreferrer"
                              style={{ 
                                color: tokens.colors.primary[500], 
                                textDecoration: 'none' 
                              }}
                            >
                              Atlassian Account Settings →
                            </a>
                          </>
                        }
                      />
                    </div>
                  )}
                </IntegrationCard>
              </div>
            )}

            {/* Account Settings */}
            {activeSection === 'account' && (
              <Card title="Account Management">
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: tokens.spacing[6],
                }}>
                  {/* User Info */}
                  <div>
                    <Text style={{
                      fontSize: tokens.typography.fontSize.sm[0],
                      fontWeight: tokens.typography.fontWeight.semibold,
                      color: tokens.colors.dark.text,
                      margin: 0,
                      marginBottom: tokens.spacing[2],
                    }}>
                      Account Information
                    </Text>
                    
                    <div style={{
                      padding: tokens.spacing[4],
                      backgroundColor: tokens.colors.dark.surface,
                      borderRadius: tokens.borderRadius.md,
                      border: `1px solid ${tokens.colors.dark.border}`,
                    }}>
                      <div style={{ marginBottom: tokens.spacing[3] }}>
                        <Text style={{
                          fontSize: tokens.typography.fontSize.xs[0],
                          color: tokens.colors.dark.muted,
                          textTransform: 'uppercase',
                          letterSpacing: tokens.typography.letterSpacing.wide,
                          margin: 0,
                          marginBottom: tokens.spacing[1],
                        }}>
                          Name
                        </Text>
                        <Text style={{ margin: 0 }}>
                          {user?.full_name || user?.username || 'Not set'}
                        </Text>
                      </div>
                      
                      <div>
                        <Text style={{
                          fontSize: tokens.typography.fontSize.xs[0],
                          color: tokens.colors.dark.muted,
                          textTransform: 'uppercase',
                          letterSpacing: tokens.typography.letterSpacing.wide,
                          margin: 0,
                          marginBottom: tokens.spacing[1],
                        }}>
                          Email
                        </Text>
                        <Text style={{ margin: 0 }}>
                          {user?.email || 'Not set'}
                        </Text>
                      </div>
                    </div>
                  </div>

                  {/* Danger Zone */}
                  <div>
                    <Text style={{
                      fontSize: tokens.typography.fontSize.sm[0],
                      fontWeight: tokens.typography.fontWeight.semibold,
                      color: tokens.colors.error[500],
                      margin: 0,
                      marginBottom: tokens.spacing[3],
                    }}>
                      Danger Zone
                    </Text>
                    
                    <div style={{
                      padding: tokens.spacing[4],
                      border: `1px solid ${tokens.colors.error[500]}30`,
                      borderRadius: tokens.borderRadius.md,
                      backgroundColor: `${tokens.colors.error[500]}10`,
                    }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}>
                        <div>
                          <Text style={{
                            fontWeight: tokens.typography.fontWeight.medium,
                            color: tokens.colors.dark.text,
                            margin: 0,
                            marginBottom: tokens.spacing[1],
                          }}>
                            Sign Out
                          </Text>
                          <Text style={{
                            fontSize: tokens.typography.fontSize.sm[0],
                            color: tokens.colors.dark.muted,
                            margin: 0,
                          }}>
                            Sign out of your account on this device
                          </Text>
                        </div>
                        
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setShowLogoutModal(true)}
                        >
                          Sign Out
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* Save Button */}
            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              marginTop: tokens.spacing[8],
              paddingTop: tokens.spacing[6],
              borderTop: `1px solid ${tokens.colors.dark.border}`,
            }}>
              <Button
                type="submit"
                variant="primary"
                loading={isSaving}
                disabled={isSaving}
                icon={CheckIcon}
              >
                {isSaving ? 'Saving...' : 'Save Settings'}
              </Button>
            </div>
          </form>
        </div>
      </div>

      {/* Logout Confirmation Modal */}
      <Modal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        title="Confirm Sign Out"
      >
        <Text style={{ marginBottom: tokens.spacing[6] }}>
          Are you sure you want to sign out? You'll need to sign in again to access your tasks.
        </Text>
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: tokens.spacing[3],
        }}>
          <Button
            variant="secondary"
            onClick={() => setShowLogoutModal(false)}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleLogout}
          >
            Sign Out
          </Button>
        </div>
      </Modal>
    </div>
  );
};

// Toggle Field Component
const ToggleField = ({ label, description, checked, onChange }) => {
  // Theme-aware colors for the toggle
  const toggleBgColor = checked 
    ? tokens.colors.primary[500] 
    : 'var(--brand-border, #E5E7EB)'; // Light gray in light mode, dark in dark mode
  
  const toggleThumbColor = tokens.colors.neutral[0]; // Always white
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: tokens.spacing[4],
    }}>
      <div style={{ flex: 1 }}>
        <Text style={{
          fontWeight: tokens.typography.fontWeight.medium,
          color: tokens.colors.dark.text,
          margin: 0,
          marginBottom: tokens.spacing[1],
        }}>
          {label}
        </Text>
        <Text style={{
          fontSize: tokens.typography.fontSize.sm[0],
          color: tokens.colors.dark.muted,
          margin: 0,
        }}>
          {description}
        </Text>
      </div>
      
      <label style={{
        position: 'relative',
        display: 'inline-block',
        width: '44px',
        height: '24px',
        cursor: 'pointer',
      }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          style={{ display: 'none' }}
        />
        <div style={{
          position: 'absolute',
          cursor: 'pointer',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: toggleBgColor,
          transition: tokens.transitions.colors,
          borderRadius: '12px',
          border: checked ? 'none' : '2px solid var(--brand-border, #D1D5DB)',
        }}>
          <div style={{
            position: 'absolute',
            height: '18px',
            width: '18px',
            left: checked ? '23px' : '3px',
            top: '3px',
            backgroundColor: toggleThumbColor,
            transition: tokens.transitions.all,
            borderRadius: '50%',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          }} />
        </div>
      </label>
    </div>
  );
};

// Input Field Component
const InputField = ({ label, type = 'text', value, onChange, placeholder, helpText }) => (
  <div>
    <Text style={{
      fontSize: tokens.typography.fontSize.sm[0],
      fontWeight: tokens.typography.fontWeight.medium,
      color: tokens.colors.dark.text,
      margin: 0,
      marginBottom: tokens.spacing[2],
    }}>
      {label}
    </Text>
    
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: '100%',
        padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
        border: `1px solid ${tokens.colors.dark.border}`,
        borderRadius: tokens.borderRadius.md,
        backgroundColor: tokens.colors.dark.surface,
        color: tokens.colors.dark.text,
        fontSize: tokens.typography.fontSize.sm[0],
        fontFamily: tokens.typography.fontFamily.sans.join(', '),
        transition: tokens.transitions.colors,
        outline: 'none',
      }}
      onFocus={(e) => {
        e.target.style.borderColor = tokens.colors.primary[500];
        e.target.style.boxShadow = `0 0 0 3px ${tokens.colors.primary[500]}20`;
      }}
      onBlur={(e) => {
        e.target.style.borderColor = tokens.colors.dark.border;
        e.target.style.boxShadow = 'none';
      }}
    />
    
    {helpText && (
      <Text style={{
        fontSize: tokens.typography.fontSize.xs[0],
        color: tokens.colors.dark.muted,
        margin: 0,
        marginTop: tokens.spacing[1],
      }}>
        {helpText}
      </Text>
    )}
  </div>
);

// Integration Card Component
const IntegrationCard = ({ title, description, enabled, onToggle, badge, badgeVariant, children }) => (
  <Card>
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      marginBottom: children ? tokens.spacing[4] : 0,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: tokens.spacing[3],
          marginBottom: tokens.spacing[1],
        }}>
          <Text style={{
            fontWeight: tokens.typography.fontWeight.semibold,
            color: tokens.colors.dark.text,
            margin: 0,
          }}>
            {title}
          </Text>
          <Badge variant={badgeVariant} size="sm">
            {badge}
          </Badge>
        </div>
        
        <Text style={{
          fontSize: tokens.typography.fontSize.sm[0],
          color: tokens.colors.dark.muted,
          margin: 0,
        }}>
          {description}
        </Text>
      </div>
      
      <ToggleField
        label=""
        description=""
        checked={enabled}
        onChange={onToggle}
      />
    </div>
    
    {children}
  </Card>
);

export default Settings;
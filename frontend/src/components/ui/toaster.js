import React from 'react';
import { tokens } from '../../design-system';

// Simple notification system without Chakra UI
class SimpleToaster {
  constructor() {
    this.toasts = [];
    this.listeners = [];
    this.nextId = 1;
  }

  create({ title, description, status = 'info', duration = 5000, isClosable = true }) {
    const toast = {
      id: this.nextId++,
      title,
      description,
      status,
      duration,
      isClosable,
      createdAt: Date.now()
    };

    this.toasts.push(toast);
    this.notifyListeners();

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        this.remove(toast.id);
      }, duration);
    }

    return toast.id;
  }

  remove(id) {
    this.toasts = this.toasts.filter(toast => toast.id !== id);
    this.notifyListeners();
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notifyListeners() {
    this.listeners.forEach(listener => listener(this.toasts));
  }
}

// Create a singleton toaster instance
export const toaster = new SimpleToaster();

// ToasterComponent for rendering notifications
export const ToasterComponent = () => {
  const [toasts, setToasts] = React.useState([]);

  React.useEffect(() => {
    const unsubscribe = toaster.subscribe(setToasts);
    return unsubscribe;
  }, []);

  if (toasts.length === 0) return null;

  const getToastStyles = (status) => {
    const baseStyles = {
      position: 'relative',
      maxWidth: '400px',
      width: '100%',
      padding: tokens.spacing[4],
      borderRadius: tokens.borderRadius.lg,
      boxShadow: tokens.boxShadow.xl,
      border: `1px solid ${tokens.colors.dark.border}`,
      backgroundColor: tokens.colors.dark.surface,
      backdropFilter: 'blur(8px)',
      marginBottom: tokens.spacing[2],
      transition: tokens.transitions.all,
      transform: 'translateX(0)',
      opacity: 1,
    };

    const statusColors = {
      success: {
        borderColor: tokens.colors.success[600],
        backgroundColor: `${tokens.colors.success[500]}20`, // 20% opacity
      },
      error: {
        borderColor: tokens.colors.error[600],
        backgroundColor: `${tokens.colors.error[500]}20`, // 20% opacity
      },
      warning: {
        borderColor: tokens.colors.warning[600],
        backgroundColor: `${tokens.colors.warning[500]}20`, // 20% opacity
      },
      info: {
        borderColor: tokens.colors.info[600],
        backgroundColor: `${tokens.colors.info[500]}20`, // 20% opacity
      },
    };

    return {
      ...baseStyles,
      ...statusColors[status],
    };
  };

  return (
    <div style={{
      position: 'fixed',
      top: tokens.spacing[4],
      right: tokens.spacing[4],
      zIndex: tokens.zIndex.toast,
      display: 'flex',
      flexDirection: 'column',
      gap: tokens.spacing[2],
    }}>
      {toasts.map(toast => (
        <div
          key={toast.id}
          style={getToastStyles(toast.status)}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              {toast.title && (
                <div style={{
                  fontWeight: tokens.typography.fontWeight.medium,
                  fontSize: tokens.typography.fontSize.sm[0],
                  marginBottom: tokens.spacing[1],
                  color: tokens.colors.dark.text,
                }}>
                  {toast.title}
                </div>
              )}
              {toast.description && (
                <div style={{
                  fontSize: tokens.typography.fontSize.sm[0],
                  color: tokens.colors.dark.muted,
                  lineHeight: tokens.typography.lineHeight.normal,
                }}>
                  {toast.description}
                </div>
              )}
            </div>
            {toast.isClosable && (
              <button
                onClick={() => toaster.remove(toast.id)}
                style={{
                  marginLeft: tokens.spacing[3],
                  opacity: 0.7,
                  transition: tokens.transitions.all,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: tokens.colors.dark.muted,
                  padding: tokens.spacing[1],
                  borderRadius: tokens.borderRadius.base,
                }}
                onMouseEnter={(e) => e.target.style.opacity = '1'}
                onMouseLeave={(e) => e.target.style.opacity = '0.7'}
              >
                <svg 
                  style={{ width: '16px', height: '16px' }} 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
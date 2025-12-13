// Professional Notification System - Replaces scattered toast notifications
import React from 'react';
import ReactDOM from 'react-dom';
import {
  Button,
  Text,
  tokens,
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
} from '../design-system';
import { useApp } from '../contexts/AppContext';

// Individual notification component
const Notification = ({ notification, onClose }) => {
  const { id, type, message, title, autoHide = true } = notification;

  // Get icon and colors based on type (dark theme optimized)
  const getNotificationStyle = (type) => {
    switch (type) {
      case 'success':
        return {
          icon: CheckCircleIcon,
          iconColor: tokens.colors.success[400],
          backgroundColor: `${tokens.colors.success[500]}15`,
          borderColor: `${tokens.colors.success[500]}40`,
          titleColor: tokens.colors.success[300],
          messageColor: tokens.colors.success[200],
        };
      case 'error':
        return {
          icon: ExclamationCircleIcon,
          iconColor: tokens.colors.error[400],
          backgroundColor: `${tokens.colors.error[500]}15`,
          borderColor: `${tokens.colors.error[500]}40`,
          titleColor: tokens.colors.error[300],
          messageColor: tokens.colors.error[200],
        };
      case 'warning':
        return {
          icon: ExclamationCircleIcon,
          iconColor: tokens.colors.warning[400],
          backgroundColor: `${tokens.colors.warning[500]}15`,
          borderColor: `${tokens.colors.warning[500]}40`,
          titleColor: tokens.colors.warning[300],
          messageColor: tokens.colors.warning[200],
        };
      case 'info':
      default:
        return {
          icon: InformationCircleIcon,
          iconColor: tokens.colors.info[400],
          backgroundColor: `${tokens.colors.info[500]}15`,
          borderColor: `${tokens.colors.info[500]}40`,
          titleColor: tokens.colors.info[300],
          messageColor: tokens.colors.info[200],
        };
    }
  };

  const style = getNotificationStyle(type);
  const Icon = style.icon;

  return (
    <div
      style={{
        position: 'relative',
        minWidth: '320px',
        maxWidth: '480px',
        backgroundColor: style.backgroundColor,
        borderColor: style.borderColor,
        borderStyle: 'solid',
        borderWidth: '1px',
        borderRadius: tokens.borderRadius.lg,
        padding: tokens.spacing[4],
        marginBottom: tokens.spacing[2],
        boxShadow: tokens.boxShadow.lg,
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: tokens.spacing[3],
      }}>
        <Icon size={20} style={{ color: style.iconColor, marginTop: '2px' }} />
        
        <div style={{ flex: 1, minWidth: 0 }}>
          {title && (
            <Text style={{
              fontWeight: tokens.typography.fontWeight.semibold,
              fontSize: tokens.typography.fontSize.sm[0],
              margin: `0 0 ${tokens.spacing[1]} 0`,
              color: style.titleColor,
            }}>
              {title}
            </Text>
          )}
          
          <Text style={{
            fontSize: tokens.typography.fontSize.sm[0],
            lineHeight: '1.4',
            margin: 0,
            color: style.messageColor,
          }}>
            {message}
          </Text>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => onClose(id)}
          style={{
            padding: tokens.spacing[1],
            minWidth: 'auto',
            height: 'auto',
            color: tokens.colors.dark.muted,
            backgroundColor: 'transparent',
          }}
        >
          ×
        </Button>
      </div>

      {/* Auto-hide progress bar */}
      {autoHide && (
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '2px',
          backgroundColor: style.borderColor,
          transformOrigin: 'left',
          animation: 'shrink 5s linear forwards',
        }} />
      )}
    </div>
  );
};

// Notification container
const NotificationContainer = () => {
  const { notifications, removeNotification } = useApp();

  if (notifications.length === 0) {
    return null;
  }

  return ReactDOM.createPortal(
    <div style={{
      position: 'fixed',
      top: tokens.spacing[4],
      right: tokens.spacing[4],
      zIndex: tokens.zIndex.toast,
      pointerEvents: 'none',
    }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: tokens.spacing[2],
      }}>
        {notifications.map(notification => (
          <div
            key={notification.id}
            style={{ pointerEvents: 'auto' }}
          >
            <Notification
              notification={notification}
              onClose={removeNotification}
            />
          </div>
        ))}
      </div>
    </div>,
    document.body
  );
};

// CSS animations for the notification system
const notificationStyles = `
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(100%);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes shrink {
    from {
      transform: scaleX(1);
    }
    to {
      transform: scaleX(0);
    }
  }
`;

// Inject styles if not already present
if (!document.querySelector('#notification-styles')) {
  const styleSheet = document.createElement('style');
  styleSheet.id = 'notification-styles';
  styleSheet.textContent = notificationStyles;
  document.head.appendChild(styleSheet);
}

export default NotificationContainer;
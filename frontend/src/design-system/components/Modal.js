import React, { useEffect } from 'react';
import { tokens } from '../tokens';

// Modal component with backdrop
export const Modal = ({ 
  isOpen = false, 
  onClose, 
  title, 
  children, 
  size = 'md',
  ...props 
}) => {
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen && onClose) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizes = {
    sm: { maxWidth: '400px' },
    md: { maxWidth: '600px' },
    lg: { maxWidth: '800px' },
    xl: { maxWidth: '1200px' },
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: tokens.zIndex.modal,
        padding: tokens.spacing[4],
        overflowY: 'auto',
      }}
      onClick={onClose}
      {...props}
    >
      <div
        style={{
          backgroundColor: 'var(--color-surface)',
          borderRadius: tokens.borderRadius.lg,
          border: '1px solid var(--color-border)',
          boxShadow: tokens.boxShadow.xl,
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          margin: 'auto',
          ...sizes[size],
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div style={{
            padding: `${tokens.spacing[4]} ${tokens.spacing[6]}`,
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <h2 style={{
              margin: 0,
              fontSize: tokens.typography.fontSize.xl[0],
              fontWeight: tokens.typography.fontWeight.semibold,
              color: 'var(--color-text)',
            }}>
              {title}
            </h2>
            {onClose && (
              <button
                onClick={onClose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  padding: tokens.spacing[1],
                  fontSize: tokens.typography.fontSize.xl[0],
                }}
              >
                ×
              </button>
            )}
          </div>
        )}
        
        <div style={{
          padding: tokens.spacing[6],
          overflowY: 'auto',
          flex: 1,
        }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;
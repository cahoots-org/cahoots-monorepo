// Professional progress bar component
import React from 'react';
import { tokens } from '../tokens';

export const Progress = ({ 
  value = 0, 
  max = 100, 
  size = 'md',
  variant = 'primary',
  showLabel = false,
  style = {},
  ...props 
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizeStyles = {
    sm: {
      height: '6px',
      borderRadius: tokens.borderRadius.sm,
    },
    md: {
      height: '8px',
      borderRadius: tokens.borderRadius.md,
    },
    lg: {
      height: '12px',
      borderRadius: tokens.borderRadius.md,
    },
  };

  const variantStyles = {
    primary: {
      backgroundColor: tokens.colors.primary[500],
    },
    success: {
      backgroundColor: tokens.colors.success[500],
    },
    warning: {
      backgroundColor: tokens.colors.warning[500],
    },
    error: {
      backgroundColor: tokens.colors.error[500],
    },
    info: {
      backgroundColor: tokens.colors.info[500],
    },
  };

  return (
    <div style={{ ...style }}>
      {showLabel && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: tokens.spacing[1],
          fontSize: tokens.typography.fontSize.sm[0],
          color: tokens.colors.dark.text,
        }}>
          <span>Progress</span>
          <span>{Math.round(percentage)}%</span>
        </div>
      )}
      
      <div
        style={{
          width: '100%',
          backgroundColor: tokens.colors.dark.border,
          overflow: 'hidden',
          ...sizeStyles[size],
        }}
        {...props}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            transition: tokens.transitions.all,
            ...variantStyles[variant],
          }}
        />
      </div>
    </div>
  );
};

export default Progress;
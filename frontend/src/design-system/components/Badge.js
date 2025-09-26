import React from 'react';
import { tokens } from '../tokens';

// Professional Badge component replacing scattered badge styles
const Badge = ({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  className = '',
  ...props
}) => {
  // Base badge styles
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: tokens.typography.fontFamily.sans.join(', '),
    fontWeight: tokens.typography.fontWeight.medium,
    borderRadius: tokens.borderRadius.full,
    border: '1px solid transparent',
    whiteSpace: 'nowrap',
    textTransform: 'capitalize',
  };

  // Size variants
  const sizes = {
    sm: {
      padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
      fontSize: tokens.typography.fontSize.xs[0],
      lineHeight: tokens.typography.fontSize.xs[1].lineHeight,
    },
    md: {
      padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
      fontSize: tokens.typography.fontSize.sm[0],
      lineHeight: tokens.typography.fontSize.sm[1].lineHeight,
    },
    lg: {
      padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
      fontSize: tokens.typography.fontSize.base[0],
      lineHeight: tokens.typography.fontSize.base[1].lineHeight,
    },
  };

  // Variant styles with proper contrast and semantic colors
  const variants = {
    primary: {
      backgroundColor: `${tokens.colors.primary[500]}20`, // 20% opacity
      color: tokens.colors.primary[400],
      borderColor: `${tokens.colors.primary[500]}30`, // 30% opacity
    },
    success: {
      backgroundColor: `${tokens.colors.success[500]}20`,
      color: tokens.colors.success[400],
      borderColor: `${tokens.colors.success[500]}30`,
    },
    warning: {
      backgroundColor: `${tokens.colors.warning[500]}20`,
      color: tokens.colors.warning[400],
      borderColor: `${tokens.colors.warning[500]}30`,
    },
    error: {
      backgroundColor: `${tokens.colors.error[500]}20`,
      color: tokens.colors.error[400],
      borderColor: `${tokens.colors.error[500]}30`,
    },
    info: {
      backgroundColor: `${tokens.colors.info[500]}20`,
      color: tokens.colors.info[400],
      borderColor: `${tokens.colors.info[500]}30`,
    },
    neutral: {
      backgroundColor: `${tokens.colors.neutral[500]}20`,
      color: tokens.colors.neutral[300],
      borderColor: `${tokens.colors.neutral[500]}30`,
    },
    // Status-specific badges
    completed: {
      backgroundColor: `${tokens.colors.success[500]}20`,
      color: tokens.colors.success[400],
      borderColor: `${tokens.colors.success[500]}30`,
    },
    'in_progress': {
      backgroundColor: `${tokens.colors.warning[500]}20`,
      color: tokens.colors.warning[400],
      borderColor: `${tokens.colors.warning[500]}30`,
    },
    pending: {
      backgroundColor: `${tokens.colors.info[500]}20`,
      color: tokens.colors.info[400],
      borderColor: `${tokens.colors.info[500]}30`,
    },
    failed: {
      backgroundColor: `${tokens.colors.error[500]}20`,
      color: tokens.colors.error[400],
      borderColor: `${tokens.colors.error[500]}30`,
    },
  };

  // Combine all styles
  const badgeStyles = {
    ...baseStyles,
    ...sizes[size],
    ...variants[variant],
  };

  return (
    <span
      style={badgeStyles}
      className={className}
      {...props}
    >
      {Icon && (
        <Icon 
          size={size === 'sm' ? 12 : size === 'lg' ? 16 : 14}
          style={{ marginRight: tokens.spacing[1] }}
        />
      )}
      {children}
    </span>
  );
};

// Utility function to get status badge variant
export const getStatusVariant = (status) => {
  const statusMap = {
    completed: 'completed',
    in_progress: 'in_progress',
    processing: 'in_progress',
    pending: 'pending',
    submitted: 'pending',
    failed: 'failed',
    error: 'failed',
    rejected: 'failed', // Use failed styling for rejected tasks
  };
  
  return statusMap[status] || 'neutral';
};

export default Badge;
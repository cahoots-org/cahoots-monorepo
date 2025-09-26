import React from 'react';
import { tokens } from '../tokens';

export const LoadingSpinner = ({ 
  size = 'md', 
  color = tokens.colors.primary[500],
  style = {},
  ...props 
}) => {
  const sizes = {
    sm: '16px',
    md: '24px',
    lg: '32px',
    xl: '48px',
  };

  return (
    <div
      style={{
        width: sizes[size],
        height: sizes[size],
        border: `3px solid ${tokens.colors.dark.border}`,
        borderTop: `3px solid ${color}`,
        borderRadius: tokens.borderRadius.full,
        animation: 'spin 1s linear infinite',
        ...style,
      }}
      {...props}
    />
  );
};

export default LoadingSpinner;
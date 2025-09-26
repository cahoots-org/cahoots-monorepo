import React from 'react';
import { tokens } from '../tokens';

export const EmptyState = ({ 
  icon: Icon, 
  title, 
  description, 
  action,
  size = 'md',
  style = {},
  ...props 
}) => {
  const sizes = {
    sm: {
      iconSize: 32,
      titleSize: tokens.typography.fontSize.lg[0],
      padding: tokens.spacing[4],
    },
    md: {
      iconSize: 48,
      titleSize: tokens.typography.fontSize.xl[0],
      padding: tokens.spacing[8],
    },
    lg: {
      iconSize: 64,
      titleSize: tokens.typography.fontSize['2xl'][0],
      padding: tokens.spacing[12],
    },
  };

  const sizeConfig = sizes[size];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: sizeConfig.padding,
        color: tokens.colors.dark.muted,
        ...style,
      }}
      {...props}
    >
      {Icon && (
        <Icon 
          size={sizeConfig.iconSize} 
          style={{ 
            marginBottom: tokens.spacing[4],
            color: tokens.colors.dark.border,
          }} 
        />
      )}
      
      {title && (
        <h3 style={{
          margin: 0,
          marginBottom: tokens.spacing[2],
          fontSize: sizeConfig.titleSize,
          fontWeight: tokens.typography.fontWeight.semibold,
          color: tokens.colors.dark.text,
        }}>
          {title}
        </h3>
      )}
      
      {description && (
        <p style={{
          margin: 0,
          marginBottom: action ? tokens.spacing[4] : 0,
          fontSize: tokens.typography.fontSize.sm[0],
          color: tokens.colors.dark.muted,
          maxWidth: '400px',
        }}>
          {description}
        </p>
      )}
      
      {action}
    </div>
  );
};

export default EmptyState;
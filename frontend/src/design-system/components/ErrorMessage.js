import React from 'react';
import { tokens } from '../tokens';

export const ErrorMessage = ({ 
  title = 'Something went wrong',
  message, 
  onRetry,
  style = {},
  ...props 
}) => {
  return (
    <div
      style={{
        backgroundColor: `${tokens.colors.error[500]}15`,
        border: `1px solid ${tokens.colors.error[500]}30`,
        borderRadius: tokens.borderRadius.lg,
        padding: tokens.spacing[6],
        textAlign: 'center',
        ...style,
      }}
      {...props}
    >
      <div style={{
        width: '48px',
        height: '48px',
        backgroundColor: `${tokens.colors.error[500]}20`,
        borderRadius: tokens.borderRadius.full,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: `0 auto ${tokens.spacing[4]}`,
      }}>
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke={tokens.colors.error[500]}
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>

      <h3 style={{
        margin: 0,
        marginBottom: tokens.spacing[2],
        fontSize: tokens.typography.fontSize.lg[0],
        fontWeight: tokens.typography.fontWeight.semibold,
        color: tokens.colors.dark.text,
      }}>
        {title}
      </h3>

      {message && (
        <p style={{
          margin: 0,
          marginBottom: onRetry ? tokens.spacing[4] : 0,
          fontSize: tokens.typography.fontSize.sm[0],
          color: tokens.colors.dark.muted,
        }}>
          {message}
        </p>
      )}

      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            backgroundColor: tokens.colors.error[500],
            color: tokens.colors.neutral[0],
            border: 'none',
            borderRadius: tokens.borderRadius.md,
            padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
            fontSize: tokens.typography.fontSize.sm[0],
            fontWeight: tokens.typography.fontWeight.medium,
            cursor: 'pointer',
            transition: tokens.transitions.colors,
          }}
        >
          Try Again
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;
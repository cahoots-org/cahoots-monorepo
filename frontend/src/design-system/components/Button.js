import React from 'react';
import { tokens } from '../tokens';

// Professional Button component replacing scattered button styles
const Button = React.forwardRef(({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon: Icon,
  iconPosition = 'left',
  className = '',
  ...props
}, ref) => {
  // Base styles using design tokens
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: tokens.typography.fontFamily.sans.join(', '),
    fontWeight: tokens.typography.fontWeight.medium,
    borderRadius: tokens.borderRadius.lg,
    transition: `all ${tokens.transitionDuration.fast} ${tokens.transitionTimingFunction.ease}`,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    outline: 'none',
    border: '1px solid transparent',
    whiteSpace: 'nowrap',
    flexDirection: 'row',
  };

  // Size variants - Better vertical proportions
  const sizes = {
    sm: {
      padding: '8px 14px',
      fontSize: '13px',
      lineHeight: '1.3',
      gap: '6px',
    },
    md: {
      padding: '10px 18px',
      fontSize: '14px',
      lineHeight: '1.4',
      gap: '8px',
    },
    lg: {
      padding: '12px 24px',
      fontSize: '16px',
      lineHeight: '1.5',
      gap: '10px',
    },
  };

  // Variant styles - Note: React inline styles don't support pseudo-selectors
  const variants = {
    primary: {
      backgroundColor: (disabled || loading) ? tokens.colors.neutral[400] : tokens.colors.primary[500],
      color: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.neutral[0],
      boxShadow: tokens.boxShadow.base,
    },
    secondary: {
      backgroundColor: (disabled || loading) ? tokens.colors.neutral[700] : tokens.colors.dark.surface,
      color: (disabled || loading) ? tokens.colors.neutral[500] : tokens.colors.dark.text,
      borderColor: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.dark.border,
    },
    success: {
      backgroundColor: (disabled || loading) ? tokens.colors.neutral[400] : tokens.colors.success[500],
      color: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.neutral[0],
    },
    danger: {
      backgroundColor: (disabled || loading) ? tokens.colors.neutral[400] : tokens.colors.error[500],
      color: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.neutral[0],
    },
    ghost: {
      backgroundColor: 'transparent',
      color: (disabled || loading) ? tokens.colors.neutral[500] : tokens.colors.dark.text,
      borderColor: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.dark.border,
    },
    outline: {
      backgroundColor: 'transparent',
      color: (disabled || loading) ? tokens.colors.neutral[500] : tokens.colors.primary[500],
      borderColor: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.primary[500],
    },
  };

  // Combine all styles
  const buttonStyles = {
    ...baseStyles,
    ...sizes[size],
    ...variants[variant],
  };

  // Loading spinner component
  const LoadingSpinner = () => (
    <svg
      className="animate-spin"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        strokeDasharray="32"
        strokeDashoffset="32"
        opacity="0.3"
      />
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        strokeDasharray="32"
        strokeDashoffset="24"
        strokeLinecap="round"
      />
    </svg>
  );

  return (
    <button
      ref={ref}
      style={buttonStyles}
      disabled={disabled || loading}
      className={className}
      {...props}
    >
      {loading && (
        <>
          <LoadingSpinner />
          <span>{children}</span>
        </>
      )}
      {!loading && Icon && iconPosition === 'left' && (
        <>
          <Icon style={{
            width: size === 'sm' ? '14px' : size === 'lg' ? '18px' : '16px',
            height: size === 'sm' ? '14px' : size === 'lg' ? '18px' : '16px',
            flexShrink: 0,
            marginRight: children ? (size === 'sm' ? '6px' : size === 'lg' ? '10px' : '8px') : 0
          }} />
          {children && <span>{children}</span>}
        </>
      )}
      {!loading && !Icon && children}
      {!loading && Icon && iconPosition === 'right' && (
        <>
          {children && <span>{children}</span>}
          <Icon style={{
            width: size === 'sm' ? '14px' : size === 'lg' ? '18px' : '16px',
            height: size === 'sm' ? '14px' : size === 'lg' ? '18px' : '16px',
            flexShrink: 0,
            marginLeft: children ? (size === 'sm' ? '6px' : size === 'lg' ? '10px' : '8px') : 0
          }} />
        </>
      )}
    </button>
  );
});

Button.displayName = 'Button';

export default Button;
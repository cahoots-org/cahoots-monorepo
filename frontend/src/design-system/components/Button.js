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

  // Size variants
  const sizes = {
    sm: {
      padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
      fontSize: tokens.typography.fontSize.sm[0],
      lineHeight: tokens.typography.fontSize.sm[1].lineHeight,
    },
    md: {
      padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
      fontSize: tokens.typography.fontSize.base[0],
      lineHeight: tokens.typography.fontSize.base[1].lineHeight,
    },
    lg: {
      padding: `${tokens.spacing[4]} ${tokens.spacing[6]}`,
      fontSize: tokens.typography.fontSize.lg[0],
      lineHeight: tokens.typography.fontSize.lg[1].lineHeight,
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
          <span style={{ marginLeft: tokens.spacing[2] }}>{children}</span>
        </>
      )}
      {!loading && Icon && iconPosition === 'left' && (
        <>
          <Icon size={size === 'sm' ? 16 : size === 'lg' ? 20 : 18} style={{ flexShrink: 0 }} />
          {children && <span style={{ marginLeft: tokens.spacing[2] }}>{children}</span>}
        </>
      )}
      {!loading && !Icon && children}
      {!loading && Icon && iconPosition === 'right' && (
        <>
          {children}
          <span style={{ marginLeft: tokens.spacing[2] }}>
            <Icon size={size === 'sm' ? 16 : size === 'lg' ? 20 : 18} />
          </span>
        </>
      )}
    </button>
  );
});

Button.displayName = 'Button';

export default Button;
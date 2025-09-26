import React from 'react';
import { tokens } from '../tokens';

// IconButton component - button optimized for just icon display
const IconButton = React.forwardRef(({
  icon: Icon,
  variant = 'ghost',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
  ...props
}, ref) => {
  // Base styles
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: tokens.typography.fontFamily.sans.join(', '),
    borderRadius: tokens.borderRadius.md,
    transition: `all ${tokens.transitionDuration.fast} ${tokens.transitionTimingFunction.ease}`,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    outline: 'none',
    border: '1px solid transparent',
  };

  // Size variants
  const sizes = {
    sm: {
      width: '32px',
      height: '32px',
    },
    md: {
      width: '40px',
      height: '40px',
    },
    lg: {
      width: '48px',
      height: '48px',
    },
  };

  // Variant styles - Note: React inline styles don't support pseudo-selectors
  const variants = {
    primary: {
      backgroundColor: (disabled || loading) ? tokens.colors.neutral[400] : tokens.colors.primary[500],
      color: (disabled || loading) ? tokens.colors.neutral[600] : tokens.colors.neutral[0],
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
      color: tokens.colors.dark.text,
    },
  };

  const iconSize = size === 'sm' ? 16 : size === 'lg' ? 24 : 20;

  const buttonStyles = {
    ...baseStyles,
    ...sizes[size],
    ...variants[variant],
  };

  return (
    <button
      ref={ref}
      style={buttonStyles}
      disabled={disabled || loading}
      className={className}
      {...props}
    >
      {Icon && <Icon size={iconSize} />}
    </button>
  );
});

IconButton.displayName = 'IconButton';

export default IconButton;
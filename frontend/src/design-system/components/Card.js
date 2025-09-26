import React from 'react';
import { tokens } from '../tokens';

// Professional Card component replacing scattered card styles
const Card = React.forwardRef(({
  children,
  variant = 'default',
  hover = false,
  padding = 'md',
  className = '',
  ...props
}, ref) => {
  // Base card styles
  const baseStyles = {
    backgroundColor: tokens.colors.dark.surface,
    borderRadius: tokens.borderRadius.lg,
    border: `1px solid ${tokens.colors.dark.border}`,
    overflow: 'hidden',
    transition: `all ${tokens.transitionDuration.normal} ${tokens.transitionTimingFunction.ease}`,
  };

  // Padding variants
  const paddingStyles = {
    none: { padding: 0 },
    sm: { padding: tokens.spacing[4] },
    md: { padding: tokens.spacing[6] },
    lg: { padding: tokens.spacing[8] },
  };

  // Card variants
  const variants = {
    default: {
      boxShadow: tokens.boxShadow.base,
    },
    elevated: {
      boxShadow: tokens.boxShadow.lg,
    },
    outlined: {
      boxShadow: 'none',
      borderColor: tokens.colors.dark.border,
    },
    gradient: {
      background: `linear-gradient(135deg, ${tokens.colors.dark.surface} 0%, ${tokens.colors.neutral[800]} 100%)`,
      boxShadow: tokens.boxShadow.base,
    },
  };

  // Hover effects
  const hoverStyles = hover ? {
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: tokens.boxShadow.xl,
      borderColor: `${tokens.colors.primary[500]}40`, // 40 = 25% opacity
    },
  } : {};

  const cardStyles = {
    ...baseStyles,
    ...paddingStyles[padding],
    ...variants[variant],
    ...hoverStyles,
  };

  return (
    <div
      ref={ref}
      style={cardStyles}
      className={className}
      {...props}
    >
      {children}
    </div>
  );
});

Card.displayName = 'Card';

// Card Header component
export const CardHeader = ({ children, className = '', ...props }) => (
  <div
    style={{
      paddingBottom: tokens.spacing[4],
      marginBottom: tokens.spacing[4],
      borderBottom: `1px solid ${tokens.colors.dark.border}`,
    }}
    className={className}
    {...props}
  >
    {children}
  </div>
);

// Card Content component  
export const CardContent = ({ children, className = '', ...props }) => (
  <div className={className} {...props}>
    {children}
  </div>
);

// Card Footer component
export const CardFooter = ({ children, className = '', ...props }) => (
  <div
    style={{
      paddingTop: tokens.spacing[4],
      marginTop: tokens.spacing[4],
      borderTop: `1px solid ${tokens.colors.dark.border}`,
    }}
    className={className}
    {...props}
  >
    {children}
  </div>
);

export default Card;
import React from 'react';
import { tokens } from '../tokens';

// Typography components for consistent text styling
const createTextComponent = (defaultElement, defaultStyles) => 
  React.forwardRef(({
    as: Element = defaultElement,
    variant,
    color = 'text',
    align = 'left',
    children,
    className = '',
    ...props
  }, ref) => {
    // Color variants
    const colors = {
      text: tokens.colors.dark.text,
      muted: tokens.colors.dark.muted,
      primary: tokens.colors.primary[500],
      success: tokens.colors.success[500],
      warning: tokens.colors.warning[500],
      error: tokens.colors.error[500],
      info: tokens.colors.info[500],
    };

    // Text alignment
    const alignments = {
      left: 'left',
      center: 'center', 
      right: 'right',
      justify: 'justify',
    };

    const textStyles = {
      ...defaultStyles,
      color: colors[color] || color,
      textAlign: alignments[align],
    };

    return (
      <Element
        ref={ref}
        style={textStyles}
        className={className}
        {...props}
      >
        {children}
      </Element>
    );
  });

// Heading components
export const Heading1 = createTextComponent('h1', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize['3xl'][0],
  lineHeight: tokens.typography.fontSize['3xl'][1].lineHeight,
  fontWeight: tokens.typography.fontWeight.bold,
  marginBottom: tokens.spacing[4],
});

export const Heading2 = createTextComponent('h2', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize['2xl'][0],
  lineHeight: tokens.typography.fontSize['2xl'][1].lineHeight,
  fontWeight: tokens.typography.fontWeight.semibold,
  marginBottom: tokens.spacing[3],
});

export const Heading3 = createTextComponent('h3', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.xl[0],
  lineHeight: tokens.typography.fontSize.xl[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.semibold,
  marginBottom: tokens.spacing[3],
});

export const Heading4 = createTextComponent('h4', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.lg[0],
  lineHeight: tokens.typography.fontSize.lg[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.medium,
  marginBottom: tokens.spacing[2],
});

// Body text components
export const Text = createTextComponent('p', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.base[0],
  lineHeight: tokens.typography.fontSize.base[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.normal,
  marginBottom: tokens.spacing[3],
});

export const TextSmall = createTextComponent('span', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.sm[0],
  lineHeight: tokens.typography.fontSize.sm[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.normal,
});

export const TextLarge = createTextComponent('span', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.lg[0],
  lineHeight: tokens.typography.fontSize.lg[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.normal,
});

// Specialized text components
export const Caption = createTextComponent('span', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.xs[0],
  lineHeight: tokens.typography.fontSize.xs[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.normal,
  color: tokens.colors.dark.muted,
});

export const Code = createTextComponent('code', {
  fontFamily: tokens.typography.fontFamily.mono.join(', '),
  fontSize: tokens.typography.fontSize.sm[0],
  backgroundColor: tokens.colors.neutral[800],
  color: tokens.colors.primary[400],
  padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
  borderRadius: tokens.borderRadius.base,
  border: `1px solid ${tokens.colors.dark.border}`,
});

// Label component
export const Label = createTextComponent('label', {
  fontFamily: tokens.typography.fontFamily.sans.join(', '),
  fontSize: tokens.typography.fontSize.sm[0],
  lineHeight: tokens.typography.fontSize.sm[1].lineHeight,
  fontWeight: tokens.typography.fontWeight.medium,
  color: tokens.colors.dark.text,
  display: 'block',
  marginBottom: tokens.spacing[1],
});

// Gradient text effect (replacing the old gradient-text class)
export const GradientText = ({ children, className = '', ...props }) => (
  <span
    style={{
      background: `linear-gradient(135deg, ${tokens.colors.primary[500]} 0%, ${tokens.colors.warning[500]} 100%)`,
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
    }}
    className={className}
    {...props}
  >
    {children}
  </span>
);

// Export default Text component
export default Text;
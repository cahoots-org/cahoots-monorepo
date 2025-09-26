import React from 'react';
import { tokens } from '../tokens';

const TextArea = ({ 
  placeholder,
  value,
  onChange,
  rows = 3,
  className = '',
  disabled = false,
  required = false,
  ...props 
}) => {
  const baseStyles = {
    width: '100%',
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.relaxed,
    color: 'var(--color-text)',
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    outline: 'none',
    transition: tokens.transitions.colors,
    fontFamily: tokens.typography.fontFamily.sans.join(', '),
    resize: 'vertical',
    minHeight: '80px',
  };

  const disabledStyles = disabled ? {
    opacity: 0.6,
    cursor: 'not-allowed',
    backgroundColor: 'var(--color-surface)',
  } : {};

  return (
    <textarea
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      rows={rows}
      disabled={disabled}
      required={required}
      className={className}
      style={{
        ...baseStyles,
        ...disabledStyles,
      }}
      onFocus={(e) => {
        if (!disabled) {
          e.target.style.borderColor = tokens.colors.primary[500];
          e.target.style.boxShadow = `0 0 0 3px ${tokens.colors.primary[500]}20`;
        }
      }}
      onBlur={(e) => {
        e.target.style.borderColor = 'var(--color-border)';
        e.target.style.boxShadow = 'none';
      }}
      {...props}
    />
  );
};

export default TextArea;
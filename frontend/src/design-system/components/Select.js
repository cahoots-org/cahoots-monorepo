import React from 'react';
import { tokens } from '../tokens';

const Select = ({ 
  value,
  onChange,
  children,
  className = '',
  disabled = false,
  required = false,
  ...props 
}) => {
  const baseStyles = {
    width: '100%',
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    fontSize: tokens.typography.fontSize.sm[0],
    lineHeight: tokens.typography.lineHeight.normal,
    color: 'var(--color-text)',
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: tokens.borderRadius.md,
    outline: 'none',
    transition: tokens.transitions.colors,
    fontFamily: tokens.typography.fontFamily.sans.join(', '),
    cursor: 'pointer',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
    backgroundPosition: 'right 0.5rem center',
    backgroundRepeat: 'no-repeat',
    backgroundSize: '1.5em 1.5em',
    paddingRight: tokens.spacing[10],
  };

  const disabledStyles = disabled ? {
    opacity: 0.6,
    cursor: 'not-allowed',
    backgroundColor: 'var(--color-surface)',
  } : {};

  return (
    <select
      value={value}
      onChange={onChange}
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
    >
      {children}
    </select>
  );
};

export default Select;
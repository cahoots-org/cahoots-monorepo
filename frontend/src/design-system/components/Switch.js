import React from 'react';
import { tokens } from '../tokens';

const Switch = ({ 
  checked = false,
  onChange,
  disabled = false,
  className = '',
  ...props 
}) => {
  const handleClick = () => {
    if (!disabled && onChange) {
      onChange(!checked);
    }
  };

  const containerStyles = {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    width: '44px',
    height: '24px',
    backgroundColor: checked ? tokens.colors.primary[500] : tokens.colors.dark.border,
    borderRadius: tokens.borderRadius.full,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: tokens.transitions.colors,
    opacity: disabled ? 0.6 : 1,
  };

  const toggleStyles = {
    position: 'absolute',
    top: '2px',
    left: checked ? '22px' : '2px',
    width: '20px',
    height: '20px',
    backgroundColor: tokens.colors.neutral[0],
    borderRadius: tokens.borderRadius.full,
    transition: 'left 0.2s ease-in-out',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  };

  return (
    <div
      className={className}
      style={containerStyles}
      onClick={handleClick}
      role="switch"
      aria-checked={checked}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => {
        if ((e.key === ' ' || e.key === 'Enter') && !disabled) {
          e.preventDefault();
          handleClick();
        }
      }}
      {...props}
    >
      <div style={toggleStyles} />
    </div>
  );
};

export default Switch;
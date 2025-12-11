import React from 'react';
import { tokens } from '../design-system/tokens';
import Badge from '../design-system/components/Badge';

const GRANULARITY_OPTIONS = [
  {
    value: 'large',
    label: 'Large Tasks',
    description: 'Fewer tasks (5-13 SP each) with high-level guidance',
    icon: '1',
  },
  {
    value: 'medium',
    label: 'Medium Tasks',
    description: 'Balanced tasks (2-8 SP each) for most teams',
    icon: '2',
    recommended: true,
  },
  {
    value: 'small',
    label: 'Small Tasks',
    description: 'Granular tasks (1-3 SP each) with detailed guidance',
    icon: '3',
  },
];

const GranularitySelector = ({ value, onChange }) => {
  return (
    <div style={styles.container}>
      <div style={styles.options}>
        {GRANULARITY_OPTIONS.map((option) => {
          const isSelected = value === option.value;
          return (
            <div
              key={option.value}
              style={{
                ...styles.option,
                ...(isSelected ? styles.optionSelected : {}),
              }}
              onClick={() => onChange(option.value)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onChange(option.value);
                }
              }}
            >
              <div style={styles.optionHeader}>
                <div style={{
                  ...styles.optionIcon,
                  ...(isSelected ? styles.optionIconSelected : {}),
                }}>
                  {option.icon}
                </div>
                <span style={{
                  ...styles.optionLabel,
                  ...(isSelected ? styles.optionLabelSelected : {}),
                }}>
                  {option.label}
                </span>
                {option.recommended && (
                  <Badge variant="primary" size="sm">
                    Recommended
                  </Badge>
                )}
              </div>
              <p style={styles.optionDescription}>{option.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles = {
  container: {
    width: '100%',
  },
  options: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[2],
  },
  option: {
    padding: tokens.spacing[3],
    borderRadius: tokens.borderRadius.lg,
    border: `2px solid ${tokens.colors.neutral[300]}`,
    backgroundColor: tokens.colors.neutral[0],
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  optionSelected: {
    borderColor: tokens.colors.primary[400],
    backgroundColor: `${tokens.colors.primary[400]}08`,
  },
  optionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
  },
  optionIcon: {
    width: '24px',
    height: '24px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: tokens.colors.neutral[200],
    color: tokens.colors.neutral[600],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: tokens.typography.fontWeight.semibold,
  },
  optionIconSelected: {
    backgroundColor: tokens.colors.primary[400],
    color: tokens.colors.neutral[0],
  },
  optionLabel: {
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
    fontSize: '14px',
  },
  optionLabelSelected: {
    color: tokens.colors.primary[600],
  },
  optionDescription: {
    fontSize: '13px',
    color: tokens.colors.neutral[500],
    marginLeft: '32px',
    margin: 0,
    marginTop: tokens.spacing[1],
    paddingLeft: '32px',
  },
};

export default GranularitySelector;
export { GRANULARITY_OPTIONS };

/**
 * PersonaSelectorBar - Mode switcher for PM/Dev/Consultant personas
 *
 * Persists selection to localStorage for session continuity.
 */
import React from 'react';
import { tokens } from '../../design-system';

const PERSONAS = [
  {
    id: 'pm',
    label: 'PM',
    fullLabel: 'Project Manager',
    icon: '📋',
    description: 'Story points, roadmaps, and exports',
    color: tokens.colors.primary[400],
  },
  {
    id: 'dev',
    label: 'Dev',
    fullLabel: 'Developer',
    icon: '💻',
    description: 'Event models, architecture, and code',
    color: tokens.colors.secondary[400],
  },
  {
    id: 'consultant',
    label: 'Consultant',
    fullLabel: 'Consultant',
    icon: '📊',
    description: 'Proposals, scope, and estimates',
    color: tokens.colors.info[500],
  },
];

const PersonaSelectorBar = ({ activePersona, onPersonaChange }) => {
  return (
    <div style={styles.container}>
      <div style={styles.label}>View as:</div>
      <div style={styles.selector}>
        {PERSONAS.map((persona) => {
          const isActive = activePersona === persona.id;
          return (
            <button
              key={persona.id}
              onClick={() => onPersonaChange(persona.id)}
              style={{
                ...styles.button,
                ...(isActive ? styles.buttonActive : {}),
                '--persona-color': persona.color,
              }}
              title={persona.description}
            >
              <span style={styles.icon}>{persona.icon}</span>
              <span style={styles.buttonLabel}>{persona.label}</span>
              {isActive && <span style={styles.activeIndicator} />}
            </button>
          );
        })}
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[4],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    backgroundColor: 'var(--color-surface)',
    borderRadius: tokens.borderRadius.xl,
    border: '1px solid var(--color-border)',
  },
  label: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    fontWeight: tokens.typography.fontWeight.medium,
  },
  selector: {
    display: 'flex',
    gap: tokens.spacing[2],
    padding: tokens.spacing[1],
    backgroundColor: 'var(--color-bg)',
    borderRadius: tokens.borderRadius.lg,
  },
  button: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
    border: 'none',
    borderRadius: tokens.borderRadius.md,
    backgroundColor: 'transparent',
    color: 'var(--color-text-muted)',
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  buttonActive: {
    backgroundColor: 'var(--color-surface)',
    color: 'var(--color-text)',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
  },
  icon: {
    fontSize: '1rem',
  },
  buttonLabel: {
    // Inherited from button
  },
  activeIndicator: {
    position: 'absolute',
    bottom: '-2px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '20px',
    height: '3px',
    backgroundColor: 'var(--persona-color)',
    borderRadius: tokens.borderRadius.full,
  },
};

export { PERSONAS };
export default PersonaSelectorBar;

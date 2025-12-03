/**
 * CreatingProject - Interim page shown immediately after clicking Create
 *
 * Shows an engaging loading state while the task is being created.
 * Once the task ID is available, redirects to the actual ProjectView.
 */
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Card,
  Text,
  LoadingSpinner,
  tokens,
} from '../design-system';

const CreatingProject = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { description, isCreating } = location.state || {};

  const [dots, setDots] = useState('');
  const [tip, setTip] = useState(0);

  const tips = [
    "Breaking down your requirements into epics and user stories...",
    "Identifying the core features and functionality...",
    "Analyzing complexity and estimating effort...",
    "Generating an event model for your system...",
    "Creating a structured project plan...",
  ];

  // Animate the dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(d => d.length >= 3 ? '' : d + '.');
    }, 400);
    return () => clearInterval(interval);
  }, []);

  // Rotate through tips
  useEffect(() => {
    const interval = setInterval(() => {
      setTip(t => (t + 1) % tips.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [tips.length]);

  // If we somehow got here without state, redirect back
  useEffect(() => {
    if (!isCreating && !description) {
      navigate('/tasks/create');
    }
  }, [isCreating, description, navigate]);

  return (
    <div style={styles.container}>
      <Card style={styles.card}>
        <div style={styles.content}>
          {/* Animated Logo/Icon */}
          <div style={styles.iconContainer}>
            <div style={styles.pulsingRing} />
            <div style={styles.icon}>
              <SparklesIcon />
            </div>
          </div>

          {/* Main Message */}
          <Text style={styles.title}>
            Creating your project{dots}
          </Text>

          {/* The description being processed */}
          <div style={styles.descriptionBox}>
            <Text style={styles.descriptionLabel}>Your request:</Text>
            <Text style={styles.description}>
              "{description?.substring(0, 150)}{description?.length > 150 ? '...' : ''}"
            </Text>
          </div>

          {/* Rotating tips */}
          <div style={styles.tipContainer}>
            <LoadingSpinner size="sm" />
            <Text style={styles.tip}>{tips[tip]}</Text>
          </div>

          {/* Progress indicator */}
          <div style={styles.progressBar}>
            <div style={styles.progressFill} />
          </div>
        </div>
      </Card>
    </div>
  );
};

const SparklesIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
    style={{ width: 40, height: 40 }}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
    />
  </svg>
);

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '80vh',
    padding: tokens.spacing[6],
  },

  card: {
    maxWidth: '500px',
    width: '100%',
  },

  content: {
    padding: tokens.spacing[8],
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },

  iconContainer: {
    position: 'relative',
    marginBottom: tokens.spacing[6],
  },

  pulsingRing: {
    position: 'absolute',
    top: '-10px',
    left: '-10px',
    right: '-10px',
    bottom: '-10px',
    borderRadius: '50%',
    border: `2px solid ${tokens.colors.primary[500]}`,
    animation: 'pulse-ring 1.5s ease-out infinite',
  },

  icon: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    backgroundColor: tokens.colors.primary[500],
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'float 2s ease-in-out infinite',
  },

  title: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.bold,
    color: 'var(--color-text)',
    marginBottom: tokens.spacing[6],
  },

  descriptionBox: {
    backgroundColor: 'var(--color-bg-secondary)',
    padding: tokens.spacing[4],
    borderRadius: tokens.borderRadius.lg,
    marginBottom: tokens.spacing[6],
    width: '100%',
  },

  descriptionLabel: {
    fontSize: tokens.typography.fontSize.xs[0],
    color: 'var(--color-text-muted)',
    marginBottom: tokens.spacing[2],
    display: 'block',
  },

  description: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text)',
    fontStyle: 'italic',
    lineHeight: 1.5,
  },

  tipContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    marginBottom: tokens.spacing[6],
  },

  tip: {
    fontSize: tokens.typography.fontSize.sm[0],
    color: 'var(--color-text-muted)',
    animation: 'fadeIn 0.3s ease-out',
  },

  progressBar: {
    width: '100%',
    height: '4px',
    backgroundColor: 'var(--color-bg-tertiary)',
    borderRadius: tokens.borderRadius.full,
    overflow: 'hidden',
  },

  progressFill: {
    height: '100%',
    width: '30%',
    backgroundColor: tokens.colors.primary[500],
    borderRadius: tokens.borderRadius.full,
    animation: 'progress-slide 2s ease-in-out infinite',
  },
};

// Add keyframe animations
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes pulse-ring {
      0% {
        transform: scale(1);
        opacity: 1;
      }
      100% {
        transform: scale(1.3);
        opacity: 0;
      }
    }

    @keyframes float {
      0%, 100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(-5px);
      }
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(5px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes progress-slide {
      0% {
        transform: translateX(-100%);
      }
      50% {
        transform: translateX(200%);
      }
      100% {
        transform: translateX(-100%);
      }
    }
  `;
  document.head.appendChild(styleSheet);
}

export default CreatingProject;

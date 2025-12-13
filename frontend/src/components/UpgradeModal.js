import React from 'react';
import { useNavigate } from 'react-router-dom';

// Feature descriptions for the upgrade modal
const FEATURE_INFO = {
  code_generation: {
    title: 'Code Generation',
    description: 'Generate production-ready code from your project specifications',
    icon: '< />',
  },
  github_integration: {
    title: 'GitHub Integration',
    description: 'Connect your GitHub account and push generated code directly to repositories',
    icon: '\u{E0A0}', // GitHub icon placeholder
  },
  export: {
    title: 'Export',
    description: 'Export your projects as JSON, Markdown, YAML, or CSV for use with other tools',
    icon: '\u{2B07}', // Download arrow
  },
};

const UpgradeModal = ({ isOpen, onClose, feature }) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const featureInfo = FEATURE_INFO[feature] || {
    title: 'Pro Feature',
    description: 'This feature is available on the Pro plan',
    icon: '\u{2B50}', // Star
  };

  const handleUpgrade = () => {
    onClose();
    navigate('/pricing');
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.7)' }}
      onClick={onClose}
    >
      <div
        className="card p-8 max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Header */}
        <div className="text-center mb-6">
          <div
            className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
            style={{
              backgroundColor: 'rgba(249, 115, 22, 0.1)',
              color: 'var(--color-brand-vibrant-orange)',
            }}
          >
            {featureInfo.icon}
          </div>
          <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>
            Upgrade to Pro
          </h2>
          <p style={{ color: 'var(--color-text-muted)' }}>
            {featureInfo.title} requires a Pro subscription
          </p>
        </div>

        {/* Feature Description */}
        <div
          className="p-4 rounded-lg mb-6"
          style={{ backgroundColor: 'var(--color-bg)' }}
        >
          <p style={{ color: 'var(--color-text)' }}>{featureInfo.description}</p>
        </div>

        {/* Benefits */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-muted)' }}>
            WHAT YOU'LL GET WITH PRO
          </h3>
          <ul className="space-y-2">
            {[
              'Code Generation',
              'GitHub Integration',
              'Export to JSON/Markdown',
              'Priority Processing',
            ].map((benefit, index) => (
              <li key={index} className="flex items-center gap-2">
                <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                <span style={{ color: 'var(--color-text)' }}>{benefit}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Price */}
        <div className="text-center mb-6">
          <span className="text-3xl font-bold" style={{ color: 'var(--color-text)' }}>
            $29
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>/month</span>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            className="btn btn-secondary flex-1"
            onClick={onClose}
          >
            Maybe Later
          </button>
          <button
            className="btn btn-primary flex-1"
            onClick={handleUpgrade}
          >
            Upgrade Now
          </button>
        </div>
      </div>
    </div>
  );
};

// Simple prompt component for inline use
export const UpgradePrompt = ({ feature, className = '' }) => {
  const navigate = useNavigate();
  const featureInfo = FEATURE_INFO[feature] || {
    title: 'Pro Feature',
    description: 'Available with Pro',
    icon: '\u{2B50}',
  };

  return (
    <div
      className={`p-4 rounded-lg text-center ${className}`}
      style={{
        backgroundColor: 'rgba(249, 115, 22, 0.05)',
        border: '1px solid rgba(249, 115, 22, 0.2)',
      }}
    >
      <div className="mb-2">
        <span
          className="inline-block w-10 h-10 rounded-full text-lg flex items-center justify-center"
          style={{
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            color: 'var(--color-brand-vibrant-orange)',
          }}
        >
          {featureInfo.icon}
        </span>
      </div>
      <p className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>
        {featureInfo.title}
      </p>
      <p className="text-sm mb-3" style={{ color: 'var(--color-text-muted)' }}>
        {featureInfo.description}
      </p>
      <button
        className="btn btn-primary btn-sm"
        onClick={() => navigate('/pricing')}
      >
        Upgrade to Pro
      </button>
    </div>
  );
};

export default UpgradeModal;

import React from 'react';
import { useNavigate } from 'react-router-dom';

const Footer = () => {
  const navigate = useNavigate();

  return (
    <footer className="border-t" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Main Footer Content */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Company Info */}
          <div className="md:col-span-2">
            <div className="flex items-center mb-4">
              <img 
                src="/icons/cottage.png" 
                alt="Cahoots" 
                width="32" 
                height="32" 
                className="mr-3"
              />
              <h3 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Cahoots</h3>
            </div>
            <p className="mb-4 max-w-md" style={{ color: 'var(--color-text-muted)' }}>
              AI-powered task decomposition that breaks down complex software projects into manageable, actionable work items.
            </p>
            <div className="flex space-x-4">
              <a
                href="https://www.linkedin.com/company/cahoots-llc/about"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-vibrant-blue hover:text-brand-vibrant-blue transition-colors"
                aria-label="LinkedIn"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
              </a>
              <a
                href="https://github.com/cahoots-org"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-brand-vibrant-orange transition-colors"
                style={{ color: 'var(--color-text-muted)' }}
                aria-label="GitHub"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Product</h4>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={() => navigate('/')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Home
                </button>
              </li>
              <li>
                <button
                  onClick={() => navigate('/about')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  About
                </button>
              </li>
              <li>
                <button
                  onClick={() => navigate('/login')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Get Started
                </button>
              </li>
              <li>
                <button
                  onClick={() => navigate('/blog')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Blog
                </button>
              </li>
              <li>
                <button
                  onClick={() => navigate('/dashboard')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Dashboard
                </button>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Support</h4>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={() => navigate('/contact')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Contact Us
                </button>
              </li>
              <li>
                <a
                  href="mailto:admin@cahoots.cc"
                  className="hover:text-brand-vibrant-orange transition-colors"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  admin@cahoots.cc
                </a>
              </li>
              <li>
                <button
                  onClick={() => navigate('/privacy')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Privacy Policy
                </button>
              </li>
              <li>
                <button
                  onClick={() => navigate('/terms')}
                  className="hover:text-brand-vibrant-orange transition-colors cursor-pointer text-left"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Terms of Service
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Nature-inspired Elements */}
        <div className="flex justify-center space-x-6 mb-6 text-2xl">
          <span title="Growth & Stability">🌳</span>
          <span title="Innovation">🍄</span>
          <span title="Interconnection">🕸️</span>
          <span title="Natural Flow">🌿</span>
          <span title="Adaptation">🌊</span>
          <span title="Collaboration">🐝</span>
          <span title="Intelligence">🦊</span>
          <span title="Wisdom">🦉</span>
          <span title="Transformation">🦋</span>
        </div>

        {/* Bottom Bar */}
        <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center" style={{ borderColor: 'var(--color-border)' }}>
          <p className="text-sm mb-4 md:mb-0" style={{ color: 'var(--color-text-muted)' }}>
            © 2025 Cahoots LLC. All rights reserved.
          </p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Built with ❤️ for software development teams
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
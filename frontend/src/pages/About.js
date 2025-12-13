import React from 'react';
import { useNavigate } from 'react-router-dom';
import Footer from '../components/Footer';
import { tokens } from '../design-system';

const About = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: '10%',
          right: '10%',
          width: '400px',
          height: '400px',
          background: `radial-gradient(circle, ${tokens.colors.primary[500]}15 0%, transparent 70%)`,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />

        <div className="max-w-4xl mx-auto px-4 py-20 relative z-10">
          <div style={{ textAlign: 'center' }}>
            <span style={{
              display: 'inline-block',
              padding: '8px 16px',
              backgroundColor: `${tokens.colors.primary[500]}15`,
              color: tokens.colors.primary[400],
              borderRadius: '9999px',
              fontSize: '14px',
              fontWeight: '600',
              marginBottom: '24px',
            }}>
              About Cahoots
            </span>
            <h1 style={{
              fontSize: 'clamp(36px, 5vw, 56px)',
              fontWeight: '800',
              lineHeight: '1.1',
              marginBottom: '24px',
              color: 'var(--color-text)',
              letterSpacing: '-1px',
            }}>
              Turn Ideas Into{' '}
              <span style={{
                background: `linear-gradient(135deg, ${tokens.colors.primary[400]} 0%, ${tokens.colors.warning[500]} 100%)`,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>Actionable Plans</span>
            </h1>
            <p style={{
              fontSize: '20px',
              color: 'var(--color-text-muted)',
              maxWidth: '600px',
              margin: '0 auto',
              lineHeight: '1.6',
            }}>
              Cahoots turns project ideas into actionable plans. Describe what you want to build,
              and get back a structured breakdown with user stories, tasks, and technical specs.
            </p>
          </div>
        </div>
      </div>

      {/* What It Does */}
      <div className="py-20" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-5xl mx-auto px-4">
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{
              fontSize: '36px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '16px',
            }}>
              What Cahoots Does
            </h2>
            <p style={{ fontSize: '18px', color: 'var(--color-text-muted)' }}>
              Everything you need to go from idea to implementation
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '24px',
          }}>
            <FeatureCard
              icon="📋"
              title="Task Decomposition"
              description="Write a project description in plain English. Cahoots breaks it down into epics, user stories with acceptance criteria, and implementation tasks with story points."
            />
            <FeatureCard
              icon="🔄"
              title="Event Modeling"
              description="Get a system design that shows how users interact with your app—what commands they can run, what events happen, and what data gets displayed."
            />
            <FeatureCard
              icon="💻"
              title="Code Generation"
              description="Generate a working codebase from your event model. Push it to GitHub and start building immediately."
            />
            <FeatureCard
              icon="📤"
              title="Export Anywhere"
              description="Export your project plan to JSON, Markdown, or CSV. Import into Jira, Trello, or whatever tools you use."
            />
          </div>
        </div>
      </div>

      {/* Who It's For */}
      <div className="py-20" style={{ backgroundColor: 'var(--color-bg)' }}>
        <div className="max-w-5xl mx-auto px-4">
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{
              fontSize: '36px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '16px',
            }}>
              Who It's For
            </h2>
            <p style={{ fontSize: '18px', color: 'var(--color-text-muted)' }}>
              Built for anyone who builds software
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '32px',
          }}>
            <PersonaCard
              icon="👨‍💻"
              title="Developers"
              description="Plan before you code. See the full picture of what you're building before writing a single line."
            />
            <PersonaCard
              icon="💼"
              title="Freelancers"
              description="Scope projects accurately and generate professional proposals with detailed breakdowns."
            />
            <PersonaCard
              icon="📊"
              title="Product Managers"
              description="Break down features into tasks your team can execute. Track story points and dependencies."
            />
            <PersonaCard
              icon="💡"
              title="Anyone with an Idea"
              description="See what building your software idea would actually involve before committing resources."
            />
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="py-20" style={{
        backgroundColor: 'var(--color-surface)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '600px',
          height: '600px',
          background: `radial-gradient(circle, ${tokens.colors.primary[500]}10 0%, transparent 60%)`,
          pointerEvents: 'none',
        }} />

        <div className="max-w-3xl mx-auto px-4 text-center relative z-10">
          <h2 style={{
            fontSize: '40px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '16px',
          }}>
            Ready to try it out?
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
            marginBottom: '32px',
          }}>
            Free tier available. No credit card required.
          </p>
          <button
            onClick={() => navigate('/')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '16px 32px',
              backgroundColor: tokens.colors.primary[500],
              color: 'white',
              fontSize: '18px',
              fontWeight: '600',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Try Cahoots
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '8px' }}>
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <Footer />
    </div>
  );
};

// Feature Card Component
const FeatureCard = ({ icon, title, description }) => (
  <div style={{
    padding: '32px',
    backgroundColor: 'var(--color-bg)',
    borderRadius: '16px',
    border: '1px solid var(--color-border)',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
  }}>
    <div style={{
      width: '56px',
      height: '56px',
      backgroundColor: `${tokens.colors.primary[500]}15`,
      borderRadius: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '28px',
      marginBottom: '20px',
    }}>
      {icon}
    </div>
    <h3 style={{
      fontSize: '20px',
      fontWeight: '600',
      color: 'var(--color-text)',
      marginBottom: '12px',
    }}>
      {title}
    </h3>
    <p style={{
      fontSize: '16px',
      color: 'var(--color-text-muted)',
      lineHeight: '1.6',
    }}>
      {description}
    </p>
  </div>
);

// Persona Card Component
const PersonaCard = ({ icon, title, description }) => (
  <div style={{
    display: 'flex',
    gap: '20px',
    padding: '24px',
    backgroundColor: 'var(--color-surface)',
    borderRadius: '12px',
    border: '1px solid var(--color-border)',
  }}>
    <div style={{
      width: '48px',
      height: '48px',
      backgroundColor: `${tokens.colors.secondary[500]}15`,
      borderRadius: '10px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '24px',
      flexShrink: 0,
    }}>
      {icon}
    </div>
    <div>
      <h3 style={{
        fontSize: '18px',
        fontWeight: '600',
        color: 'var(--color-text)',
        marginBottom: '8px',
      }}>
        {title}
      </h3>
      <p style={{
        fontSize: '15px',
        color: 'var(--color-text-muted)',
        lineHeight: '1.5',
      }}>
        {description}
      </p>
    </div>
  </div>
);

export default About;

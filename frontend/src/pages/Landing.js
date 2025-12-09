import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Footer from '../components/Footer';
import SEO from '../components/SEO';
import { tokens } from '../design-system';

// ============================================================================
// LANDING PAGE - Product Showcase Design
// ============================================================================

const Landing = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // If user is logged in, redirect to dashboard
  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <SEO
        title="AI-Powered Project Planning & Code Generation"
        description="Turn your project ideas into working code. Cahoots uses AI to create system blueprints, generate implementation tasks, and write production-ready code automatically."
      />

      {/* Navigation Bar */}
      <NavBar onGetStarted={() => navigate('/login')} />

      {/* Hero Section with Product Screenshot */}
      <HeroSection onGetStarted={() => navigate('/login')} />

      {/* Product Demo Section */}
      <ProductDemoSection />

      {/* Feature Showcase with Screenshots */}
      <FeatureShowcase />

      {/* How It Works - Visual Flow */}
      <HowItWorksSection />

      {/* Use Cases */}
      <UseCasesSection />

      {/* Final CTA */}
      <FinalCTASection onGetStarted={() => navigate('/login')} />

      <Footer />
    </div>
  );
};

// ============================================================================
// NAVIGATION BAR
// ============================================================================

const NavBar = ({ onGetStarted }) => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 1000,
      padding: '16px 24px',
      backgroundColor: scrolled ? 'rgba(13, 9, 3, 0.95)' : 'transparent',
      backdropFilter: scrolled ? 'blur(10px)' : 'none',
      transition: 'all 0.3s ease',
      borderBottom: scrolled ? '1px solid var(--color-border)' : 'none',
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img src="/icons/cottage.png" alt="Cahoots" width="36" height="36" />
          <span style={{
            fontSize: '24px',
            fontWeight: '700',
            color: 'var(--color-text)',
            letterSpacing: '-0.5px',
          }}>Cahoots</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
          <a href="#features" style={navLinkStyle}>Features</a>
          <a href="#how-it-works" style={navLinkStyle}>How It Works</a>
          <a href="#use-cases" style={navLinkStyle}>Use Cases</a>
          <button onClick={onGetStarted} style={primaryButtonStyle}>
            Get Started Free
          </button>
        </div>
      </div>
    </nav>
  );
};

const navLinkStyle = {
  color: 'var(--color-text-muted)',
  textDecoration: 'none',
  fontSize: '15px',
  fontWeight: '500',
  transition: 'color 0.2s ease',
};

// ============================================================================
// HERO SECTION
// ============================================================================

const HeroSection = ({ onGetStarted }) => {
  return (
    <section style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      padding: '120px 24px 80px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background gradient orbs */}
      <div style={{
        position: 'absolute',
        top: '10%',
        left: '10%',
        width: '600px',
        height: '600px',
        background: `radial-gradient(circle, ${tokens.colors.primary[500]}15 0%, transparent 70%)`,
        filter: 'blur(60px)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        bottom: '20%',
        right: '5%',
        width: '500px',
        height: '500px',
        background: `radial-gradient(circle, ${tokens.colors.secondary[400]}15 0%, transparent 70%)`,
        filter: 'blur(60px)',
        pointerEvents: 'none',
      }} />

      <div style={{ maxWidth: '1200px', margin: '0 auto', position: 'relative', zIndex: 1 }}>
        {/* Badge */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: `${tokens.colors.primary[500]}20`,
            border: `1px solid ${tokens.colors.primary[500]}40`,
            borderRadius: '9999px',
            fontSize: '14px',
            fontWeight: '500',
            color: tokens.colors.primary[400],
          }}>
            <span style={{ fontSize: '12px' }}>NEW</span>
            AI-Powered Code Generation Now Available
          </span>
        </div>

        {/* Main Headline */}
        <h1 style={{
          fontSize: 'clamp(40px, 6vw, 72px)',
          fontWeight: '800',
          textAlign: 'center',
          lineHeight: '1.1',
          marginBottom: '24px',
          color: 'var(--color-text)',
          letterSpacing: '-2px',
        }}>
          Turn Your Ideas Into<br />
          <span style={{
            background: `linear-gradient(135deg, ${tokens.colors.primary[400]} 0%, ${tokens.colors.warning[500]} 100%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>Production-Ready Code</span>
        </h1>

        {/* Subheadline */}
        <p style={{
          fontSize: '20px',
          textAlign: 'center',
          color: 'var(--color-text-muted)',
          maxWidth: '700px',
          margin: '0 auto 40px',
          lineHeight: '1.6',
        }}>
          Describe your project in plain English. Cahoots creates a complete system blueprint,
          breaks it into tasks, and generates working code with pull requests ready to merge.
        </p>

        {/* CTA Buttons */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '16px',
          marginBottom: '64px',
          flexWrap: 'wrap',
        }}>
          <button onClick={onGetStarted} style={{
            ...primaryButtonStyle,
            padding: '16px 32px',
            fontSize: '18px',
          }}>
            Start Building Free
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '8px' }}>
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
          <button onClick={() => document.getElementById('demo-video')?.scrollIntoView({ behavior: 'smooth' })} style={{
            ...secondaryButtonStyle,
            padding: '16px 32px',
            fontSize: '18px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{ marginRight: '8px' }}>
              <path d="M8 5v14l11-7z" />
            </svg>
            Watch Demo
          </button>
        </div>

        {/* Product Screenshot - Hero Image */}
        <div style={{
          position: 'relative',
          maxWidth: '1100px',
          margin: '0 auto',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: `0 50px 100px -20px rgba(0, 0, 0, 0.5), 0 30px 60px -30px rgba(0, 0, 0, 0.3), 0 0 0 1px ${tokens.colors.neutral[800]}`,
        }}>
          {/* Browser chrome */}
          <div style={{
            backgroundColor: tokens.colors.neutral[900],
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            borderBottom: `1px solid ${tokens.colors.neutral[800]}`,
          }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ff5f57' }} />
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#febc2e' }} />
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#28c840' }} />
            </div>
            <div style={{
              flex: 1,
              backgroundColor: tokens.colors.neutral[800],
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              color: 'var(--color-text-muted)',
              textAlign: 'center',
            }}>
              app.cahoots.dev
            </div>
          </div>

          {/* Screenshot placeholder - you'll replace this with actual screenshot */}
          <div style={{
            backgroundColor: tokens.colors.neutral[950],
            aspectRatio: '16/9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
          }}>
            {/* Placeholder - Replace with: <img src="/images/hero-screenshot.png" alt="Cahoots Dashboard" style={{ width: '100%' }} /> */}
            <div style={{
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              padding: '40px',
            }}>
              <div style={{
                width: '80px',
                height: '80px',
                margin: '0 auto 16px',
                backgroundColor: `${tokens.colors.primary[500]}20`,
                borderRadius: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '36px',
              }}>
                📸
              </div>
              <p style={{ fontSize: '18px', marginBottom: '8px' }}>Hero Screenshot</p>
              <p style={{ fontSize: '14px', opacity: 0.7 }}>
                Replace with a screenshot showing the dashboard<br />
                with a project being analyzed or code being generated
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ============================================================================
// PRODUCT DEMO SECTION
// ============================================================================

const ProductDemoSection = () => {
  return (
    <section id="demo-video" style={{
      padding: '100px 24px',
      backgroundColor: 'var(--color-bg)',
    }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
        <h2 style={{
          fontSize: '40px',
          fontWeight: '700',
          color: 'var(--color-text)',
          marginBottom: '16px',
        }}>
          See Cahoots in Action
        </h2>
        <p style={{
          fontSize: '18px',
          color: 'var(--color-text-muted)',
          marginBottom: '48px',
          maxWidth: '600px',
          margin: '0 auto 48px',
        }}>
          Watch how a simple project description transforms into a complete codebase
          with pull requests ready to review.
        </p>

        {/* Video Player Container */}
        <div style={{
          position: 'relative',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: `0 25px 50px -12px rgba(0, 0, 0, 0.4)`,
          border: `1px solid ${tokens.colors.neutral[800]}`,
          aspectRatio: '16/9',
          backgroundColor: tokens.colors.neutral[950],
        }}>
          {/* Video placeholder - Replace with actual video embed */}
          <div style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}>
            <div style={{
              textAlign: 'center',
              padding: '40px',
            }}>
              {/* Play button */}
              <div style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                backgroundColor: tokens.colors.primary[500],
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 24px',
                boxShadow: `0 0 0 8px ${tokens.colors.primary[500]}30`,
                cursor: 'pointer',
                transition: 'transform 0.2s ease',
              }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="white">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '16px' }}>
                Click to play demo video
              </p>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', opacity: 0.7, marginTop: '8px' }}>
                Replace with video embed or YouTube/Vimeo link
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ============================================================================
// FEATURE SHOWCASE
// ============================================================================

const FeatureShowcase = () => {
  return (
    <section id="features" style={{
      padding: '100px 24px',
      backgroundColor: 'var(--color-surface)',
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '80px' }}>
          <h2 style={{
            fontSize: '40px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '16px',
          }}>
            Everything You Need to Ship Faster
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
            maxWidth: '600px',
            margin: '0 auto',
          }}>
            From idea to production code in minutes, not weeks.
          </p>
        </div>

        {/* Feature 1: Project Breakdown */}
        <FeatureBlock
          badge="AI-Powered Analysis"
          title="From Idea to Organized Plan"
          description="Describe your project and watch as AI breaks it into Epics, User Stories, and organized Chapters. Everything structured and ready for development."
          imagePlaceholder="Screenshot of the Summary tab showing project stats, epics count, stories, and chapters"
          imageAlt="Project Summary Screenshot"
          reversed={false}
          highlights={[
            'Automatic Epic & Story generation',
            'Organized into logical chapters',
            'Editable and refinable with AI assistance',
          ]}
        />

        {/* Feature 2: Task Generation */}
        <FeatureBlock
          badge="Smart Decomposition"
          title="Tasks That Actually Make Sense"
          description="No more vague tickets. Every task includes clear descriptions, story points, and fits into a proper hierarchy. Perfect for solo devs or teams."
          imagePlaceholder="Screenshot of the All Tasks view showing the expandable task tree with story points"
          imageAlt="Task Tree Screenshot"
          reversed={true}
          highlights={[
            'Hierarchical task breakdown',
            'Story point estimation',
            'Export to Trello, JIRA, or GitHub',
          ]}
        />

        {/* Feature 3: Code Generation */}
        <FeatureBlock
          badge="Code Generation"
          title="From Tasks to Working Code"
          description="One click generates production-ready code for your entire project. APIs, database schemas, frontend components - automatically created and pushed to your repository."
          imagePlaceholder="Screenshot of code generation in progress or the tech stack selection modal"
          imageAlt="Code Generation Screenshot"
          reversed={false}
          highlights={[
            'Full-stack code generation',
            'Automatic pull request creation',
            'Multiple tech stack support',
          ]}
        />
      </div>
    </section>
  );
};

const FeatureBlock = ({ badge, title, description, imagePlaceholder, imageAlt, reversed, highlights }) => (
  <div style={{
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '80px',
    alignItems: 'center',
    marginBottom: '120px',
  }}>
    <div style={{ order: reversed ? 2 : 1 }}>
      <span style={{
        display: 'inline-block',
        padding: '6px 12px',
        backgroundColor: `${tokens.colors.primary[500]}15`,
        color: tokens.colors.primary[400],
        borderRadius: '6px',
        fontSize: '13px',
        fontWeight: '600',
        marginBottom: '16px',
      }}>
        {badge}
      </span>
      <h3 style={{
        fontSize: '32px',
        fontWeight: '700',
        color: 'var(--color-text)',
        marginBottom: '16px',
        lineHeight: '1.2',
      }}>
        {title}
      </h3>
      <p style={{
        fontSize: '18px',
        color: 'var(--color-text-muted)',
        lineHeight: '1.6',
        marginBottom: '24px',
      }}>
        {description}
      </p>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {highlights.map((item, i) => (
          <li key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '12px',
            fontSize: '16px',
            color: 'var(--color-text)',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2">
              <path d="M20 6L9 17l-5-5" />
            </svg>
            {item}
          </li>
        ))}
      </ul>
    </div>

    <div style={{ order: reversed ? 1 : 2 }}>
      {/* Screenshot placeholder */}
      <div style={{
        backgroundColor: tokens.colors.neutral[900],
        borderRadius: '12px',
        padding: '8px',
        boxShadow: `0 25px 50px -12px rgba(0, 0, 0, 0.4)`,
        border: `1px solid ${tokens.colors.neutral[800]}`,
      }}>
        <div style={{
          backgroundColor: tokens.colors.neutral[950],
          borderRadius: '8px',
          aspectRatio: '4/3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: '24px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              margin: '0 auto 12px',
              backgroundColor: `${tokens.colors.primary[500]}20`,
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
            }}>
              📸
            </div>
            <p style={{ fontSize: '14px' }}>{imagePlaceholder}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
);

// ============================================================================
// HOW IT WORKS SECTION
// ============================================================================

const HowItWorksSection = () => {
  const steps = [
    {
      number: '01',
      title: 'Describe Your Project',
      description: 'Write a description of what you want to build. Be as detailed or high-level as you like.',
      icon: '✏️',
    },
    {
      number: '02',
      title: 'AI Creates Your Blueprint',
      description: 'Watch in real-time as AI analyzes your requirements and creates a complete system design.',
      icon: '🧠',
    },
    {
      number: '03',
      title: 'Review & Refine',
      description: 'Edit modules, add features, or ask AI to make changes. You\'re always in control.',
      icon: '✨',
    },
    {
      number: '04',
      title: 'Generate Code',
      description: 'Select your tech stack and generate production-ready code with a single click.',
      icon: '🚀',
    },
  ];

  return (
    <section id="how-it-works" style={{
      padding: '100px 24px',
      backgroundColor: 'var(--color-bg)',
    }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '64px' }}>
          <h2 style={{
            fontSize: '40px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '16px',
          }}>
            From Idea to Code in 4 Steps
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
          }}>
            No complex setup. No learning curve. Just describe and build.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '32px',
          position: 'relative',
        }}>
          {/* Connection line */}
          <div style={{
            position: 'absolute',
            top: '40px',
            left: '12.5%',
            right: '12.5%',
            height: '2px',
            background: `linear-gradient(90deg, ${tokens.colors.primary[500]} 0%, ${tokens.colors.secondary[400]} 100%)`,
            opacity: 0.3,
          }} />

          {steps.map((step, i) => (
            <div key={i} style={{ textAlign: 'center', position: 'relative' }}>
              <div style={{
                width: '80px',
                height: '80px',
                margin: '0 auto 24px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-surface)',
                border: `2px solid ${tokens.colors.primary[500]}40`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '32px',
                position: 'relative',
                zIndex: 1,
              }}>
                {step.icon}
              </div>
              <div style={{
                fontSize: '12px',
                fontWeight: '700',
                color: tokens.colors.primary[400],
                marginBottom: '8px',
                letterSpacing: '1px',
              }}>
                STEP {step.number}
              </div>
              <h3 style={{
                fontSize: '18px',
                fontWeight: '600',
                color: 'var(--color-text)',
                marginBottom: '8px',
              }}>
                {step.title}
              </h3>
              <p style={{
                fontSize: '14px',
                color: 'var(--color-text-muted)',
                lineHeight: '1.5',
              }}>
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============================================================================
// USE CASES SECTION
// ============================================================================

const UseCasesSection = () => {
  const useCases = [
    {
      icon: '🚀',
      title: 'Side Projects',
      description: 'Go from idea to MVP in a weekend. Perfect for indie hackers and hobbyists.',
    },
    {
      icon: '🏢',
      title: 'Startups',
      description: 'Ship features faster with AI-generated boilerplate and clear task breakdowns.',
    },
    {
      icon: '👨‍💻',
      title: 'Freelancers',
      description: 'Estimate projects accurately and deliver consistent quality every time.',
    },
    {
      icon: '📚',
      title: 'Learning',
      description: 'Understand how production apps are structured by seeing the complete system design.',
    },
  ];

  return (
    <section id="use-cases" style={{
      padding: '100px 24px',
      backgroundColor: 'var(--color-surface)',
    }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '64px' }}>
          <h2 style={{
            fontSize: '40px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '16px',
          }}>
            Built for How You Work
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
          }}>
            Whether you're solo or on a team, Cahoots adapts to your workflow.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '24px',
        }}>
          {useCases.map((useCase, i) => (
            <div key={i} style={{
              padding: '32px',
              backgroundColor: 'var(--color-bg)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}>
              <div style={{
                fontSize: '40px',
                marginBottom: '16px',
              }}>
                {useCase.icon}
              </div>
              <h3 style={{
                fontSize: '20px',
                fontWeight: '600',
                color: 'var(--color-text)',
                marginBottom: '8px',
              }}>
                {useCase.title}
              </h3>
              <p style={{
                fontSize: '16px',
                color: 'var(--color-text-muted)',
                lineHeight: '1.5',
              }}>
                {useCase.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============================================================================
// FINAL CTA SECTION
// ============================================================================

const FinalCTASection = ({ onGetStarted }) => {
  return (
    <section style={{
      padding: '120px 24px',
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
        width: '800px',
        height: '800px',
        background: `radial-gradient(circle, ${tokens.colors.primary[500]}10 0%, transparent 60%)`,
        pointerEvents: 'none',
      }} />

      <div style={{
        maxWidth: '700px',
        margin: '0 auto',
        textAlign: 'center',
        position: 'relative',
        zIndex: 1,
      }}>
        <h2 style={{
          fontSize: '48px',
          fontWeight: '700',
          color: 'var(--color-text)',
          marginBottom: '24px',
          lineHeight: '1.1',
        }}>
          Ready to Build Something Amazing?
        </h2>
        <p style={{
          fontSize: '20px',
          color: 'var(--color-text-muted)',
          marginBottom: '40px',
          lineHeight: '1.6',
        }}>
          Stop planning. Start shipping. Your next project is waiting.
        </p>
        <button onClick={onGetStarted} style={{
          ...primaryButtonStyle,
          padding: '20px 48px',
          fontSize: '20px',
        }}>
          Get Started Free
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '12px' }}>
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
        <p style={{
          marginTop: '16px',
          fontSize: '14px',
          color: 'var(--color-text-muted)',
        }}>
          No credit card required. Free tier available.
        </p>
      </div>
    </section>
  );
};

// ============================================================================
// SHARED STYLES
// ============================================================================

const primaryButtonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '12px 24px',
  backgroundColor: tokens.colors.primary[500],
  color: 'white',
  fontSize: '16px',
  fontWeight: '600',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
};

const secondaryButtonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '12px 24px',
  backgroundColor: 'transparent',
  color: 'var(--color-text)',
  fontSize: '16px',
  fontWeight: '600',
  border: '1px solid var(--color-border)',
  borderRadius: '8px',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
};

export default Landing;

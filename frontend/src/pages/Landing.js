import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toaster } from '../components/ui/toaster';
import Footer from '../components/Footer';
import SEO from '../components/SEO';
import { tokens } from '../design-system';

// Custom hook for responsive design
const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }
    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
};

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

  // Scroll to the login form at the top of the page
  const scrollToLogin = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <SEO
        title="AI-Powered Project Decomposition & Planning"
        description="Transform complex project ideas into actionable plans. Cahoots uses AI to break down requirements into epics, stories, and implementation tasks with story points and dependencies."
      />

      {/* Navigation Bar */}
      <NavBar onGetStarted={scrollToLogin} />

      {/* Hero Section with Login Form */}
      <HeroSection />

      {/* Feature Showcase with Screenshots */}
      <FeatureShowcase />

      {/* How It Works - Visual Flow */}
      <HowItWorksSection />

      {/* Use Cases */}
      <UseCasesSection />

      {/* Pricing Section */}
      <PricingSection onGetStarted={scrollToLogin} />

      {/* Final CTA */}
      <FinalCTASection onGetStarted={scrollToLogin} />

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

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <a href="#pricing" style={navLinkStyle}>Pricing</a>
          <button onClick={onGetStarted} style={primaryButtonStyle}>
            Try Cahoots
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
// HERO SECTION WITH LOGIN
// ============================================================================

const HeroSection = () => {
  const navigate = useNavigate();
  const { login, getOAuthUrl } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);
  const isMobile = useMediaQuery('(max-width: 1024px)');
  const isSmallMobile = useMediaQuery('(max-width: 640px)');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await login(email, password);
      toaster.create({
        title: 'Login successful',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/dashboard');
    } catch (error) {
      toaster.create({
        title: 'Login failed',
        description: error.response?.data?.detail || 'Invalid credentials',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOAuthLogin = async (provider) => {
    if (isOAuthLoading) return;
    sessionStorage.removeItem('oauth_state');
    setIsOAuthLoading(true);
    try {
      const authUrl = await getOAuthUrl(provider);
      localStorage.setItem('oauth_request_time', Date.now().toString());
      localStorage.setItem('oauth_flow_started', 'true');
      window.location.href = authUrl;
    } catch (error) {
      console.error('OAuth login error:', error);
      setIsOAuthLoading(false);
      toaster.create({
        title: `${provider} login failed`,
        description: error.response?.data?.detail || 'Failed to initiate OAuth flow',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      localStorage.removeItem('oauth_flow_started');
    }
  };

  const handleDevBypass = () => {
    localStorage.setItem('token', 'dev-bypass-token');
    localStorage.setItem('user', JSON.stringify({
      id: 'dev-user-123',
      email: 'test@example.com',
      username: 'testuser',
      full_name: 'Test User'
    }));
    toaster.create({
      title: 'Development login successful',
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
    navigate('/dashboard');
  };

  return (
    <section style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      padding: '100px 24px 80px',
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

      <div style={{ maxWidth: '1600px', margin: '0 auto', position: 'relative', zIndex: 1, width: '100%', padding: isSmallMobile ? '0 20px' : '0 60px' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : '1fr 520px',
          gap: isMobile ? '48px' : '80px',
          alignItems: 'center',
        }}>
          {/* Left side - Copy */}
          <div>
            <h1 style={{
              fontSize: isSmallMobile ? '36px' : isMobile ? '52px' : '80px',
              fontWeight: '800',
              lineHeight: '1.0',
              marginBottom: isSmallMobile ? '24px' : '40px',
              color: 'var(--color-text)',
              letterSpacing: isSmallMobile ? '-1px' : '-3px',
            }}>
              Turn Complex Ideas Into{' '}
              <span style={{
                background: `linear-gradient(135deg, ${tokens.colors.primary[400]} 0%, ${tokens.colors.warning[500]} 100%)`,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>Actionable Plans</span>
            </h1>

            <p style={{
              fontSize: isSmallMobile ? '17px' : isMobile ? '20px' : '26px',
              color: 'var(--color-text-muted)',
              marginBottom: isSmallMobile ? '32px' : '48px',
              lineHeight: '1.5',
              maxWidth: '700px',
            }}>
              Describe your project in plain English. Get back user stories, tasks with story points, and technical specs.
            </p>

            <div style={{ display: 'flex', flexDirection: isSmallMobile ? 'column' : 'row', flexWrap: 'wrap', gap: isSmallMobile ? '12px' : isMobile ? '20px' : '40px', color: 'var(--color-text-muted)', fontSize: isSmallMobile ? '16px' : isMobile ? '18px' : '22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <svg width={isSmallMobile ? '22' : '28'} height={isSmallMobile ? '22' : '28'} viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2.5">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Task decomposition
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <svg width={isSmallMobile ? '22' : '28'} height={isSmallMobile ? '22' : '28'} viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2.5">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Event modeling
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <svg width={isSmallMobile ? '22' : '28'} height={isSmallMobile ? '22' : '28'} viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2.5">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Code generation
              </div>
            </div>
          </div>

          {/* Right side - Login Form */}
          <div style={{
            backgroundColor: 'var(--color-surface)',
            borderRadius: isSmallMobile ? '16px' : '24px',
            padding: isSmallMobile ? '24px' : isMobile ? '32px' : '48px',
            border: '1px solid var(--color-border)',
            boxShadow: '0 30px 60px -12px rgba(0, 0, 0, 0.5)',
          }}>
            <h2 style={{ fontSize: isSmallMobile ? '22px' : isMobile ? '26px' : '32px', fontWeight: '600', marginBottom: isSmallMobile ? '24px' : '32px', color: 'var(--color-text)' }}>
              Try Cahoots
            </h2>

            <form onSubmit={handleSubmit} style={{ marginBottom: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '16px', fontWeight: '500', marginBottom: '10px', color: 'var(--color-text)' }}>
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="input-field"
                  style={{ width: '100%', padding: '18px 20px', fontSize: '17px', borderRadius: '12px' }}
                />
              </div>

              <div style={{ marginBottom: '32px' }}>
                <label style={{ display: 'block', fontSize: '16px', fontWeight: '500', marginBottom: '10px', color: 'var(--color-text)' }}>
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="input-field"
                  style={{ width: '100%', padding: '18px 20px', fontSize: '17px', borderRadius: '12px' }}
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  ...primaryButtonStyle,
                  width: '100%',
                  padding: '20px 28px',
                  fontSize: '18px',
                  borderRadius: '12px',
                  opacity: isSubmitting ? 0.7 : 1,
                }}
              >
                {isSubmitting ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '32px' }}>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--color-border)' }} />
              <span style={{ padding: '0 20px', fontSize: '15px', color: 'var(--color-text-muted)' }}>or</span>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--color-border)' }} />
            </div>

            {/* OAuth */}
            <button
              onClick={() => handleOAuthLogin('google')}
              disabled={isOAuthLoading}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '18px 28px',
                backgroundColor: 'white',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                fontSize: '17px',
                fontWeight: '500',
                color: '#374151',
                cursor: 'pointer',
                marginBottom: '16px',
              }}
            >
              <svg style={{ width: '24px', height: '24px', marginRight: '14px' }} viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {isOAuthLoading ? 'Connecting...' : 'Continue with Google'}
            </button>

            {/* Dev bypass */}
            {(window.CAHOOTS_CONFIG?.ENVIRONMENT === 'development') && (
              <button
                onClick={handleDevBypass}
                style={{
                  width: '100%',
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  border: `1px solid ${tokens.colors.primary[500]}`,
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: tokens.colors.primary[500],
                  cursor: 'pointer',
                }}
              >
                Dev Bypass
              </button>
            )}

            {/* Sign up link */}
            <p style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: 'var(--color-text-muted)' }}>
              Don't have an account?{' '}
              <Link to="/register" style={{ color: tokens.colors.primary[500], textDecoration: 'none', fontWeight: '500' }}>
                Sign up
              </Link>
            </p>
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
            Everything You Need to Plan Better
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
            maxWidth: '600px',
            margin: '0 auto',
          }}>
            From vague idea to detailed implementation plan in minutes.
          </p>
        </div>

        {/* Feature 1: Multi-Persona Views */}
        <FeatureBlock
          badge="Role-Based Views"
          title="See What Matters to You"
          description="Switch between PM, Developer, and Consultant perspectives. Each view shows the exact information that role needs - from task lists to technical specs to client proposals."
          image="/images/feature-1.png"
          imagePlaceholder="Screenshot showing the persona selector with PM/Dev/Consultant tabs and their different views"
          imageAlt="Multi-Persona Views Screenshot"
          reversed={false}
          highlights={[
            'PM view: Tasks, story points & progress tracking',
            'Dev view: Technical specs, test scenarios & system design',
            'Consultant view: Scope analysis & proposal generation',
          ]}
        />

        {/* Feature 2: Implementation Tasks */}
        <FeatureBlock
          badge="Smart Decomposition"
          title="Tasks That Actually Make Sense"
          description="Every task includes clear descriptions, story points, implementation details, and dependency tracking. Expand any task to see what it depends on and how to build it."
          image="/images/feature-2.png"
          imagePlaceholder="Screenshot of the Tasks tab showing expandable task cards with story points, dependencies, and implementation details"
          imageAlt="Task List Screenshot"
          reversed={true}
          highlights={[
            'Story points & complexity scoring',
            'Visual dependency tracking',
            'Detailed implementation guidance',
          ]}
        />

        {/* Feature 3: System Design */}
        <FeatureBlock
          badge="Technical Architecture"
          title="System Design Included"
          description="Cahoots doesn't just list tasks—it maps out how your system works. See what commands trigger what events, and how data flows through your application."
          image="/images/feature-3.png"
          imagePlaceholder="Screenshot of the Dev view showing system components organized by feature area"
          imageAlt="System Design Screenshot"
          reversed={false}
          highlights={[
            'Commands, events & data flow',
            'Test scenarios in Given-When-Then format',
            'Organized by feature area',
          ]}
        />

        {/* Feature 4: Flexible Export */}
        <FeatureBlock
          badge="Universal Export"
          title="Export Anywhere, Any Format"
          description="Export your project artifacts to JSON, CSV, Markdown, or YAML. Create LLM prompts for design reviews or implementation guides. Download as a single file or organized ZIP archive."
          image="/images/feature-4.png"
          imagePlaceholder="Screenshot of the Export modal showing artifact selection, format options, and download structure"
          imageAlt="Export Modal Screenshot"
          reversed={true}
          highlights={[
            'Multiple formats: JSON, CSV, Markdown, YAML',
            'LLM prompt templates for AI assistance',
            'Single document or ZIP with separate files',
            'Export your project plan to JIRA or Trello'
          ]}
        />
      </div>
    </section>
  );
};

const FeatureBlock = ({ badge, title, description, image, imagePlaceholder, imageAlt, reversed, highlights }) => {
  const isMobile = useMediaQuery('(max-width: 768px)');

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
      gap: isMobile ? '40px' : '80px',
      alignItems: 'center',
      marginBottom: isMobile ? '60px' : '120px',
    }}>
      <div style={{ order: isMobile ? 1 : (reversed ? 2 : 1) }}>
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

    <div style={{ order: isMobile ? 2 : (reversed ? 1 : 2) }}>
      <div style={{
        backgroundColor: tokens.colors.neutral[900],
        borderRadius: '12px',
        padding: '8px',
        boxShadow: `0 25px 50px -12px rgba(0, 0, 0, 0.4)`,
        border: `1px solid ${tokens.colors.neutral[800]}`,
      }}>
        {image ? (
          <img
            src={image}
            alt={imageAlt || title}
            style={{
              width: '100%',
              borderRadius: '8px',
              display: 'block',
            }}
          />
        ) : (
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
        )}
      </div>
    </div>
  </div>
  );
};

// ============================================================================
// HOW IT WORKS SECTION
// ============================================================================

const HowItWorksSection = () => {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');

  const steps = [
    {
      number: '01',
      title: 'Describe Your Project',
      description: 'Write a description of what you want to build. Be as detailed or high-level as you like.',
      icon: '✏️',
    },
    {
      number: '02',
      title: 'AI Breaks It Down',
      description: 'Watch in real-time as AI creates epics, user stories, and maps out how your system should work.',
      icon: '🧠',
    },
    {
      number: '03',
      title: 'Generate Tasks',
      description: 'Get detailed implementation tasks with story points, dependencies, and technical guidance.',
      icon: '📋',
    },
    {
      number: '04',
      title: 'Export & Execute',
      description: 'Export to JIRA, Trello, or your favorite tool. Share proposals with clients. Start building.',
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
            From Idea to Plan in 4 Steps
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
          }}>
            No complex setup. No learning curve. Just describe and plan.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : isTablet ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
          gap: isMobile ? '32px' : '32px',
          position: 'relative',
        }}>
          {/* Connection line - hide on mobile */}
          {!isMobile && (
            <div style={{
              position: 'absolute',
              top: '40px',
              left: '12.5%',
              right: '12.5%',
              height: '2px',
              background: `linear-gradient(90deg, ${tokens.colors.primary[500]} 0%, ${tokens.colors.secondary[400]} 100%)`,
              opacity: 0.3,
            }} />
          )}

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
  const isMobile = useMediaQuery('(max-width: 640px)');

  const useCases = [
    {
      icon: '🚀',
      title: 'Side Projects',
      description: 'Turn your weekend idea into a clear plan before writing a single line of code.',
    },
    {
      icon: '🏢',
      title: 'Startups',
      description: 'Break down features into manageable tasks. Keep the whole team aligned on what to build.',
    },
    {
      icon: '👨‍💻',
      title: 'Freelancers & Consultants',
      description: 'Generate professional proposals with scope analysis. Estimate projects accurately with story points.',
    },
    {
      icon: '📐',
      title: 'Technical Architects',
      description: 'Map out system behavior and data flows. Export technical specs for your team to implement.',
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
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
          gap: isMobile ? '16px' : '24px',
        }}>
          {useCases.map((useCase, i) => (
            <div key={i} style={{
              padding: isMobile ? '24px' : '32px',
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
// PRICING SECTION
// ============================================================================

const PricingSection = ({ onGetStarted }) => {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');

  const tiers = [
    {
      name: 'Free',
      price: '$0',
      period: '/month',
      description: 'Perfect for trying out Cahoots',
      features: [
        'Task decomposition',
        'Event modeling',
        'Unlimited projects',
        'Community support',
      ],
      cta: 'Try Cahoots',
      ctaAction: onGetStarted,
      highlighted: false,
    },
    {
      name: 'Hobbyist',
      price: '$10',
      period: '/month',
      description: 'For side projects and personal use',
      features: [
        'Everything in Free, plus:',
        'Export to JSON/Markdown',
        'Email support',
      ],
      cta: 'Try Cahoots',
      ctaAction: onGetStarted,
      highlighted: false,
    },
    {
      name: 'Pro',
      price: '$50',
      period: '/month',
      description: 'For professional developers and teams',
      features: [
        'Everything in Hobbyist, plus:',
        'Code generation',
        'GitHub integration',
        'API access',
        'Priority email support',
      ],
      cta: 'Try Cahoots',
      ctaAction: onGetStarted,
      highlighted: true,
      badge: 'Most Popular',
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'For large teams with custom needs',
      features: [
        'Everything in Pro, plus:',
        'SSO/SAML authentication',
        'Custom integrations',
        'Priority support',
        'Dedicated account manager',
      ],
      cta: 'Contact Sales',
      ctaAction: () => window.location.href = 'mailto:sales@cahoots.cc',
      highlighted: false,
    },
  ];

  return (
    <section id="pricing" style={{
      padding: '100px 24px',
      backgroundColor: 'var(--color-bg)',
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '64px' }}>
          <h2 style={{
            fontSize: '40px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '16px',
          }}>
            Simple, Transparent Pricing
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
            maxWidth: '600px',
            margin: '0 auto',
          }}>
            Start free and upgrade as you grow. No hidden fees.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : isTablet ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
          gap: isMobile ? '16px' : '20px',
          alignItems: 'stretch',
        }}>
          {tiers.map((tier, i) => (
            <div key={i} style={{
              padding: isMobile ? '24px' : '32px',
              backgroundColor: tier.highlighted ? `${tokens.colors.primary[500]}10` : 'var(--color-surface)',
              borderRadius: '16px',
              border: tier.highlighted
                ? `2px solid ${tokens.colors.primary[500]}`
                : '1px solid var(--color-border)',
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
            }}>
              {/* Popular Badge */}
              {tier.badge && (
                <div style={{
                  position: 'absolute',
                  top: '-12px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  backgroundColor: tokens.colors.primary[500],
                  color: 'white',
                  padding: '4px 16px',
                  borderRadius: '9999px',
                  fontSize: '12px',
                  fontWeight: '600',
                }}>
                  {tier.badge}
                </div>
              )}

              <div style={{ marginBottom: '24px' }}>
                <h3 style={{
                  fontSize: '24px',
                  fontWeight: '600',
                  color: 'var(--color-text)',
                  marginBottom: '8px',
                }}>
                  {tier.name}
                </h3>
                <p style={{
                  fontSize: '14px',
                  color: 'var(--color-text-muted)',
                  marginBottom: '16px',
                }}>
                  {tier.description}
                </p>
                <div style={{ display: 'flex', alignItems: 'baseline' }}>
                  <span style={{
                    fontSize: '48px',
                    fontWeight: '700',
                    color: 'var(--color-text)',
                  }}>
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span style={{
                      fontSize: '16px',
                      color: 'var(--color-text-muted)',
                      marginLeft: '4px',
                    }}>
                      {tier.period}
                    </span>
                  )}
                </div>
              </div>

              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                marginBottom: '32px',
                flex: 1,
              }}>
                {tier.features.map((feature, j) => (
                  <li key={j} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    marginBottom: '12px',
                    fontSize: '15px',
                    color: 'var(--color-text)',
                  }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                onClick={tier.ctaAction}
                style={tier.highlighted ? {
                  ...primaryButtonStyle,
                  width: '100%',
                  padding: '14px 24px',
                } : {
                  ...secondaryButtonStyle,
                  width: '100%',
                  padding: '14px 24px',
                }}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>

        <p style={{
          textAlign: 'center',
          marginTop: '32px',
          fontSize: '14px',
          color: 'var(--color-text-muted)',
        }}>
          All plans include 14-day free trial. Cancel anytime.
        </p>
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
          Ready to Plan Something Amazing?
        </h2>
        <p style={{
          fontSize: '20px',
          color: 'var(--color-text-muted)',
          marginBottom: '40px',
          lineHeight: '1.6',
        }}>
          Stop guessing scope. Start with a clear plan.
        </p>
        <button onClick={onGetStarted} style={{
          ...primaryButtonStyle,
          padding: '20px 48px',
          fontSize: '20px',
        }}>
          Try Cahoots
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '12px' }}>
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
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

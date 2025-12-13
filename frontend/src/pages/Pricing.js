import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { loadStripe } from '@stripe/stripe-js';
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout
} from '@stripe/react-stripe-js';
import { useAuth } from '../contexts/AuthContext';
import { useSubscription } from '../contexts/SubscriptionContext';
import Footer from '../components/Footer';
import SEO from '../components/SEO';
import { tokens } from '../design-system';
import { XMarkIcon } from '../design-system/icons';

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

// Stripe promise will be loaded dynamically
let stripePromise = null;

const Pricing = () => {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();
  const {
    subscription,
    plans,
    fetchPlans,
    createEmbeddedCheckout,
    getStripeConfig,
    error: subError
  } = useSubscription();
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const [clientSecret, setClientSecret] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState(null);

  // Check for canceled checkout
  const canceled = searchParams.get('canceled') === 'true';
  const success = searchParams.get('success') === 'true';

  // Initialize Stripe
  useEffect(() => {
    const initStripe = async () => {
      if (!stripePromise) {
        try {
          const config = await getStripeConfig();
          if (config?.publishable_key) {
            stripePromise = loadStripe(config.publishable_key);
          }
        } catch (err) {
          console.error('Failed to initialize Stripe:', err);
        }
      }
    };
    initStripe();
  }, [getStripeConfig]);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const handleGetStarted = async (planId) => {
    if (!isAuthenticated()) {
      navigate('/', { state: { returnTo: '/pricing' } });
      return;
    }

    if (planId === 'free') {
      navigate('/dashboard');
      return;
    }

    if (planId === 'enterprise') {
      window.location.href = 'mailto:sales@cahoots.cc?subject=Cahoots Enterprise Inquiry';
      return;
    }

    try {
      setCheckoutLoading(true);
      setSelectedPlanId(planId);
      const plan = plans.find(p => p.id === planId);
      if (!plan?.stripe_price_id) {
        alert('Payment system is not configured. Please contact support.');
        return;
      }

      // Create embedded checkout session
      const result = await createEmbeddedCheckout(plan.stripe_price_id);
      if (result?.client_secret) {
        setClientSecret(result.client_secret);
        setShowCheckoutModal(true);
      }
    } catch (err) {
      console.error('Checkout error:', err);
      alert('Failed to start checkout. Please try again.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleCloseCheckout = useCallback(() => {
    setShowCheckoutModal(false);
    setClientSecret(null);
    setSelectedPlanId(null);
  }, []);

  const currentTier = subscription?.tier || 'free';

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <SEO
        title="Pricing - Cahoots"
        description="Choose the plan that's right for your team. From free task decomposition to enterprise-grade features."
      />

      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Background decorations */}
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '5%',
          width: '400px',
          height: '400px',
          background: `radial-gradient(circle, ${tokens.colors.primary[500]}15 0%, transparent 70%)`,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute',
          top: '20%',
          right: '10%',
          width: '300px',
          height: '300px',
          background: `radial-gradient(circle, ${tokens.colors.secondary[500]}15 0%, transparent 70%)`,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />

        <div className="max-w-4xl mx-auto px-4 py-20 text-center relative z-10">
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
            Pricing Plans
          </span>
          <h1 style={{
            fontSize: 'clamp(36px, 5vw, 56px)',
            fontWeight: '800',
            lineHeight: '1.1',
            marginBottom: '20px',
            color: 'var(--color-text)',
            letterSpacing: '-1px',
          }}>
            Simple,{' '}
            <span style={{
              background: `linear-gradient(135deg, ${tokens.colors.primary[400]} 0%, ${tokens.colors.warning[500]} 100%)`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>Transparent</span>{' '}
            Pricing
          </h1>
          <p style={{
            fontSize: '20px',
            color: 'var(--color-text-muted)',
            maxWidth: '500px',
            margin: '0 auto',
          }}>
            Start free and upgrade as your needs grow. No hidden fees.
          </p>
          {canceled && (
            <div style={{
              marginTop: '24px',
              padding: '16px 24px',
              borderRadius: '12px',
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgb(245, 158, 11)',
              display: 'inline-block',
            }}>
              <p style={{ color: 'rgb(245, 158, 11)', margin: 0 }}>
                Checkout was canceled. Feel free to try again when you're ready.
              </p>
            </div>
          )}
          {success && (
            <div style={{
              marginTop: '24px',
              padding: '16px 24px',
              borderRadius: '12px',
              backgroundColor: `${tokens.colors.success[500]}15`,
              border: `1px solid ${tokens.colors.success[500]}`,
              display: 'inline-block',
            }}>
              <p style={{ color: tokens.colors.success[500], margin: 0 }}>
                Thank you for subscribing! Your Pro features are now active.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="py-20" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-7xl mx-auto px-4">
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : isTablet ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
            gap: isMobile ? '16px' : '20px',
            alignItems: 'stretch',
          }}>
            {/* Free Tier */}
            <PricingCard
              name="Free"
              price="$0"
              period="/month"
              description="Perfect for exploring Cahoots"
              icon="🚀"
              features={[
                { name: 'Task Decomposition', included: true },
                { name: 'Event Modeling', included: true },
                { name: 'Unlimited Projects', included: true },
                { name: 'Community Support', included: true },
              ]}
              buttonText={currentTier === 'free' ? 'Current Plan' : 'Try Cahoots'}
              buttonDisabled={currentTier === 'free'}
              onButtonClick={() => handleGetStarted('free')}
              loading={false}
            />

            {/* Hobbyist Tier */}
            <PricingCard
              name="Hobbyist"
              price="$10"
              period="/month"
              description="For side projects and personal use"
              icon="🎨"
              features={[
                { name: 'Everything in Free, plus:', included: true, highlight: true },
                { name: 'Export to JSON/Markdown', included: true },
                { name: 'Email Support', included: true },
              ]}
              buttonText={currentTier === 'hobbyist' ? 'Current Plan' : 'Upgrade to Hobbyist'}
              buttonDisabled={currentTier === 'hobbyist' || checkoutLoading}
              onButtonClick={() => handleGetStarted('hobbyist')}
              loading={checkoutLoading && selectedPlanId === 'hobbyist'}
            />

            {/* Pro Tier */}
            <PricingCard
              name="Pro"
              price="$50"
              period="/month"
              description="For professional developers and teams"
              icon="⚡"
              features={[
                { name: 'Everything in Hobbyist, plus:', included: true, highlight: true },
                { name: 'Code Generation', included: true },
                { name: 'GitHub Integration', included: true },
                { name: 'API Access', included: true },
                { name: 'Priority Email Support', included: true },
              ]}
              buttonText={currentTier === 'pro' ? 'Current Plan' : 'Upgrade to Pro'}
              buttonDisabled={currentTier === 'pro' || checkoutLoading}
              onButtonClick={() => handleGetStarted('pro')}
              loading={checkoutLoading && selectedPlanId === 'pro'}
              popular={true}
            />

            {/* Enterprise Tier */}
            <PricingCard
              name="Enterprise"
              price="Custom"
              period=""
              description="For large teams with custom needs"
              icon="🏢"
              features={[
                { name: 'Everything in Pro, plus:', included: true, highlight: true },
                { name: 'SSO / SAML', included: true },
                { name: 'Custom Integrations', included: true },
                { name: 'Priority Support', included: true },
                { name: 'Dedicated Account Manager', included: true },
              ]}
              buttonText={currentTier === 'enterprise' ? 'Current Plan' : 'Contact Sales'}
              buttonDisabled={currentTier === 'enterprise'}
              onButtonClick={() => handleGetStarted('enterprise')}
              loading={false}
            />
          </div>

          {subError && (
            <div style={{ marginTop: '32px', textAlign: 'center' }}>
              <p style={{ color: 'var(--color-error)' }}>{subError}</p>
            </div>
          )}

          <p style={{
            textAlign: 'center',
            marginTop: '40px',
            fontSize: '15px',
            color: 'var(--color-text-muted)',
          }}>
            All paid plans include a 14-day money-back guarantee. Cancel anytime.
          </p>
        </div>
      </div>

      {/* Feature Comparison */}
      <div className="py-20" style={{ backgroundColor: 'var(--color-bg)' }}>
        <div className="max-w-4xl mx-auto px-4">
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{
              fontSize: '36px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '16px',
            }}>
              Compare Plans
            </h2>
            <p style={{ fontSize: '18px', color: 'var(--color-text-muted)' }}>
              See what's included in each plan
            </p>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            borderRadius: '16px',
            border: '1px solid var(--color-border)',
            overflow: 'auto',
            WebkitOverflowScrolling: 'touch',
          }}>
            <ComparisonTable />
          </div>
          {isMobile && (
            <p style={{ textAlign: 'center', marginTop: '12px', fontSize: '13px', color: 'var(--color-text-muted)' }}>
              Scroll horizontally to see all plans
            </p>
          )}
        </div>
      </div>

      {/* FAQ Section */}
      <div className="py-20" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-3xl mx-auto px-4">
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{
              fontSize: '36px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '16px',
            }}>
              Frequently Asked Questions
            </h2>
            <p style={{ fontSize: '18px', color: 'var(--color-text-muted)' }}>
              Everything you need to know about our pricing
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <FAQItem
              question="Can I cancel anytime?"
              answer="Yes! You can cancel your subscription at any time. You'll continue to have access to Pro features until the end of your billing period."
            />
            <FAQItem
              question="What payment methods do you accept?"
              answer="We accept all major credit cards (Visa, Mastercard, American Express) and process payments securely through Stripe."
            />
            <FAQItem
              question="What happens when I upgrade?"
              answer="When you upgrade to Pro, you'll immediately get access to all Pro features including code generation, GitHub integration, and exports."
            />
            <FAQItem
              question="Do you offer refunds?"
              answer="We offer a 14-day money-back guarantee. If you're not satisfied, contact us and we'll process a full refund."
            />
            <FAQItem
              question="Can I change plans later?"
              answer="Absolutely! You can upgrade, downgrade, or cancel your plan at any time from your billing settings."
            />
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20" style={{
        backgroundColor: 'var(--color-bg)',
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
            Ready to get started?
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'var(--color-text-muted)',
            marginBottom: '32px',
          }}>
            Join thousands of developers using Cahoots to plan their projects
          </p>
          <button
            onClick={() => navigate(isAuthenticated() ? '/dashboard' : '/')}
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
            {isAuthenticated() ? 'Go to Dashboard' : 'Start for Free'}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '8px' }}>
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <Footer />

      {/* Embedded Checkout Modal */}
      {showCheckoutModal && clientSecret && stripePromise && (
        <CheckoutModal
          clientSecret={clientSecret}
          stripePromise={stripePromise}
          onClose={handleCloseCheckout}
          planName={plans.find(p => p.id === selectedPlanId)?.name || 'Pro'}
        />
      )}
    </div>
  );
};

// Checkout Modal Component
const CheckoutModal = ({ clientSecret, stripePromise, onClose, planName }) => {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--color-surface)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '500px',
          maxHeight: '90vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 24px',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div>
            <h2 style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: '700',
              color: 'var(--color-text)',
            }}>
              Upgrade to {planName}
            </h2>
            <p style={{
              margin: '4px 0 0',
              fontSize: '14px',
              color: 'var(--color-text-muted)',
            }}>
              Complete your subscription
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '8px',
              color: 'var(--color-text-muted)',
              transition: 'background-color 0.2s',
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg)'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <XMarkIcon size={24} />
          </button>
        </div>

        {/* Stripe Embedded Checkout */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '24px',
          }}
        >
          <EmbeddedCheckoutProvider
            stripe={stripePromise}
            options={{ clientSecret }}
          >
            <EmbeddedCheckout />
          </EmbeddedCheckoutProvider>
        </div>
      </div>
    </div>
  );
};

// Pricing Card Component
const PricingCard = ({
  name,
  price,
  period,
  description,
  icon,
  features,
  buttonText,
  buttonDisabled,
  onButtonClick,
  loading,
  popular,
}) => {
  return (
    <div style={{
      padding: '32px',
      backgroundColor: popular ? `${tokens.colors.primary[500]}08` : 'var(--color-bg)',
      borderRadius: '20px',
      border: popular ? `2px solid ${tokens.colors.primary[500]}` : '1px solid var(--color-border)',
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    }}>
      {popular && (
        <div style={{
          position: 'absolute',
          top: '-14px',
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '6px 20px',
          backgroundColor: tokens.colors.primary[500],
          color: 'white',
          borderRadius: '9999px',
          fontSize: '13px',
          fontWeight: '600',
        }}>
          Most Popular
        </div>
      )}

      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{
          width: '56px',
          height: '56px',
          margin: '0 auto 16px',
          backgroundColor: popular ? `${tokens.colors.primary[500]}20` : 'var(--color-surface)',
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '28px',
        }}>
          {icon}
        </div>
        <h3 style={{
          fontSize: '24px',
          fontWeight: '700',
          color: 'var(--color-text)',
          marginBottom: '8px',
        }}>
          {name}
        </h3>
        <div style={{ marginBottom: '8px' }}>
          <span style={{
            fontSize: '48px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-2px',
          }}>
            {price}
          </span>
          {period && (
            <span style={{
              fontSize: '16px',
              color: 'var(--color-text-muted)',
            }}>
              {period}
            </span>
          )}
        </div>
        <p style={{
          fontSize: '15px',
          color: 'var(--color-text-muted)',
        }}>
          {description}
        </p>
      </div>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, marginBottom: '24px', flex: 1 }}>
        {features.map((feature, index) => (
          <li key={index} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '14px',
            fontSize: '15px',
          }}>
            {feature.included ? (
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: `${tokens.colors.success[500]}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="3">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
            ) : (
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-surface)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="3">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </div>
            )}
            <span style={{
              color: feature.included ? 'var(--color-text)' : 'var(--color-text-muted)',
              fontWeight: feature.highlight ? '600' : '400',
            }}>
              {feature.name}
            </span>
          </li>
        ))}
      </ul>

      <button
        onClick={onButtonClick}
        disabled={buttonDisabled || loading}
        style={{
          width: '100%',
          padding: '14px 24px',
          backgroundColor: popular ? tokens.colors.primary[500] : 'transparent',
          color: popular ? 'white' : 'var(--color-text)',
          fontSize: '16px',
          fontWeight: '600',
          border: popular ? 'none' : '1px solid var(--color-border)',
          borderRadius: '10px',
          cursor: buttonDisabled ? 'not-allowed' : 'pointer',
          opacity: buttonDisabled ? 0.5 : 1,
          transition: 'all 0.2s ease',
        }}
      >
        {loading ? 'Loading...' : buttonText}
      </button>
    </div>
  );
};

// Comparison Table Component
const ComparisonTable = () => {
  const features = [
    { name: 'Task Decomposition', free: true, hobbyist: true, pro: true, enterprise: true },
    { name: 'Event Modeling', free: true, hobbyist: true, pro: true, enterprise: true },
    { name: 'Unlimited Projects', free: true, hobbyist: true, pro: true, enterprise: true },
    { name: 'Export (JSON/Markdown/CSV)', free: false, hobbyist: true, pro: true, enterprise: true },
    { name: 'Code Generation', free: false, hobbyist: false, pro: true, enterprise: true },
    { name: 'GitHub Integration', free: false, hobbyist: false, pro: true, enterprise: true },
    { name: 'API Access', free: false, hobbyist: false, pro: true, enterprise: true },
    { name: 'SSO / SAML', free: false, hobbyist: false, pro: false, enterprise: true },
    { name: 'Custom Integrations', free: false, hobbyist: false, pro: false, enterprise: true },
    { name: 'Priority Support', free: false, hobbyist: false, pro: false, enterprise: true },
    { name: 'SLA Guarantee', free: false, hobbyist: false, pro: false, enterprise: true },
  ];

  const CheckIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={tokens.colors.success[500]} strokeWidth="2">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );

  const XIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
          <th style={{ padding: '20px 24px', textAlign: 'left', color: 'var(--color-text)', fontWeight: '600' }}>
            Feature
          </th>
          <th style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--color-text)', fontWeight: '600' }}>
            Free
          </th>
          <th style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--color-text)', fontWeight: '600' }}>
            Hobbyist
          </th>
          <th style={{ padding: '20px 16px', textAlign: 'center', color: tokens.colors.primary[500], fontWeight: '600' }}>
            Pro
          </th>
          <th style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--color-text)', fontWeight: '600' }}>
            Enterprise
          </th>
        </tr>
      </thead>
      <tbody>
        {features.map((feature, index) => (
          <tr key={index} style={{ borderBottom: index < features.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
            <td style={{ padding: '16px 24px', color: 'var(--color-text)', fontSize: '15px' }}>
              {feature.name}
            </td>
            <td style={{ padding: '16px 16px', textAlign: 'center' }}>
              {feature.free ? <CheckIcon /> : <XIcon />}
            </td>
            <td style={{ padding: '16px 16px', textAlign: 'center' }}>
              {feature.hobbyist ? <CheckIcon /> : <XIcon />}
            </td>
            <td style={{ padding: '16px 16px', textAlign: 'center', backgroundColor: `${tokens.colors.primary[500]}05` }}>
              {feature.pro ? <CheckIcon /> : <XIcon />}
            </td>
            <td style={{ padding: '16px 16px', textAlign: 'center' }}>
              {feature.enterprise ? <CheckIcon /> : <XIcon />}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

// FAQ Item Component
const FAQItem = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{
      backgroundColor: 'var(--color-bg)',
      borderRadius: '12px',
      border: '1px solid var(--color-border)',
      overflow: 'hidden',
    }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 24px',
          backgroundColor: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{
          fontSize: '16px',
          fontWeight: '600',
          color: 'var(--color-text)',
        }}>
          {question}
        </span>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-text-muted)"
          strokeWidth="2"
          style={{
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
            flexShrink: 0,
            marginLeft: '16px',
          }}
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div style={{
          padding: '0 24px 20px',
          color: 'var(--color-text-muted)',
          fontSize: '15px',
          lineHeight: '1.6',
        }}>
          {answer}
        </div>
      )}
    </div>
  );
};

export default Pricing;

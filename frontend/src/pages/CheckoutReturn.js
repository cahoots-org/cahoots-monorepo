import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSubscription } from '../contexts/SubscriptionContext';
import { tokens } from '../design-system';
import { CheckCircleIcon, ExclamationCircleIcon, ClockIcon } from '../design-system/icons';

const CheckoutReturn = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { getCheckoutStatus, refreshSubscription } = useSubscription();
  const [status, setStatus] = useState('loading');
  const [customerEmail, setCustomerEmail] = useState(null);

  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (!sessionId) {
      navigate('/pricing');
      return;
    }

    const checkStatus = async () => {
      try {
        const result = await getCheckoutStatus(sessionId);
        setStatus(result.status);
        setCustomerEmail(result.customer_email);

        // If payment was successful, refresh subscription data
        if (result.status === 'complete') {
          await refreshSubscription();
        }
      } catch (err) {
        console.error('Failed to get checkout status:', err);
        setStatus('error');
      }
    };

    checkStatus();
  }, [sessionId, getCheckoutStatus, refreshSubscription, navigate]);

  const renderContent = () => {
    switch (status) {
      case 'loading':
        return (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              backgroundColor: `${tokens.colors.primary[500]}15`,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <ClockIcon size={40} style={{ color: tokens.colors.primary[500] }} />
            </div>
            <h1 style={{
              fontSize: '28px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '12px',
            }}>
              Processing your payment...
            </h1>
            <p style={{
              fontSize: '16px',
              color: 'var(--color-text-muted)',
              maxWidth: '400px',
              margin: '0 auto',
            }}>
              Please wait while we confirm your subscription.
            </p>
          </div>
        );

      case 'complete':
        return (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              backgroundColor: `${tokens.colors.success[500]}15`,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <CheckCircleIcon size={40} style={{ color: tokens.colors.success[500] }} />
            </div>
            <h1 style={{
              fontSize: '28px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '12px',
            }}>
              Payment successful!
            </h1>
            <p style={{
              fontSize: '16px',
              color: 'var(--color-text-muted)',
              maxWidth: '400px',
              margin: '0 auto 8px',
            }}>
              Thank you for upgrading to Pro. Your new features are now active.
            </p>
            {customerEmail && (
              <p style={{
                fontSize: '14px',
                color: 'var(--color-text-muted)',
                marginBottom: '32px',
              }}>
                A confirmation email has been sent to {customerEmail}
              </p>
            )}
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
              <button
                onClick={() => navigate('/dashboard')}
                style={{
                  padding: '12px 24px',
                  backgroundColor: tokens.colors.primary[500],
                  color: 'white',
                  fontSize: '16px',
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
              >
                Go to Dashboard
              </button>
              <button
                onClick={() => navigate('/settings')}
                style={{
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  color: 'var(--color-text)',
                  fontSize: '16px',
                  fontWeight: '600',
                  border: '1px solid var(--color-border)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
              >
                View Settings
              </button>
            </div>
          </div>
        );

      case 'open':
        return (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              backgroundColor: `${tokens.colors.warning[500]}15`,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <ClockIcon size={40} style={{ color: tokens.colors.warning[500] }} />
            </div>
            <h1 style={{
              fontSize: '28px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '12px',
            }}>
              Payment pending
            </h1>
            <p style={{
              fontSize: '16px',
              color: 'var(--color-text-muted)',
              maxWidth: '400px',
              margin: '0 auto 32px',
            }}>
              Your payment is still being processed. Please wait a moment and try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '12px 24px',
                backgroundColor: tokens.colors.primary[500],
                color: 'white',
                fontSize: '16px',
                fontWeight: '600',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              Refresh Status
            </button>
          </div>
        );

      case 'error':
      default:
        return (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              backgroundColor: `${tokens.colors.error[500]}15`,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <ExclamationCircleIcon size={40} style={{ color: tokens.colors.error[500] }} />
            </div>
            <h1 style={{
              fontSize: '28px',
              fontWeight: '700',
              color: 'var(--color-text)',
              marginBottom: '12px',
            }}>
              Something went wrong
            </h1>
            <p style={{
              fontSize: '16px',
              color: 'var(--color-text-muted)',
              maxWidth: '400px',
              margin: '0 auto 32px',
            }}>
              We couldn't verify your payment. Please contact support if you believe this is an error.
            </p>
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
              <button
                onClick={() => navigate('/pricing')}
                style={{
                  padding: '12px 24px',
                  backgroundColor: tokens.colors.primary[500],
                  color: 'white',
                  fontSize: '16px',
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.href = 'mailto:support@cahoots.cc'}
                style={{
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  color: 'var(--color-text)',
                  fontSize: '16px',
                  fontWeight: '600',
                  border: '1px solid var(--color-border)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                Contact Support
              </button>
            </div>
          </div>
        );
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--color-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--color-surface)',
          borderRadius: '16px',
          padding: '48px',
          maxWidth: '500px',
          width: '100%',
          border: '1px solid var(--color-border)',
        }}
      >
        {renderContent()}
      </div>
    </div>
  );
};

export default CheckoutReturn;

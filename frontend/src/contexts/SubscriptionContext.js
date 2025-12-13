import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { useAuth } from './AuthContext';
import apiClient from '../services/unifiedApiClient';

const SubscriptionContext = createContext();

// Feature flags by tier
const TIER_FEATURES = {
  free: {
    code_generation: false,
    github_integration: false,
    export: false,
    api_access: false,
  },
  hobbyist: {
    code_generation: false,
    github_integration: false,
    export: true,
    api_access: false,
  },
  pro: {
    code_generation: true,
    github_integration: true,
    export: true,
    api_access: true,
  },
  enterprise: {
    code_generation: true,
    github_integration: true,
    export: true,
    api_access: true,
    sso: true,
    priority_support: true,
    custom_integrations: true,
  },
};

export const SubscriptionProvider = ({ children }) => {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Extract subscription from user data
  useEffect(() => {
    if (user?.subscription) {
      setSubscription(user.subscription);
    } else if (user) {
      // Default to free tier if no subscription data
      setSubscription({
        tier: 'free',
        status: 'active',
      });
    } else {
      setSubscription(null);
    }
  }, [user]);

  // Fetch available plans
  const fetchPlans = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/subscriptions/plans');
      setPlans(response.plans || []);
    } catch (err) {
      console.error('Failed to fetch plans:', err);
      setError('Failed to load subscription plans');
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if user has access to a feature
  const hasFeature = useCallback((feature) => {
    const tier = subscription?.tier || 'free';
    return TIER_FEATURES[tier]?.[feature] || false;
  }, [subscription]);

  // Convenience methods for common features
  const canUseCodeGen = useCallback(() => hasFeature('code_generation'), [hasFeature]);
  const canUseGitHub = useCallback(() => hasFeature('github_integration'), [hasFeature]);
  const canExport = useCallback(() => hasFeature('export'), [hasFeature]);
  const canUseAPI = useCallback(() => hasFeature('api_access'), [hasFeature]);

  // Tier checks
  const isPro = subscription?.tier === 'pro';
  const isEnterprise = subscription?.tier === 'enterprise';
  const isHobbyist = subscription?.tier === 'hobbyist';
  const isFree = !subscription?.tier || subscription?.tier === 'free';

  // Create checkout session (redirect flow)
  const createCheckout = useCallback(async (priceId, successUrl, cancelUrl) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.post('/subscriptions/checkout', {
        price_id: priceId,
        success_url: successUrl || `${window.location.origin}/settings/billing?success=true`,
        cancel_url: cancelUrl || `${window.location.origin}/pricing?canceled=true`,
      });
      return response;
    } catch (err) {
      console.error('Checkout error:', err);
      setError(err.userMessage || 'Failed to start checkout');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Create embedded checkout session (inline flow)
  const createEmbeddedCheckout = useCallback(async (priceId, returnUrl) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.post('/subscriptions/embedded-checkout', {
        price_id: priceId,
        return_url: returnUrl || `${window.location.origin}/checkout/return?session_id={CHECKOUT_SESSION_ID}`,
      });
      return response;
    } catch (err) {
      console.error('Embedded checkout error:', err);
      setError(err.userMessage || 'Failed to start checkout');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Get Stripe config (publishable key)
  const getStripeConfig = useCallback(async () => {
    try {
      const response = await apiClient.get('/subscriptions/config');
      return response;
    } catch (err) {
      console.error('Failed to get Stripe config:', err);
      setError('Payment system is not available');
      throw err;
    }
  }, []);

  // Get checkout session status
  const getCheckoutStatus = useCallback(async (sessionId) => {
    try {
      const response = await apiClient.get(`/subscriptions/checkout-status/${sessionId}`);
      return response;
    } catch (err) {
      console.error('Failed to get checkout status:', err);
      throw err;
    }
  }, []);

  // Open billing portal
  const openBillingPortal = useCallback(async (returnUrl) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.post('/subscriptions/portal', null, {
        params: { return_url: returnUrl || window.location.href },
      });
      if (response.portal_url) {
        window.location.href = response.portal_url;
      }
      return response;
    } catch (err) {
      console.error('Portal error:', err);
      setError(err.userMessage || 'Failed to open billing portal');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh subscription data
  const refreshSubscription = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/subscriptions/current');
      setSubscription(response);
      return response;
    } catch (err) {
      console.error('Failed to refresh subscription:', err);
      setError('Failed to refresh subscription data');
    } finally {
      setLoading(false);
    }
  }, []);

  const contextValue = {
    // State
    subscription,
    plans,
    loading,
    error,

    // Tier flags
    isPro,
    isEnterprise,
    isHobbyist,
    isFree,

    // Feature checks
    hasFeature,
    canUseCodeGen,
    canUseGitHub,
    canExport,
    canUseAPI,

    // Actions
    fetchPlans,
    createCheckout,
    createEmbeddedCheckout,
    getStripeConfig,
    getCheckoutStatus,
    openBillingPortal,
    refreshSubscription,

    // Clear error
    clearError: () => setError(null),
  };

  return (
    <SubscriptionContext.Provider value={contextValue}>
      {children}
    </SubscriptionContext.Provider>
  );
};

export const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};

export default SubscriptionContext;

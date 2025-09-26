import React, { useState, useEffect } from 'react';
import { BellIcon } from '@heroicons/react/24/solid';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import apiClient from '../services/unifiedApiClient';
import Button from '../design-system/components/Button';
import Card from '../design-system/components/Card';
import Input from '../design-system/components/Input';
import { Heading3, Text } from '../design-system/components/Typography';
import { tokens } from '../design-system/tokens';

const BlogSubscription = ({ variant = 'inline', title = 'Subscribe to our blog' }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [mySubscription, setMySubscription] = useState(null);
  const [showEmailForm, setShowEmailForm] = useState(false);
  
  const { showToast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      fetchMySubscription();
    }
  }, [user]);

  const fetchMySubscription = async () => {
    try {
      const subscription = await apiClient.get('/blog/my-subscription');
      setMySubscription(subscription);
    } catch (error) {
      // User doesn't have a subscription
      setMySubscription(null);
    }
  };

  const handleSubscribe = async (subscriptionEmail) => {
    setLoading(true);
    try {
      const data = {
        email: subscriptionEmail,
        frequency: 'weekly',
        categories: [],
      };
      
      await apiClient.post('/blog/subscribe', data);
      showToast('Successfully subscribed! You\'ll receive weekly updates.', 'success');
      
      if (user) {
        fetchMySubscription();
      } else {
        setShowEmailForm(false);
        setEmail('');
      }
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to subscribe', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUnsubscribe = async () => {
    if (!user) return;
    
    if (window.confirm('Are you sure you want to unsubscribe from blog notifications?')) {
      setLoading(true);
      try {
        await apiClient.delete('/blog/my-subscription');
        showToast('Successfully unsubscribed', 'success');
        setMySubscription(null);
      } catch (error) {
        showToast(error.response?.data?.detail || 'Failed to unsubscribe', 'error');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleEmailSubmit = (e) => {
    e.preventDefault();
    if (email.trim()) {
      handleSubscribe(email);
    }
  };

  const handleQuickSubscribe = () => {
    if (user) {
      if (mySubscription) {
        handleUnsubscribe();
      } else {
        handleSubscribe(user.email);
      }
    } else {
      setShowEmailForm(true);
    }
  };

  if (variant === 'compact') {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacing[2],
        padding: `${tokens.spacing[3]} 0`,
        borderTop: `1px solid ${tokens.colors.dark.border}`,
        borderBottom: `1px solid ${tokens.colors.dark.border}`,
        margin: `${tokens.spacing[4]} 0`,
      }}>
        <BellIcon style={{ 
          width: '20px', 
          height: '20px', 
          color: tokens.colors.primary[500] 
        }} />
        <Text style={{ 
          flex: 1, 
          margin: 0,
          color: tokens.colors.dark.text 
        }}>
          {user && mySubscription 
            ? 'You\'re subscribed to blog updates' 
            : 'Get notified of new blog posts'
          }
        </Text>
        <Button
          onClick={handleQuickSubscribe}
          variant={user && mySubscription ? 'secondary' : 'primary'}
          size="sm"
          loading={loading}
        >
          {user && mySubscription ? 'Subscribed' : 'Subscribe'}
        </Button>
      </div>
    );
  }

  return (
    <Card style={{ 
      margin: `${tokens.spacing[6]} 0`,
      textAlign: 'center',
      background: `linear-gradient(135deg, ${tokens.colors.dark.surface} 0%, ${tokens.colors.dark.surfaceVariant} 100%)`
    }}>
      <BellIcon style={{ 
        width: '48px', 
        height: '48px', 
        color: tokens.colors.primary[500],
        margin: '0 auto',
        marginBottom: tokens.spacing[3]
      }} />
      
      <Heading3 style={{ 
        marginBottom: tokens.spacing[2],
        color: tokens.colors.dark.text
      }}>
        {title}
      </Heading3>
      
      <Text style={{ 
        marginBottom: tokens.spacing[4],
        color: tokens.colors.dark.textMuted,
        maxWidth: '400px',
        margin: `0 auto ${tokens.spacing[4]} auto`
      }}>
        {user && mySubscription 
          ? `You're currently subscribed and will receive ${mySubscription.frequency} updates. Manage your subscription anytime.`
          : 'Stay updated with our latest insights on AI-powered project management, task decomposition, and software development best practices.'
        }
      </Text>

      {user ? (
        // Authenticated user
        <Button
          onClick={handleQuickSubscribe}
          variant={mySubscription ? 'secondary' : 'primary'}
          size="lg"
          icon={BellIcon}
          loading={loading}
        >
          {mySubscription ? 'Manage Subscription' : 'Subscribe Now'}
        </Button>
      ) : (
        // Non-authenticated user
        <div>
          {!showEmailForm ? (
            <Button
              onClick={() => setShowEmailForm(true)}
              variant="primary"
              size="lg"
              icon={BellIcon}
            >
              Subscribe Now
            </Button>
          ) : (
            <form onSubmit={handleEmailSubmit} style={{
              display: 'flex',
              flexDirection: 'column',
              gap: tokens.spacing[3],
              maxWidth: '320px',
              margin: '0 auto'
            }}>
              <Input
                type="email"
                placeholder="Enter your email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <div style={{ display: 'flex', gap: tokens.spacing[2] }}>
                <Button
                  type="submit"
                  variant="primary"
                  loading={loading}
                  style={{ flex: 1 }}
                >
                  Subscribe
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowEmailForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </Card>
  );
};

export default BlogSubscription;
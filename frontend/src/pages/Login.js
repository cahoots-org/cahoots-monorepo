import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toaster } from '../components/ui/toaster';
import CottageIcon from '../components/CottageIcon';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);
  const { login, getOAuthUrl } = useAuth();
  const navigate = useNavigate();

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
    if (isOAuthLoading) {
      return;
    }
    sessionStorage.removeItem('oauth_state');
    setIsOAuthLoading(true);
    try {
      const authUrl = await getOAuthUrl(provider);
      // Record flow start for diagnostics
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
    // Set development bypass token
    localStorage.setItem('token', 'dev-bypass-token');
    localStorage.setItem('user', JSON.stringify({
      id: 'dev-user-123',
      email: 'test@example.com',
      username: 'testuser',
      full_name: 'Test User'
    }));
    
    toaster.create({
      title: 'Development login successful',
      description: 'Logged in with development bypass token',
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
    
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Background Pattern */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full opacity-50" style={{ background: 'linear-gradient(to bottom right, var(--color-bg), var(--color-surface), var(--color-bg))' }}></div>
        <div className="absolute top-20 left-10 w-32 h-32 bg-brand-vibrant-blue bg-opacity-10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-10 w-40 h-40 bg-brand-vibrant-orange bg-opacity-10 rounded-full blur-3xl"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 py-12">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-6">
              <CottageIcon size="text-6xl" className="text-brand-vibrant-orange" />
            </div>
            <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>Welcome Back</h1>
            <p style={{ color: 'var(--color-text-muted)' }}>
              Sign in to continue to Cahoots Project Manager
            </p>
          </div>

          {/* Login Card */}
          <div className="card p-8 backdrop-blur-sm shadow-2xl" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email Field */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Email address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="input-field w-full"
                />
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="input-field w-full"
                />
              </div>

              {/* Sign In Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full btn btn-primary py-3 text-lg font-medium rounded-lg transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" style={{ borderColor: 'var(--color-border)' }}></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text-muted)' }}>Or continue with</span>
              </div>
            </div>

            {/* OAuth and Development Options */}
            <div className="space-y-4">
              {/* Google OAuth */}
              <button
                onClick={() => handleOAuthLogin('google')}
                disabled={isOAuthLoading}
                className="w-full flex items-center justify-center px-4 py-3 border rounded-lg bg-white hover:bg-gray-50 transition-colors duration-200 text-gray-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                {isOAuthLoading ? 'Connecting...' : 'Continue with Google'}
              </button>
              
              {/* Development bypass button - only show in development */}
              {(window.CAHOOTS_CONFIG?.ENVIRONMENT === 'development') && (
                <button
                  onClick={handleDevBypass}
                  className="w-full flex items-center justify-center px-4 py-3 border border-brand-vibrant-orange text-brand-vibrant-orange rounded-lg hover:bg-brand-vibrant-orange hover:bg-opacity-10 transition-all duration-200 font-medium"
                >
                  <span className="mr-2">🚀</span>
                  Development Bypass (ENV: {window.CAHOOTS_CONFIG?.ENVIRONMENT || 'not loaded'})
                </button>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="text-center mt-8">
            <p style={{ color: 'var(--color-text-muted)' }}>
              Don't have an account?{' '}
              <Link to="/register" className="text-brand-vibrant-orange hover:text-brand-vibrant-orange hover:underline font-medium transition-colors duration-200">
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

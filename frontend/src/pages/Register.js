import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toaster } from '../components/ui/toaster';
import CottageIcon from '../components/CottageIcon';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const { register, login, getOAuthUrl } = useAuth();
  const navigate = useNavigate();
  // Using toaster instead of useToast

  // Handle input change
  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
    // Clear field error when user starts typing
    if (fieldErrors[id]) {
      setFieldErrors((prev) => ({
        ...prev,
        [id]: null,
      }));
    }
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Validate password confirmation
    if (formData.password !== formData.confirmPassword) {
      toaster.create({
        title: 'Password mismatch',
        description: 'Password and confirm password must match.',
        status: 'error',
      });
      setIsSubmitting(false);
      return;
    }

    try {
      // Register user
      await register({
        email: formData.email,
        username: formData.email, // Use email as username
        password: formData.password,
        full_name: formData.fullName || '',
        provider: 'local',
        disabled: false,
        role: 'user',
        subscription_tier: 'free',
        subscription_status: 'active',
        monthly_task_limit: 10,
        tasks_created_this_month: 0
      });

      // Login after successful registration
      await login(formData.email, formData.password);

      toaster.create({
        title: 'Registration successful!',
        description: 'You have been registered successfully.',
        status: 'success',
      });

      navigate('/dashboard');
    } catch (error) {
      // Check if it's an "Email already registered" error
      if (error.message && error.message.includes('Email already registered')) {
        setFieldErrors({
          email: 'This email is already registered. Please use a different email or sign in instead.',
        });
      } else {
        // For other errors, show a general notification
        toaster.create({
          title: 'Registration failed',
          description: error.message,
          status: 'error',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle OAuth registration
  const handleOAuthRegister = async (provider) => {
    try {
      const authUrl = await getOAuthUrl(provider);
      window.location.href = authUrl;
    } catch (error) {
      toaster.create({
        title: `${provider} registration failed`,
        description: error.message,
        status: 'error',
      });
    }
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
            <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>Create Account</h1>
            <p style={{ color: 'var(--color-text-muted)' }}>
              Join Cahoots Project Manager
            </p>
          </div>

          {/* Registration Card */}
          <div className="card p-8 backdrop-blur-sm shadow-2xl" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email Field */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Email address *
                </label>
                <input
                  type="email"
                  id="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="your@email.com"
                  required
                  className={`input-field w-full ${fieldErrors.email ? 'border-red-500 focus:border-red-500' : ''}`}
                />
                {fieldErrors.email && (
                  <p className="text-red-600 text-sm flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {fieldErrors.email}
                  </p>
                )}
              </div>


              {/* Full Name Field */}
              <div className="space-y-2">
                <label htmlFor="fullName" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  id="fullName"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="John Doe"
                  className="input-field w-full"
                />
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Password *
                </label>
                <input
                  type="password"
                  id="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  required
                  className="input-field w-full"
                />
              </div>

              {/* Confirm Password Field */}
              <div className="space-y-2">
                <label htmlFor="confirmPassword" className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Confirm Password *
                </label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm your password"
                  required
                  className="input-field w-full"
                />
                {/* Password match indicator */}
                {formData.password && formData.confirmPassword && (
                  <div className="flex items-center text-sm">
                    {formData.password === formData.confirmPassword ? (
                      <span className="text-green-600 flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        Passwords match
                      </span>
                    ) : (
                      <span className="text-red-600 flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        Passwords don't match
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Sign Up Button */}
              <button
                type="submit"
                disabled={isSubmitting || (formData.password && formData.confirmPassword && formData.password !== formData.confirmPassword)}
                className="w-full btn btn-primary py-3 text-lg font-medium rounded-lg transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating account...
                  </span>
                ) : (
                  'Sign Up'
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" style={{ borderColor: 'var(--color-border)' }}></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text-muted)' }}>Or sign up with</span>
              </div>
            </div>

            {/* OAuth Options */}
            <div className="space-y-4">
              {/* Google OAuth */}
              <button
                onClick={() => handleOAuthRegister('google')}
                className="w-full flex items-center justify-center px-4 py-3 border rounded-lg bg-white hover:bg-gray-50 transition-colors duration-200 text-gray-700 font-medium"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center mt-8">
            <p style={{ color: 'var(--color-text-muted)' }}>
              Already have an account?{' '}
              <Link to="/" className="text-brand-vibrant-orange hover:text-brand-vibrant-orange hover:underline font-medium transition-colors duration-200">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;

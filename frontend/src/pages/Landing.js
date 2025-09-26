import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Footer from '../components/Footer';
import SEO from '../components/SEO';

// Cottage mascot image
const CottageMascot = () => (
  <img 
    src="/icons/cottage.png" 
    alt="Cahoots Cottage" 
    width="80" 
    height="80" 
    className="mx-auto mb-6"
  />
);

const Landing = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <SEO 
        title="AI-Powered Project Task Decomposition"
        description="Transform complex software projects into manageable tasks with Cahoots. Our AI-powered decomposition breaks down requirements into atomic, actionable work items."
      />
      {/* Hero Section */}
      <div className="flex flex-col items-center justify-center min-h-screen px-4 relative">
        <div className="max-w-4xl w-full text-center fade-in">
          <CottageMascot />
          <h1 className="heading-1 gradient-text mb-4">Where Great Projects Come Together</h1>
          <p className="text-xl mb-8 max-w-2xl mx-auto" style={{ color: 'var(--color-text)' }}>
            AI-powered task decomposition that breaks down complex software projects into manageable, actionable work items.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <button
              className="btn btn-primary text-lg px-8 py-3"
              onClick={() => navigate('/login')}
            >
              Get Started Free
            </button>
            <button
              className="btn btn-secondary text-lg px-8 py-3"
              onClick={() => navigate('/about')}
            >
              Learn More
            </button>
          </div>
        </div>
        
        {/* Scroll Indicator */}
        <div 
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-center cursor-pointer hover:text-brand-vibrant-orange transition-colors"
          onClick={() => {
            const featuresSection = document.getElementById('features-section');
            if (featuresSection) {
              featuresSection.scrollIntoView({ behavior: 'smooth' });
            }
          }}
        >
          <p className="text-sm mb-2" style={{ color: 'var(--color-text-muted)' }}>See how it works</p>
          <div className="animate-bounce">
            <svg 
              className="w-6 h-6 text-brand-vibrant-orange mx-auto" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M19 14l-7 7m0 0l-7-7m7 7V3" 
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Transition gradient */}
      <div className="h-24" style={{ background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))' }}></div>
      
      {/* Features Section */}
      <div id="features-section" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-6xl mx-auto px-4 py-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>How It Works</h2>
            <p className="text-xl" style={{ color: 'var(--color-text-muted)' }}>Three simple steps to organized, actionable project plans</p>
          </div>

        {/* Step-by-step process */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          <div className="text-center">
            <div className="w-16 h-16 bg-brand-vibrant-orange bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🧩</span>
            </div>
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text)' }}>1. Describe Your Project</h3>
            <p style={{ color: 'var(--color-text-muted)' }}>Tell us about your big idea or complex feature in plain english.</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-brand-vibrant-blue bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">⚡</span>
            </div>
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text)' }}>2. AI Breaks It Down</h3>
            <p style={{ color: 'var(--color-text-muted)' }}>Watch as complex requirements become organized, atomic tasks with clear acceptance criteria.</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-brand-vibrant-green bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🚀</span>
            </div>
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text)' }}>3. Export & Execute</h3>
            <p style={{ color: 'var(--color-text-muted)' }}>Send tasks to your favorite project management tool. Start building!</p>
          </div>
        </div>

        {/* Key features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
          <div className="card card-hover p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-purple-500 bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                <span className="text-2xl">🎯</span>
              </div>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Smart Task Trees</h3>
            </div>
            <p style={{ color: 'var(--color-text-muted)' }}>Visual hierarchy shows how your project breaks down, with complexity scoring and story point estimation.</p>
          </div>
          <div className="card card-hover p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-blue-500 bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                <span className="text-2xl">📊</span>
              </div>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Trello & JIRA Export</h3>
            </div>
            <p style={{ color: 'var(--color-text-muted)' }}>Export to your team's existing workflow. Boards, cards, and tickets created automatically.</p>
          </div>
          <div className="card card-hover p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-green-500 bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Real-Time Updates</h3>
            </div>
            <p style={{ color: 'var(--color-text-muted)' }}>Watch your project break down into atomic tasks in real-time.</p>
          </div>
          <div className="card card-hover p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-orange-500 bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                <span className="text-2xl">🤖</span>
              </div>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Atomic Detection</h3>
            </div>
            <p style={{ color: 'var(--color-text-muted)' }}>AI knows when tasks are small enough to execute directly.</p>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center rounded-lg p-8" style={{ backgroundColor: 'var(--color-bg)' }}>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Ready to Turn Ideas into Action?</h2>
          <p className="mb-6" style={{ color: 'var(--color-text-muted)' }}>Join developers who are already using AI to streamline their project planning.</p>
          <button
            className="btn btn-primary text-lg px-8 py-3"
            onClick={() => navigate('/login')}
          >
            Start Planning Now
          </button>
        </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default Landing;

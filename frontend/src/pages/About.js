import React from 'react';
import { useNavigate } from 'react-router-dom';
import CottageIcon from '../components/CottageIcon';
import Footer from '../components/Footer';

const About = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Hero Section */}
      <div style={{ background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))' }}>
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <CottageIcon size="text-6xl" className="mb-6" />
          <h1 className="heading-1 gradient-text mb-4">About Cahoots</h1>
          <p className="text-xl max-w-2xl mx-auto" style={{ color: 'var(--color-text)' }}>
            Revolutionizing software development through intelligent AI-human collaboration
          </p>
        </div>
      </div>

      {/* Mission Section */}
      <div className="py-16" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-6" style={{ color: 'var(--color-text)' }}>Our Mission</h2>
              <p className="text-lg mb-4" style={{ color: 'var(--color-text)' }}>
                <strong>Cahoots</strong> is about augmenting human software development teams with AI capabilities.
              </p>
              <p className="mb-6" style={{ color: 'var(--color-text-muted)' }}>
                Our vision is to create a collaborative ecosystem where AI and humans work side-by-side, enhancing productivity, creativity, and project outcomes.
              </p>
              <div className="flex flex-wrap gap-3">
                <span className="px-3 py-1 bg-brand-vibrant-orange bg-opacity-20 text-brand-vibrant-orange rounded-full text-sm font-medium">
                  AI-Powered
                </span>
                <span className="px-3 py-1 bg-brand-vibrant-blue bg-opacity-20 text-brand-vibrant-blue rounded-full text-sm font-medium">
                  Human-Centered
                </span>
                <span className="px-3 py-1 bg-brand-vibrant-green bg-opacity-20 text-brand-vibrant-green rounded-full text-sm font-medium">
                  Collaborative
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-brand-vibrant-orange bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🎯</span>
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>Smart Planning</h3>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>AI-powered task decomposition</p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-brand-vibrant-blue bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🤝</span>
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>Human Collaboration</h3>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Seamless AI-human handoffs</p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-brand-vibrant-green bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🚀</span>
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>Productivity</h3>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Enhanced team capacity</p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-500 bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🌿</span>
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>Flow</h3>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Fill in the gaps in your team's workflow</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Philosophy Section */}
      <div className="py-16" style={{ backgroundColor: 'var(--color-bg)' }}>
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-6" style={{ color: 'var(--color-text)' }}>Our Philosophy</h2>
          <p className="text-lg mb-8" style={{ color: 'var(--color-text)' }}>
            Provide AI assistance to teams where it is needed most.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="card card-hover p-6">
              <div className="text-4xl mb-4">🌳</div>
              <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>Growth & Stability</h3>
              <p style={{ color: 'var(--color-text-muted)' }}>
                Building systems that grow with your team's needs while maintaining reliability.
              </p>
            </div>
            <div className="card card-hover p-6">
              <div className="text-4xl mb-4">🕸️</div>
              <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>Interconnection</h3>
              <p style={{ color: 'var(--color-text-muted)' }}>
                Creating networks of collaboration where AI and humans strengthen each other's capabilities.
              </p>
            </div>
            <div className="card card-hover p-6">
              <div className="text-4xl mb-4">🦋</div>
              <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>Transformation</h3>
              <p style={{ color: 'var(--color-text-muted)' }}>
                Enabling teams to evolve and adapt to new challenges with intelligent support systems.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Current Focus Section */}
      <div className="py-16" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-3xl font-bold mb-6 text-center" style={{ color: 'var(--color-text)' }}>What We're Building Today</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="card p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-brand-vibrant-orange bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                  <span className="text-2xl">🧩</span>
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>Task Decomposition</h3>
              </div>
              <p style={{ color: 'var(--color-text-muted)' }}>
                AI-powered breakdown of complex projects into atomic, actionable tasks with clear acceptance criteria.
              </p>
            </div>
            <div className="card p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-brand-vibrant-blue bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                  <span className="text-2xl">📊</span>
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>Team Integration</h3>
              </div>
              <p style={{ color: 'var(--color-text-muted)' }}>
                Seamless export to Trello, JIRA, and other project management tools your team already uses.
              </p>
            </div>
            <div className="card p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-purple-500 bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                  <span className="text-2xl">🎯</span>
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>Smart Estimation</h3>
              </div>
              <p style={{ color: 'var(--color-text-muted)' }}>
                AI-driven complexity scoring and story point estimation to help teams plan more effectively.
              </p>
            </div>
            <div className="card p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-brand-vibrant-green bg-opacity-20 rounded-lg flex items-center justify-center mr-4">
                  <span className="text-2xl">⚡</span>
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>Customization</h3>
              </div>
              <p style={{ color: 'var(--color-text-muted)' }}>
                Receive task breakdowns that are tailored to your team's needs and preferences.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Future Vision Section */}
      <div className="py-16" style={{ backgroundColor: 'var(--color-bg)' }}>
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-6" style={{ color: 'var(--color-text)' }}>The Future of Development</h2>
          <p className="text-lg mb-8" style={{ color: 'var(--color-text-muted)' }}>
            We believe the next leap in software development will come from intelligent, context-aware collaboration—not just automation.
          </p>
          <div className="rounded-lg p-8 mb-8" style={{ backgroundColor: 'var(--color-surface)' }}>
            <h3 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Coming Soon</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
              <div>
                <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>🔗 Deeper Integrations</h4>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Slack, GitHub, and CI/CD pipeline connections</p>
              </div>
              <div>
                <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>🎨 UX & Design AI</h4>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>AI agents specialized in user experience design</p>
              </div>
              <div>
                <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>🔍 QA Automation</h4>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Intelligent testing and quality assurance workflows</p>
              </div>
              <div>
                <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>📈 Project Intelligence</h4>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Advanced analytics and predictive project insights</p>
              </div>
            </div>
          </div>
          <button
            className="btn btn-primary text-lg px-8 py-3"
            onClick={() => navigate('/login')}
          >
            Join the Future
          </button>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default About;

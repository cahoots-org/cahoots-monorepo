import React from 'react';
import { useNavigate } from 'react-router-dom';
import CottageIcon from '../components/CottageIcon';
import Footer from '../components/Footer';

const PrivacyPolicy = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Header */}
      <div style={{ background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))' }}>
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <CottageIcon size="text-4xl" className="mb-4" />
          <h1 className="heading-1 gradient-text mb-4">Privacy Policy</h1>
          <p className="text-lg" style={{ color: 'var(--color-text-muted)' }}>
            Last Updated: August 3, 2025
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="py-8" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-4xl mx-auto px-4">
          <div className="card p-8" style={{ backgroundColor: 'var(--color-bg)' }}>
            
            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Introduction</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                Cahoots Project Manager ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our project management application and services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Information We Collect</h2>
              
              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>1. Account Information</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Authentication Data</strong>: When you sign in using OAuth providers (Google, Apple), we receive basic profile information including your email address and name</li>
                <li><strong>User Identification</strong>: We generate and store unique user identifiers to isolate your tasks from other users</li>
              </ul>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>2. Task and Project Data</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Task Information</strong>: We collect and store the tasks, subtasks, and project information you create and manage within the application</li>
                <li><strong>Task Metadata</strong>: We collect information about task complexity, status, relationships, and completion data</li>
              </ul>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>3. DSPy Optimization Data</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Model Training Data</strong>: We collect anonymized task decomposition patterns and user interactions to optimize our DSPy (Declarative Self-improving Python) machine learning models</li>
                <li><strong>Prediction Feedback</strong>: We collect feedback on system predictions to improve task decomposition accuracy</li>
                <li><strong>Performance Metrics</strong>: We collect system performance data to enhance our machine learning algorithms</li>
              </ul>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>4. Context and External Data</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Internet Context Fetching</strong>: Our system may retrieve publicly available information from the internet to provide relevant context for your tasks and projects</li>
                <li><strong>External References</strong>: We may access and cache publicly available documentation, best practices, and technical resources related to your project requirements</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>How We Use Your Information</h2>
              
              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Primary Uses</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Service Delivery</strong>: To provide, maintain, and improve our project management services</li>
                <li><strong>Task Processing</strong>: To decompose complex tasks into manageable subtasks using our AI-powered system</li>
                <li><strong>User Experience</strong>: To personalize and optimize your experience with our application</li>
              </ul>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Machine Learning Optimization</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>DSPy Model Training</strong>: We use aggregated, anonymized data to train and improve our task decomposition models</li>
                <li><strong>Pattern Recognition</strong>: We analyze task patterns to enhance our system's ability to break down complex projects</li>
                <li><strong>Algorithm Enhancement</strong>: We use performance data to optimize our machine learning algorithms</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Data Security</h2>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Encryption</strong>: All data is encrypted in transit and at rest</li>
                <li><strong>Access Controls</strong>: We implement strict access controls to limit who can access your data</li>
                <li><strong>Regular Audits</strong>: We conduct regular security audits and assessments</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>We Do Not Sell Your Data</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                We do not sell, trade, or otherwise transfer your personal information to third parties for commercial purposes.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Your Rights and Choices</h2>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li><strong>Access</strong>: You can access and review your account information and task data</li>
                <li><strong>Correction</strong>: You can update or correct your account information</li>
                <li><strong>Deletion</strong>: You can request deletion of your account and associated data</li>
                <li><strong>Export</strong>: You can export your task and project data</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Third-Party Services</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                We integrate with third-party OAuth providers (Google, Apple) for authentication. Their privacy policies govern the data they collect. When fetching context from the internet, we may access publicly available information from various sources.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Children's Privacy</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                Our service is not intended for children under 13 years of age. We do not knowingly collect personal information from children under 13.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Changes to This Privacy Policy</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                We may update this Privacy Policy from time to time. We will notify you of any material changes by posting the updated policy on our website, sending email notifications for significant changes, and displaying prominent notices within our application.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Contact Information</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                If you have questions or concerns about this Privacy Policy or our data practices, please contact us at:
              </p>
              <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
                <p style={{ color: 'var(--color-text)' }}><strong>Email:</strong> privacy@cahoots.cc</p>
                <p style={{ color: 'var(--color-text)' }}><strong>Website:</strong> https://cahoots.cc</p>
              </div>
            </section>

            <div className="text-center pt-8">
              <button
                className="btn btn-primary"
                onClick={() => navigate(-1)}
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default PrivacyPolicy;
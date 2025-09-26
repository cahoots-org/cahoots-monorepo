import React from 'react';
import { useNavigate } from 'react-router-dom';
import CottageIcon from '../components/CottageIcon';
import Footer from '../components/Footer';

const TermsOfService = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Header */}
      <div style={{ background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))' }}>
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <CottageIcon size="text-4xl" className="mb-4" />
          <h1 className="heading-1 gradient-text mb-4">Terms of Service</h1>
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
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Agreement to Terms</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                By accessing or using Cahoots Project Manager ("the Service," "our Service"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of these terms, then you may not access the Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Description of Service</h2>
              
              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Service Overview</h3>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                Cahoots Project Manager is a software-as-a-service (SaaS) application that provides intelligent project management capabilities, including:
              </p>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>Task creation and management</li>
                <li>AI-powered task decomposition using DSPy (Declarative Self-improving Python) framework</li>
                <li>Automated subtask generation and complexity analysis</li>
                <li>Real-time collaboration and status updates</li>
                <li>Context-aware project assistance</li>
              </ul>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>AI and Machine Learning Features</h3>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                Our Service incorporates artificial intelligence and machine learning technologies that analyze task complexity, generate automated subtasks, provide context-aware recommendations, and continuously improve through user interactions.
              </p>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4 rounded-lg mb-4">
                <p className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Important AI Disclaimer:</p>
                <p style={{ color: 'var(--color-text)' }}>
                  AI Services use machine learning models that generate predictions based on patterns in data. You should evaluate all AI-generated output for accuracy and appropriateness for your use case, including using human review as appropriate.
                </p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>User Accounts and Registration</h2>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>You must provide accurate, complete, and current information during registration</li>
                <li>You are responsible for maintaining the confidentiality of your account credentials</li>
                <li>You must be at least 13 years of age to use our Service</li>
                <li>We support authentication through third-party OAuth providers (Google, Apple)</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>User Responsibilities</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>You are responsible for:</p>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>All activities that occur under your account</li>
                <li>Maintaining the security of your login credentials</li>
                <li>All decisions made, advice followed, and actions taken based on AI-generated content</li>
                <li>Evaluating AI output for accuracy and appropriateness</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Acceptable Use Policy</h2>
              
              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Prohibited Activities</h3>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>You agree not to:</p>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>Use the Service for any illegal or unauthorized purpose</li>
                <li>Violate any applicable laws or regulations</li>
                <li>Interfere with or disrupt the Service or servers</li>
                <li>Attempt to gain unauthorized access to any portion of the Service</li>
                <li>Upload harmful, threatening, or otherwise objectionable content</li>
                <li>Use automated scripts, bots, or other automated means to access the Service</li>
                <li>Reverse engineer, decompile, or disassemble any portion of the Service</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Intellectual Property Rights</h2>
              
              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Service Ownership</h3>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                The Service and its original content, features, and functionality are and will remain the exclusive property of Cahoots Project Manager and its licensors.
              </p>

              <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Your Content</h3>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>You retain ownership of any intellectual property rights in content you submit</li>
                <li>By submitting content, you grant us a license to use it solely for providing the Service</li>
                <li>We may use aggregated, anonymized data to improve our AI models</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Service Availability</h2>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>We strive to maintain high availability but do not guarantee uninterrupted access</li>
                <li>We reserve the right to modify, suspend, or discontinue any aspect of the Service</li>
                <li>We may update these Terms at any time with reasonable notice</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Disclaimers and Limitations</h2>
              
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg mb-4">
                <p className="font-semibold text-red-800 dark:text-red-200 mb-2">Important Disclaimers:</p>
                <ul className="list-disc list-inside space-y-2" style={{ color: 'var(--color-text)' }}>
                  <li>THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND</li>
                  <li>AI-generated content is provided for informational purposes only</li>
                  <li>You are solely responsible for evaluating and verifying AI-generated output</li>
                  <li>We disclaim all liability for decisions made based on AI-generated content</li>
                </ul>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Termination</h2>
              <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: 'var(--color-text)' }}>
                <li>You may terminate your account at any time</li>
                <li>We may terminate accounts that breach these Terms</li>
                <li>Upon termination, your right to use the Service ceases immediately</li>
                <li>We may delete your account and data after a reasonable grace period</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Governing Law</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                These Terms are governed by and construed in accordance with the laws of the United States. Any disputes should first be addressed through direct communication with our support team.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Changes to Terms</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                We reserve the right to modify these Terms at any time. We will notify users of material changes by posting updated Terms on our website, sending email notifications, and displaying notices within the Service. Continued use after changes constitutes acceptance of the new Terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>Contact Information</h2>
              <p className="mb-4" style={{ color: 'var(--color-text)' }}>
                If you have questions about these Terms, please contact us at:
              </p>
              <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
                <p style={{ color: 'var(--color-text)' }}><strong>Email:</strong> legal@cahoots.cc</p>
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

export default TermsOfService;
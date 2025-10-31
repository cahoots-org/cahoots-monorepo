import React from 'react';
import Footer from '../components/Footer';

const Contact = () => {
  return (
    <div style={{ backgroundColor: 'var(--color-bg)', minHeight: '100vh' }}>
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="text-center mb-8">
          <h1 className="heading-1 mb-4" style={{ color: 'var(--color-text)' }}>Contact Us</h1>
          <p className="text-lg" style={{ color: 'var(--color-text)' }}>
            We'd love to hear from you! Send us a message and we'll get back to you as soon as possible.
          </p>
        </div>

        <div className="card p-8">
          <form action="https://formsubmit.co/admin@cahoots.cc" method="POST" className="space-y-6">
            {/* FormSubmit.co configuration - hidden fields */}
            <input type="hidden" name="_subject" value="New Contact Form Submission - Cahoots" />
            <input type="hidden" name="_captcha" value="false" />
            <input type="hidden" name="_template" value="table" />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                  Name *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  required
                  className="input-field w-full"
                  placeholder="Your full name"
                />
              </div>
              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                  Email *
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  required
                  className="input-field w-full"
                  placeholder="your.email@example.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="subject" className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                Subject
              </label>
              <input
                type="text"
                id="subject"
                name="subject"
                className="input-field w-full"
                placeholder="What's this about?"
              />
            </div>

            <div>
              <label htmlFor="message" className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                Message *
              </label>
              <textarea
                id="message"
                name="message"
                required
                rows={6}
                className="input-field w-full resize-none"
                placeholder="Tell us about your question, feedback, or how we can help..."
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                type="submit"
                className="btn btn-primary px-8 py-3"
              >
                Send Message
              </button>
              <a
                href="mailto:admin@cahoots.cc"
                className="btn btn-secondary px-8 py-3 text-center"
              >
                Email Directly
              </a>
            </div>
          </form>

          <div className="mt-8 pt-6 border-t" style={{ borderColor: 'var(--color-border)' }}>
            <div className="text-center">
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                You can also reach us directly at:{' '}
                <a href="mailto:admin@cahoots.cc" className="text-brand-vibrant-orange font-semibold">
                  admin@cahoots.cc
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default Contact;

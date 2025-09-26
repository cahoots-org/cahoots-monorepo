import React, { useState } from 'react';
import { useToast } from '../hooks/useToast';
import Footer from '../components/Footer';

const Contact = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { addToast } = useToast();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Create mailto link with form data
      const subject = encodeURIComponent(formData.subject || 'Contact Form Submission');
      const body = encodeURIComponent(
        `Name: ${formData.name}\nEmail: ${formData.email}\n\nMessage:\n${formData.message}`
      );
      const mailtoLink = `mailto:admin@cahoots.cc?subject=${subject}&body=${body}`;
      
      // Open email client
      window.location.href = mailtoLink;
      
      // Reset form
      setFormData({ name: '', email: '', subject: '', message: '' });
      addToast('Email client opened with your message!', 'success');
    } catch (error) {
      addToast('Unable to open email client. Please email us directly at admin@cahoots.cc', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

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
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                  Name *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
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
                  value={formData.email}
                  onChange={handleChange}
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
                value={formData.subject}
                onChange={handleChange}
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
                value={formData.message}
                onChange={handleChange}
                required
                rows={6}
                className="input-field w-full resize-none"
                placeholder="Tell us about your question, feedback, or how we can help..."
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary px-8 py-3"
              >
                {isSubmitting ? 'Opening Email...' : 'Send Message'}
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

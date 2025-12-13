import React from 'react';
import Footer from '../components/Footer';
import { tokens } from '../design-system';

const Contact = () => {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(to bottom, var(--color-bg), var(--color-surface))',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: '20%',
          left: '5%',
          width: '300px',
          height: '300px',
          background: `radial-gradient(circle, ${tokens.colors.secondary[500]}15 0%, transparent 70%)`,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute',
          bottom: '10%',
          right: '10%',
          width: '250px',
          height: '250px',
          background: `radial-gradient(circle, ${tokens.colors.primary[500]}15 0%, transparent 70%)`,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />

        <div className="max-w-4xl mx-auto px-4 py-16 relative z-10">
          <div style={{ textAlign: 'center' }}>
            <span style={{
              display: 'inline-block',
              padding: '8px 16px',
              backgroundColor: `${tokens.colors.secondary[500]}15`,
              color: tokens.colors.secondary[400],
              borderRadius: '9999px',
              fontSize: '14px',
              fontWeight: '600',
              marginBottom: '24px',
            }}>
              Get in Touch
            </span>
            <h1 style={{
              fontSize: 'clamp(32px, 5vw, 48px)',
              fontWeight: '800',
              lineHeight: '1.1',
              marginBottom: '16px',
              color: 'var(--color-text)',
              letterSpacing: '-1px',
            }}>
              We'd Love to Hear From You
            </h1>
            <p style={{
              fontSize: '18px',
              color: 'var(--color-text-muted)',
              maxWidth: '500px',
              margin: '0 auto',
              lineHeight: '1.6',
            }}>
              Have a question, feedback, or just want to say hello? Drop us a message and we'll get back to you soon.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="py-16" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-5xl mx-auto px-4">
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1.5fr',
            gap: '48px',
            alignItems: 'start',
          }}>
            {/* Contact Info */}
            <div>
              <h2 style={{
                fontSize: '24px',
                fontWeight: '700',
                color: 'var(--color-text)',
                marginBottom: '24px',
              }}>
                Other Ways to Reach Us
              </h2>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <ContactMethod
                  icon={
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  }
                  title="Email"
                  value="admin@cahoots.cc"
                  link="mailto:admin@cahoots.cc"
                />
                <ContactMethod
                  icon={
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
                    </svg>
                  }
                  title="Enterprise Sales"
                  value="sales@cahoots.cc"
                  link="mailto:sales@cahoots.cc"
                />
                <ContactMethod
                  icon={
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  }
                  title="Response Time"
                  value="Usually within 24 hours"
                />
              </div>

              {/* FAQ teaser */}
              <div style={{
                marginTop: '40px',
                padding: '24px',
                backgroundColor: 'var(--color-bg)',
                borderRadius: '12px',
                border: '1px solid var(--color-border)',
              }}>
                <h3 style={{
                  fontSize: '16px',
                  fontWeight: '600',
                  color: 'var(--color-text)',
                  marginBottom: '8px',
                }}>
                  Looking for answers?
                </h3>
                <p style={{
                  fontSize: '14px',
                  color: 'var(--color-text-muted)',
                  marginBottom: '12px',
                }}>
                  Check out our pricing page for FAQs about plans, billing, and features.
                </p>
                <a
                  href="/pricing"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: tokens.colors.primary[500],
                    textDecoration: 'none',
                  }}
                >
                  View Pricing & FAQs
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '4px' }}>
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Contact Form */}
            <div style={{
              backgroundColor: 'var(--color-bg)',
              borderRadius: '16px',
              padding: '32px',
              border: '1px solid var(--color-border)',
              boxShadow: '0 4px 24px rgba(0, 0, 0, 0.1)',
            }}>
              <h2 style={{
                fontSize: '20px',
                fontWeight: '600',
                color: 'var(--color-text)',
                marginBottom: '24px',
              }}>
                Send us a message
              </h2>

              <form action="https://formsubmit.co/admin@cahoots.cc" method="POST">
                {/* FormSubmit.co configuration */}
                <input type="hidden" name="_subject" value="New Contact Form Submission - Cahoots" />
                <input type="hidden" name="_captcha" value="false" />
                <input type="hidden" name="_template" value="table" />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '14px',
                      fontWeight: '500',
                      color: 'var(--color-text)',
                      marginBottom: '8px',
                    }}>
                      Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      required
                      placeholder="Your name"
                      className="input-field"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '14px',
                      fontWeight: '500',
                      color: 'var(--color-text)',
                      marginBottom: '8px',
                    }}>
                      Email *
                    </label>
                    <input
                      type="email"
                      name="email"
                      required
                      placeholder="you@example.com"
                      className="input-field"
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: 'var(--color-text)',
                    marginBottom: '8px',
                  }}>
                    Subject
                  </label>
                  <input
                    type="text"
                    name="subject"
                    placeholder="What's this about?"
                    className="input-field"
                    style={{ width: '100%' }}
                  />
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <label style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: 'var(--color-text)',
                    marginBottom: '8px',
                  }}>
                    Message *
                  </label>
                  <textarea
                    name="message"
                    required
                    rows={5}
                    placeholder="Tell us how we can help..."
                    className="input-field"
                    style={{ width: '100%', resize: 'none' }}
                  />
                </div>

                <button
                  type="submit"
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '14px 24px',
                    backgroundColor: tokens.colors.primary[500],
                    color: 'white',
                    fontSize: '16px',
                    fontWeight: '600',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  Send Message
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: '8px' }}>
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

// Contact Method Component
const ContactMethod = ({ icon, title, value, link }) => (
  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
    <div style={{
      width: '48px',
      height: '48px',
      backgroundColor: `${tokens.colors.primary[500]}15`,
      borderRadius: '10px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: tokens.colors.primary[500],
      flexShrink: 0,
    }}>
      {icon}
    </div>
    <div>
      <p style={{
        fontSize: '14px',
        color: 'var(--color-text-muted)',
        marginBottom: '4px',
      }}>
        {title}
      </p>
      {link ? (
        <a
          href={link}
          style={{
            fontSize: '16px',
            fontWeight: '500',
            color: 'var(--color-text)',
            textDecoration: 'none',
          }}
        >
          {value}
        </a>
      ) : (
        <p style={{
          fontSize: '16px',
          fontWeight: '500',
          color: 'var(--color-text)',
        }}>
          {value}
        </p>
      )}
    </div>
  </div>
);

export default Contact;

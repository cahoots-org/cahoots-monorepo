// Redesigned Layout - Professional replacement using design system
import React, { useState, useEffect, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useApp } from '../contexts/AppContext';
import NotificationContainer from './NotificationSystem';
import Footer from './Footer';
import {
  Button,
  Text,
  GradientText,
  HomeIcon,
  DocumentIcon,
  CogIcon,
  BookOpenIcon,
  PlusIcon,
  tokens,
} from '../design-system';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';

const Layout = ({ children }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const { globalLoading } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Check if screen is mobile size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close mobile menu when route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);
  
  // Debug user role changes
  useEffect(() => {
    console.log('[Layout] User changed:', user);
    if (user) {
      console.log('[Layout] User role:', user.role);
      console.log('[Layout] User email:', user.email);
    }
  }, [user]);

  // Navigation items - recalculate when user changes
  const navigationItems = useMemo(() => {
    const items = [
      { path: '/dashboard', icon: HomeIcon, label: 'Dashboard' },
      { path: '/tasks/create', icon: PlusIcon, label: 'Create Task' },
      { path: '/blog', icon: BookOpenIcon, label: 'Blog' },
      { path: '/settings', icon: CogIcon, label: 'Settings' },
    ];
    
    // Add admin items if user is admin
    if (user?.role === 'admin') {
      console.log('[Layout] Adding Blog Admin to nav - user role:', user.role);
      items.push({ path: '/admin/blog', icon: DocumentIcon, label: 'Blog Admin' });
    }
    
    return items;
  }, [user]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: tokens.colors.dark.bg,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: tokens.colors.dark.surface,
        borderBottom: `1px solid ${tokens.colors.dark.border}`,
        position: 'sticky',
        top: 0,
        zIndex: tokens.zIndex.sticky,
      }}>
        <div className="container">
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '64px',
          }}>
            {/* Logo */}
            <Link to={isAuthenticated() ? "/dashboard" : "/"} style={{
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
            }}>
              <img 
                src="/text-logo.png" 
                alt="Cahoots"
                style={{
                  height: '36px',
                  objectFit: 'contain',
                }}
              />
            </Link>

            {/* Desktop Navigation */}
            {!isMobile && (
              <nav style={{
                display: 'flex',
                alignItems: 'center',
                gap: tokens.spacing[1],
              }}>
                {isAuthenticated() ? (
                  // Authenticated navigation
                  navigationItems.map(item => {
                    const isActive = location.pathname === item.path;
                    const Icon = item.icon;
                    
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        style={{ textDecoration: 'none' }}
                      >
                        <Button
                          variant={isActive ? 'primary' : 'ghost'}
                          size="sm"
                          icon={Icon}
                        >
                          {item.label}
                        </Button>
                      </Link>
                    );
                  })
                ) : (
                  // Public navigation
                  <>
                    <Link to="/" style={{ textDecoration: 'none' }}>
                      <Button
                        variant={location.pathname === '/' ? 'primary' : 'ghost'}
                        size="sm"
                        icon={HomeIcon}
                      >
                        Home
                      </Button>
                    </Link>
                    <Link to="/about" style={{ textDecoration: 'none' }}>
                      <Button
                        variant={location.pathname === '/about' ? 'primary' : 'ghost'}
                        size="sm"
                      >
                        About
                      </Button>
                    </Link>
                    <Link to="/contact" style={{ textDecoration: 'none' }}>
                      <Button
                        variant={location.pathname === '/contact' ? 'primary' : 'ghost'}
                        size="sm"
                      >
                        Contact
                      </Button>
                    </Link>
                    <Link to="/blog" style={{ textDecoration: 'none' }}>
                      <Button
                        variant={location.pathname.startsWith('/blog') ? 'primary' : 'ghost'}
                        size="sm"
                        icon={BookOpenIcon}
                      >
                        Blog
                      </Button>
                    </Link>
                    <Link to="/login" style={{ textDecoration: 'none' }}>
                      <Button
                        variant="secondary"
                        size="sm"
                      >
                        Sign In
                      </Button>
                    </Link>
                  </>
                )}
              </nav>
            )}

            {/* Mobile Hamburger Button */}
            {isMobile && (
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: tokens.colors.dark.text,
                  cursor: 'pointer',
                  padding: tokens.spacing[2],
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {mobileMenuOpen ? (
                  <XMarkIcon style={{ width: '24px', height: '24px' }} />
                ) : (
                  <Bars3Icon style={{ width: '24px', height: '24px' }} />
                )}
              </button>
            )}

            {/* User Menu - Only for authenticated users on desktop */}
            {isAuthenticated() && !isMobile && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: tokens.spacing[3],
              }}>
                {/* User Info */}
                {user && (
                  <Text style={{
                    color: tokens.colors.dark.text,
                    fontSize: tokens.typography.fontSize.sm[0],
                    margin: 0,
                  }}>
                    {user.full_name || user.email}
                  </Text>
                )}

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleLogout}
                >
                  Logout
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Menu Dropdown */}
      {isMobile && mobileMenuOpen && (
        <div style={{
          position: 'fixed',
          top: '64px',
          left: 0,
          right: 0,
          backgroundColor: tokens.colors.dark.surface,
          borderBottom: `1px solid ${tokens.colors.dark.border}`,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          zIndex: tokens.zIndex.dropdown,
          maxHeight: 'calc(100vh - 64px)',
          overflowY: 'auto',
        }}>
          <div style={{
            padding: tokens.spacing[4],
            display: 'flex',
            flexDirection: 'column',
            gap: tokens.spacing[2],
          }}>
            {isAuthenticated() ? (
              <>
                {/* User info for mobile */}
                <div style={{
                  padding: `${tokens.spacing[3]} 0`,
                  borderBottom: `1px solid ${tokens.colors.dark.border}`,
                  marginBottom: tokens.spacing[2],
                }}>
                  <Text style={{
                    color: tokens.colors.dark.text,
                    fontSize: tokens.typography.fontSize.sm[0],
                    margin: 0,
                  }}>
                    {user?.full_name || user?.email}
                  </Text>
                </div>
                
                {/* Navigation items */}
                {navigationItems.map(item => {
                  const isActive = location.pathname === item.path;
                  const Icon = item.icon;
                  
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      style={{ textDecoration: 'none' }}
                    >
                      <Button
                        variant={isActive ? 'primary' : 'ghost'}
                        size="md"
                        icon={Icon}
                        style={{ width: '100%', justifyContent: 'flex-start' }}
                      >
                        {item.label}
                      </Button>
                    </Link>
                  );
                })}
                
                <div style={{
                  marginTop: tokens.spacing[2],
                  paddingTop: tokens.spacing[2],
                  borderTop: `1px solid ${tokens.colors.dark.border}`,
                }}>
                  <Button
                    variant="secondary"
                    size="md"
                    onClick={handleLogout}
                    style={{ width: '100%' }}
                  >
                    Logout
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Link to="/" style={{ textDecoration: 'none' }}>
                  <Button
                    variant={location.pathname === '/' ? 'primary' : 'ghost'}
                    size="md"
                    icon={HomeIcon}
                    style={{ width: '100%', justifyContent: 'flex-start' }}
                  >
                    Home
                  </Button>
                </Link>
                <Link to="/about" style={{ textDecoration: 'none' }}>
                  <Button
                    variant={location.pathname === '/about' ? 'primary' : 'ghost'}
                    size="md"
                    style={{ width: '100%', justifyContent: 'flex-start' }}
                  >
                    About
                  </Button>
                </Link>
                <Link to="/contact" style={{ textDecoration: 'none' }}>
                  <Button
                    variant={location.pathname === '/contact' ? 'primary' : 'ghost'}
                    size="md"
                    style={{ width: '100%', justifyContent: 'flex-start' }}
                  >
                    Contact
                  </Button>
                </Link>
                <Link to="/blog" style={{ textDecoration: 'none' }}>
                  <Button
                    variant={location.pathname.startsWith('/blog') ? 'primary' : 'ghost'}
                    size="md"
                    icon={BookOpenIcon}
                    style={{ width: '100%', justifyContent: 'flex-start' }}
                  >
                    Blog
                  </Button>
                </Link>
                <div style={{
                  marginTop: tokens.spacing[2],
                  paddingTop: tokens.spacing[2],
                  borderTop: `1px solid ${tokens.colors.dark.border}`,
                }}>
                  <Link to="/login" style={{ textDecoration: 'none' }}>
                    <Button
                      variant="primary"
                      size="md"
                      style={{ width: '100%' }}
                    >
                      Sign In
                    </Button>
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main style={{
        flex: 1,
        position: 'relative',
      }}>
        {children}
      </main>

      {/* Footer */}
      <Footer />

      {/* Global Loading Overlay */}
      {globalLoading && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: tokens.zIndex.overlay,
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: tokens.spacing[4],
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              border: `4px solid ${tokens.colors.dark.border}`,
              borderTop: `4px solid ${tokens.colors.primary[500]}`,
              borderRadius: tokens.borderRadius.full,
              animation: 'spin 1s linear infinite',
            }} />
            <Text style={{ color: tokens.colors.dark.text }}>
              Loading...
            </Text>
          </div>
        </div>
      )}

      {/* Notification System */}
      <NotificationContainer />
    </div>
  );
};

export default Layout;
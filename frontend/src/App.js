import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { HelmetProvider } from 'react-helmet-async';
import { queryClient } from './lib/query-client';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppProvider } from './contexts/AppContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import TaskBoard from './pages/TaskBoard';
import ProjectView from './pages/ProjectView';
import CreateTask from './pages/CreateTask';
import CreatingProject from './pages/CreatingProject';
import NotFound from './pages/NotFound';
import Landing from './pages/Landing';
import About from './pages/About';
import Contact from './pages/Contact';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Register from './pages/Register';
import OAuthCallback from './pages/OAuthCallback';
import OAuthCallbackSecure from './pages/OAuthCallbackSecure';
import BlogPage from './pages/BlogPage';
import BlogAdminPage from './pages/BlogAdminPage';
import { ToasterComponent } from './components/ui/toaster';
import { UserSettingsSync } from './components/UserSettingsSync';

// Import design system styles
import './design-system/styles/globals.css';

// AuthRoute component to conditionally render Landing or Dashboard based on auth status
const AuthRoute = () => {
  const { isAuthenticated, loading, user } = useAuth();
  
  // If still loading auth state, return null (Layout will show spinner)
  if (loading) {
    console.log('AuthRoute: still loading auth state');
    return null;
  }
  
  // If authenticated, redirect to dashboard, otherwise show landing page
  const authenticated = isAuthenticated();
  console.log('AuthRoute: authenticated status:', authenticated);
  console.log('AuthRoute: user:', user);
  console.log('AuthRoute: will render:', authenticated ? 'Dashboard redirect' : 'Landing page');
  
  return authenticated ? <Navigate to="/dashboard" replace /> : <Landing />;
};

function App() {
  // Check if we have a successful OAuth login flag
  React.useEffect(() => {
    const oauthLoginSuccess = sessionStorage.getItem('oauth_login_success');
    const redirectPath = sessionStorage.getItem('redirect_after_reload');
    
    if (oauthLoginSuccess === 'true' && redirectPath) {
      console.log('Detected successful OAuth login, clearing flags');
      sessionStorage.removeItem('oauth_login_success');
      sessionStorage.removeItem('redirect_after_reload');
    }
  }, []);
  
  return (
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <SettingsProvider>
            <UserSettingsSync />
            <ThemeProvider>
              <AppProvider>
                <WebSocketProvider>
                    <Layout>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<AuthRoute />} />
            <Route path="/landing" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/oauth-callback" element={<OAuthCallbackSecure />} />
            <Route path="/oauth/:provider/callback" element={<OAuthCallback />} />
            <Route path="/404" element={<NotFound />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/blog" element={<BlogPage />} />
            <Route path="/blog/:slug" element={<BlogPage />} />

            {/* Protected routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/tasks/create" element={
              <ProtectedRoute>
                <CreateTask />
              </ProtectedRoute>
            } />
            <Route path="/tasks/:taskId" element={
              <ProtectedRoute>
                <TaskBoard />
              </ProtectedRoute>
            } />
            <Route path="/projects/creating" element={
              <ProtectedRoute>
                <CreatingProject />
              </ProtectedRoute>
            } />
            <Route path="/projects/:taskId" element={
              <ProtectedRoute>
                <ProjectView />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } />
            <Route path="/admin/blog" element={
              <ProtectedRoute>
                <BlogAdminPage />
              </ProtectedRoute>
            } />
            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
                    </Layout>
                </WebSocketProvider>
              </AppProvider>
            </ThemeProvider>
        </SettingsProvider>
      </AuthProvider>
      <ToasterComponent />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
    </HelmetProvider>
  );
}

export default App;
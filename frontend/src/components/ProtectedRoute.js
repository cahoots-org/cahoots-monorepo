import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Text, tokens } from '../design-system';

/**
 * ProtectedRoute component that redirects to login page if user is not authenticated
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication status
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: tokens.spacing[4],
        backgroundColor: tokens.colors.dark.bg,
      }}>
        <div style={{
          width: '48px',
          height: '48px',
          border: `4px solid ${tokens.colors.dark.border}`,
          borderTop: `4px solid ${tokens.colors.primary[500]}`,
          borderRadius: tokens.borderRadius.full,
          animation: 'spin 1s linear infinite',
        }} />
        <Text style={{ color: tokens.colors.dark.muted }}>
          Checking authentication...
        </Text>
      </div>
    );
  }

  // Redirect to login if not authenticated
  const authenticated = isAuthenticated();
  
  if (!authenticated) {
    // Not authenticated, redirecting to login
    // Save the current location to redirect back after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Render children if authenticated
  return children;
};

export default ProtectedRoute;

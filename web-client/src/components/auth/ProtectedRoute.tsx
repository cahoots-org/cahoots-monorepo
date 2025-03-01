import { ReactNode, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';
import { LoadingOverlay } from '@mantine/core';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    const init = async () => {
      if (!isAuthenticated) {
        await checkAuth();
      }
    };
    init();
  }, [checkAuth, isAuthenticated]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/', { state: { from: location.pathname } });
    }
  }, [isLoading, isAuthenticated, navigate, location]);

  if (isLoading) {
    return <LoadingOverlay visible />;
  }

  return isAuthenticated ? <>{children}</> : null;
} 
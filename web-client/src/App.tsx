import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MantineProvider, createTheme, Stack } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { HomePage } from './pages/home/HomePage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { ProjectsPage } from './pages/projects/ProjectsPage';
import { ProjectDetailsPage } from './pages/projects/ProjectDetailsPage';
import PricingPage from './pages/pricing/PricingPage';
import FeaturesPage from './pages/features/FeaturesPage';
import GitHubCallback from './pages/auth/GitHubCallback';
import GoogleCallback from './pages/auth/GoogleCallback';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Header } from './components/layout/Header';
import { config } from './config/config';

const theme = createTheme({
  primaryColor: 'orange',
  colors: {
    orange: [
      '#FFE8E3',
      '#FFD1C7',
      '#FFBAA8',
      '#FFA289',
      '#FF8B6A',
      '#FF734B',
      '#FF4B2B', // Primary
      '#FF3311',
      '#F71F00',
      '#E31C00',
    ],
    dark: [
      '#C1C2C5',
      '#A6A7AB',
      '#909296',
      '#5C5F66',
      '#373A40',
      '#2C2E33',
      '#25262B',
      '#1A1B1E',
      '#141517',
      '#101113',
    ],
  },
  fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  headings: {
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontWeight: '600',
  },
  defaultRadius: 'md',
  components: {
    Button: {
      defaultProps: {
        size: 'md',
      },
      styles: {
        root: {
          fontWeight: 500,
          backgroundImage: config.ui.theme.gradients.primary,
          border: 0,
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: config.ui.theme.shadows.button,
          },
        },
        label: {
          color: '#FFFFFF',
          textShadow: '-0.5px -0.5px 0 rgba(0,0,0,0.2), 0.5px -0.5px 0 rgba(0,0,0,0.2), -0.5px 0.5px 0 rgba(0,0,0,0.2), 0.5px 0.5px 0 rgba(0,0,0,0.2)',
        },
      },
    },
    Card: {
      defaultProps: {
        radius: 'md',
        withBorder: true,
      },
      styles: {
        root: {
          backgroundColor: config.ui.theme.surfaceColor,
          borderColor: config.ui.theme.borderColor,
          boxShadow: config.ui.theme.shadows.card,
        },
      },
    },
    TextInput: {
      styles: {
        input: {
          backgroundColor: '#1A1B1E', // Using dark[7] directly
          borderColor: config.ui.theme.borderColor,
          color: config.ui.theme.textColor,
          '&:focus': {
            borderColor: config.ui.theme.primaryColor,
          },
        },
      },
    },
    PasswordInput: {
      styles: {
        input: {
          backgroundColor: '#1A1B1E', // Using dark[7] directly
          borderColor: config.ui.theme.borderColor,
          color: config.ui.theme.textColor,
          '&:focus': {
            borderColor: config.ui.theme.primaryColor,
          },
        },
      },
    },
  },
});

export function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications />
      <Router>
        <Stack gap={0}>
          <Header />
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/auth/github/callback" element={<GitHubCallback />} />
            <Route path="/auth/google/callback" element={<GoogleCallback />} />

            {/* Protected Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects"
              element={
                <ProtectedRoute>
                  <ProjectsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:id"
              element={
                <ProtectedRoute>
                  <ProjectDetailsPage />
                </ProtectedRoute>
              }
            />

            {/* Redirect unmatched routes to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Stack>
      </Router>
    </MantineProvider>
  );
}

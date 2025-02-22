import { Group, Button, Box, Container, Drawer, Burger } from '@mantine/core';
import { Link, useLocation } from 'react-router-dom';
import { useDisclosure } from '@mantine/hooks';
import { Logo } from '../common/Logo';
import { config } from '../../config/config';

export function Header() {
  const location = useLocation();
  const [drawerOpened, { toggle: toggleDrawer, close: closeDrawer }] = useDisclosure(false);
  const isAuthPage = ['/login', '/register'].includes(location.pathname);

  if (isAuthPage) return null;

  const navigationItems = [
    { label: 'Features', to: '/features' },
    { label: 'Pricing', to: '/pricing' },
    { label: 'Sign In', to: '/login' },
  ];

  return (
    <Box 
      style={{ 
        borderBottom: `1px solid ${config.ui.theme.borderColor}`,
        backgroundColor: config.ui.theme.surfaceColor,
        position: 'sticky',
        top: 0,
        zIndex: 1000,
      }}
    >
      <Container size="lg">
        <Group justify="space-between" h="60px">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <Logo size={32} withText={true} />
          </Link>

          {/* Desktop Navigation */}
          <Group 
            gap="sm" 
            visibleFrom="sm"
          >
            {navigationItems.map((item) => (
              <Button
                key={item.to}
                component={Link}
                to={item.to}
                variant="subtle"
                color="gray"
              >
                {item.label}
              </Button>
            ))}
            <Button
              component={Link}
              to="/register"
              style={{
                backgroundImage: config.ui.theme.gradients.primary,
              }}
            >
              Get Started
            </Button>
          </Group>

          {/* Mobile Burger */}
          <Burger 
            opened={drawerOpened} 
            onClick={toggleDrawer} 
            hiddenFrom="sm"
          />
        </Group>
      </Container>

      {/* Mobile Drawer */}
      <Drawer
        opened={drawerOpened}
        onClose={closeDrawer}
        size="100%"
        padding="md"
        title={<Logo size={32} withText={false} />}
        styles={{
          header: {
            backgroundColor: config.ui.theme.surfaceColor,
            borderBottom: `1px solid ${config.ui.theme.borderColor}`,
          },
          body: {
            backgroundColor: config.ui.theme.backgroundColor,
          }
        }}
      >
        <Box py="md">
          {navigationItems.map((item) => (
            <Button
              key={item.to}
              component={Link}
              to={item.to}
              variant="subtle"
              color="gray"
              fullWidth
              mb="sm"
              onClick={closeDrawer}
            >
              {item.label}
            </Button>
          ))}
          <Button
            component={Link}
            to="/register"
            fullWidth
            style={{
              backgroundImage: config.ui.theme.gradients.primary,
            }}
            onClick={closeDrawer}
          >
            Get Started
          </Button>
        </Box>
      </Drawer>
    </Box>
  );
} 
import { NavLink, Stack } from '@mantine/core';
import { IconDashboard, IconFolder, IconSettings } from '@tabler/icons-react';
import { Link, useLocation } from 'react-router-dom';

export function NavMenu() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <Stack gap="xs">
      <NavLink
        component={Link}
        to="/"
        label="Dashboard"
        leftSection={<IconDashboard size="1.2rem" />}
        active={isActive('/')}
      />
      <NavLink
        component={Link}
        to="/projects"
        label="Projects"
        leftSection={<IconFolder size="1.2rem" />}
        active={isActive('/projects')}
      />
      <NavLink
        component={Link}
        to="/settings"
        label="Settings"
        leftSection={<IconSettings size="1.2rem" />}
        active={isActive('/settings')}
      />
    </Stack>
  );
} 
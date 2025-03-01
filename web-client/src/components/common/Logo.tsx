import { Image, Box, Text } from '@mantine/core';

interface LogoProps {
  size?: number;
  withText?: boolean;
}

export function Logo({ size = 32, withText = false }: LogoProps) {
  return (
    <Box style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <Image
        src="/cahoots-logo.png"
        alt="Cahoots Logo"
        w={size}
        h={size}
        style={{ objectFit: 'contain' }}
      />
      {withText && (
        <Text
          component="span"
          style={{
            fontSize: size * 0.75,
            fontWeight: 700,
            color: '#FFFFFF',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          Cahoots
        </Text>
      )}
    </Box>
  );
} 
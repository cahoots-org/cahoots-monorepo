import { Container, Title, Text, Button, Stack, Group, Card, SimpleGrid, Box } from '@mantine/core';
import { Link } from 'react-router-dom';
import { IconRobot, IconBrain, IconCode, IconGitBranch } from '../../components/common/icons';
import { Logo } from '../../components/common/Logo';
import { config } from '../../config/config';

const features = [
  {
    icon: IconRobot,
    title: 'AI Development Team',
    description: 'Your personal team of AI agents that work together to build your software projects.',
  },
  {
    icon: IconBrain,
    title: 'Context-Aware',
    description: 'Agents understand your project deeply and maintain context across conversations.',
  },
  {
    icon: IconCode,
    title: 'Full-Stack Development',
    description: 'From frontend to backend, database to DevOps, we handle it all.',
  },
  {
    icon: IconGitBranch,
    title: 'Git Integration',
    description: 'Seamless integration with GitHub for version control and collaboration.',
  },
];

export function HomePage() {
  return (
    <Box style={{ background: config.ui.theme.backgroundColor, minHeight: '100vh' }}>
      <Container size="lg" py="6rem">
        <Stack gap="6rem">
          {/* Hero Section */}
          <Stack gap="lg" align="center" style={{ textAlign: 'center' }}>
            <Logo size={100} withText={false} />
            <Stack gap="md" maw={800} mx="auto" px="md">
              <Title 
                order={1} 
                style={{ 
                  fontSize: 'clamp(2rem, 5vw, 3rem)',
                  lineHeight: 1.2 
                }} 
                c="white"
              >
                Your AI Development Team
              </Title>
              <Text 
                style={{ 
                  fontSize: 'clamp(1rem, 2vw, 1.25rem)'
                }} 
                c="dimmed" 
                maw={600} 
                mx="auto"
              >
                Build your next project with a team of AI agents that work together seamlessly.
              </Text>
            </Stack>
            <Group gap="md" wrap="wrap" justify="center">
              <Button
                component={Link}
                to="/register"
                size="lg"
                style={{
                  backgroundImage: config.ui.theme.gradients.primary,
                }}
              >
                Get Started
              </Button>
              <Button
                component={Link}
                to="/features"
                variant="outline"
                size="lg"
              >
                Learn More
              </Button>
            </Group>
          </Stack>

          {/* Features Section */}
          <SimpleGrid 
            cols={{ base: 1, sm: 2 }} 
            spacing={{ base: 'md', sm: 'xl' }}
            verticalSpacing={{ base: 'md', sm: 'xl' }}
          >
            {features.map((feature) => (
              <Card 
                key={feature.title}
                padding="xl"
                radius="md"
                style={{
                  backgroundColor: config.ui.theme.surfaceColor,
                  borderColor: config.ui.theme.borderColor,
                }}
              >
                <feature.icon size={40} stroke={1.5} color={config.ui.theme.primaryColor} />
                <Text size="lg" fw={500} mt="md" c="white">
                  {feature.title}
                </Text>
                <Text size="sm" c="dimmed" mt="sm">
                  {feature.description}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      </Container>
    </Box>
  );
} 
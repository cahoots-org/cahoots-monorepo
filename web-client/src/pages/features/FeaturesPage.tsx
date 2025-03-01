import { Container, Title, Text, Stack, Card, SimpleGrid, Box, List } from '@mantine/core';
import { IconBrain, IconRobot, IconCode, IconGitBranch, IconBuildingFactory, IconTestPipe, IconBug, IconServer } from '../../components/common/icons';
import { config } from '../../config/config';

const features = [
  {
    icon: IconRobot,
    title: 'AI Development Team',
    description: 'A complete team of specialized AI agents working together on your project.',
    details: [
      'Project Manager for task coordination',
      'Frontend Developer for UI/UX',
      'Backend Developer for APIs and services',
      'DevOps Engineer for infrastructure',
      'QA Engineer for testing and quality',
    ],
  },
  {
    icon: IconBrain,
    title: 'Context-Aware Development',
    description: 'Agents maintain deep understanding of your project context.',
    details: [
      'Remembers previous discussions and decisions',
      'Understands project architecture',
      'Maintains coding style consistency',
      'Tracks dependencies and requirements',
      'Evolves with your project',
    ],
  },
  {
    icon: IconBuildingFactory,
    title: 'End-to-End Development',
    description: 'Complete software development lifecycle support.',
    details: [
      'Project planning and architecture',
      'Frontend and backend development',
      'Database design and optimization',
      'API development and integration',
      'Documentation and maintenance',
    ],
  },
  {
    icon: IconGitBranch,
    title: 'Version Control Integration',
    description: 'Seamless integration with Git and GitHub.',
    details: [
      'Automatic repository setup',
      'Branch management',
      'Pull request creation',
      'Code review assistance',
      'Merge conflict resolution',
    ],
  },
  {
    icon: IconTestPipe,
    title: 'Automated Testing',
    description: 'Comprehensive testing at every level.',
    details: [
      'Unit test generation',
      'Integration testing',
      'End-to-end testing',
      'Performance testing',
      'Security testing',
    ],
  },
  {
    icon: IconBug,
    title: 'Intelligent Debugging',
    description: 'Advanced debugging and error resolution.',
    details: [
      'Error pattern recognition',
      'Root cause analysis',
      'Fix suggestions',
      'Regression testing',
      'Performance optimization',
    ],
  },
  {
    icon: IconServer,
    title: 'Infrastructure Management',
    description: 'Complete DevOps and infrastructure support.',
    details: [
      'Docker containerization',
      'Kubernetes orchestration',
      'CI/CD pipeline setup',
      'Cloud deployment',
      'Monitoring and logging',
    ],
  },
  {
    icon: IconCode,
    title: 'Modern Tech Stack',
    description: 'Support for modern technologies and frameworks.',
    details: [
      'React, Vue, Angular frontends',
      'Node.js, Python, Go backends',
      'SQL and NoSQL databases',
      'REST and GraphQL APIs',
      'Microservices architecture',
    ],
  },
];

export default function FeaturesPage() {
  return (
    <Box style={{ background: config.ui.theme.backgroundColor, minHeight: '100vh' }}>
      <Container size="lg" py="xl">
        <Stack gap="xl">
          <Stack gap="md" align="center" style={{ textAlign: 'center' }}>
            <Title order={1} size="h1" c="white">
              Features
            </Title>
            <Text size="xl" c="dimmed" maw={600}>
              Everything you need to build your next project with AI-powered development.
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
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
                <List
                  mt="md"
                  spacing="sm"
                  size="sm"
                  c="dimmed"
                >
                  {feature.details.map((detail) => (
                    <List.Item key={detail}>{detail}</List.Item>
                  ))}
                </List>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      </Container>
    </Box>
  );
} 
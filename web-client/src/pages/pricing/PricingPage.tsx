import { Container, Title, Text, Stack, Card, SimpleGrid, Box, Button, List, Group, Tooltip } from '@mantine/core';
import { Link } from 'react-router-dom';
import { IconCheck, IconInfoCircle } from '../../components/common/icons';
import { config } from '../../config/config';

const plans = [
  {
    name: 'Starter',
    price: '$49',
    period: 'per month',
    description: 'Perfect for small projects and individual developers.',
    features: [
      'Up to 3 concurrent projects',
      ['Limited AI models', 'Access to basic models like GPT-3.5'],
      'GitHub repository management',
      'Basic task automation',
      'Community support',
      'Email support',
    ],
    highlight: false,
    buttonText: 'Start Free Trial',
    trialDays: 14,
  },
  {
    name: 'Professional',
    price: '$149',
    period: 'per month',
    description: 'Ideal for growing teams and businesses.',
    features: [
      'Up to 10 concurrent projects',
      ['Advanced AI models', 'Access to GPT-4, Claude, and more'],
      'Full GitHub integration',
      'CI/CD automation',
      'Priority support',
      'Slack support',
      'Custom task workflows',
    ],
    highlight: true,
    buttonText: 'Start Free Trial',
    trialDays: 14,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'per month',
    description: 'For large organizations with custom needs.',
    features: [
      'Unlimited projects',
      ['All AI models', 'Full access to all available AI models'],
      'Custom integrations',
      'Dedicated support team',
      'SLA guarantees',
      'On-premises deployment',
      'Custom security controls',
      'Audit logging',
    ],
    highlight: false,
    buttonText: 'Contact Sales',
    trialDays: 0,
  },
];

export default function PricingPage() {
  return (
    <Box style={{ background: config.ui.theme.backgroundColor, minHeight: '100vh' }}>
      <Container size="lg" py="xl">
        <Stack gap="xl">
          <Stack gap="md" align="center" style={{ textAlign: 'center' }}>
            <Title order={1} size="h1" c="white">
              Simple, Transparent Pricing
            </Title>
            <Text size="xl" c="dimmed" maw={600}>
              Choose the plan that best fits your needs. Starter and Professional plans include a 14-day free trial.
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="xl">
            {plans.map((plan) => (
              <Card 
                key={plan.name}
                padding="xl"
                radius="md"
                style={{
                  backgroundColor: config.ui.theme.surfaceColor,
                  borderColor: plan.highlight ? config.ui.theme.primaryColor : config.ui.theme.borderColor,
                  borderWidth: plan.highlight ? 2 : 1,
                  display: 'flex',
                  flexDirection: 'column',
                  height: '100%',
                }}
              >
                <Stack gap="md" style={{ flex: 1, justifyContent: 'space-between' }}>
                  <div>
                    <Group justify="space-between" align="flex-start">
                      <div>
                        <Text size="xl" fw={700} c="white">
                          {plan.name}
                        </Text>
                        <Text size="sm" c="dimmed">
                          {plan.description}
                        </Text>
                      </div>
                      <Stack gap={0} align="flex-end">
                        <Text size="xl" fw={700} c="white">
                          {plan.price}
                        </Text>
                        <Text size="sm" c="dimmed">
                          {plan.period}
                        </Text>
                      </Stack>
                    </Group>

                    <List
                      spacing="sm"
                      size="sm"
                      center
                      icon={
                        <IconCheck 
                          style={{ color: config.ui.theme.primaryColor }} 
                          size={16}
                        />
                      }
                      mt="md"
                    >
                      {plan.features.map((feature) => (
                        <List.Item key={Array.isArray(feature) ? feature[0] : feature}>
                          {Array.isArray(feature) ? (
                            <Group gap="xs" wrap="nowrap">
                              <Text c="dimmed">{feature[0]}</Text>
                              <Tooltip label={feature[1]} position="top">
                                <IconInfoCircle 
                                  style={{ color: config.ui.theme.mutedTextColor }} 
                                  size={16}
                                />
                              </Tooltip>
                            </Group>
                          ) : (
                            <Text c="dimmed">{feature}</Text>
                          )}
                        </List.Item>
                      ))}
                    </List>
                  </div>

                  <Button
                    component={Link}
                    to={plan.name === 'Enterprise' ? '/contact' : '/register'}
                    fullWidth
                    size="lg"
                    variant={plan.highlight ? 'filled' : 'outline'}
                    style={plan.highlight ? {
                      backgroundImage: config.ui.theme.gradients.primary,
                    } : undefined}
                  >
                    {plan.buttonText}
                  </Button>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      </Container>
    </Box>
  );
} 
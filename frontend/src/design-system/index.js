// Design System Index - Centralized exports for easy importing

// Tokens
export { default as tokens, cssVariables } from './tokens';

// Icons
export * from './icons';

// Components
export { default as Button } from './components/Button';
export { default as IconButton } from './components/IconButton';
export { default as Card, CardHeader, CardContent, CardFooter } from './components/Card';
export { default as Badge, getStatusVariant } from './components/Badge';
export { default as Modal } from './components/Modal';
export { default as LoadingSpinner } from './components/LoadingSpinner';
export { default as EmptyState } from './components/EmptyState';
export { default as ErrorMessage } from './components/ErrorMessage';
export { default as Progress } from './components/Progress';
export { default as Input } from './components/Input';
export { default as TextArea } from './components/TextArea';
export { default as Select } from './components/Select';
export { default as Switch } from './components/Switch';
export {
  default as Text,
  Heading1,
  Heading2,
  Heading3, 
  Heading4,
  TextSmall,
  TextLarge,
  Caption,
  Code,
  Label,
  GradientText,
} from './components/Typography';

// Styles
export { default as globalStyles } from './styles/globals.css';
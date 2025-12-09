/**
 * User-Friendly Terminology Mapping
 *
 * Maps technical/domain terms to user-friendly alternatives.
 * Use these throughout the UI to keep language consistent and accessible.
 */

// Main terminology mapping
export const terms = {
  // Event Modeling concepts -> User-friendly
  slice: 'feature',
  slices: 'features',
  chapter: 'module',
  chapters: 'modules',
  swimlane: 'business area',
  swimlanes: 'business areas',

  // CQRS/Event Sourcing -> User-friendly
  readModel: 'data view',
  readModels: 'data views',
  command: 'action',
  commands: 'actions',
  event: 'event',
  events: 'events',
  domainEvent: 'system event',
  domainEvents: 'system events',

  // Process terms -> User-friendly
  decomposition: 'planning',
  decompose: 'break down',
  eventModeling: 'system design',
  eventModel: 'system blueprint',
  automation: 'background process',
  automations: 'background processes',

  // Task terms
  epic: 'major goal',
  epics: 'major goals',
  userStory: 'user need',
  userStories: 'user needs',
  storyPoints: 'complexity',

  // Technical terms
  schema: 'data structure',
  schemas: 'data structures',
  api: 'interface',
  endpoint: 'connection point',
};

// Capitalized versions for titles/headers
export const Terms = {
  Slice: 'Feature',
  Slices: 'Features',
  Chapter: 'Module',
  Chapters: 'Modules',
  Swimlane: 'Business Area',
  Swimlanes: 'Business Areas',
  ReadModel: 'Data View',
  ReadModels: 'Data Views',
  Command: 'Action',
  Commands: 'Actions',
  Event: 'Event',
  Events: 'Events',
  EventModel: 'System Blueprint',
  Epic: 'Major Goal',
  Epics: 'Major Goals',
  UserStory: 'User Need',
  UserStories: 'User Needs',
  Schema: 'Data Structure',
  Schemas: 'Data Structures',
  Automation: 'Background Process',
  Automations: 'Background Processes',
};

// Explanatory tooltips for technical concepts
export const tooltips = {
  feature: 'A specific capability or piece of functionality in your system',
  module: 'A group of related features that work together',
  businessArea: 'A category of functionality (like "User Management" or "Payments")',
  dataView: 'How data is displayed or queried - what users see on screen',
  action: 'Something a user or the system can do (like "Create Account" or "Submit Order")',
  event: 'Something that happened in the system (like "User Registered" or "Order Placed")',
  blueprint: 'The overall design showing how all parts of your system connect',
  backgroundProcess: 'Automated tasks that run without user interaction',
  majorGoal: 'A large objective that contains multiple smaller tasks',
  userNeed: 'A specific thing a user wants to accomplish',
  complexity: 'How much effort is needed - higher numbers mean more work',
  dataStructure: 'The shape and format of data in your system',
};

// Processing stage descriptions - what's actually happening
export const stageDescriptions = {
  source_processing: {
    name: 'Reading Your Request',
    description: 'Understanding what you want to build',
    detail: 'We\'re carefully reading through your requirements to understand every detail.',
  },
  context_analysis: {
    name: 'Understanding Context',
    description: 'Figuring out how everything connects',
    detail: 'We\'re identifying how different parts of your system will work together.',
  },
  complexity_analysis: {
    name: 'Estimating Complexity',
    description: 'Calculating how much work is needed',
    detail: 'We\'re assessing the size and complexity of each part of your project.',
  },
  technical_planning: {
    name: 'Technical Planning',
    description: 'Designing the system architecture',
    detail: 'We\'re deciding on the best technical approach for each feature.',
  },
  task_decomposition: {
    name: 'Breaking It Down',
    description: 'Creating actionable tasks',
    detail: 'We\'re dividing your project into specific, implementable pieces.',
  },
  final_composition: {
    name: 'Putting It Together',
    description: 'Finalizing your project plan',
    detail: 'We\'re organizing everything into a complete, ready-to-build plan.',
  },
  event_modeling: {
    name: 'Designing System Blueprint',
    description: 'Planning how data flows through your app',
    detail: 'We\'re mapping out user actions, system responses, and data views.',
  },
};

// Activity feed message templates - conversational style
export const activityMessages = {
  // Analysis events
  'analysis.started': 'Starting to analyze your project...',
  'analysis.reading': 'Reading through your requirements...',
  'analysis.understanding': 'Understanding what you want to build...',

  // Discovery events
  'discovery.epic': (name) => `Found a major goal: "${name}"`,
  'discovery.story': (name) => `Identified user need: "${name}"`,
  'discovery.task': (name) => `Created task: "${name}"`,
  'discovery.event': (name) => `Discovered system event: "${name}"`,
  'discovery.action': (name) => `Found user action: "${name}"`,
  'discovery.dataView': (name) => `Identified data view: "${name}"`,

  // Progress events
  'progress.techStack': 'Analyzed your technology choices...',
  'progress.complexity': 'Calculated project complexity...',
  'progress.structure': 'Organized project structure...',

  // Completion events
  'complete.analysis': 'Finished analyzing your requirements!',
  'complete.planning': 'Project plan is ready!',
  'complete.blueprint': 'System blueprint is complete!',

  // Code generation events
  'codegen.started': 'Starting to generate code...',
  'codegen.scaffolding': 'Setting up project structure...',
  'codegen.feature': (name) => `Building feature: "${name}"`,
  'codegen.testing': 'Running tests...',
  'codegen.complete': 'Code generation complete!',
};

// Helper function to get user-friendly term
export function friendly(technicalTerm) {
  const lower = technicalTerm.toLowerCase();
  return terms[lower] || terms[technicalTerm] || technicalTerm;
}

// Helper function to get capitalized user-friendly term
export function Friendly(technicalTerm) {
  return Terms[technicalTerm] || terms[technicalTerm.toLowerCase()] || technicalTerm;
}

// Helper to pluralize/singularize
export function pluralize(term, count) {
  if (count === 1) {
    return terms[term] || term;
  }
  // Try to find plural form
  const pluralKey = term + 's';
  return terms[pluralKey] || terms[term] + 's';
}

export default {
  terms,
  Terms,
  tooltips,
  stageDescriptions,
  activityMessages,
  friendly,
  Friendly,
  pluralize,
};

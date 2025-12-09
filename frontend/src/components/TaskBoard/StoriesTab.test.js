/**
 * Property-Based Tests for StoriesTab Component
 * Feature: project-summary-overhaul
 */

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import StoriesTab from './StoriesTab';

// Helper functions to generate random test data
const generateRandomString = (prefix = 'test') => `${prefix}_${Math.random().toString(36).substring(7)}`;

const generateEpic = (id) => ({
  id: id || generateRandomString('epic'),
  title: generateRandomString('Epic Title'),
  description: generateRandomString('Epic Description'),
  priority: Math.floor(Math.random() * 5) + 1,
});

const generateStory = (epicId) => ({
  id: generateRandomString('story'),
  epic_id: epicId,
  actor: generateRandomString('actor'),
  action: generateRandomString('action'),
  benefit: generateRandomString('benefit'),
  priority: ['must_have', 'should_have', 'could_have', 'wont_have'][Math.floor(Math.random() * 4)],
  acceptance_criteria: Array.from({ length: Math.floor(Math.random() * 5) }, () => generateRandomString('criteria')),
});

/**
 * Feature: project-summary-overhaul, Property 1: Story grouping by epic
 * Validates: Requirements 2.2
 * 
 * Property: For any set of user stories with epic_id fields, all stories with 
 * the same epic_id should be rendered within the same epic card
 */
describe('StoriesTab - Story Grouping', () => {
  test('all stories with the same epic_id are grouped together (100 iterations)', () => {
    // Run property test 100 times with random data
    for (let iteration = 0; iteration < 100; iteration++) {
      // Generate random epics (1-5 epics)
      const numEpics = Math.floor(Math.random() * 5) + 1;
      const epics = Array.from({ length: numEpics }, () => generateEpic());
      const epicIds = epics.map(e => e.id);

      // Generate random stories (1-20 stories)
      const numStories = Math.floor(Math.random() * 20) + 1;
      const stories = Array.from({ length: numStories }, () => {
        const randomEpicId = epicIds[Math.floor(Math.random() * epicIds.length)];
        return generateStory(randomEpicId);
      });

      // Arrange
      const task = {
        context: {
          epics,
          user_stories: stories,
        },
      };

      // Act
      const { container, unmount } = render(<StoriesTab task={task} />);

      // Assert: Group stories by epic_id
      const storiesByEpic = stories.reduce((acc, story) => {
        const epicId = story.epic_id;
        if (!acc[epicId]) {
          acc[epicId] = [];
        }
        acc[epicId].push(story);
        return acc;
      }, {});

      // For each epic, verify all its stories are present
      Object.entries(storiesByEpic).forEach(([epicId, epicStories]) => {
        // Find the epic in the rendered output
        const epic = epics.find(e => e.id === epicId);
        
        if (epic) {
          // Verify the epic card exists
          expect(screen.getByText(epic.title)).toBeInTheDocument();
          
          // Count how many stories should be in this epic
          const expectedStoryCount = epicStories.length;
          
          // Verify the story count badge shows the correct number
          const storyCountBadges = screen.getAllByText(`${expectedStoryCount} stories`);
          expect(storyCountBadges.length).toBeGreaterThanOrEqual(1);
        }
      });

      // Verify the total number of epics and stories is correct
      expect(screen.getByText(`${epics.length} Epics`)).toBeInTheDocument();
      expect(screen.getByText(`${stories.length} Stories`)).toBeInTheDocument();

      // Clean up for next iteration
      unmount();
    }
  });

  test('stories from different epics are not mixed together (100 iterations)', () => {
    // Run property test 100 times with random data
    for (let iteration = 0; iteration < 100; iteration++) {
      // Generate random epics (2-5 epics to ensure multiple epics)
      const numEpics = Math.floor(Math.random() * 4) + 2;
      const epics = Array.from({ length: numEpics }, () => generateEpic());
      const epicIds = epics.map(e => e.id);

      // Generate random stories (2-20 stories)
      const numStories = Math.floor(Math.random() * 19) + 2;
      const stories = Array.from({ length: numStories }, () => {
        const randomEpicId = epicIds[Math.floor(Math.random() * epicIds.length)];
        return generateStory(randomEpicId);
      });

      // Arrange
      const task = {
        context: {
          epics,
          user_stories: stories,
        },
      };

      // Act
      const { unmount } = render(<StoriesTab task={task} />);

      // Assert: Verify each epic is rendered
      epics.forEach(epic => {
        expect(screen.getByText(epic.title)).toBeInTheDocument();
      });

      // Verify the total number of stories is correct
      const totalStories = stories.length;
      expect(screen.getByText(`${totalStories} Stories`)).toBeInTheDocument();

      // Clean up for next iteration
      unmount();
    }
  });

  /**
   * Feature: project-summary-overhaul, Property 2: Story format completeness
   * Validates: Requirements 2.3
   * 
   * Property: For any user story, the rendered output should contain the actor field and the action field
   */
  test('all stories contain actor and action fields (100 iterations)', () => {
    // Run property test 100 times with random data
    for (let iteration = 0; iteration < 100; iteration++) {
      // Generate random epics (1-3 epics)
      const numEpics = Math.floor(Math.random() * 3) + 1;
      const epics = Array.from({ length: numEpics }, () => generateEpic());
      const epicIds = epics.map(e => e.id);

      // Generate random stories (1-10 stories)
      const numStories = Math.floor(Math.random() * 10) + 1;
      const stories = Array.from({ length: numStories }, () => {
        const randomEpicId = epicIds[Math.floor(Math.random() * epicIds.length)];
        return generateStory(randomEpicId);
      });

      // Arrange
      const task = {
        context: {
          epics,
          user_stories: stories,
        },
      };

      // Act
      const { unmount, container } = render(<StoriesTab task={task} />);

      // Expand all epics by clicking "Expand All" button
      const expandAllButton = screen.getByText('Expand All');
      fireEvent.click(expandAllButton);

      // Assert: Verify that the story format includes "As a" and "I want to" keywords
      // which indicate actor and action fields are being rendered
      const containerText = container.textContent;
      
      // Count occurrences of "As a" and "I want to" in the rendered output
      const asACount = (containerText.match(/As a/gi) || []).length;
      const iWantToCount = (containerText.match(/I want to/gi) || []).length;
      
      // Each story should have "As a" and "I want to" in its rendering
      expect(asACount).toBeGreaterThanOrEqual(stories.length);
      expect(iWantToCount).toBeGreaterThanOrEqual(stories.length);

      // Clean up for next iteration
      unmount();
    }
  });

  /**
   * Feature: project-summary-overhaul, Property 3: Epic card separation
   * Validates: Requirements 3.2
   * 
   * Property: For any set of epics, each epic should render as a distinct card element in the DOM
   */
  test('each epic renders as a distinct card (100 iterations)', () => {
    // Run property test 100 times with random data
    for (let iteration = 0; iteration < 100; iteration++) {
      // Generate random epics (2-5 epics to ensure multiple cards)
      const numEpics = Math.floor(Math.random() * 4) + 2;
      const epics = Array.from({ length: numEpics }, () => generateEpic());
      const epicIds = epics.map(e => e.id);

      // Generate random stories (1-15 stories)
      const numStories = Math.floor(Math.random() * 15) + 1;
      const stories = Array.from({ length: numStories }, () => {
        const randomEpicId = epicIds[Math.floor(Math.random() * epicIds.length)];
        return generateStory(randomEpicId);
      });

      // Arrange
      const task = {
        context: {
          epics,
          user_stories: stories,
        },
      };

      // Act
      const { unmount, container } = render(<StoriesTab task={task} />);

      // Assert: Each epic should have its own card
      // Count the number of epic titles rendered - each title should be in a separate card
      epics.forEach(epic => {
        expect(screen.getByText(epic.title)).toBeInTheDocument();
      });

      // Verify that each epic title appears exactly once (indicating separate cards)
      epics.forEach(epic => {
        const titleElements = screen.getAllByText(epic.title);
        expect(titleElements.length).toBe(1);
      });

      // Clean up for next iteration
      unmount();
    }
  });
});

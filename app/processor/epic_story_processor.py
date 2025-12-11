"""Epic and Story driven task processing."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.models import (
    Task, TaskStatus, TaskTree,
    Epic, EpicGeneration, EpicStatus,
    UserStory, StoryGeneration, StoryStatus
)
from app.storage import TaskStorage
from app.analyzer import (
    EpicAnalyzer,
    StoryAnalyzer,
    CoverageValidator,
    CoverageReport
)


class EpicStoryProcessor:
    """Manages Epic and Story driven task decomposition."""

    def __init__(
        self,
        storage: TaskStorage,
        epic_analyzer: EpicAnalyzer,
        story_analyzer: StoryAnalyzer,
        coverage_validator: CoverageValidator
    ):
        """Initialize the Epic/Story processor.

        Args:
            storage: Task storage instance
            epic_analyzer: Epic analyzer instance
            story_analyzer: Story analyzer instance
            coverage_validator: Coverage validator instance
        """
        self.storage = storage
        self.epic_analyzer = epic_analyzer
        self.story_analyzer = story_analyzer
        self.coverage_validator = coverage_validator

        # Track epics and stories for the current processing session
        self.current_epics: List[Epic] = []
        self.current_stories: Dict[str, List[UserStory]] = {}  # epic_id -> stories
        self.task_to_stories: Dict[str, List[str]] = {}  # task_id -> story_ids

    def reset(self):
        """Reset all state for a new task generation.

        MUST be called before processing a new root task to prevent
        cross-task contamination of IDs and data.
        """
        self.current_epics = []
        self.current_stories = {}
        self.task_to_stories = {}
        # Reset the story analyzer's counter
        self.story_analyzer.reset()

    async def initialize_epics_and_stories(
        self,
        root_task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Epic], Dict[str, List[UserStory]]]:
        """Initialize epics and core stories for a root task.

        This is called once at the beginning of task processing to set up
        the epic/story structure that will guide decomposition.

        Args:
            root_task: The root task
            context: Optional context

        Returns:
            Tuple of (epics, stories_by_epic)
        """
        # Reset all state to prevent cross-task contamination
        self.reset()

        print(f"[EpicStoryProcessor] Generating epics for root task: {root_task.description[:100]}...")

        # Step 1: Generate comprehensive epics
        epic_generation = await self.epic_analyzer.generate_epics(
            root_task.description,
            root_task.id,
            context
        )
        self.current_epics = epic_generation.epics

        # Save epics to storage
        for epic in self.current_epics:
            await self.storage.save_epic(epic)

        print(f"[EpicStoryProcessor] Generated {len(self.current_epics)} epics")

        # Step 2: Generate initial stories for each epic
        for epic in self.current_epics:
            print(f"[EpicStoryProcessor] Generating stories for epic: {epic.title}")

            story_generation = await self.story_analyzer.generate_initial_stories(
                epic,
                root_task.description,
                context
            )

            self.current_stories[epic.id] = story_generation.stories

            # Save stories to storage
            for story in story_generation.stories:
                await self.storage.save_story(story)
                epic.add_story(story.id)

            # Update epic with story count
            await self.storage.save_epic(epic)

            print(f"[EpicStoryProcessor] Generated {len(story_generation.stories)} stories for {epic.title}")

        # Step 3: Update root task with epic IDs
        root_task.epic_ids = [epic.id for epic in self.current_epics]
        await self.storage.save_task(root_task)

        return self.current_epics, self.current_stories

    async def process_task_with_stories(
        self,
        task: Task,
        parent_epic: Optional[Epic] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Epic], List[UserStory], bool]:
        """Process a task in the context of epics and stories.

        This determines:
        1. Which epic the task belongs to
        2. Which stories it implements
        3. Whether new stories need to be generated (gap detection)

        Args:
            task: Task to process
            parent_epic: Parent task's epic (if any)
            context: Optional context

        Returns:
            Tuple of (assigned_epic, matched_stories, has_gap)
        """
        # Step 1: Determine epic assignment
        if parent_epic and task.complexity_score < 0.7:
            # Simple tasks inherit parent's epic
            assigned_epic = parent_epic
        else:
            # Complex tasks or root-level tasks need classification
            assigned_epic, confidence = await self.epic_analyzer.classify_to_epic(
                task.description,
                self.current_epics,
                context
            )

            # Check if this reveals an epic gap (complex task with poor fit)
            if confidence < 0.5 and task.complexity_score > 0.7:
                print(f"[EpicStoryProcessor] Epic gap detected for task: {task.description[:50]}")

                # Generate new epic for this functionality
                new_epic = await self.epic_analyzer.generate_epic_for_gap(
                    task.description,
                    task.id,
                    self.current_epics,
                    context
                )

                self.current_epics.append(new_epic)
                self.current_stories[new_epic.id] = []
                await self.storage.save_epic(new_epic)

                assigned_epic = new_epic
                print(f"[EpicStoryProcessor] Created new epic: {new_epic.title}")

        if not assigned_epic:
            # Fallback to first epic if classification fails
            assigned_epic = self.current_epics[0] if self.current_epics else None

        if not assigned_epic:
            print(f"[EpicStoryProcessor] Warning: No epic assigned to task {task.id}")
            return None, [], False

        # Update task with epic assignment
        task.epic_ids = [assigned_epic.id]

        # Step 2: Check story coverage
        epic_stories = self.current_stories.get(assigned_epic.id, [])
        has_gap, coverage_score = await self.story_analyzer.detect_story_gap(
            task.description,
            assigned_epic,
            epic_stories,
            threshold=0.6
        )

        matched_stories = []

        if has_gap:
            print(f"[EpicStoryProcessor] Story gap detected (coverage: {coverage_score:.2f})")

            # Generate story to fill the gap
            new_story = await self.story_analyzer.generate_story_for_gap(
                task.description,
                assigned_epic,
                epic_stories,
                task.depth,
                context
            )

            new_story.discovered_from_task_id = task.id
            self.current_stories[assigned_epic.id].append(new_story)
            await self.storage.save_story(new_story)

            assigned_epic.add_story(new_story.id)
            await self.storage.save_epic(assigned_epic)

            matched_stories = [new_story]
            print(f"[EpicStoryProcessor] Generated gap-filling story: {new_story.id}")
        else:
            # Match task to existing stories
            matched_stories = await self.story_analyzer.match_task_to_stories(
                task.description,
                epic_stories
            )

        # Step 3: Update task with story assignments
        if matched_stories:
            task.story_ids = [story.id for story in matched_stories]
            task.coverage_status = "covered"

            # Update stories with task assignment
            for story in matched_stories:
                story.add_task(task.id)
                await self.storage.save_story(story)
        else:
            task.coverage_status = "gap"

        await self.storage.save_task(task)

        return assigned_epic, matched_stories, has_gap

    async def should_decompose_based_on_stories(
        self,
        task: Task,
        matched_stories: List[UserStory]
    ) -> bool:
        """Determine if a task should be decomposed based on story matching.

        A task should be decomposed if:
        1. It implements multiple stories (needs to be split)
        2. It's a partial implementation of a complex story
        3. It's not atomic but has no story match (needs exploration)

        Args:
            task: Task to evaluate
            matched_stories: Stories the task implements

        Returns:
            True if task should be decomposed
        """
        # If task is already marked as atomic, don't decompose
        if task.is_atomic:
            return False

        # If task implements multiple stories, it should be decomposed
        if len(matched_stories) > 1:
            print(f"[EpicStoryProcessor] Task implements {len(matched_stories)} stories, should decompose")
            return True

        # If task has high complexity but matches a single story,
        # check if it's a complete or partial implementation
        if matched_stories and task.complexity_score > 0.6:
            # Complex task implementing one story - likely needs decomposition
            return True

        # If no story match and not atomic, explore through decomposition
        if not matched_stories and not task.is_atomic:
            return True

        return False

    async def validate_coverage(
        self,
        root_task: Task,
        task_tree: TaskTree
    ) -> CoverageReport:
        """Validate coverage of the entire task tree.

        Args:
            root_task: Root task
            task_tree: Complete task tree

        Returns:
            Coverage validation report
        """
        # Get all tasks from tree
        all_tasks = list(task_tree.tasks.values())

        # Get all stories
        all_stories = []
        for story_list in self.current_stories.values():
            all_stories.extend(story_list)

        # Generate coverage report
        report = self.coverage_validator.generate_coverage_report(
            root_task,
            self.current_epics,
            all_stories,
            all_tasks
        )

        print(f"[EpicStoryProcessor] Coverage Report:")
        print(f"  - Coverage Score: {report.coverage_score:.2%}")
        print(f"  - Gaps: {len(report.gaps)}")
        print(f"  - Overlaps: {len(report.overlaps)}")
        print(f"  - Recommendations: {len(report.recommendations)}")

        return report

    async def update_story_completion(
        self,
        task: Task
    ) -> None:
        """Update story completion when a task is completed.

        Args:
            task: Completed task
        """
        if task.status != TaskStatus.COMPLETED:
            return

        for story_id in task.story_ids:
            # Load story from storage
            story = await self.storage.get_story(story_id)
            if story:
                story.mark_task_completed()
                await self.storage.save_story(story)

                # Check if epic needs update
                epic = await self.storage.get_epic(story.epic_id)
                if epic and story.status == StoryStatus.COMPLETED:
                    epic.completed_story_count += 1
                    await self.storage.save_epic(epic)

                print(f"[EpicStoryProcessor] Updated story {story_id} completion: {story.calculate_completion_percentage():.0f}%")

    async def get_uncovered_stories(
        self,
        epic_id: Optional[str] = None
    ) -> List[UserStory]:
        """Get stories that haven't been fully covered by tasks.

        Args:
            epic_id: Optional epic ID to filter by

        Returns:
            List of uncovered stories
        """
        uncovered = []

        stories_to_check = []
        if epic_id:
            stories_to_check = self.current_stories.get(epic_id, [])
        else:
            for story_list in self.current_stories.values():
                stories_to_check.extend(story_list)

        for story in stories_to_check:
            if not story.task_ids or story.status != StoryStatus.COMPLETED:
                uncovered.append(story)

        return uncovered

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current processing session.

        Returns:
            Processing statistics
        """
        total_stories = sum(len(stories) for stories in self.current_stories.values())
        covered_stories = sum(
            len([s for s in stories if s.task_ids])
            for stories in self.current_stories.values()
        )

        return {
            "epics_count": len(self.current_epics),
            "stories_count": total_stories,
            "covered_stories": covered_stories,
            "coverage_percentage": (covered_stories / max(total_stories, 1)) * 100,
            "stories_per_epic": total_stories / max(len(self.current_epics), 1),
            "gap_filled_stories": sum(
                len([s for s in stories if s.is_gap_filler])
                for stories in self.current_stories.values()
            )
        }
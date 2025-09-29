"""User Story analyzer for generating and managing user stories within epics."""

from typing import List, Dict, Any, Optional, Tuple, Set
import uuid
from datetime import datetime, timezone

from app.models import UserStory, StoryStatus, StoryPriority, StoryGeneration, Epic
from .llm_client import LLMClient


class StoryAnalyzer:
    """Analyzes epics and tasks to generate and manage user stories."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the story analyzer.

        Args:
            llm_client: LLM client for making API calls
        """
        self.llm = llm_client
        self.story_counter = 0

    async def generate_all_stories_with_deduplication(
        self,
        epics: List[Epic],
        root_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, StoryGeneration], List[str]]:
        """Generate stories for all epics, then deduplicate across epics.

        Two-pass approach:
        1. Generate all stories for all epics
        2. Remove duplicates and empty epics

        Args:
            epics: All epics to generate stories for
            root_description: The root task description
            context: Optional context

        Returns:
            Tuple of (stories by epic_id, list of removed epic IDs)
        """
        # Pass 1: Generate all stories
        all_stories = {}
        for epic in epics:
            story_gen = await self.generate_initial_stories(epic, root_description, context)
            all_stories[epic.id] = story_gen

        # Pass 2: Deduplicate and remove empty epics
        deduped_stories, removed_epics = await self._deduplicate_across_epics(all_stories, epics)

        return deduped_stories, removed_epics

    async def generate_initial_stories(
        self,
        epic: Epic,
        root_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StoryGeneration:
        """Generate initial core stories for an epic.

        These are the known stories identified upfront from the epic scope.

        Args:
            epic: The epic to generate stories for
            root_description: The root task description for context
            context: Optional context

        Returns:
            StoryGeneration with initial stories
        """
        system_prompt = self._build_story_generation_prompt(context)
        user_prompt = f"""Generate core user stories for this epic.

Epic: "{epic.title}"
Epic Description: "{epic.description}"
System Context: "{root_description}"

Guidelines:
- Generate the essential user stories that capture the core functionality of this epic
- Each story should represent a meaningful unit of user value
- Combine related functionality into single stories when appropriate
- Focus on stories that directly implement the epic's main purpose
- Ensure each story is independently valuable and testable
- Avoid creating stories that overlap or duplicate functionality
- Do not create separate stories for implementation methods

For each story, provide:
- actor: The user role (be specific to the domain)
- action: What they want to do (clear and actionable)
- benefit: Why they want it (business value)
- acceptance_criteria: 2-4 specific criteria (testable conditions)
- priority: must_have/should_have/could_have
- story_points: Estimated points (1,2,3,5,8,13)

Return as JSON with a "stories" array."""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.4,
                max_tokens=16000  # Plenty of room for all stories
            )

            stories = []
            story_data_list = response.get("stories", [])

            for story_data in story_data_list:
                self.story_counter += 1
                story = UserStory(
                    id=f"US-{self.story_counter}",
                    epic_id=epic.id,
                    actor=story_data.get("actor", "user"),
                    action=story_data.get("action", ""),
                    benefit=story_data.get("benefit", ""),
                    acceptance_criteria=story_data.get("acceptance_criteria", []),
                    priority=StoryPriority(story_data.get("priority", "should_have")),
                    story_points=story_data.get("story_points", 5),
                    status=StoryStatus.READY,
                    discovered_at_depth=0,
                    is_gap_filler=False
                )
                stories.append(story)

            return StoryGeneration(
                stories=stories,
                generation_context="initial",
                reasoning=f"Initial story generation for epic: {epic.title}"
            )

        except Exception as e:
            print(f"Error generating initial stories: {e}")
            return StoryGeneration(
                stories=[],
                generation_context="initial",
                reasoning=f"Failed to generate stories: {str(e)}"
            )

    async def detect_story_gap(
        self,
        task_description: str,
        epic: Epic,
        existing_stories: List[UserStory],
        threshold: float = 0.6
    ) -> Tuple[bool, float]:
        """Detect if a task represents a gap in story coverage.

        Args:
            task_description: Task to check
            epic: Parent epic
            existing_stories: Existing stories in the epic
            threshold: Minimum coverage score to consider covered

        Returns:
            Tuple of (has_gap, coverage_score)
        """
        if not existing_stories:
            return True, 0.0

        # Check coverage using LLM
        story_summaries = [
            f"- {story.get_full_story_text()}"
            for story in existing_stories
        ]

        system_prompt = """You are checking if a task is covered by existing user stories.
A task is covered if it implements part of an existing story."""

        user_prompt = f"""Does this task implement any of these user stories?

Task: "{task_description}"

Existing stories in {epic.title}:
{chr(10).join(story_summaries)}

Return JSON with:
- is_covered: true/false
- coverage_score: 0.0-1.0 (how well the stories cover this task)
- matching_stories: List of story IDs that this task implements
- reasoning: Brief explanation"""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.2,
                max_tokens=1000
            )

            coverage_score = response.get("coverage_score", 0.0)
            is_covered = response.get("is_covered", False)

            # A gap exists if coverage is below threshold
            has_gap = coverage_score < threshold

            return has_gap, coverage_score

        except Exception as e:
            print(f"Error detecting story gap: {e}")
            # Conservative: assume gap if error
            return True, 0.0

    async def generate_story_for_gap(
        self,
        task_description: str,
        epic: Epic,
        existing_stories: List[UserStory],
        depth: int,
        context: Optional[Dict[str, Any]] = None
    ) -> UserStory:
        """Generate a new story to fill a coverage gap.

        Args:
            task_description: Task that revealed the gap
            epic: Parent epic
            existing_stories: Existing stories in the epic
            depth: Depth where gap was discovered
            context: Optional context

        Returns:
            New user story to fill the gap
        """
        existing_summaries = [
            story.get_full_story_text()
            for story in existing_stories
        ]

        system_prompt = """You are creating a user story for functionality not covered by existing stories.
The story should be specific to the gap found, not duplicate existing stories."""

        user_prompt = f"""A task was found that isn't covered by existing stories.
Create a user story for this functionality.

Task revealing gap: "{task_description}"
Epic: "{epic.title}"

Existing stories (DO NOT DUPLICATE):
{chr(10).join(existing_summaries) if existing_summaries else "None"}

Provide:
- actor: Specific user role
- action: What they want to do (related to the task)
- benefit: Why they want it
- acceptance_criteria: 2-4 specific criteria
- priority: must_have/should_have/could_have
- story_points: 1-13

Return as JSON."""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.4,
                max_tokens=1000
            )

            self.story_counter += 1
            return UserStory(
                id=f"US-{self.story_counter}",
                epic_id=epic.id,
                actor=response.get("actor", "user"),
                action=response.get("action", task_description),
                benefit=response.get("benefit", "improved functionality"),
                acceptance_criteria=response.get("acceptance_criteria", []),
                priority=StoryPriority(response.get("priority", "should_have")),
                story_points=response.get("story_points", 5),
                status=StoryStatus.READY,
                discovered_at_depth=depth,
                is_gap_filler=True,
                discovered_from_task_id=None  # Will be set by caller
            )

        except Exception as e:
            print(f"Error generating gap story: {e}")
            # Fallback story
            self.story_counter += 1
            return UserStory(
                id=f"US-{self.story_counter}",
                epic_id=epic.id,
                actor="user",
                action=task_description,
                benefit="complete the functionality",
                acceptance_criteria=[f"Task '{task_description}' is implemented"],
                priority=StoryPriority.SHOULD_HAVE,
                story_points=5,
                discovered_at_depth=depth,
                is_gap_filler=True
            )

    async def match_task_to_stories(
        self,
        task_description: str,
        stories: List[UserStory]
    ) -> List[UserStory]:
        """Match a task to the stories it implements.

        A task may implement multiple stories or parts of stories.

        Args:
            task_description: Task to match
            stories: Available stories

        Returns:
            List of matching stories
        """
        if not stories:
            return []

        story_summaries = [
            f"{story.id}: {story.get_full_story_text()}"
            for story in stories
        ]

        system_prompt = """You are matching a task to user stories it implements.
A task can implement one or more stories, or parts of stories."""

        user_prompt = f"""Which user stories does this task implement?

Task: "{task_description}"

Available stories:
{chr(10).join(story_summaries)}

Return JSON with:
- matching_story_ids: List of story IDs this task implements
- confidence: 0.0-1.0 confidence in the matches
- reasoning: Brief explanation"""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.2,
                max_tokens=1000
            )

            matching_ids = response.get("matching_story_ids", [])
            matched_stories = [
                story for story in stories
                if story.id in matching_ids
            ]

            return matched_stories

        except Exception as e:
            print(f"Error matching task to stories: {e}")
            return []

    async def validate_story_coverage(
        self,
        epic: Epic,
        stories: List[UserStory],
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate that stories adequately cover an epic and its tasks.

        Args:
            epic: The epic to validate
            stories: Stories in the epic
            tasks: Tasks that should be covered

        Returns:
            Validation report with coverage metrics
        """
        uncovered_tasks = []
        story_usage = {story.id: [] for story in stories}

        for task in tasks:
            matched_stories = await self.match_task_to_stories(
                task.get("description", ""),
                stories
            )

            if not matched_stories:
                uncovered_tasks.append(task)
            else:
                for story in matched_stories:
                    story_usage[story.id].append(task.get("id"))

        # Find unused stories
        unused_stories = [
            story_id for story_id, task_ids in story_usage.items()
            if not task_ids
        ]

        coverage_score = 1.0 - (len(uncovered_tasks) / max(len(tasks), 1))

        return {
            "epic_id": epic.id,
            "coverage_score": coverage_score,
            "total_stories": len(stories),
            "total_tasks": len(tasks),
            "uncovered_tasks": uncovered_tasks,
            "unused_stories": unused_stories,
            "story_usage": story_usage,
            "is_complete": len(uncovered_tasks) == 0 and len(unused_stories) == 0
        }

    def _build_story_generation_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for story generation.

        Args:
            context: Optional context dictionary

        Returns:
            System prompt string
        """
        base_prompt = """You are a product owner creating user stories for software development.

User stories follow the format:
"As a [actor], I want to [action], so that [benefit]"

Good user stories are:
- Independent: Can be developed separately
- Negotiable: Details can be discussed
- Valuable: Provides clear business value
- Estimable: Can be sized
- Small: Can be completed in a sprint
- Testable: Has clear acceptance criteria

Focus on user-facing functionality and business value.

CRITICAL: User stories describe WHAT the user wants, not HOW it's implemented:
- Focus on the outcome, not the method
- Avoid mentioning specific technologies or implementation details
- Input methods, storage systems, and technical architecture are task-level details"""

        if context:
            domain = context.get("domain", "")
            user_types = context.get("user_types", [])

            if domain:
                base_prompt += f"\n\nDomain: {domain}"
            if user_types:
                base_prompt += f"\n\nUser Types: {', '.join(user_types)}"

        return base_prompt

    async def _deduplicate_across_epics(
        self,
        all_stories: Dict[str, StoryGeneration],
        epics: List[Epic]
    ) -> Tuple[Dict[str, StoryGeneration], List[str]]:
        """Deduplicate stories across all epics and remove empty epics.

        Args:
            all_stories: Dictionary of epic_id -> StoryGeneration
            epics: List of all epics

        Returns:
            Tuple of (deduplicated stories, list of removed epic IDs)
        """
        # Build a flat list of all stories with their epic IDs
        story_map = {}  # story_id -> (epic_id, story)
        for epic_id, story_gen in all_stories.items():
            for story in story_gen.stories:
                story_map[story.id] = (epic_id, story)

        # Find duplicate groups
        duplicate_groups = self._find_duplicate_groups(
            [story for _, story in story_map.values()]
        )

        # Track which stories to keep
        stories_to_remove = set()

        for dup_group in duplicate_groups:
            # Keep the best story from each duplicate group
            best_story_id = self._select_best_story(
                dup_group,
                {sid: story for sid, (_, story) in story_map.items()}
            )

            # Mark others for removal
            for story_id in dup_group:
                if story_id != best_story_id:
                    stories_to_remove.add(story_id)

        # Rebuild story lists without duplicates
        deduped_stories = {}
        removed_epics = []

        for epic in epics:
            epic_stories = []

            if epic.id in all_stories:
                for story in all_stories[epic.id].stories:
                    if story.id not in stories_to_remove:
                        epic_stories.append(story)

            # If epic has no stories after deduplication, mark for removal
            if not epic_stories:
                removed_epics.append(epic.id)
            else:
                deduped_stories[epic.id] = StoryGeneration(
                    stories=epic_stories,
                    generation_context="deduplicated",
                    reasoning=f"Deduplicated from {len(all_stories[epic.id].stories)} to {len(epic_stories)} stories"
                )

        return deduped_stories, removed_epics

    def _find_duplicate_groups(self, stories: List[UserStory]) -> List[Set[str]]:
        """Find groups of duplicate stories.

        Args:
            stories: List of all stories to check

        Returns:
            List of sets containing story IDs that are duplicates
        """
        duplicate_groups = []
        processed = set()

        for i, story1 in enumerate(stories):
            if story1.id in processed:
                continue

            # Find all stories that are duplicates of story1
            dup_group = {story1.id}

            for story2 in stories[i+1:]:
                if story2.id not in processed:
                    if self._are_stories_duplicate(story1, story2):
                        dup_group.add(story2.id)

            # Only add groups with actual duplicates
            if len(dup_group) > 1:
                duplicate_groups.append(dup_group)
                processed.update(dup_group)

        return duplicate_groups

    def _are_stories_duplicate(self, story1: UserStory, story2: UserStory) -> bool:
        """Check if two stories are duplicates.

        Stories are considered duplicates if they have:
        - Same actor AND
        - Similar semantic meaning (checking key concepts)

        Args:
            story1: First story
            story2: Second story

        Returns:
            True if stories are duplicates
        """
        # Must have same actor
        if story1.actor.lower() != story2.actor.lower():
            return False

        # Define semantic equivalents for common actions
        concept_groups = [
            {'move', 'control', 'steer', 'navigate', 'position'},
            {'view', 'see', 'display', 'show', 'visible', 'watch'},
            {'score', 'points', 'progress'},
            {'piece', 'pieces', 'block', 'blocks', 'tetromino'},
            {'start', 'begin', 'new', 'init', 'initialize'},
            {'left', 'right', 'arrow', 'keys', 'keyboard', 'input'},
        ]

        # Extract key concepts from actions
        action1_lower = story1.action.lower()
        action2_lower = story2.action.lower()

        # Check if actions refer to same concept
        for concept_group in concept_groups:
            has_concept1 = any(concept in action1_lower for concept in concept_group)
            has_concept2 = any(concept in action2_lower for concept in concept_group)

            if has_concept1 and has_concept2:
                # Both actions refer to same concept group
                # Check if they're talking about similar functionality

                # Special cases for common duplicates
                if 'score' in concept_group:
                    if ('view' in action1_lower or 'see' in action1_lower or 'display' in action1_lower) and \
                       ('view' in action2_lower or 'see' in action2_lower or 'display' in action2_lower):
                        return True

                if 'move' in concept_group or 'control' in concept_group:
                    # Check if both are about piece movement
                    piece_words = {'piece', 'pieces', 'block', 'blocks', 'tetromino'}
                    if any(w in action1_lower for w in piece_words) and \
                       any(w in action2_lower for w in piece_words):
                        return True

        # More general similarity check
        # Normalize and tokenize
        stop_words = {'to', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'for',
                     'with', 'my', 'using', 'have', 'be', 'as', 'so', 'that', 'can'}

        action1_words = set(action1_lower.split()) - stop_words
        action2_words = set(action2_lower.split()) - stop_words

        # Check if core functionality overlaps
        key_overlap = action1_words & action2_words
        if len(key_overlap) >= 2:  # At least 2 key words in common
            return True

        # Check acceptance criteria for functional overlap
        ac1_text = " ".join(story1.acceptance_criteria).lower()
        ac2_text = " ".join(story2.acceptance_criteria).lower()

        if ac1_text and ac2_text:
            # Look for same functional requirements
            ac1_words = set(ac1_text.split()) - stop_words
            ac2_words = set(ac2_text.split()) - stop_words

            ac_overlap = ac1_words & ac2_words
            # High overlap in acceptance criteria suggests same functionality
            if len(ac_overlap) >= 3:
                return True

        return False

    def _select_best_story(
        self,
        duplicate_group: Set[str],
        stories_map: Dict[str, UserStory]
    ) -> str:
        """Select the best story from a group of duplicates.

        Selection criteria (in order):
        1. More detailed acceptance criteria
        2. Higher priority (must_have > should_have > could_have)
        3. More complete description (longer action + benefit)

        Args:
            duplicate_group: Set of duplicate story IDs
            stories_map: Map of story_id -> UserStory

        Returns:
            ID of the best story to keep
        """
        stories = [stories_map[sid] for sid in duplicate_group if sid in stories_map]

        if not stories:
            return next(iter(duplicate_group))

        def score_story(s: UserStory) -> int:
            score = 0

            # Acceptance criteria count (more is better)
            score += len(s.acceptance_criteria) * 100

            # Priority score
            priority_scores = {
                StoryPriority.MUST_HAVE: 50,
                StoryPriority.SHOULD_HAVE: 30,
                StoryPriority.COULD_HAVE: 10
            }
            score += priority_scores.get(s.priority, 0)

            # Description completeness
            score += len(s.action.split()) + len(s.benefit.split())

            return score

        best_story = max(stories, key=score_story)
        return best_story.id
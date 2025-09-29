"""Story-driven task analyzer where all tasks stem from user stories."""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timezone

from app.models import (
    Task, TaskStatus, TaskAnalysis, TaskDecomposition,
    UserStory, StoryStatus, Epic
)
from .llm_client import LLMClient


class StoryDrivenAnalyzer:
    """Analyzer that ensures all tasks are driven by user stories."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the story-driven analyzer.

        Args:
            llm_client: LLM client for making API calls
        """
        self.llm = llm_client

    async def decompose_stories_to_tasks(
        self,
        stories: List[UserStory],
        epic: Epic,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, TaskDecomposition]:
        """Decompose multiple user stories into implementation tasks in a single call.

        This batches all stories from an epic to reduce API calls and maintain context.

        Args:
            stories: List of user stories to decompose
            epic: Parent epic for context
            context: Optional context (tech stack, etc.)

        Returns:
            Dictionary mapping story IDs to their TaskDecompositions
        """
        system_prompt = self._build_story_decomposition_prompt(context)

        # Build stories list for the prompt
        stories_text = []
        for i, story in enumerate(stories, 1):
            story_text = f"""Story {i} (ID: {story.id}):
"As a {story.actor}, I want to {story.action} so that {story.benefit}"
Acceptance Criteria:
{chr(10).join(f"- {criterion}" for criterion in story.acceptance_criteria)}
Story Points: {story.story_points}"""
            stories_text.append(story_text)

        # Customize user prompt based on repository context
        if context and context.get("repository_architecture"):
            additional_instructions = """

CRITICAL: You are working with an EXISTING CODEBASE.
- Reference the actual directory structure when creating new files
- Consolidate related functionality into single tasks
- Avoid creating too many separate files

Example task descriptions:
- "Create app/integrations/[service].py with complete integration logic"
- "Add all necessary API endpoints to existing routes file or create new one if needed"
- "Implement frontend components in appropriate directory"
"""
        else:
            additional_instructions = ""

        user_prompt = f"""Decompose ALL these user stories from the epic into implementation tasks.

Epic: "{epic.title}"

{chr(10).join(stories_text)}

For EACH story, generate implementation tasks that satisfy its acceptance criteria.{additional_instructions}

Return as JSON with structure:
{{
  "story_tasks": {{
    "[story_id]": {{
      "tasks": [
        {{
          "description": "Specific implementation task with file paths",
          "is_atomic": true/false,
          "implementation_details": "Technical approach referencing specific files",
          "story_points": 1-8,
          "dependencies": []
        }}
      ]
    }}
  }}
}}

CRITICAL DECOMPOSITION RULES:
- Group related acceptance criteria into single tasks when they're part of the same implementation
- Do NOT create a separate task for each acceptance criterion
- Quality attributes (performance, responsiveness) are part of implementation, not separate tasks

Important:
- Process ALL stories in one response
- ALL tasks should be ATOMIC
- Mark ALL tasks as is_atomic: true
- Use implementation verbs: Create, Implement, Add, Build, Connect
- Maintain consistency across related stories"""

        response = await self.llm.generate_json(
            system_prompt,
            user_prompt,
            temperature=0.3,
            max_tokens=20000  # Batch processing all stories needs more tokens
        )

        result = {}
        story_tasks = response.get("story_tasks", {})

        for story in stories:
            tasks_data = story_tasks.get(story.id, {}).get("tasks", [])

            if not tasks_data:
                raise ValueError(f"No tasks generated for story {story.id}")

            # Add story and epic IDs to each task
            for task_data in tasks_data:
                task_data["story_id"] = story.id
                task_data["epic_id"] = epic.id

            result[story.id] = TaskDecomposition(
                subtasks=tasks_data,
                decomposition_reasoning=f"Batch processed with {len(stories)} stories",
                story_id=story.id,
                epic_id=epic.id
            )

        return result

    async def analyze_story_task(
        self,
        task_description: str,
        story: UserStory,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskAnalysis:
        """Analyze a task in the context of its user story.

        Args:
            task_description: Task to analyze
            story: Parent user story
            context: Optional context

        Returns:
            Task analysis with story context
        """
        system_prompt = """You are a senior engineer evaluating implementation tasks.

A task is ATOMIC when it:
- Implements ONE specific aspect of the story
- Can be completed in 2-4 hours
- Has clear success criteria from the story's acceptance criteria
- Would be a single pull request

A task NEEDS DECOMPOSITION when it:
- Covers multiple acceptance criteria
- Would take more than 4 hours
- Involves multiple components or layers"""

        user_prompt = f"""Analyze this implementation task:

Task: "{task_description}"
Parent Story: "As a {story.actor}, I want to {story.action}"
Story Points: {story.story_points}

Is this task atomic and ready for implementation?"""

        response = await self.llm.generate_json(
            system_prompt,
            user_prompt,
            temperature=0.1,
            max_tokens=1000
        )

        return TaskAnalysis(
            complexity_score=float(response.get("complexity_score", 0.5)),
            is_atomic=bool(response.get("is_atomic", False)),
            is_specific=True,  # Tasks from stories are always specific
            confidence=float(response.get("confidence", 0.8)),
            reasoning=response.get("reasoning", ""),
            implementation_hints=response.get("implementation_hints"),
            estimated_story_points=response.get("story_points", 3),
            story_id=story.id,
            epic_id=story.epic_id
        )

    def _build_story_decomposition_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for story-to-task decomposition.

        Args:
            context: Optional context dictionary

        Returns:
            System prompt string
        """
        # Check if we have repository context
        has_repo_context = context and context.get("repository_architecture")

        if has_repo_context:
            # When we have repository context, be very specific about using it
            base_prompt = """You are a senior software engineer working with an EXISTING CODEBASE.
You must break down user stories into implementation tasks that integrate with the current architecture.

## CRITICAL REQUIREMENT:
ALL tasks MUST reference specific files and follow patterns from the existing codebase provided below.

## EXISTING CODEBASE STRUCTURE:
"""
            base_prompt += context["repository_architecture"]

            # Add specific instructions based on repository analysis
            if context.get("repository_analysis"):
                analysis = context["repository_analysis"]

                base_prompt += "\n\n## DETECTED PATTERNS TO FOLLOW:\n"

                # List existing API endpoints
                if analysis.get("patterns", {}).get("api_endpoints"):
                    endpoints = analysis["patterns"]["api_endpoints"][:5]
                    base_prompt += f"- API Routes: {', '.join(endpoints)}\n"
                    base_prompt += "  → New API endpoints MUST follow the same file structure\n"

                # List existing services
                if analysis.get("patterns", {}).get("services"):
                    services = analysis["patterns"]["services"][:3]
                    base_prompt += f"- Services: {', '.join(services)}\n"
                    base_prompt += "  → New services MUST be added in the same directory structure\n"

                # Note existing integrations
                if "integrations" in str(analysis.get("structure", {}).get("directories", [])):
                    base_prompt += "- Existing integrations found in app/integrations/\n"
                    base_prompt += "  → New integrations MUST be added as app/integrations/[service].py\n"

            base_prompt += """

## TASK CREATION RULES:
1. Each task should represent a substantial unit of functionality
2. Consolidate related changes into single tasks
3. Reference codebase structure appropriately
4. Let the actual complexity of the feature determine task count

## EXAMPLES:
- "Implement [service] module in app/[appropriate_dir]/[service].py"
- "Add API endpoints and business logic for [feature]"
- "Create frontend components for [feature]"

## IMPORTANT:
Balance between avoiding micro-tasks and providing adequate detail.
"""
        else:
            # Original prompt for when no repository context is available
            base_prompt = """You are a senior software engineer breaking down user stories into implementation tasks.

## DECOMPOSITION RULES:

1. Every task must directly contribute to fulfilling the user story
2. Group related acceptance criteria into single tasks
3. Use implementation-focused language (Create, Implement, Add, Build, Connect)
4. Include technical details specific to the story requirements
5. Recognize that multiple acceptance criteria often represent ONE implementation

## PATTERN RECOGNITION:

For "authentication" stories → Break into:
- User model/schema with required fields
- Authentication endpoint implementation
- Session/token management
- Password hashing and validation
- Error handling and security measures

For "CRUD" stories → Break into:
- Data model and validation
- Create endpoint with input validation
- Read endpoints with filtering/pagination
- Update with partial updates support
- Delete with cascading/soft delete
- Permissions and access control

For "UI" stories → Break into:
- Component structure and state
- Form validation and error display
- API integration and data fetching
- Loading and error states
- Responsive design implementation"""

        base_prompt += """

## IMPORTANT:
Tasks must be traceable back to the story's acceptance criteria.
Never create tasks for planning, documentation, or deployment.
Focus on implementation tasks that deliver the story's value."""

        if context:
            tech_stack = context.get("tech_stack", "")
            if tech_stack and isinstance(tech_stack, dict):
                languages = tech_stack.get("preferred_languages", [])
                frameworks = tech_stack.get("frameworks", {})
                if languages or frameworks:
                    base_prompt += f"\n\nTech Stack Configuration: Languages: {languages}, Frameworks: {frameworks}"
            elif tech_stack:
                base_prompt += f"\n\nTech Stack: {tech_stack}"

        return base_prompt
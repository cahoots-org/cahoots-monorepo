"""Story-driven task analyzer where all tasks stem from user stories."""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timezone

from app.models import (
    Task, TaskStatus, TaskAnalysis, TaskDecomposition,
    UserStory, StoryStatus, Epic
)
from .llm_client import LLMClient
from app.config import PromptTuningConfig


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
        context: Optional[Dict[str, Any]] = None,
        config: Optional[PromptTuningConfig] = None
    ) -> Dict[str, TaskDecomposition]:
        """Decompose multiple user stories into implementation tasks in a single call.

        This batches all stories from an epic to reduce API calls and maintain context.

        Args:
            stories: List of user stories to decompose
            epic: Parent epic for context
            context: Optional context (tech stack, etc.)
            config: Optional prompt tuning configuration

        Returns:
            Dictionary mapping story IDs to their TaskDecompositions
        """
        # Load config or use default
        if config is None:
            # Determine complexity from context and load appropriate config
            complexity = context.get("complexity", "medium") if context else "medium"
            config = PromptTuningConfig.for_complexity(complexity)

        system_prompt = self._build_story_decomposition_prompt(context)

        # Inject prompt tuning guidance
        complexity = context.get("complexity", "medium") if context else "medium"
        prompt_guidance = config.to_prompt_guidance(complexity=complexity)
        system_prompt += "\n\n" + prompt_guidance

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

        # DEBUG: Log prompts to understand what's being sent
        print(f"[StoryAnalyzer] DEBUG: System prompt length: {len(system_prompt)} chars")
        print(f"[StoryAnalyzer] DEBUG: User prompt length: {len(user_prompt)} chars")
        print(f"[StoryAnalyzer] DEBUG: System prompt preview: {system_prompt[:500]}")
        print(f"[StoryAnalyzer] DEBUG: User prompt preview: {user_prompt[:500]}")

        # Save full prompts to /tmp for debugging if needed
        import os
        debug_dir = "/tmp/cahoots_prompts"
        os.makedirs(debug_dir, exist_ok=True)
        debug_file = f"{debug_dir}/story_decomp_{epic.id[:8]}.txt"
        with open(debug_file, "w") as f:
            f.write("=== SYSTEM PROMPT ===\n")
            f.write(system_prompt)
            f.write("\n\n=== USER PROMPT ===\n")
            f.write(user_prompt)
        print(f"[StoryAnalyzer] Full prompts saved to: {debug_file}")

        response = await self.llm.generate_json(
            system_prompt,
            user_prompt,
<<<<<<< Updated upstream
            temperature=config.task_decomposition_temperature,
            max_tokens=config.max_tokens_task_decomposition
=======
            temperature=0.3,
            max_tokens=32000  # Cerebras max output: 32k (free) / 40k (paid)
>>>>>>> Stashed changes
        )

        result = {}
        story_tasks = response.get("story_tasks", {})

        # Debug logging for missing stories
        if not story_tasks:
            print(f"[StoryAnalyzer] ERROR: Empty story_tasks in LLM response")
            print(f"[StoryAnalyzer] Full response: {str(response)[:2000]}")
            print(f"[StoryAnalyzer] Expected stories: {[s.id for s in stories]}")
            raise ValueError("LLM returned empty story_tasks - this is a model/prompt issue")

        for story in stories:
            story_data = story_tasks.get(story.id, {})

            # Handle both formats: {"tasks": [...]} or directly [...]
            if isinstance(story_data, list):
                tasks_data = story_data
            elif isinstance(story_data, dict):
                tasks_data = story_data.get("tasks", [])
            else:
                tasks_data = []

            if not tasks_data:
                print(f"[StoryAnalyzer] ERROR: No tasks for story {story.id}")
                print(f"[StoryAnalyzer] Available story IDs: {list(story_tasks.keys())}")
                print(f"[StoryAnalyzer] Story {story.id} data: {story_tasks.get(story.id, 'MISSING')}")
                print(f"[StoryAnalyzer] Story data type: {type(story_data)}")
                raise ValueError(f"No tasks generated for story {story.id}")

            # Add story and epic IDs to each task, converting strings to dicts if needed
            normalized_tasks = []
            for i, task_data in enumerate(tasks_data):
                # Handle case where LLM returned string instead of dict
                if isinstance(task_data, str):
                    task_dict = {"description": task_data, "is_atomic": True}
                elif isinstance(task_data, dict):
                    task_dict = task_data
                else:
                    # Skip invalid entries
                    continue

                task_dict["story_id"] = story.id
                task_dict["epic_id"] = epic.id
                normalized_tasks.append(task_dict)

            result[story.id] = TaskDecomposition(
                subtasks=normalized_tasks,
                decomposition_reasoning=f"Batch processed with {len(stories)} stories",
                story_id=story.id,
                epic_id=epic.id
            )

        # Filter out redundant tasks if we have feature overlap data from GitHub context
        if context and context.get("existing_features"):
            print("[StoryDrivenAnalyzer] Filtering redundant tasks based on existing features...")
            result = await self._filter_redundant_tasks(result, context["existing_features"])

        return result

    async def _filter_redundant_tasks(
        self,
        story_decompositions: Dict[str, TaskDecomposition],
        existing_features: Dict[str, Any]
    ) -> Dict[str, TaskDecomposition]:
        """
        Filter out tasks that implement features that already exist.

        Args:
            story_decompositions: Dictionary mapping story IDs to TaskDecompositions
            existing_features: Feature overlap analysis from FeatureOverlapDetector

        Returns:
            Filtered dictionary of TaskDecompositions with redundant tasks removed
        """
        from app.services.feature_overlap_detector import FeatureOverlapDetector

        detector = FeatureOverlapDetector(self.llm)

        # Collect all tasks across all stories
        all_tasks = []
        story_task_mapping = {}  # Map task index to (story_id, task_index_in_story)

        task_idx = 0
        for story_id, decomposition in story_decompositions.items():
            for local_idx, task in enumerate(decomposition.subtasks):
                all_tasks.append(task)
                story_task_mapping[task_idx] = (story_id, local_idx)
                task_idx += 1

        # Filter tasks
        filter_result = await detector.filter_redundant_tasks(all_tasks, existing_features)

        # Rebuild story decompositions without redundant tasks
        filtered_decompositions = {}
        removed_count = 0

        for story_id, decomposition in story_decompositions.items():
            # Collect non-redundant tasks for this story
            kept_tasks = []
            for local_idx, task in enumerate(decomposition.subtasks):
                task_desc = task.get("description", "")
                # Check if this task was removed
                is_removed = any(
                    removed_task.get("description", "") == task_desc
                    for removed_task in filter_result["removed_tasks"]
                )

                if not is_removed:
                    kept_tasks.append(task)
                else:
                    removed_count += 1
                    print(f"  ✗ Removed from story {story_id}: {task_desc[:80]}")

            # Only create decomposition if there are tasks left
            if kept_tasks:
                reasoning = decomposition.decomposition_reasoning
                if removed_count > 0:
                    reasoning += f" ({removed_count} redundant tasks filtered)"

                filtered_decompositions[story_id] = TaskDecomposition(
                    subtasks=kept_tasks,
                    decomposition_reasoning=reasoning,
                    story_id=decomposition.story_id,
                    epic_id=decomposition.epic_id
                )

        print(f"[StoryDrivenAnalyzer] ✅ Filtered {removed_count} redundant tasks total")
        return filtered_decompositions

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
        # Check model size to decide whether to include verbose event model context
        # Smaller models (14B) get overwhelmed by event model details
        import os
        model_name = os.getenv("LOCAL_LLM_MODEL", "")
        is_small_model = any(size in model_name.lower() for size in ["14b", "7b", "13b"])

        # Check if we have event model context
        has_event_model = context and context.get("event_model") and not is_small_model

        # Check if we have repository context
        has_repo_context = context and context.get("repository_architecture")

        # Start with event model context if available
        base_prompt = ""
        if has_event_model:
            event_model = context["event_model"]
            commands = event_model.get("commands", [])
            events = event_model.get("events", [])
            read_models = event_model.get("read_models", [])

            base_prompt = """You are a senior software engineer working with an EVENT-DRIVEN ARCHITECTURE.
The Event Model below defines the domain language and behavior of the system.

## EVENT MODEL (DOMAIN BLUEPRINT):

"""
            # Add commands summary
            if commands:
                base_prompt += f"### Commands ({len(commands)} total):\n"
                for cmd in commands[:10]:  # Show first 10
                    base_prompt += f"- **{cmd['name']}**: {cmd['description']}\n"
                    if cmd.get('triggers_events'):
                        base_prompt += f"  → Triggers: {', '.join(cmd['triggers_events'])}\n"
                if len(commands) > 10:
                    base_prompt += f"... and {len(commands) - 10} more\n"
                base_prompt += "\n"

            # Add events summary
            if events:
                base_prompt += f"### Events ({len(events)} total):\n"
                event_names = []
                for evt in events[:10]:  # Show first 10
                    if hasattr(evt, 'name'):
                        event_names.append(evt.name)
                        base_prompt += f"- **{evt.name}**: {evt.description}\n"
                    else:
                        event_names.append(evt.get('name', 'Unknown'))
                        base_prompt += f"- **{evt.get('name', 'Unknown')}**: {evt.get('description', '')}\n"
                if len(events) > 10:
                    base_prompt += f"... and {len(events) - 10} more\n"
                base_prompt += "\n"

            # Add read models summary
            if read_models:
                base_prompt += f"### Read Models ({len(read_models)} total):\n"
                for rm in read_models[:10]:  # Show first 10
                    base_prompt += f"- **{rm['name']}**: {rm['description']}\n"
                if len(read_models) > 10:
                    base_prompt += f"... and {len(read_models) - 10} more\n"
                base_prompt += "\n"

            base_prompt += """
## CRITICAL: Ensure Complete Feature Coverage

The event model above defines ALL user actions and system behaviors.
Generate implementation tasks that cover every command and read model.

**Task Description Guidelines:**
1. Use clear, implementation-focused language (NOT event modeling jargon)
2. Describe WHAT to build in developer-friendly terms
3. Include technical details: API endpoints, UI components, database operations
4. Every command and read model must have corresponding implementation tasks

**Task Examples:**
- "Add like/unlike functionality for posts with real-time counter updates"
- "Implement friend request acceptance with automatic friend list updates"
- "Create user profile page with edit and settings capabilities"
- "Build post sharing feature with privacy controls"
- "Add notifications for friend requests and post interactions"

**Coverage Check:**
- LikePost command → Need task for like/unlike posts
- AcceptFriendRequest command → Need task for accepting friend requests
- NotificationsList read model → Need task for notification display
- Every command/read model must map to at least one implementation task

"""

        if has_repo_context:
            # When we have repository context, append it to the existing prompt
            if not base_prompt:
                base_prompt = """You are a senior software engineer working with an EXISTING CODEBASE.
You must break down user stories into implementation tasks that integrate with the current architecture.

"""
            else:
                base_prompt += """
## EXISTING CODEBASE INTEGRATION

"""
            base_prompt += """## CRITICAL REQUIREMENT:
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
        elif not has_event_model:
            # Only use this fallback if we have NEITHER event model NOR repo context
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

        # Inject tech stack information - this is CRITICAL for correct implementation details
        if context and context.get("tech_stack"):
            tech_stack = context["tech_stack"]
            frontend = tech_stack.get("frontend", "")
            backend = tech_stack.get("backend", "")
            services = tech_stack.get("services", {})

            # Infer languages from frameworks
            backend_lang = ""
            if backend == "FastAPI":
                backend_lang = "Python"
            elif backend == "Express":
                backend_lang = "TypeScript"

            frontend_lang = "TypeScript/JavaScript" if frontend else ""

            base_prompt += """

## MANDATORY TECH STACK (YOU MUST USE THESE EXACT TECHNOLOGIES):
"""
            if backend:
                base_prompt += f"\n**Backend Framework:** {backend} ({backend_lang})"
            if frontend:
                base_prompt += f"\n**Frontend Framework:** {frontend} ({frontend_lang})"
            if services:
                base_prompt += f"\n**Required Services:** {', '.join(f'{k}: {v}' for k, v in services.items())}"

            base_prompt += "\n\n**CRITICAL IMPLEMENTATION RULES:**\n"

            # FastAPI (Python) specific
            if backend == "FastAPI":
                base_prompt += """- Use Python for ALL backend code
- Use FastAPI for API endpoints (NOT Express, NOT Node.js)
- Use Pydantic models for validation
- File paths: `app/routes/*.py`, `app/models/*.py`, `app/services/*.py`
- Database: Use SQLAlchemy or similar Python ORM
- Authentication: Use Python libraries (NOT Passport.js, NOT JWT.js)
"""

            # Express (TypeScript) specific
            elif backend == "Express":
                base_prompt += """- Use TypeScript for ALL backend code
- Use Express.js for API endpoints (NOT FastAPI, NOT Flask)
- File paths: `src/routes/*.ts`, `src/models/*.ts`, `src/services/*.ts`
- Use TypeScript interfaces for types
- Authentication: Use Node.js libraries (Passport, jsonwebtoken, etc.)
"""

            # React frontend
            if frontend == "React":
                base_prompt += """- Use React for frontend (NOT Vue, NOT Angular)
- File paths: `frontend/src/components/*.jsx` or `*.tsx`
- Use React hooks (useState, useEffect, etc.)
"""

            # Next.js frontend
            elif frontend == "Next.js":
                base_prompt += """- Use Next.js for frontend (NOT plain React)
- File paths: `pages/*.tsx` or `app/*.tsx` (depending on Next.js version)
- Use Next.js features (getServerSideProps, API routes, etc.)
"""

            base_prompt += "\n**YOU MUST NOT use technologies outside this tech stack!**\n"

        return base_prompt
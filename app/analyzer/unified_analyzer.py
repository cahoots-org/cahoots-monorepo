"""Unified task analyzer that combines multiple analyses into single LLM calls."""

from typing import Dict, Any, List, Optional
import json

from app.models import TaskAnalysis, TaskDecomposition, ApproachType
from .llm_client import LLMClient


class UnifiedAnalyzer:
    """Unified analyzer that reduces LLM calls by combining multiple analyses."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the analyzer.

        Args:
            llm_client: LLM client for making API calls
        """
        self.llm = llm_client

    async def analyze_task(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0
    ) -> TaskAnalysis:
        """Analyze a task in a single LLM call.

        This replaces multiple separate calls for:
        - Complexity scoring
        - Atomicity checking
        - Specificity checking
        - Implementation hints

        Args:
            description: Task description to analyze
            context: Optional context (tech stack, best practices, etc.)
            depth: Current depth in task tree

        Returns:
            Comprehensive task analysis
        """
        system_prompt = self._build_analysis_prompt(context)
        user_prompt = f"""Analyze this task and provide a comprehensive assessment:

Task: "{description}"
Current depth in decomposition: {depth}

Provide your analysis as a JSON object with these fields:
- complexity_score: float (0.0-1.0) - How complex is this task?
- is_atomic: boolean - Can this be done in a single focused work session (2-4 hours)?
- is_specific: boolean - Is the task specific enough to implement?
- confidence: float (0.0-1.0) - How confident are you in this analysis?
- reasoning: string - Brief explanation of your analysis
- suggested_approach: string - One of: "decompose", "implement", "template"
- implementation_hints: string or null - If atomic, brief implementation guidance
- estimated_story_points: integer or null - Fibonacci scale (1,2,3,5,8,13,21)
- similar_patterns: array of strings - Common patterns this resembles (e.g., "CRUD", "auth")
- missing_details: array of strings - What information is missing?
- dependencies: array of strings - What this task depends on
- risk_factors: array of strings - Potential risks or challenges"""

        try:
            print(f"DEBUG: Analyzing task: {description[:100]}")
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.1,
                max_tokens=1500
            )
            print(f"DEBUG: LLM response: {response}")

            # Convert suggested_approach string to enum
            approach_map = {
                "decompose": ApproachType.DECOMPOSE,
                "implement": ApproachType.IMPLEMENT,
                "template": ApproachType.TEMPLATE
            }
            approach = approach_map.get(
                response.get("suggested_approach", "decompose").lower(),
                ApproachType.DECOMPOSE
            )

            analysis = TaskAnalysis(
                complexity_score=float(response.get("complexity_score", 0.5)),
                is_atomic=bool(response.get("is_atomic", False)),
                is_specific=bool(response.get("is_specific", True)),
                confidence=float(response.get("confidence", 0.7)),
                reasoning=str(response.get("reasoning", "No reasoning provided")),
                suggested_approach=approach,
                implementation_hints=response.get("implementation_hints"),
                estimated_story_points=response.get("estimated_story_points"),
                requires_human_review=False,  # Never set by LLM - only via API
                similar_patterns=response.get("similar_patterns", []),
                missing_details=response.get("missing_details", []),
                dependencies=response.get("dependencies", []),
                risk_factors=response.get("risk_factors", [])
            )

            print(f"DEBUG: Analysis result - is_atomic: {analysis.is_atomic}, complexity: {analysis.complexity_score}, approach: {analysis.suggested_approach}")
            return analysis

        except Exception as e:
            # Return a conservative default analysis on error
            print(f"Error in task analysis: {e}")
            return TaskAnalysis(
                complexity_score=0.7,
                is_atomic=False,
                is_specific=False,
                confidence=0.3,
                reasoning=f"Analysis failed: {str(e)}",
                suggested_approach=ApproachType.HUMAN_REVIEW,
                requires_human_review=True
            )

    def _is_meta_task(self, description: str) -> bool:
        """Check if a task description is a meta-task that should be filtered.

        Args:
            description: Task description to check

        Returns:
            True if this is a meta-task
        """
        desc_lower = description.lower()

        # Keywords that indicate meta-tasks (more aggressive)
        meta_keywords = [
            # Full phrase checks first
            "define game rules", "game rules", "project requirements",
            "choose a programming", "choose programming", "choose a language",
            "design the architecture", "design architecture",
            "test and debug", "test the game", "add features",
        ]

        for keyword in meta_keywords:
            if keyword in desc_lower:
                return True

        # List of meta-task patterns to filter
        meta_patterns = [
            # Testing (should be part of implementation)
            "test the", "write tests", "unit test", "integration test", "test coverage",
            "testing", "test app", "test application",

            # Refactoring/optimization (should be part of implementation)
            "refactor", "optimize", "clean up", "improve performance",

            # Setup/configuration (implied in first real task)
            "set up the project", "choose a programming language", "select a framework",
            "configure the environment", "set up development environment",
            "setup the", "set up the",

            # Documentation (should be inline)
            "document the", "write documentation", "create readme",

            # Deployment (separate concern)
            "deploy the", "host the", "publish the", "deployment",

            # Planning (not a task)
            "plan the", "design the architecture", "create a roadmap",
            "define the app's requirements", "define requirements", "gather requirements",
            "define features", "requirements and features", "analyze requirements",
            "define project scope", "project scope", "gather project",
            "identify stakeholder", "establish project", "determine project",
            "conduct testing", "quality assurance",

            # Architecture/Design (should be implicit in implementation)
            "design the user interface", "design ui", "design the ui",
            "choose technology", "select technology", "technology stack",

            # Generic non-implementation tasks
            "prepare for", "finalize", "review the"
        ]

        return any(pattern in desc_lower for pattern in meta_patterns)

    async def decompose_task(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        max_subtasks: int = 7,
        depth: int = 0
    ) -> TaskDecomposition:
        """Decompose a task into subtasks with inline analysis.

        This combines decomposition with immediate analysis of each subtask,
        eliminating the need for separate analysis calls.

        Args:
            description: Task to decompose
            context: Optional context
            max_subtasks: Maximum number of subtasks to generate
            depth: Current depth in task tree

        Returns:
            Task decomposition with analyzed subtasks
        """
        system_prompt = self._build_decomposition_prompt(context)
        user_prompt = f"""Decompose this task into subtasks:

Task: "{description}"
Current depth: {depth}

For each subtask, provide:
- description: Clear, actionable description
- is_atomic: Can it be done in 2-4 hours?
- implementation_details: If atomic, brief implementation guide (null otherwise)
- story_points: Estimate (1,2,3,5,8,13,21)
- dependencies: Array of indices this depends on (0-based)
- parallel_group: Integer indicating which group can be done in parallel

Also provide:
- decomposition_reasoning: Why you decomposed it this way
- estimated_total_points: Sum of all story points
- suggested_order: Array of indices in execution order
- parallel_groups: Array of arrays, grouping indices that can be done in parallel

Return as JSON with "subtasks" array and the additional fields."""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.2,
                max_tokens=10000  # Allow for comprehensive decomposition
            )

            # Ensure subtasks is a list
            subtasks = response.get("subtasks", [])
            if not isinstance(subtasks, list):
                subtasks = []

            # Validate and clean subtasks
            cleaned_subtasks = []
            seen_descriptions = set()

            for i, subtask in enumerate(subtasks[:max_subtasks]):
                if not isinstance(subtask, dict):
                    continue

                subtask_desc = subtask.get("description", f"Subtask {i+1}")

                # Check for duplicate or too-similar descriptions
                desc_lower = subtask_desc.lower().strip()

                # Skip if this is a meta-task
                if self._is_meta_task(subtask_desc):
                    print(f"[UnifiedAnalyzer] Skipping meta-task: '{subtask_desc}'")
                    continue

                # Skip if this is identical or too similar to the parent task
                if desc_lower == description.lower().strip():
                    print(f"[UnifiedAnalyzer] Skipping subtask identical to parent: '{subtask_desc}'")
                    continue

                if self._is_too_similar(description.lower(), desc_lower):
                    print(f"[UnifiedAnalyzer] Skipping subtask too similar to parent: '{subtask_desc}' vs '{description}'")
                    continue

                # Skip if we've seen a very similar description already
                if self._is_duplicate_subtask(desc_lower, seen_descriptions):
                    print(f"Skipping duplicate subtask: '{subtask_desc}'")
                    continue

                seen_descriptions.add(desc_lower)

                cleaned_subtask = {
                    "description": subtask_desc,
                    "is_atomic": bool(subtask.get("is_atomic", False)),
                    "implementation_details": subtask.get("implementation_details"),
                    "story_points": subtask.get("story_points", 3),
                    "dependencies": subtask.get("dependencies", []),
                    "parallel_group": subtask.get("parallel_group", i)
                }
                cleaned_subtasks.append(cleaned_subtask)

            # If we only have one subtask that's identical/similar to parent, mark parent as atomic
            if len(cleaned_subtasks) == 1 and self._is_too_similar(
                description.lower(),
                cleaned_subtasks[0]["description"].lower()
            ):
                print(f"Single subtask too similar to parent, marking as atomic: '{description}'")
                return TaskDecomposition(
                    subtasks=[{
                        "description": description,
                        "is_atomic": True,
                        "implementation_details": "Implement as specified",
                        "story_points": 5
                    }],
                    decomposition_reasoning="Task is already atomic"
                )

            return TaskDecomposition(
                subtasks=cleaned_subtasks,
                decomposition_reasoning=response.get(
                    "decomposition_reasoning",
                    "Task decomposed into logical components"
                ),
                estimated_total_points=response.get("estimated_total_points"),
                suggested_order=response.get("suggested_order"),
                parallel_groups=response.get("parallel_groups")
            )

        except Exception as e:
            print(f"Error in task decomposition: {e}")
            # Return a simple fallback decomposition
            return TaskDecomposition(
                subtasks=[{
                    "description": description,
                    "is_atomic": True,
                    "implementation_details": "Implement as specified",
                    "story_points": 5
                }],
                decomposition_reasoning=f"Decomposition failed: {str(e)}"
            )

    def _build_analysis_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for task analysis.

        Args:
            context: Optional context dictionary

        Returns:
            System prompt string
        """
        base_prompt = """You are a senior software engineer evaluating task complexity.

## WHEN TO USE WEB SEARCH:
Use web search when the task involves:
- Specific APIs or services you're unfamiliar with (e.g., "integrate with Stripe API")
- New frameworks or libraries (e.g., "build with Astro framework")
- Domain-specific requirements (e.g., "implement GDPR compliance")
- Technical standards or protocols (e.g., "add OAuth2 authentication")

## ANALYSIS CRITERIA:

A task is ATOMIC when it:
- Describes ONE specific feature or component
- Has clear inputs and outputs
- Could be completed in 2-4 hours of coding
- Is at depth 2 or greater (grandchildren of root)

A task NEEDS DECOMPOSITION when it:
- Is at depth 0 or 1 (root or direct children)
- Contains multiple features connected by "and"
- Describes an entire system or application
- Would take more than 4 hours to implement

## FEW-SHOT EXAMPLES:

Task: "Create user registration form with email, password, and name fields"
Analysis: ONE feature (registration form), specific fields listed, single component
Result: is_atomic: true, complexity_score: 0.3

Task: "Implement shopping cart with add, remove, and update quantity"
Analysis: ONE feature (cart) with related operations, cohesive functionality
Result: is_atomic: true, complexity_score: 0.4

Task: "Build product catalog and inventory management system"
Analysis: TWO distinct systems joined by "and", would be separate modules
Result: is_atomic: false, complexity_score: 0.8

Task: "Create Tetris game"
Analysis: Entire application with multiple subsystems (graphics, input, game logic)
Result: is_atomic: false, complexity_score: 0.7

Task: "Add pagination to product list with 10 items per page"
Analysis: ONE specific enhancement, clear requirements
Result: is_atomic: true, complexity_score: 0.2

## SCORING GUIDE:
- 0.0-0.3: Single function or small UI component
- 0.3-0.5: Single feature with multiple functions
- 0.5-0.7: Complex feature or small system
- 0.7-1.0: Multiple systems or entire application"""

        if context:
            tech_stack = context.get("tech_stack", "")
            best_practices = context.get("best_practices", "")
            repository_context = context.get("repository_context", "")

            if tech_stack:
                base_prompt += f"\n\nTech Stack: {tech_stack}"
            if best_practices:
                base_prompt += f"\n\nBest Practices: {best_practices}"
            if repository_context:
                base_prompt += f"\n\n{repository_context}"

        return base_prompt

    def _build_decomposition_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for task decomposition.

        Args:
            context: Optional context dictionary

        Returns:
            System prompt string
        """
        base_prompt = """You are a senior software engineer breaking down tasks into concrete implementation steps.

## DECOMPOSITION RULES:

1. Every subtask must be MORE SPECIFIC than its parent
2. Break down into distinct, non-overlapping components
3. Use concrete verbs: "Implement", "Create", "Add", "Build", "Connect"
4. Include implementation details: data structures, algorithms, UI elements
5. Each subtask should represent 1-3 hours of focused coding

## PATTERN RECOGNITION:

For "Create [game]" → Break into game-specific components:
- Game state/board representation
- Game pieces/entities
- Core game mechanics
- Input handling
- Display/rendering
- Scoring/win conditions

For "Build [CRUD app]" → Break into data operations:
- Data model/schema
- Create operation with validation
- Read/display with filtering
- Update operation
- Delete with confirmation
- Data persistence

For "Implement [feature]" → Focus on user actions:
- Core functionality
- User interface
- Input validation
- State management
- Error handling

## EXAMPLES OF GOOD DECOMPOSITION:

Task: "Create a password manager"
Subtasks:
1. "Implement encrypted password storage using AES-256"
2. "Create password entry form with strength indicator"
3. "Build password list view with search and categories"
4. "Add password generator with customizable rules"
5. "Implement secure copy-to-clipboard with auto-clear"
6. "Create master password authentication with lockout"

Task: "Build a markdown editor"
Subtasks:
1. "Create split-pane editor with syntax highlighting"
2. "Implement real-time markdown-to-HTML preview"
3. "Add toolbar with formatting shortcuts (bold, italic, links)"
4. "Build file operations (new, open, save, export)"
5. "Implement auto-save with local storage"

Task: "Implement shopping cart"
Subtasks:
1. "Create cart state management with add/remove actions"
2. "Build cart display with item quantities and totals"
3. "Implement quantity update with stock validation"
4. "Add discount/promo code application"
5. "Create cart persistence across sessions"

Task: "Implement block shapes and rotations"
Subtasks:
1. "Define tetromino shapes as 2D arrays (I, O, T, S, Z, J, L pieces)"
2. "Create rotation matrices for 90-degree clockwise rotation"
3. "Build rotation state manager with boundary checking"
4. "Add wall-kick logic for edge case rotations"
5. "Implement shape preview for next piece display"

## IMPORTANT:
The user already knows WHAT they want. Your job is HOW to build it.
Never suggest researching, planning, or defining requirements.
Jump straight to implementation tasks."""

        if context:
            tech_stack = context.get("tech_stack", "")
            best_practices = context.get("best_practices", "")
            repository_context = context.get("repository_context", "")

            if tech_stack:
                base_prompt += f"\n\nTech Stack: {tech_stack}"
            if best_practices:
                base_prompt += f"\n\nBest Practices: {best_practices}"
            if repository_context:
                base_prompt += f"\n\n{repository_context}"

        return base_prompt

    def _is_too_similar(self, str1: str, str2: str, threshold: float = 0.75) -> bool:
        """Check if two strings are too similar using simple heuristics.

        Args:
            str1: First string
            str2: Second string
            threshold: Similarity threshold (0-1)

        Returns:
            True if strings are too similar
        """
        # Exact match
        if str1 == str2:
            return True

        # One string contains the other (with small additions)
        if len(str1) > 10 and len(str2) > 10:
            if str1 in str2 or str2 in str1:
                # Check if the difference is small (like adding "the" or "a")
                len_diff = abs(len(str1) - len(str2))
                if len_diff < 10:
                    return True

        # Check word overlap
        words1 = set(str1.split())
        words2 = set(str2.split())

        # Filter out common words
        stop_words = {"the", "a", "an", "and", "or", "for", "in", "on", "at", "to", "from"}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return False

        similarity = intersection / union
        return similarity >= threshold

    def _is_duplicate_subtask(self, desc: str, seen_descriptions: set) -> bool:
        """Check if a subtask description is too similar to already seen ones.

        Args:
            desc: Description to check
            seen_descriptions: Set of already seen descriptions

        Returns:
            True if this is a duplicate
        """
        for seen in seen_descriptions:
            if self._is_too_similar(desc, seen, threshold=0.8):
                return True
        return False

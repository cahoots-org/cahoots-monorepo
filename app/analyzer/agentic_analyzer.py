"""Agentic task analyzer that can use tools to gather context."""

from typing import Dict, Any, List, Optional
import json

from app.models import TaskAnalysis, TaskDecomposition, ApproachType
from .llm_client import LLMClient
from .tools import AnalyzerTools


class AgenticAnalyzer:
    """Analyzer that uses tools to gather context before analysis."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the agentic analyzer.

        Args:
            llm_client: LLM client for making API calls
        """
        self.llm = llm_client
        self.tools = AnalyzerTools()

    async def analyze_task_with_tools(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0
    ) -> TaskAnalysis:
        """Analyze a task using tools to gather context first.

        Args:
            description: Task description to analyze
            context: Optional context (tech stack, best practices, etc.)
            depth: Current depth in task tree

        Returns:
            Comprehensive task analysis
        """
        # Step 1: Gather context using tools
        gathered_context = await self._gather_context(description)

        # Step 2: Analyze with enriched context
        system_prompt = self._build_analysis_prompt_with_context(context, gathered_context)
        user_prompt = f"""Analyze this task with the gathered context:

Task: "{description}"
Current depth in decomposition: {depth}

Context from web search:
{json.dumps(gathered_context, indent=2)}

Provide your analysis as a JSON object with these fields:
- complexity_score: float (0.0-1.0) - How complex is this task?
- is_atomic: boolean - Can this be done in a single focused work session (2-4 hours)?
- is_specific: boolean - Is the task specific enough to implement?
- confidence: float (0.0-1.0) - How confident are you in this analysis?
- reasoning: string - Brief explanation of your analysis
- suggested_approach: string - One of: "decompose", "implement", "template"
- implementation_hints: string or null - If atomic, brief implementation guidance
- estimated_story_points: integer or null - Fibonacci scale (1,2,3,5,8,13,21)
- similar_patterns: array of strings - Common patterns this resembles
- missing_details: array of strings - What information is missing?
- dependencies: array of strings - What this task depends on
- risk_factors: array of strings - Potential risks or challenges"""

        try:
            print(f"DEBUG: Analyzing task with context: {description[:100]}")
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.1,
                max_tokens=1500
            )

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

            return TaskAnalysis(
                complexity_score=float(response.get("complexity_score", 0.5)),
                is_atomic=bool(response.get("is_atomic", False)),
                is_specific=bool(response.get("is_specific", True)),
                confidence=float(response.get("confidence", 0.7)),
                reasoning=str(response.get("reasoning", "No reasoning provided")),
                suggested_approach=approach,
                implementation_hints=response.get("implementation_hints"),
                estimated_story_points=response.get("estimated_story_points"),
                requires_human_review=False,
                similar_patterns=response.get("similar_patterns", []),
                missing_details=response.get("missing_details", []),
                dependencies=response.get("dependencies", []),
                risk_factors=response.get("risk_factors", [])
            )

        except Exception as e:
            print(f"Error in task analysis with tools: {e}")
            # Fallback to basic analysis without context
            return TaskAnalysis(
                complexity_score=0.7,
                is_atomic=False,
                is_specific=False,
                confidence=0.3,
                reasoning=f"Analysis failed, using conservative defaults: {str(e)}",
                suggested_approach=ApproachType.DECOMPOSE,
                requires_human_review=False
            )

    async def decompose_task_with_context(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        max_subtasks: int = 7,
        depth: int = 0
    ) -> TaskDecomposition:
        """Decompose a task using gathered context.

        Args:
            description: Task to decompose
            context: Optional context
            max_subtasks: Maximum number of subtasks
            depth: Current depth

        Returns:
            Task decomposition with analyzed subtasks
        """
        # Gather context for better decomposition
        gathered_context = await self._gather_context(description)

        system_prompt = self._build_decomposition_prompt_with_context(context, gathered_context)
        user_prompt = f"""Decompose this task into {max_subtasks} or fewer subtasks:

Task: "{description}"
Current depth: {depth}

Context from research:
{json.dumps(gathered_context, indent=2)}

Based on the research, create specific subtasks that align with the actual requirements.

For each subtask, provide:
- description: Clear, actionable description specific to the context
- is_atomic: Can it be done in 2-4 hours?
- implementation_details: If atomic, brief implementation guide
- story_points: Estimate (1,2,3,5,8,13,21)
- dependencies: Array of indices this depends on (0-based)
- parallel_group: Integer indicating which group can be done in parallel

Return as JSON with "subtasks" array and additional fields:
- decomposition_reasoning: Why you decomposed it this way
- estimated_total_points: Sum of all story points
- suggested_order: Array of indices in execution order"""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.2,
                max_tokens=3000
            )

            subtasks = response.get("subtasks", [])
            if not isinstance(subtasks, list):
                subtasks = []

            # Validate and clean subtasks
            cleaned_subtasks = []
            for i, subtask in enumerate(subtasks[:max_subtasks]):
                if not isinstance(subtask, dict):
                    continue

                cleaned_subtask = {
                    "description": subtask.get("description", f"Subtask {i+1}"),
                    "is_atomic": bool(subtask.get("is_atomic", False)),
                    "implementation_details": subtask.get("implementation_details"),
                    "story_points": subtask.get("story_points", 3),
                    "dependencies": subtask.get("dependencies", []),
                    "parallel_group": subtask.get("parallel_group", i)
                }
                cleaned_subtasks.append(cleaned_subtask)

            return TaskDecomposition(
                subtasks=cleaned_subtasks,
                decomposition_reasoning=response.get(
                    "decomposition_reasoning",
                    "Task decomposed based on context"
                ),
                estimated_total_points=response.get("estimated_total_points"),
                suggested_order=response.get("suggested_order"),
                parallel_groups=response.get("parallel_groups")
            )

        except Exception as e:
            print(f"Error in contextual decomposition: {e}")
            # Re-raise the error to be handled by the task processor
            raise

    async def _gather_context(self, description: str) -> Dict[str, Any]:
        """Gather context about the task using tools.

        Args:
            description: Task description

        Returns:
            Dictionary with gathered context
        """
        context = {}

        # Search for similar projects
        print(f"DEBUG: Searching for context about: {description}")
        similar = await self.tools.search_similar_projects(description)
        if similar:
            context["similar_projects"] = similar[:3]  # Top 3 results

        # Search for complexity indicators
        complexity = await self.tools.analyze_task_complexity(description)
        if complexity:
            context["complexity_indicators"] = complexity

        # Extract key technologies mentioned
        tech_keywords = self._extract_technologies(description)
        if tech_keywords:
            tech_docs = []
            for tech in tech_keywords[:2]:  # Limit to avoid too many searches
                docs = await self.tools.search_technical_docs(tech)
                if docs:
                    tech_docs.extend(docs[:2])
            if tech_docs:
                context["technical_docs"] = tech_docs

        return context

    def _extract_technologies(self, description: str) -> List[str]:
        """Extract technology keywords from task description.

        Args:
            description: Task description

        Returns:
            List of technology keywords
        """
        # Common technology keywords to look for
        tech_keywords = [
            "react", "vue", "angular", "django", "flask", "express",
            "postgres", "mysql", "mongodb", "redis", "elasticsearch",
            "aws", "gcp", "azure", "docker", "kubernetes",
            "api", "rest", "graphql", "websocket",
            "authentication", "jwt", "oauth",
            "payment", "stripe", "paypal",
            "ecommerce", "shopping", "cart", "checkout"
        ]

        description_lower = description.lower()
        found = []
        for tech in tech_keywords:
            if tech in description_lower:
                found.append(tech)

        return found

    def _build_analysis_prompt_with_context(
        self,
        context: Optional[Dict[str, Any]],
        gathered_context: Dict[str, Any]
    ) -> str:
        """Build system prompt with gathered context.

        Args:
            context: User-provided context
            gathered_context: Context from tools

        Returns:
            System prompt string
        """
        base_prompt = """You are an expert software architect analyzing tasks for decomposition.
You have access to web search results and context to make informed decisions.

Use the gathered context to:
1. Understand the specific domain and requirements
2. Identify common patterns and best practices
3. Make accurate complexity assessments
4. Suggest appropriate decomposition strategies

Consider atomic tasks as those that:
- Can be completed in a single focused work session (2-4 hours)
- Have a single, clear objective
- Don't require multiple distinct components

Complexity scoring guidelines:
- 0.0-0.3: Trivial tasks (simple CRUD, basic UI)
- 0.3-0.5: Simple tasks (standard features, common patterns)
- 0.5-0.7: Moderate tasks (integration, custom logic)
- 0.7-0.9: Complex tasks (architecture, algorithms)
- 0.9-1.0: Very complex tasks (system design, research)"""

        if gathered_context:
            base_prompt += "\n\nGathered Context Summary:"
            if "similar_projects" in gathered_context:
                base_prompt += "\n- Similar projects found with implementation patterns"
            if "complexity_indicators" in gathered_context:
                base_prompt += "\n- Complexity analysis available"
            if "technical_docs" in gathered_context:
                base_prompt += "\n- Technical documentation referenced"

        if context:
            tech_stack = context.get("tech_stack", "")
            if tech_stack:
                base_prompt += f"\n\nUser's Tech Stack: {tech_stack}"

        return base_prompt

    def _build_decomposition_prompt_with_context(
        self,
        context: Optional[Dict[str, Any]],
        gathered_context: Dict[str, Any]
    ) -> str:
        """Build decomposition prompt with context.

        Args:
            context: User-provided context
            gathered_context: Context from tools

        Returns:
            System prompt string
        """
        base_prompt = """You are an expert software architect decomposing tasks into implementable subtasks.
You have researched the task and have context about similar implementations.

CRITICAL RULES TO PREVENT DUPLICATION:
1. Each subtask must have a UNIQUE responsibility - no overlapping functionality
2. Do NOT create subtasks that repeat work covered by other subtasks
3. Ensure clear separation of concerns between all subtasks
4. If a subtask mentions "X and Y", split it unless they're tightly coupled

Use the gathered context to create subtasks that:
- Align with industry best practices
- Follow common architectural patterns
- Are specific to the actual requirements
- Can be implemented efficiently

Create subtasks that are:
- Focused on a SINGLE responsibility (not multiple)
- Logically ordered with clear dependencies
- Balanced in complexity
- Actionable and specific
- Non-overlapping in scope

BEFORE creating each subtask, check:
- Is this functionality already covered by another subtask?
- Can this be merged with an existing subtask without overloading it?
- Is the scope clearly distinct from other subtasks?

IMPORTANT: Base your decomposition on the research results, not on generic patterns."""

        if gathered_context:
            base_prompt += "\n\nYou have researched:"
            if "similar_projects" in gathered_context:
                base_prompt += "\n- How similar projects are structured"
            if "technical_docs" in gathered_context:
                base_prompt += "\n- Technical documentation and best practices"

        return base_prompt
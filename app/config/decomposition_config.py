"""
Decomposition Configuration - Prompt Tuning Levers

This module provides configurable parameters that affect HOW we ask the LLM
to decompose tasks, not artificial limits on outputs.
"""

from typing import Optional
from pydantic import BaseModel, Field


class PromptTuningConfig(BaseModel):
    """Configuration for tuning LLM prompts and generation behavior."""

    # ============================================================================
    # TEMPERATURE SETTINGS
    # ============================================================================

    story_generation_temperature: float = Field(
        default=0.06,
        ge=0.0,
        le=1.0,
        description="LLM temperature for user story generation (0.0-1.0). "
                    "Lower = more deterministic/conservative. Higher = more creative/varied."
    )

    task_decomposition_temperature: float = Field(
        default=0.09,
        ge=0.0,
        le=1.0,
        description="LLM temperature for task decomposition (0.0-1.0). "
                    "Lower = more consistent/predictable. Higher = more creative."
    )

    event_modeling_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature for event modeling (0.0-1.0)"
    )

    # ============================================================================
    # DECOMPOSITION GUIDANCE (how to guide the LLM's thinking)
    # ============================================================================

    task_sizing_guidance: str = Field(
        default="granular",
        description="How to guide task sizing in prompts. Options:\n"
                    "- 'consolidated': Emphasize grouping related work into comprehensive tasks\n"
                    "- 'balanced': Standard guidance for moderate task granularity\n"
                    "- 'granular': Encourage breaking work into smaller, focused tasks"
    )

    story_detail_level: str = Field(
        default="detailed",
        description="How much detail to request in user stories. Options:\n"
                    "- 'high_level': Request broader, simpler stories\n"
                    "- 'balanced': Standard story detail\n"
                    "- 'detailed': Request more specific, detailed stories"
    )

    implementation_focus: str = Field(
        default="architectural",
        description="What to emphasize in implementation descriptions. Options:\n"
                    "- 'practical': Focus on what needs to be built\n"
                    "- 'technical': Include more technical implementation details\n"
                    "- 'architectural': Include design and architecture considerations"
    )

    # ============================================================================
    # EMPHASIS FLAGS (what to stress in prompts)
    # ============================================================================

    emphasize_consolidation: bool = Field(
        default=False,
        description="Whether to emphasize consolidating related work into single tasks in prompts"
    )

    emphasize_grouping_acceptance_criteria: bool = Field(
        default=True,
        description="Whether to emphasize grouping acceptance criteria that belong together"
    )

    emphasize_avoiding_micro_tasks: bool = Field(
        default=True,
        description="Whether to emphasize avoiding overly granular micro-tasks"
    )

    emphasize_substantial_tasks: bool = Field(
        default=True,
        description="Whether to emphasize creating substantial, meaningful tasks (vs many small tasks)"
    )

    emphasize_feature_completeness: bool = Field(
        default=False,
        description="Whether to emphasize covering all features completely"
    )

    # ============================================================================
    # REFERENCE EXAMPLES (examples to show in prompts)
    # ============================================================================

    show_good_task_examples: bool = Field(
        default=True,
        description="Whether to include examples of well-sized tasks in prompts"
    )

    show_bad_task_examples: bool = Field(
        default=True,
        description="Whether to include anti-pattern examples (what NOT to do) in prompts"
    )

    # ============================================================================
    # COMPLEXITY-SPECIFIC GUIDANCE
    # ============================================================================

    atomic_guidance: str = Field(
        default="standard",
        description="How to guide decomposition for atomic tasks. Options:\n"
                    "- 'treat_as_single_feature': Emphasize this is a single cohesive feature\n"
                    "- 'minimal_breakdown': Request minimal necessary breakdown\n"
                    "- 'standard': Use standard decomposition approach"
    )

    medium_guidance: str = Field(
        default="moderate_breakdown",
        description="How to guide decomposition for medium tasks. Options:\n"
                    "- 'conservative': Lean toward fewer, larger tasks\n"
                    "- 'moderate_breakdown': Balanced approach\n"
                    "- 'thorough': More comprehensive breakdown"
    )

    complex_guidance: str = Field(
        default="thorough_but_grouped",
        description="How to guide decomposition for complex tasks. Options:\n"
                    "- 'grouped': Emphasize grouping related functionality\n"
                    "- 'thorough_but_grouped': Thorough coverage but group related work\n"
                    "- 'comprehensive': Full detailed breakdown"
    )

    epic_guidance: str = Field(
        default="comprehensive",
        description="How to guide decomposition for epic tasks. Options:\n"
                    "- 'high_level_modules': Break into major modules/components\n"
                    "- 'feature_based': Break by major features\n"
                    "- 'comprehensive': Full detailed breakdown"
    )

    # ============================================================================
    # TONE AND STYLE
    # ============================================================================

    prompt_tone: str = Field(
        default="directive",
        description="Tone to use in prompts. Options:\n"
                    "- 'directive': Strong, clear instructions\n"
                    "- 'guiding': Helpful guidance and suggestions\n"
                    "- 'neutral': Factual, neutral instructions"
    )

    use_examples: bool = Field(
        default=True,
        description="Whether to include examples in prompts"
    )

    use_anti_patterns: bool = Field(
        default=True,
        description="Whether to explicitly call out what NOT to do"
    )

    # ============================================================================
    # TOKEN LIMITS
    # ============================================================================

    max_tokens_story_generation: int = Field(
        default=16000,
        description="Max tokens for story generation responses"
    )

    max_tokens_task_decomposition: int = Field(
        default=64000,
        description="Max tokens for task decomposition responses (reduced for better latency)"
    )

    max_tokens_event_modeling: int = Field(
        default=32000,
        description="Max tokens for event modeling responses"
    )

    def to_prompt_guidance(self, complexity: str = "medium") -> str:
        """
        Generate prompt guidance text to inject into LLM prompts based on configuration.

        Args:
            complexity: Task complexity level ('atomic', 'medium', 'complex', 'epic')

        Returns:
            String containing configuration-based guidance for the LLM
        """
        guidance = []

        # Complexity-specific guidance
        complexity_guidance = self._get_complexity_guidance(complexity)
        if complexity_guidance:
            guidance.append(complexity_guidance)

        # Task sizing guidance
        sizing_guidance = self._get_sizing_guidance()
        if sizing_guidance:
            guidance.append(sizing_guidance)

        # Emphasis points
        emphasis_points = self._get_emphasis_points()
        if emphasis_points:
            guidance.append(emphasis_points)

        # Examples
        examples = self._get_examples(complexity)
        if examples:
            guidance.append(examples)

        return "\n\n".join(guidance)

    def _get_complexity_guidance(self, complexity: str) -> str:
        """Get complexity-specific guidance text."""
        guidance_map = {
            "atomic": self.atomic_guidance,
            "medium": self.medium_guidance,
            "complex": self.complex_guidance,
            "epic": self.epic_guidance
        }

        guidance_type = guidance_map.get(complexity, "moderate_breakdown")

        if complexity == "atomic":
            if guidance_type == "treat_as_single_feature":
                return """## ATOMIC TASK CONTEXT:
This is a SINGLE, COHESIVE FEATURE. Treat it as one unified piece of functionality.

Think of this as implementing ONE thing, not many separate things.
Combine frontend, backend, database, and validation into SINGLE comprehensive tasks.
DO NOT create separate tasks for each component - group them together.
Favor creating very few, highly consolidated tasks over many small ones."""

            elif guidance_type == "minimal_breakdown":
                return """## ATOMIC TASK CONTEXT:
This is a simple feature. Break it down MINIMALLY - only separate concerns that truly need to be separate.
Err on the side of keeping related work together."""

        elif complexity == "medium":
            if guidance_type == "conservative":
                return """## MEDIUM COMPLEXITY CONTEXT:
This is a moderate feature. Create fewer, more substantial tasks rather than many micro-tasks.

Group related implementation work together. Combine multiple related features into single tasks.
Each task should be a complete vertical slice (frontend + backend + database for a feature area).
Strongly prefer consolidation - create as few tasks as possible while maintaining clarity."""

            elif guidance_type == "moderate_breakdown":
                return """## MEDIUM COMPLEXITY CONTEXT:
This is a moderate feature. Break it into logical, substantial chunks of work.
Each task should represent a meaningful piece of functionality."""

        elif complexity == "complex":
            if guidance_type == "grouped":
                return """## COMPLEX PROJECT CONTEXT:
This is a complex project. Group related functionality into cohesive tasks.
Avoid over-fragmenting - keep related work together even if it's substantial."""

            elif guidance_type == "thorough_but_grouped":
                return """## COMPLEX PROJECT CONTEXT:
This is a complex project requiring thorough coverage. Break it down comprehensively,
but group related functionality together. Balance completeness with cohesion."""

        elif complexity == "epic":
            if guidance_type == "high_level_modules":
                return """## EPIC PROJECT CONTEXT:
This is a large-scale project. Break it into major modules and components.
Focus on high-level architectural boundaries."""

            elif guidance_type == "feature_based":
                return """## EPIC PROJECT CONTEXT:
This is a large-scale project. Break it into major feature areas.
Each major feature may encompass multiple related capabilities."""

        return ""

    def _get_sizing_guidance(self) -> str:
        """Get task sizing guidance text."""
        if self.task_sizing_guidance == "consolidated":
            return """## TASK SIZING PHILOSOPHY:
**CRITICAL REQUIREMENT**: Create VERY FEW, HIGHLY CONSOLIDATED tasks. Each task should combine extensive related functionality.

**CONSOLIDATION RULES (NON-NEGOTIABLE):**
- Multiple related acceptance criteria → ALWAYS COMBINE into ONE task
- Same feature area → ALWAYS COMBINE into ONE task
- Frontend + backend + database for same feature → ALWAYS COMBINE into ONE task
- Multiple endpoints for same resource (GET, POST, PUT, DELETE) → ALWAYS COMBINE into ONE task
- Related UI components → ALWAYS COMBINE into ONE task
- Testing and implementation → COMBINED (not separate tasks)

**Good task example:** "Implement complete user authentication system with login, registration, password reset, session management, email verification, and password strength validation"
**Bad task examples:** Separate tasks for "Create login form", "Add login validation", "Create login endpoint", "Handle login errors", "Add password reset"

**CRITICAL**: Err heavily on the side of consolidation. When in doubt, COMBINE tasks rather than split them.
Think in terms of complete feature delivery, not individual components."""

        elif self.task_sizing_guidance == "balanced":
            return """## TASK SIZING PHILOSOPHY:
Create tasks that are substantial enough to be meaningful, but focused enough to be clear.

**Good task size:** Represents 2-4 hours of focused development work.
**Too small:** "Add validation to email field" (micro-task)
**Too large:** "Build entire user management system" (needs breakdown)
**Just right:** "Implement user registration with validation and email verification"

**Consolidation principle:** Group acceptance criteria that naturally belong together."""

        elif self.task_sizing_guidance == "granular":
            return """## TASK SIZING PHILOSOPHY:
Break work into focused, specific tasks. Each task should have a clear, singular purpose.

**Prefer:** Smaller, well-defined tasks over large multi-purpose tasks.
**Good example:** Separate tasks for data model, API endpoints, UI components, validation.
**Focus:** Each task should be independently testable and reviewable."""

        return ""

    def _get_emphasis_points(self) -> str:
        """Get emphasis points based on flags."""
        points = []

        if self.emphasize_consolidation:
            points.append("- **GROUP RELATED WORK**: Consolidate related implementation into single tasks")

        if self.emphasize_grouping_acceptance_criteria:
            points.append("- **GROUP ACCEPTANCE CRITERIA**: Multiple acceptance criteria often = ONE implementation task")

        if self.emphasize_avoiding_micro_tasks:
            points.append("- **AVOID MICRO-TASKS**: Don't create separate tasks for every small detail")

        if self.emphasize_substantial_tasks:
            points.append("- **CREATE SUBSTANTIAL TASKS**: Each task should represent meaningful, cohesive work")

        if self.emphasize_feature_completeness:
            points.append("- **ENSURE COMPLETENESS**: Cover all necessary functionality")

        if not points:
            return ""

        tone_prefix = {
            "directive": "## CRITICAL REQUIREMENTS:",
            "guiding": "## GUIDANCE:",
            "neutral": "## CONSIDERATIONS:"
        }.get(self.prompt_tone, "## GUIDANCE:")

        return f"{tone_prefix}\n" + "\n".join(points)

    def _get_examples(self, complexity: str) -> str:
        """Get example tasks based on configuration."""
        if not (self.show_good_task_examples or self.show_bad_task_examples):
            return ""

        examples = "## EXAMPLES:\n\n"

        if self.show_good_task_examples:
            examples += "### ✅ GOOD Task Descriptions:\n"
            if complexity == "atomic":
                examples += """- "Build contact form with name, email, message fields, validation, and submission to API endpoint"
- "Create weather widget displaying current temperature, conditions, and humidity with auto-refresh"
- "Implement TODO list with add, complete, delete, and filter functionality"
"""
            else:
                examples += """- "Implement user authentication system with registration, login, and password reset"
- "Create blog post management with rich text editor, draft/publish workflow, and image upload"
- "Build product catalog with search, filtering, pagination, and detail views"
"""

        if self.show_bad_task_examples:
            examples += "\n### ❌ BAD Task Descriptions (AVOID THESE):\n"
            examples += """- "Create form" (too vague)
- "Add validation" (incomplete - validation for what?)
- "Style the button" (micro-task)
- "Handle edge cases" (not specific enough)
- "Test the feature" (testing isn't an implementation task)
- "Deploy to production" (not an implementation task)
"""

        if self.use_anti_patterns:
            examples += "\n### 🚫 ANTI-PATTERNS TO AVOID:\n"
            examples += """- Creating separate tasks for: "Create model", "Add validation to model", "Write tests for model" → Should be ONE task
- Creating tasks for planning, documentation, or deployment → Focus on IMPLEMENTATION only
- Creating tasks for quality attributes separately → "Make it fast", "Make it responsive" → Build these INTO implementation tasks
"""

        return examples

    @classmethod
    def for_complexity(cls, complexity: str) -> "PromptTuningConfig":
        """
        Create a pre-configured PromptTuningConfig optimized for a specific complexity level.

        Args:
            complexity: One of 'atomic', 'medium', 'complex', 'epic'

        Returns:
            PromptTuningConfig instance tuned for that complexity
        """
        config = cls()

        if complexity == "atomic":
            config.task_sizing_guidance = "consolidated"
            config.story_detail_level = "high_level"
            config.atomic_guidance = "treat_as_single_feature"
            config.emphasize_consolidation = True
            config.emphasize_avoiding_micro_tasks = True
            config.emphasize_substantial_tasks = True

        elif complexity == "medium":
            config.task_sizing_guidance = "consolidated"
            config.story_detail_level = "balanced"
            config.medium_guidance = "moderate_breakdown"
            config.emphasize_consolidation = True
            config.emphasize_grouping_acceptance_criteria = True

        elif complexity == "complex":
            config.task_sizing_guidance = "balanced"
            config.story_detail_level = "balanced"
            config.complex_guidance = "thorough_but_grouped"
            config.emphasize_consolidation = False
            config.emphasize_feature_completeness = True

        elif complexity == "epic":
            config.task_sizing_guidance = "balanced"
            config.story_detail_level = "detailed"
            config.epic_guidance = "comprehensive"
            config.emphasize_consolidation = False
            config.emphasize_feature_completeness = True

        return config


# Default configuration
DEFAULT_CONFIG = PromptTuningConfig()

# Conservative profile (favor consolidation)
CONSERVATIVE_CONFIG = PromptTuningConfig(
    task_sizing_guidance="consolidated",
    story_detail_level="high_level",
    emphasize_consolidation=True,
    emphasize_avoiding_micro_tasks=True,
    emphasize_substantial_tasks=True,
    atomic_guidance="treat_as_single_feature",
    medium_guidance="conservative"
)

# Detailed profile (more granular)
DETAILED_CONFIG = PromptTuningConfig(
    task_sizing_guidance="granular",
    story_detail_level="detailed",
    emphasize_consolidation=False,
    emphasize_feature_completeness=True,
    complex_guidance="comprehensive",
    epic_guidance="comprehensive"
)

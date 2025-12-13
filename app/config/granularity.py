"""Granularity configuration for task decomposition.

This module defines granularity levels that control how tasks are decomposed
based on the target team's experience level and working style.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class GranularityConfig:
    """Configuration for a granularity level."""
    name: str
    display_name: str
    min_story_points: int
    max_story_points: int
    tasks_per_story_hint: str  # e.g., "2-4", "4-8", "8-15"
    implementation_detail_level: str  # "high-level", "standard", "detailed"
    prompt_guidance: str


GRANULARITY_CONFIGS: Dict[str, GranularityConfig] = {
    "large": GranularityConfig(
        name="large",
        display_name="Large Tasks",
        min_story_points=5,
        max_story_points=13,
        tasks_per_story_hint="2-4",
        implementation_detail_level="high-level",
        prompt_guidance="""
Create fewer, larger tasks suitable for experienced developers:
- Each task should be 5-13 story points
- Combine related work into cohesive units
- Focus on WHAT to build, not HOW (experienced devs know how)
- Assume familiarity with patterns and best practices
- 2-4 tasks per user story is typical
- Keep implementation details high-level
"""
    ),
    "medium": GranularityConfig(
        name="medium",
        display_name="Medium Tasks",
        min_story_points=2,
        max_story_points=8,
        tasks_per_story_hint="1-5",
        implementation_detail_level="standard",
        prompt_guidance="""
Create balanced tasks suitable for most development teams:
- Each task should be 2-8 story points
- Combine related work into single tasks
- 1-5 tasks per user story depending on complexity
"""
    ),
    "small": GranularityConfig(
        name="small",
        display_name="Small Tasks",
        min_story_points=1,
        max_story_points=3,
        tasks_per_story_hint="1-8",
        implementation_detail_level="detailed",
        prompt_guidance="""
Create granular tasks for junior developers:
- Each task should be 1-3 story points
- Include specific implementation guidance
- 1-8 tasks per user story depending on complexity
"""
    ),
}


def get_granularity_config(level: str) -> GranularityConfig:
    """Get configuration for a granularity level.

    Args:
        level: Granularity level ('small', 'medium', or 'large')

    Returns:
        GranularityConfig for the specified level, defaults to 'medium'
    """
    return GRANULARITY_CONFIGS.get(level, GRANULARITY_CONFIGS["medium"])


def get_story_point_guidance(level: str) -> str:
    """Get story point guidance text for prompts.

    Args:
        level: Granularity level

    Returns:
        Formatted string with SP guidance for LLM prompts
    """
    config = get_granularity_config(level)
    return f"""
Story Point Guidelines for {config.display_name}:
- Minimum: {config.min_story_points} SP
- Maximum: {config.max_story_points} SP
- Target tasks per story: {config.tasks_per_story_hint}
- Detail level: {config.implementation_detail_level}
"""

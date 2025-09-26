"""Processing rules engine for conditional task processing."""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.models import Task, TaskAnalysis, ApproachType


@dataclass
class ProcessingConfig:
    """Configuration for task processing rules."""
    max_depth: int = 10  # Allow natural decomposition depth
    complexity_threshold: float = 0.45
    force_atomic_depth: int = 10  # Only force atomic at extreme depth
    skip_gap_analysis_depth: int = 1  # Skip gap analysis for deeper tasks
    batch_sibling_threshold: int = 3


class ProcessingRules:
    """Rules engine that determines how tasks should be processed."""

    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize processing rules.

        Args:
            config: Configuration for processing rules
        """
        self.config = config or ProcessingConfig()

    def should_decompose(self, task: Task, analysis: TaskAnalysis) -> bool:
        """Determine if a task should be decomposed.

        Args:
            task: Task to evaluate
            analysis: Analysis results

        Returns:
            True if task should be decomposed
        """
        # Force atomic at maximum depth
        if task.depth >= self.config.force_atomic_depth:
            return False

        # Don't decompose if already atomic
        if analysis.is_atomic:
            return False

        # Don't decompose if complexity is below threshold
        if analysis.complexity_score < self.config.complexity_threshold:
            return False

        # Follow analysis recommendation
        if analysis.suggested_approach == ApproachType.DECOMPOSE:
            return True

        # Default to not decomposing if unclear
        return False


    def should_batch_process(self, sibling_count: int, depth: int) -> bool:
        """Determine if sibling tasks should be batch processed.

        Args:
            sibling_count: Number of sibling tasks
            depth: Current depth

        Returns:
            True if siblings should be batch processed
        """
        # Only batch at deeper levels to avoid over-optimization
        if depth < 2:
            return False

        # Batch if we have enough siblings
        return sibling_count >= self.config.batch_sibling_threshold

    def should_skip_gap_analysis(self, task: Task) -> bool:
        """Determine if gap analysis should be skipped.

        Args:
            task: Task to evaluate

        Returns:
            True if gap analysis should be skipped
        """
        # Skip gap analysis for deeper tasks to avoid over-decomposition
        return task.depth > self.config.skip_gap_analysis_depth

    def should_require_human_review(
        self,
        task: Task,
        analysis: TaskAnalysis
    ) -> bool:
        """Determine if human review is required.

        Human review is OPT-IN only through the API. The LLM should NOT
        control this - it's purely based on user request.

        Args:
            task: Task to evaluate
            analysis: Analysis results

        Returns:
            True if human review is required
        """
        # Check if task has explicit human_review flag in context/metadata
        if task.context and task.context.get("require_human_review"):
            return True

        if task.metadata and task.metadata.get("require_human_review"):
            return True

        # Never require review otherwise - it's completely opt-in via API
        return False

    def get_processing_priority(
        self,
        task: Task,
        analysis: TaskAnalysis
    ) -> int:
        """Get processing priority for task scheduling.

        Args:
            task: Task to evaluate
            analysis: Analysis results

        Returns:
            Priority score (higher = more urgent)
        """
        priority = 0

        # Prioritize by depth (shallower = higher priority)
        priority += (10 - task.depth) * 10

        # Prioritize atomic tasks (can be completed immediately)
        if analysis.is_atomic:
            priority += 20

        # Prioritize based on confidence
        priority += int(analysis.confidence * 10)

        # Prioritize simpler tasks
        priority += int((1 - analysis.complexity_score) * 10)

        # Boost priority if blocking other tasks
        if analysis.dependencies:
            priority += len(analysis.dependencies) * 5

        return priority

    def get_processing_strategy(
        self,
        task: Task,
        analysis: TaskAnalysis
    ) -> Dict[str, Any]:
        """Get comprehensive processing strategy for a task.

        Args:
            task: Task to evaluate
            analysis: Analysis results

        Returns:
            Dictionary with processing strategy
        """
        return {
            "should_decompose": self.should_decompose(task, analysis),
            "should_require_review": self.should_require_human_review(task, analysis),
            "skip_gap_analysis": self.should_skip_gap_analysis(task),
            "priority": self.get_processing_priority(task, analysis),
            "approach": analysis.suggested_approach,
            "confidence": analysis.confidence,
            "estimated_effort": analysis.estimated_story_points or 5
        }


    def get_max_subtasks(self, task: Task, analysis: TaskAnalysis) -> int:
        """Get maximum number of subtasks for decomposition.

        Args:
            task: Task to evaluate
            analysis: Analysis results

        Returns:
            Maximum number of subtasks
        """
        # No artificial limits - let the LLM decide based on the task
        # The LLM should naturally create the right number of subtasks
        # based on the task's complexity and the atomicity guidelines
        return 99  # Effectively unlimited, but capped for safety
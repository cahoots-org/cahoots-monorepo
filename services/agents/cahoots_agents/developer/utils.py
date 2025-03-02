"""Utility functions for the developer agent."""

from typing import List

from cahoots_core.models.task import Task


def needs_ux_design(tasks: List[Task]) -> bool:
    """Check if any tasks require UX design.

    Args:
        tasks: List of tasks to check

    Returns:
        True if any task requires UX design
    """
    return any(task.requires_ux for task in tasks)

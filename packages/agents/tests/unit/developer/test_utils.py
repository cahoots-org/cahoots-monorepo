"""Tests for developer utility functions."""
import pytest
from unittest.mock import MagicMock

from cahoots_core.models.task import Task

from ....src.cahoots_agents.developer.utils import needs_ux_design

def test_needs_ux_design_with_ux_tasks():
    """Test needs_ux_design with UX tasks."""
    tasks = [
        Task(id="1", title="Task 1", description="Test task", requires_ux=True),
        Task(id="2", title="Task 2", description="Test task", requires_ux=False)
    ]
    assert needs_ux_design(tasks) is True

def test_needs_ux_design_with_no_ux_tasks():
    """Test needs_ux_design with no UX tasks."""
    tasks = [
        Task(id="1", title="Task 1", description="Test task", requires_ux=False),
        Task(id="2", title="Task 2", description="Test task", requires_ux=False)
    ]
    assert needs_ux_design(tasks) is False

def test_needs_ux_design_with_all_ux_tasks():
    """Test needs_ux_design with all UX tasks."""
    tasks = [
        Task(id="1", title="Task 1", description="Test task", requires_ux=True),
        Task(id="2", title="Task 2", description="Test task", requires_ux=True)
    ]
    assert needs_ux_design(tasks) is True

def test_needs_ux_design_with_empty_tasks():
    """Test needs_ux_design with empty tasks list."""
    assert needs_ux_design([]) is False 
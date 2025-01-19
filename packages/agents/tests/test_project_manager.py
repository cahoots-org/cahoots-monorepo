"""Tests for the project manager agent.

This module contains tests for the ProjectManagerAgent class, which handles:
- Project creation and setup
- Story management
- Roadmap generation
- Task tracking
"""
from datetime import datetime
from typing import Any, Dict, List, AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
import json
import os

import pytest
from pytest_mock import MockFixture

from agent_pm.agent import ProjectManagerAgent
from core.models import Task
from core.utils.event_system import EventSystem
from core.services.github_service import GitHubService
from core.utils.base_logger import BaseLogger

# Test constants
TEST_PROJECT_NAME = "Test Project"
TEST_PROJECT_DESC = "A test project"
TEST_BOARD_ID = "board-1"
TEST_LIST_ID = "list-1"
TEST_CARD_ID = "card-1"

# Test data
TEST_STORY_DATA = {
    "id": "story-1",
    "type": "story_created",
    "title": "New Story",
    "description": "A new story",
    "priority": "medium",
    "requirements": {
        "ui_ux": "Design user interface",
        "implementation": "Implement backend API"
    }
}

TEST_TASK_DATA = {
    "id": "task-1",
    "type": "task_completed",
    "status": "completed",
    "completion_data": {
        "pr_url": "https://github.com/org/repo/pull/1"
    }
}

TEST_PR_DATA = {
    "id": "pr-1",
    "type": "pr_created",
    "title": "Implement feature",
    "description": "Added new feature",
    "files": ["src/components/Feature.tsx", "src/api/feature.py"],
    "labels": {"performance": True}
}

TEST_DESIGN_DATA = {
    "id": "design-1",
    "type": "design_completed",
    "design_url": "https://figma.com/design/1",
    "specs": "Design specifications",
    "components": [
        {
            "id": "comp-1",
            "name": "FeatureComponent",
            "specs": "Component specifications"
        }
    ]
}

@pytest.fixture
def mock_github_service() -> AsyncMock:
    """Create mock GitHub service for testing."""
    mock = AsyncMock(spec=GitHubService)
    mock.update_pr = AsyncMock(return_value={"id": "pr-1"})
    return mock

@pytest.fixture
def mock_event_system() -> AsyncMock:
    """Create mock event system for testing."""
    mock = AsyncMock(spec=EventSystem)
    mock.publish = AsyncMock()
    return mock

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create mock logger for testing."""
    mock = Mock(spec=BaseLogger)
    mock.error = Mock()
    mock.info = Mock()
    mock.debug = Mock()
    mock.warning = Mock()
    return mock

@pytest.fixture
async def project_manager(
    mock_github_service: AsyncMock,
    mock_event_system: AsyncMock,
    mock_base_logger: Mock
) -> ProjectManagerAgent:
    """Create project manager instance for testing."""
    pm = ProjectManagerAgent(
        github_service=mock_github_service,
        event_system=mock_event_system,
        start_listening=False
    )
    pm.logger = mock_base_logger
    return pm

class TestProjectManagerAgent:
    """Tests for the ProjectManagerAgent class."""
    
    @pytest.mark.asyncio
    async def test_handle_story_created(
        self,
        project_manager: ProjectManagerAgent,
        mock_event_system: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling story creation."""
        # Execute
        result = await project_manager.handle_story_created(TEST_STORY_DATA)
        
        # Verify tasks created
        assert len(result["tasks"]) == 3  # Design, Development, Testing
        assert result["tasks"][0]["type"] == "design"
        assert result["tasks"][1]["type"] == "development"
        assert result["tasks"][2]["type"] == "testing"
        
        # Verify dependencies
        assert result["dependencies"][result["tasks"][1]["id"]] == [result["tasks"][0]["id"]]
        assert result["dependencies"][result["tasks"][2]["id"]] == [result["tasks"][1]["id"]]
        
        # Verify assignments
        assert result["assignments"][result["tasks"][0]["id"]] == "ux_designer"
        assert result["assignments"][result["tasks"][1]["id"]] == "developer"
        assert result["assignments"][result["tasks"][2]["id"]] == "qa_tester"
        
        # Verify event published
        mock_event_system.publish.assert_called_once()
        event = mock_event_system.publish.call_args[0][1]
        assert event["type"] == "story_updated"
        assert event["payload"] == result
    
    @pytest.mark.asyncio
    async def test_handle_task_completed(
        self,
        project_manager: ProjectManagerAgent,
        mock_event_system: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling task completion."""
        # Execute
        result = await project_manager.handle_task_completed(TEST_TASK_DATA)
        
        # Verify result
        assert result["status"] == "success"
        assert result["task"]["status"] == "completed"
        
        # Verify event published
        mock_event_system.publish.assert_called_once()
        event = mock_event_system.publish.call_args[0][1]
        assert event["type"] == "task_completed"
        assert event["payload"]["task"] == result["task"]
    
    @pytest.mark.asyncio
    async def test_handle_pr_created(
        self,
        project_manager: ProjectManagerAgent,
        mock_github_service: AsyncMock,
        mock_event_system: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling PR creation."""
        # Execute
        result = await project_manager.handle_pr_created(TEST_PR_DATA)
        
        # Verify reviewers assigned
        assert "qa_tester" in result["reviewers"]
        assert "ux_designer" in result["reviewers"]  # Due to UI file changes
        
        # Verify PR updated
        mock_github_service.update_pr.assert_called_once_with(
            TEST_PR_DATA["id"],
            {"reviewers": result["reviewers"]}
        )
        
        # Verify event published
        mock_event_system.publish.assert_called_once()
        event = mock_event_system.publish.call_args[0][1]
        assert event["type"] == "pr_assigned"
        assert event["payload"]["pr"] == result["pr"]
        assert event["payload"]["reviewers"] == result["reviewers"]
    
    @pytest.mark.asyncio
    async def test_handle_design_completed(
        self,
        project_manager: ProjectManagerAgent,
        mock_event_system: AsyncMock,
        mock_base_logger: Mock
    ) -> None:
        """Test handling design completion."""
        # Execute
        result = await project_manager.handle_design_completed(TEST_DESIGN_DATA)
        
        # Verify implementation tasks created
        assert len(result["tasks"]) == 1
        task = result["tasks"][0]
        assert task["type"] == "development"
        assert task["title"] == "Implement FeatureComponent"
        
        # Verify assignments
        assert result["assignments"][task["id"]] == "developer"
        
        # Verify event published
        mock_event_system.publish.assert_called_once()
        event = mock_event_system.publish.call_args[0][1]
        assert event["type"] == "design_implementation_tasks_created"
        assert event["payload"]["tasks"] == result["tasks"]
        assert event["payload"]["assignments"] == result["assignments"] 
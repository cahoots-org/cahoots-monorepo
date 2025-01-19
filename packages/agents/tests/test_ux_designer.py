"""Tests for the UXDesignerAgent class."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List
import asyncio

from agent_ux.agent import UXDesignerAgent
from agent_ux.design_system import DesignSystem
from agent_ux.accessibility import AccessibilityChecker
from agent_ux.pattern_library import PatternLibrary
from core.services.github_service import GitHubService
from core.models.team_config import TeamConfig, ServiceRole, RoleConfig

@pytest.fixture
def mock_design_system() -> Mock:
    """Create a mock design system."""
    mock = Mock(spec=DesignSystem)
    mock.apply = AsyncMock()
    mock.version = "1.0"
    return mock

@pytest.fixture
def mock_accessibility_checker() -> Mock:
    """Create a mock accessibility checker."""
    mock = Mock(spec=AccessibilityChecker)
    mock.validate = AsyncMock()
    return mock

@pytest.fixture
def mock_pattern_library() -> Mock:
    """Create a mock pattern library."""
    mock = Mock(spec=PatternLibrary)
    mock.select_patterns = AsyncMock()
    return mock

@pytest.fixture
def mock_github_service() -> Mock:
    """Create a mock GitHub service."""
    mock = Mock(spec=GitHubService)
    mock.create_issue = AsyncMock()
    mock.update_issue = AsyncMock()
    mock.get_issue = AsyncMock()
    mock.create_comment = AsyncMock()
    return mock

@pytest.fixture
def mock_event_system() -> AsyncMock:
    """Create a mock event system."""
    mock = AsyncMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    return mock

@pytest.fixture
def mock_task() -> Dict[str, Any]:
    """Create a mock design task."""
    return {
        "id": "task-1",
        "title": "Test Design Task",
        "description": "Create a test design",
        "type": "design",
        "metadata": {
            "priority": "high",
            "components": ["navigation", "forms"]
        }
    }

@pytest.fixture
async def designer(
    mock_event_system: AsyncMock,
    mock_github_service: Mock,
    mock_design_system: Mock,
    mock_accessibility_checker: Mock,
    mock_pattern_library: Mock,
    monkeypatch: pytest.MonkeyPatch
) -> UXDesignerAgent:
    """Create a UXDesignerAgent instance with mocked dependencies."""
    # Mock environment variables
    monkeypatch.setenv("DESIGNER_ID", "test-designer")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Create designer with mocked dependencies
    designer = UXDesignerAgent(
        designer_id="test-designer",
        start_listening=False,
        event_system=mock_event_system,
        github_service=mock_github_service,
        github_config={
            'design_system': {
                'version': '1.0',
                'model': 'gpt-4-1106-preview'
            }
        }
    )
    
    # Set mocked components
    designer.design_system = mock_design_system
    designer.accessibility_checker = mock_accessibility_checker
    designer.pattern_library = mock_pattern_library
    
    await designer.start()
    return designer

@pytest.mark.asyncio
async def test_setup_events(designer: UXDesignerAgent, mock_event_system: AsyncMock) -> None:
    """Test event system setup."""
    await designer.setup_events()
    mock_event_system.subscribe.assert_awaited()

@pytest.mark.asyncio
async def test_handle_story_assigned(
    designer: UXDesignerAgent,
    mock_event_system: AsyncMock,
    mock_design_system: Mock,
    mock_pattern_library: Mock
) -> None:
    """Test handling of story assignment."""
    story_data = {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test description",
        "assigned_to": "test-designer"
    }
    
    # Mock responses
    mock_design_specs = {"specs": "test specs"}
    mock_mockups = {"mockups": "test mockups"}
    
    # Configure mocks
    designer.create_design_specs = Mock(return_value=mock_design_specs)
    designer.create_mockups = AsyncMock(return_value=mock_mockups)
    
    result = await designer.handle_story_assigned(story_data)
    
    assert result["status"] == "success"
    assert result["data"]["design_specs"] == mock_design_specs
    assert result["data"]["mockups"] == mock_mockups
    
    mock_event_system.publish.assert_awaited_once_with(
        "design_completed",
        {
            "story_id": story_data["story_id"],
            "designer_id": designer.designer_id,
            "design_specs": mock_design_specs,
            "mockups": mock_mockups
        }
    )

@pytest.mark.asyncio
async def test_handle_design_request(
    designer: UXDesignerAgent,
    mock_event_system: AsyncMock,
    mock_task: Dict[str, Any]
) -> None:
    """Test handling of design request."""
    request_data = {
        "story_id": "story-1",
        "tasks": [mock_task],
        "designer_id": "test-designer"
    }
    
    # Mock responses
    mock_design_specs = {"specs": "test specs"}
    mock_mockups = {"mockups": "test mockups"}
    
    # Configure mocks
    designer.create_design_specs = Mock(return_value=mock_design_specs)
    designer.create_mockups = AsyncMock(return_value=mock_mockups)
    
    result = await designer.handle_design_request(request_data)
    
    assert result["status"] == "success"
    assert "design_specs" in result["data"]
    assert "mockups" in result["data"]
    
    mock_event_system.publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_accessibility_audit(
    designer: UXDesignerAgent,
    mock_accessibility_checker: Mock
) -> None:
    """Test handling of accessibility audit."""
    audit_data = {
        "story_id": "story-1",
        "audit_results": {
            "violations": [
                {"id": "color-contrast", "impact": "serious"}
            ]
        }
    }
    
    # Mock responses
    mock_analysis = {"issues": [{"type": "color-contrast"}]}
    mock_remediation = {"fixes": ["update color scheme"]}
    mock_updated_specs = {"updated": "specs"}
    
    # Configure mocks
    designer._analyze_audit_results = AsyncMock(return_value=mock_analysis)
    designer._generate_remediation_plan = AsyncMock(return_value=mock_remediation)
    designer._update_design_specs = AsyncMock(return_value=mock_updated_specs)
    
    result = await designer.handle_accessibility_audit(audit_data)
    
    assert result["status"] == "remediation_required"
    assert "analysis" in result["data"]
    assert "remediation_plan" in result["data"]
    assert "updated_specs" in result["data"] 
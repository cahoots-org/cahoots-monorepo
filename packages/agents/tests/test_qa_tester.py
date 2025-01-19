"""Tests for the QATesterAgent class."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List
import asyncio

from agent_qa.agent import QATesterAgent
from core.services.github_service import GitHubService
from core.models.team_config import TeamConfig, ServiceRole, RoleConfig

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
    """Create a mock test task."""
    return {
        "id": "task-1",
        "title": "Test Task",
        "description": "Run tests for feature",
        "type": "test",
        "priority": "high",
        "metadata": {
            "components": ["api", "database"],
            "requirements": ["performance", "security"]
        }
    }

@pytest.fixture
def mock_pr_data() -> Dict[str, Any]:
    """Create mock PR data."""
    return {
        "id": "pr-1",
        "title": "Feature Implementation",
        "files": ["src/core/api.py", "src/models/user.py"],
        "labels": {"performance": True}
    }

@pytest.fixture
def mock_design_data() -> Dict[str, Any]:
    """Create mock design data."""
    return {
        "id": "design-1",
        "title": "UI Component",
        "components": ["navigation", "forms"],
        "urls": ["http://localhost:3000/nav", "http://localhost:3000/form"]
    }

@pytest.fixture
async def tester(
    mock_event_system: AsyncMock,
    mock_github_service: Mock,
    monkeypatch: pytest.MonkeyPatch
) -> QATesterAgent:
    """Create a QATesterAgent instance with mocked dependencies."""
    # Mock environment variables
    monkeypatch.setenv("TESTER_ID", "test-tester")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    # Create tester with mocked dependencies
    tester = QATesterAgent(
        tester_id="test-tester",
        start_listening=False,
        event_system=mock_event_system,
        github_service=mock_github_service
    )
    
    await tester.start()
    return tester

@pytest.mark.asyncio
async def test_setup_events(tester: QATesterAgent, mock_event_system: AsyncMock) -> None:
    """Test event system setup."""
    await tester.setup_events()
    mock_event_system.subscribe.assert_awaited()

@pytest.mark.asyncio
async def test_handle_task(
    tester: QATesterAgent,
    mock_task: Dict[str, Any]
) -> None:
    """Test handling of test task."""
    # Mock test plan and results
    test_plan = {
        "strategies": ["unit", "integration"],
        "requirements": ["performance", "security"],
        "priority": "high"
    }
    test_results = {
        "unit": {"passed": True, "coverage": 85},
        "integration": {"passed": True, "coverage": 90}
    }
    
    # Configure mocks
    tester._create_test_plan = Mock(return_value=test_plan)
    tester._execute_tests = AsyncMock(return_value=test_results)
    tester._generate_coverage_report = Mock(return_value={"total_coverage": 87.5})
    
    result = await tester.handle_task(mock_task)
    
    assert result["test_results"] == test_results
    assert "test_coverage_report" in result
    tester._create_test_plan.assert_called_once_with(mock_task)
    tester._execute_tests.assert_awaited_once_with(test_plan)

@pytest.mark.asyncio
async def test_handle_code_review(
    tester: QATesterAgent,
    mock_pr_data: Dict[str, Any]
) -> None:
    """Test handling of code review."""
    # Mock test scope and results
    test_scope = ["unit", "integration", "performance"]
    test_results = {
        "unit": {"passed": True},
        "integration": {"passed": True},
        "performance": {"passed": False, "issues": ["slow database query"]}
    }
    
    # Configure mocks
    tester._determine_test_scope = Mock(return_value=test_scope)
    tester._run_test_suite = AsyncMock(return_value={"passed": True})
    tester._create_bug_report = Mock(return_value={"issues": []})
    
    result = await tester.handle_code_review(mock_pr_data)
    
    assert "test_results" in result
    assert "bug_report" in result
    tester._determine_test_scope.assert_called_once_with(mock_pr_data)

@pytest.mark.asyncio
async def test_handle_design(
    tester: QATesterAgent,
    mock_design_data: Dict[str, Any]
) -> None:
    """Test handling of design testing."""
    # Mock test plan and results
    test_plan = {
        "type": "accessibility",
        "standards": ["WCAG 2.1"],
        "components": ["navigation", "forms"]
    }
    test_results = {
        "passed": False,
        "violations": [
            {"id": "color-contrast", "impact": "serious"}
        ]
    }
    
    # Configure mocks
    tester._create_accessibility_test_plan = Mock(return_value=test_plan)
    tester._execute_accessibility_tests = AsyncMock(return_value=test_results)
    tester._create_accessibility_report = Mock(return_value={"issues": []})
    
    result = await tester.handle_design(mock_design_data)
    
    assert "test_results" in result
    assert "bug_report" in result
    tester._create_accessibility_test_plan.assert_called_once_with(mock_design_data)
    tester._execute_accessibility_tests.assert_awaited_once_with(test_plan)

@pytest.mark.asyncio
async def test_handle_test_results(tester: QATesterAgent) -> None:
    """Test handling of test results."""
    test_data = {
        "results": {
            "unit": {"passed": True, "coverage": 85},
            "integration": {"passed": True, "coverage": 90}
        }
    }
    
    # Configure mocks
    tester._analyze_test_results = Mock(return_value={"analysis": "data"})
    tester._generate_reports = Mock(return_value={"reports": "data"})
    
    result = await tester.handle_test_results(test_data)
    
    assert "test_results" in result
    assert "test_coverage_report" in result
    tester._analyze_test_results.assert_called_once()
    tester._generate_reports.assert_called_once()

def test_determine_test_scope(tester: QATesterAgent, mock_pr_data: Dict[str, Any]) -> None:
    """Test determining test scope from PR data."""
    scope = tester._determine_test_scope(mock_pr_data)
    
    assert "unit" in scope  # Always included
    assert "integration" in scope  # Multiple files changed
    assert "performance" in scope  # Performance label present
    assert len(scope) == 3 
"""Tests for the Tester class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict, List

from src.agents.tester import Tester
from src.services.github_service import GitHubService
from src.models.project import Project
from src.models.story import Story
from src.models.task import Task

@pytest.fixture
def tester(
    mock_event_system_singleton: AsyncMock,
    mock_base_logger: Mock,
    mock_model: Mock,
    mock_github_service: Mock
) -> Tester:
    """Create a Tester instance with mocked dependencies."""
    tester = Tester(event_system=mock_event_system_singleton)
    tester.logger = mock_base_logger
    tester.event_system = mock_event_system_singleton
    tester.model = mock_model
    tester.github_service = mock_github_service
    tester._running = False
    return tester

@pytest.fixture
def mock_github_service(mocker: "MockerFixture") -> Mock:
    """Mock the GitHub service."""
    mock = Mock()
    mock.create_issue = AsyncMock()
    mock.update_issue = AsyncMock()
    mock.get_issue = AsyncMock()
    mock.create_comment = AsyncMock()
    mocker.patch("src.agents.tester.GitHubService", return_value=mock)
    return mock

@pytest.fixture
def mock_story() -> Story:
    """Create a mock story."""
    return Story(
        id="story-1",
        title="Test Story",
        description="Test story description",
        assigned_to=None,
        status="todo"
    )

@pytest.fixture
def mock_project(mock_story: Story) -> Project:
    """Create a mock project."""
    return Project(
        id="project-1",
        name="Test Project",
        description="Test project description",
        stories=[mock_story],
        status="In Progress"
    )

async def test_init_success(tester: Tester, mock_base_logger: Mock) -> None:
    """Test successful Tester initialization."""
    assert tester.model_name == "gpt-4"
    assert tester.logger == mock_base_logger
    assert mock_base_logger.debug.call_count >= 2
    assert mock_base_logger.info.call_count >= 1

async def test_init_failure_missing_env(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test initialization failure when environment variable is missing."""
    mocker.patch.dict(os.environ, {}, clear=True)
    
    with pytest.raises(RuntimeError) as exc_info:
        Tester()
    
    assert "TESTER_ID environment variable is required" in str(exc_info.value)

async def test_setup_events(
    tester: Tester,
    mock_event_system: Mock
) -> None:
    """Test event system setup."""
    await tester.setup_events()
    
    mock_event_system.connect.assert_called_once()
    assert mock_event_system.subscribe.call_count == 2
    
    subscribed_channels = [call.args[0] for call in mock_event_system.subscribe.call_args_list]
    assert "system" in subscribed_channels
    assert "story_assigned" in subscribed_channels

async def test_handle_story_assigned_success(
    tester: Tester,
    mock_event_system: Mock
) -> None:
    """Test successful story assignment handling."""
    data = {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test description",
        "assigned_to": "test_tester"
    }
    
    await tester.handle_story_assigned(data)
    
    mock_event_system.publish.assert_called_once()
    publish_args = mock_event_system.publish.call_args[0]
    assert publish_args[0] == "tests_completed"
    assert publish_args[1]["story_id"] == "story-1"
    assert publish_args[1]["tester_id"] == "test_tester"
    assert "test_suite" in publish_args[1]
    assert "results" in publish_args[1]

async def test_handle_story_assigned_wrong_tester(
    tester: Tester,
    mock_event_system: Mock
) -> None:
    """Test story assignment handling when assigned to different tester."""
    data = {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test description",
        "assigned_to": "other_tester"
    }
    
    await tester.handle_story_assigned(data)
    mock_event_system.publish.assert_not_called()

async def test_handle_story_assigned_missing_fields(
    tester: Tester,
    mock_event_system: Mock
) -> None:
    """Test story assignment handling with missing fields."""
    data = {
        "story_id": "story-1",
        "title": "Test Story"
    }
    
    await tester.handle_story_assigned(data)
    mock_event_system.publish.assert_not_called()

async def test_handle_test_request(
    tester: Tester,
    mock_project: Project
) -> None:
    """Test test request handling."""
    message = {
        "type": "test_request",
        "project": mock_project.dict()
    }
    
    result = await tester._handle_message(message)
    
    assert result["status"] == "success"
    assert "passed" in result
    assert "coverage" in result
    assert "report" in result

async def test_handle_unknown_message_type(
    tester: Tester
) -> None:
    """Test handling of unknown message type."""
    message = {
        "type": "unknown_type",
        "data": "test"
    }
    
    with pytest.raises(ValueError) as exc_info:
        await tester._handle_message(message)
    
    assert "Unknown message type: unknown_type" in str(exc_info.value)

def test_create_test_suite(
    tester: Tester
) -> None:
    """Test test suite creation."""
    test_suite = tester.create_test_suite(
        story_id="story-1",
        title="Test Story",
        description="Test description"
    )
    
    assert isinstance(test_suite, TestSuite)
    assert test_suite.title == "Test Suite for Test Story"
    assert len(test_suite.test_cases) == 2
    
    # Verify first test case
    test_case = test_suite.test_cases[0]
    assert test_case.title == "Test Login"
    assert test_case.description == "Verify user login functionality"
    assert len(test_case.steps) == 2
    assert test_case.expected_result == "User should be logged in successfully"
    
    # Verify second test case
    test_case = test_suite.test_cases[1]
    assert test_case.title == "Test Invalid Login"
    assert test_case.description == "Verify invalid login handling"
    assert len(test_case.steps) == 2
    assert test_case.expected_result == "Error message should be displayed"

def test_run_test_suite(
    tester: Tester
) -> None:
    """Test running a test suite."""
    test_suite = tester.create_test_suite(
        story_id="story-1",
        title="Test Story",
        description="Test description"
    )
    
    # Mock test execution response
    tester.generate_response = Mock(return_value="PASS: Test executed successfully")
    
    results = tester.run_test_suite(test_suite)
    
    assert results["total_tests"] == 2
    assert results["passed_tests"] == 2
    assert results["failed_tests"] == 0
    assert results["coverage"] == "100.0%"
    assert len(results["test_cases"]) == 2
    
    # Verify test case results
    for test_case_id, test_result in results["test_cases"].items():
        assert test_result["status"] == "PASSED"
        assert test_result["actual_result"] == "PASS: Test executed successfully"

def test_run_test_suite_with_failures(
    tester: Tester
) -> None:
    """Test running a test suite with failures."""
    test_suite = tester.create_test_suite(
        story_id="story-1",
        title="Test Story",
        description="Test description"
    )
    
    # Mock test execution response to alternate between pass and fail
    responses = ["PASS: Test executed successfully", "FAIL: Test failed"]
    tester.generate_response = Mock(side_effect=responses)
    
    results = tester.run_test_suite(test_suite)
    
    assert results["total_tests"] == 2
    assert results["passed_tests"] == 1
    assert results["failed_tests"] == 1
    assert results["coverage"] == "50.0%"
    
    # Verify test case results
    test_cases = list(results["test_cases"].values())
    assert test_cases[0]["status"] == "PASSED"
    assert test_cases[1]["status"] == "FAILED"

async def test_generate_test_suite(
    tester: Tester,
    mock_project: Project,
    mock_event_system: Mock
) -> None:
    """Test test suite generation for a project.
    
    Verifies:
    1. Test suite structure
    2. Test case content and quality
    3. Coverage of project requirements
    4. Error handling
    """
    # Test normal case
    test_suite = tester.generate_test_suite(mock_project)
    
    # Verify structure
    assert len(test_suite) == 1
    assert "story-1" in test_suite
    assert test_suite["story-1"]["story"] == mock_project.stories[0].to_dict()
    assert test_suite["story-1"]["test_cases"] is not None
    
    # Verify test case content
    test_cases = test_suite["story-1"]["test_cases"]
    assert len(test_cases) > 0
    for test_case in test_cases:
        assert isinstance(test_case, TestCase)
        assert test_case.id is not None
        assert len(test_case.title) > 0
        assert len(test_case.description) > 0
        assert len(test_case.steps) > 0
        assert len(test_case.expected_result) > 0
        assert test_case.status == "NOT_RUN"
        
    # Verify test coverage
    test_titles = {tc.title for tc in test_cases}
    assert any("positive" in t.lower() for t in test_titles), "Missing positive test cases"
    assert any("negative" in t.lower() for t in test_titles), "Missing negative test cases"
    assert any("edge" in t.lower() for t in test_titles), "Missing edge case tests"
    
    # Test error handling
    with pytest.raises(ValueError):
        tester.generate_test_suite(None)
        
    empty_project = Project(
        id="empty",
        name="Empty Project",
        description="Empty project for testing",
        stories=[],
        status="In Progress"
    )
    empty_suite = tester.generate_test_suite(empty_project)
    assert len(empty_suite) == 0 
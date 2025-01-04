"""Tests for Tester agent."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.agents.tester import Tester
from src.models.test_suite import TestSuite, TestCase, TestResult
from src.services.test_runner import TestRunner
from src.services.test_suite_generator import TestSuiteGenerator

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    return AsyncMock()

@pytest.fixture
def mock_model():
    """Create mock model."""
    return AsyncMock()

@pytest.fixture
async def tester(mock_event_system, mock_model):
    """Create Tester instance."""
    # Create tester with start_listening=False to prevent automatic task creation
    tester = Tester(event_system=mock_event_system, start_listening=False)
    tester.model = mock_model
    tester.test_suite_generator = Mock(spec=TestSuiteGenerator)
    tester.test_runner = Mock(spec=TestRunner)
    tester._running = False
    
    yield tester
    
    # Cleanup
    await tester.stop()

@pytest.mark.asyncio
async def test_handle_story_assigned_success(tester: Tester) -> None:
    """Test successful story assignment handling."""
    story_data = {
        "type": "story_assigned",
        "story_id": "test123",
        "title": "Test Story",
        "description": "Test description",
        "requirements": ["req1", "req2"]
    }

    # Mock test suite generator
    test_suite = TestSuite(
        story_id="test123",
        title="Test Suite for Test Story",
        description="Test suite for story",
        test_cases=[
            TestCase(
                title="Test Case 1",
                description="First test case",
                steps=["Step 1", "Step 2"],
                expected_result="Expected result"
            )
        ]
    )
    tester.test_suite_generator.generate_test_suite = AsyncMock(return_value=test_suite)

    # Mock test runner
    test_result = TestResult(
        test_case=test_suite.test_cases[0],
        passed=True,
        details="Test passed successfully",
        execution_time=1.0,
        timestamp=datetime.now()
    )
    tester.test_runner.run_test_suite = AsyncMock(return_value=[test_result])

    # Handle story assignment
    result = await tester.handle_story_assigned(story_data)

    # Verify test suite was generated and run
    assert result["status"] == "success"
    tester.test_suite_generator.generate_test_suite.assert_called_once()
    tester.test_runner.run_test_suite.assert_called_once()

@pytest.mark.asyncio
async def test_handle_story_assigned_failure(tester: Tester) -> None:
    """Test story assignment handling with failure."""
    story_data = {
        "type": "story_assigned",
        "story_id": "test123",
        "title": "Test Story",
        "description": "Test description",
        "requirements": ["req1", "req2"]
    }

    # Mock test suite generator to raise error
    tester.test_suite_generator.generate_test_suite = AsyncMock(
        side_effect=Exception("Failed to generate test suite")
    )

    # Handle story assignment
    result = await tester.handle_story_assigned(story_data)

    # Verify error handling
    assert result["status"] == "error"
    assert "Failed to generate test suite" in result["message"] 
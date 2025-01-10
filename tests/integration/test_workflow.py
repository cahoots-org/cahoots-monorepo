"""Integration tests for workflow."""
import pytest
from unittest.mock import AsyncMock, patch

from src.models.qa_suite import TestSuite, TestCase, QAResult, TestStatus
from src.utils.event_system import EventSystem

@pytest.fixture
def event_system():
    """Create event system instance."""
    return EventSystem()

@pytest.fixture
def test_suite():
    """Create test suite for testing."""
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    return TestSuite(
        story_id="STORY-123",
        title="Login Test Suite",
        description="Test suite for login functionality",
        test_cases=[test_case]
    )

@pytest.mark.asyncio
async def test_workflow_success(event_system, test_suite):
    """Test successful workflow execution."""
    # Mock QA runner
    mock_runner = AsyncMock()
    qa_result = QAResult(
        test_case_title="Test Login",
        status=TestStatus.PASSED,
        actual_result="User is logged in",
        execution_time=1.23
    )
    mock_runner.run_test_suite.return_value = [qa_result]
    
    with patch('src.services.qa_runner.QARunner', return_value=mock_runner):
        # Subscribe to test results
        results = []
        async def handle_results(data):
            results.append(data)
        await event_system.subscribe("test_results_ready", handle_results)
        
        # Publish story assigned event
        await event_system.publish("story_assigned", {
            "story_id": "STORY-123",
            "title": "Test Story",
            "description": "Test description"
        })
        
        # Verify results
        assert len(results) == 1
        assert results[0]["story_id"] == "STORY-123"
        assert results[0]["test_results"]["total_tests"] == 1
        assert results[0]["test_results"]["passed_tests"] == 1 
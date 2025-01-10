"""Tests for QATester agent."""
import pytest
from unittest.mock import AsyncMock, patch
import uuid

from src.agents.qa_tester import QATester
from src.models.qa_suite import TestSuite, TestCase, QAResult, TestStatus
from src.utils.exceptions import ExternalServiceException
from src.utils.event_system import EventSystem

@pytest.fixture
def event_system():
    """Create a mock event system."""
    mock_event_system = AsyncMock(spec=EventSystem)
    return mock_event_system

@pytest.fixture
def qa_tester(event_system):
    """Create a QATester instance for testing."""
    return QATester(event_system=event_system, start_listening=False)

@pytest.fixture
def user_story():
    """Create a realistic user story for testing."""
    return {
        "story_id": "STORY-123",
        "title": "User Authentication Flow",
        "description": """
        As a user, I want to be able to:
        1. Register with email and password
        2. Verify my email
        3. Log in with my credentials
        4. Reset my password if forgotten
        
        Acceptance Criteria:
        - Password must be at least 8 characters
        - Email verification link expires in 24 hours
        - Failed login attempts are logged
        """
    }

@pytest.fixture
def test_suite():
    """Create a comprehensive test suite for testing."""
    test_cases = [
        TestCase(
            title="User Registration - Happy Path",
            description="Test successful user registration flow",
            steps=[
                "Navigate to registration page",
                "Enter valid email: test@example.com",
                "Enter valid password: SecurePass123!",
                "Click register button"
            ],
            expected_result="User account is created and verification email is sent"
        ),
        TestCase(
            title="Login - Invalid Credentials",
            description="Test login with incorrect password",
            steps=[
                "Navigate to login page",
                "Enter existing email",
                "Enter incorrect password",
                "Click login button"
            ],
            expected_result="Error message displayed and failed attempt logged"
        )
    ]
    return TestSuite(
        story_id="STORY-123",
        title="Authentication Test Suite",
        description="Comprehensive test suite for user authentication flows",
        test_cases=test_cases
    )

@pytest.mark.asyncio
async def test_story_assignment_generates_and_runs_tests(qa_tester, user_story, event_system, test_suite):
    """Test the complete flow of story assignment to test results."""
    # Setup mock responses
    mock_results = [
        QAResult(
            test_case_title="User Registration - Happy Path",
            status=TestStatus.PASSED,
            actual_result="Account created successfully",
            execution_time=1.5
        ),
        QAResult(
            test_case_title="Login - Invalid Credentials",
            status=TestStatus.PASSED,
            actual_result="Error message shown correctly",
            execution_time=0.8
        )
    ]
    
    # Mock the test generation and execution
    with patch('src.services.qa_suite_generator.QASuiteGenerator.generate_test_suite') as mock_generate, \
         patch('src.services.qa_runner.QARunner.run_test_suite') as mock_run:
        mock_generate.return_value = test_suite
        mock_run.return_value = mock_results
        
        # Test the behavior
        result = await qa_tester.handle_story_assigned(user_story)
        
        # Verify the complete flow
        assert result["status"] == "success"
        assert result["data"]["total_tests"] == 2
        assert result["data"]["passed_tests"] == 2
        assert result["data"]["coverage"] == "100.0%"
        
        # Verify test results were published
        event_system.publish.assert_called_with(
            "test_results_ready",
            {
                "story_id": "STORY-123",
                "test_results": result["data"]
            }
        )

@pytest.mark.asyncio
async def test_story_assignment_handles_test_failures(qa_tester, user_story, event_system, test_suite):
    """Test handling of test failures in the story assignment flow."""
    # Setup mock responses with a failed test
    mock_results = [
        QAResult(
            test_case_title="User Registration - Happy Path",
            status=TestStatus.FAILED,
            actual_result="Verification email not sent",
            execution_time=1.5,
            error_details={"error": "SMTP service unavailable", "service": "email"}
        )
    ]
    
    # Mock the test generation and execution
    with patch('src.services.qa_suite_generator.QASuiteGenerator.generate_test_suite') as mock_generate, \
         patch('src.services.qa_runner.QARunner.run_test_suite') as mock_run:
        mock_generate.return_value = TestSuite(
            story_id="STORY-123",
            title="Auth Tests",
            description="Auth test suite",
            test_cases=[test_suite.test_cases[0]]  # Just use the first test case
        )
        mock_run.return_value = mock_results
        
        # Test the behavior
        result = await qa_tester.handle_story_assigned(user_story)
        
        # Verify failure handling
        assert result["status"] == "success"  # The process completed successfully
        assert result["data"]["total_tests"] == 1
        assert result["data"]["passed_tests"] == 0
        assert result["data"]["failed_tests"] == 1
        assert "SMTP service unavailable" in str(result["data"]["test_cases"][0]["error_details"])

@pytest.mark.asyncio
async def test_story_assignment_handles_service_errors(qa_tester, user_story):
    """Test handling of service failures during story assignment."""
    # Mock the test generation to fail
    with patch('src.services.qa_suite_generator.QASuiteGenerator.generate_test_suite') as mock_generate:
        mock_generate.side_effect = ExternalServiceException(
            service="QASuiteGenerator",
            operation="generate_test_suite",
            error="OpenAI API unavailable"
        )
        
        # Test the behavior
        result = await qa_tester.handle_story_assigned(user_story)
        
        # Verify error handling
        assert result["status"] == "error"
        assert "OpenAI API unavailable" in result["message"]

@pytest.mark.asyncio
async def test_agent_startup_and_shutdown(event_system):
    """Test the lifecycle of the QA tester agent."""
    # Create agent without auto-start
    qa_tester = QATester(event_system=event_system, start_listening=False)
    
    # Test startup
    await qa_tester.start()
    event_system.subscribe.assert_called_with("story_assigned", qa_tester.handle_story_assigned)
    
    # Test shutdown (if implemented)
    if hasattr(qa_tester, 'shutdown'):
        await qa_tester.shutdown()
        # Verify cleanup actions 

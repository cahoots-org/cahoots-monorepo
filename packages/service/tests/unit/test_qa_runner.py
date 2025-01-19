"""Tests for QA runner service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.services.qa_runner import QARunner
from src.models.qa_suite import TestSuite, TestCase, TestStatus, QAResult
from src.utils.exceptions import ExternalServiceException
from src.core.dependencies import ServiceDeps

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.model = AsyncMock()
    deps.model.generate_response = AsyncMock()
    deps.event_system = AsyncMock()
    return deps

@pytest.fixture
def qa_runner(mock_deps):
    """Create QA runner instance with mock dependencies."""
    return QARunner(deps=mock_deps)

@pytest.fixture
def valid_test_case():
    """Create a valid test case."""
    return TestCase(
        title="Test Login Feature",
        description="Test user login functionality",
        steps=["Navigate to login page", "Enter valid credentials", "Click login button"],
        expected_result="User is logged in successfully"
    )

@pytest.fixture
def valid_test_suite(valid_test_case):
    """Create a valid test suite."""
    return TestSuite(
        story_id="story123",
        title="Login Test Suite",
        description="Test suite for login functionality",
        test_cases=[valid_test_case]
    )

@pytest.mark.asyncio
async def test_async_context_manager(qa_runner):
    """Test async context manager methods."""
    async with qa_runner as runner:
        assert runner == qa_runner
        assert await runner.check_connection()
    # Verify __aexit__ completed successfully
    assert not qa_runner.running

@pytest.mark.asyncio
async def test_check_connection(qa_runner):
    """Test connection check."""
    assert await qa_runner.check_connection() == True

@pytest.mark.asyncio
async def test_close(qa_runner):
    """Test cleanup method."""
    await qa_runner.close()
    # Verify no exceptions raised

@pytest.mark.asyncio
async def test_run_test_case_all_steps_pass(qa_runner, valid_test_case, mock_deps):
    """Test successful test case execution with all steps passing."""
    # Mock model responses for each step
    mock_responses = [
        """Status: PASS
        Actual Result: Login page loaded successfully
        Details: Page loaded in 0.5s""",
        
        """Status: PASS
        Actual Result: Credentials entered correctly
        Details: Username and password fields populated""",
        
        """Status: PASS
        Actual Result: User is logged in successfully
        Details: Redirected to dashboard"""
    ]
    
    mock_deps.model.generate_response.side_effect = mock_responses
    
    result = await qa_runner.run_test_case(valid_test_case)
    
    assert result.status == TestStatus.PASSED
    assert result.actual_result == valid_test_case.expected_result
    assert result.execution_time is not None
    assert mock_deps.model.generate_response.call_count == 3

@pytest.mark.asyncio
async def test_run_test_case_with_failure(qa_runner, valid_test_case, mock_deps):
    """Test test case execution with a failing step."""
    # Mock responses with one failing step
    mock_responses = [
        """Status: PASS
        Actual Result: Login page loaded successfully
        Details: Page loaded in 0.5s""",
        
        """Status: FAIL
        Actual Result: Invalid credentials error
        Details: Server returned 401 unauthorized""",
        
        """Status: FAIL
        Actual Result: Login button disabled
        Details: Button remains inactive"""
    ]
    
    mock_deps.model.generate_response.side_effect = mock_responses
    
    result = await qa_runner.run_test_case(valid_test_case)
    
    assert result.status == TestStatus.FAILED
    assert "Step 2: Invalid credentials error" in result.actual_result
    assert "Step 3: Login button disabled" in result.actual_result
    assert result.execution_time is not None
    assert mock_deps.model.generate_response.call_count == 3

@pytest.mark.asyncio
async def test_run_test_case_with_exception(qa_runner, valid_test_case, mock_deps):
    """Test test case execution with an exception."""
    mock_deps.model.generate_response.side_effect = Exception("Network error")
    
    result = await qa_runner.run_test_case(valid_test_case)
    
    assert result.status == TestStatus.ERROR
    assert result.actual_result == "Network error"
    assert result.error_details == {
        "type": "Exception",
        "message": "Network error"
    }
    assert result.execution_time is not None

@pytest.mark.asyncio
async def test_run_test_case_without_model(valid_test_case):
    """Test error handling when model is not provided."""
    deps = MagicMock(spec=ServiceDeps)
    deps.model = None
    deps.event_system = AsyncMock()
    runner = QARunner(deps=deps)
    
    with pytest.raises(ValueError, match="Model is required for test execution"):
        await runner.run_test_case(valid_test_case)

@pytest.mark.asyncio
async def test_run_test_case_none_input(qa_runner):
    """Test error handling with None test case."""
    with pytest.raises(ValueError, match="Test case cannot be None"):
        await qa_runner.run_test_case(None)

@pytest.mark.asyncio
async def test_parse_step_result_complete(qa_runner):
    """Test parsing complete step execution results."""
    response = """Status: PASS
    Actual Result: Login successful
    Details: Redirected to dashboard"""
    
    result = qa_runner._parse_step_result(response)
    
    assert result['status'] == 'PASS'
    assert result['actual_result'] == 'Login successful'
    assert result['details'] == 'Redirected to dashboard'

@pytest.mark.asyncio
async def test_parse_step_result_partial(qa_runner):
    """Test parsing partial step execution results."""
    response = """Status: FAIL
    Actual Result: Login failed"""
    
    result = qa_runner._parse_step_result(response)
    
    assert result['status'] == 'FAIL'
    assert result['actual_result'] == 'Login failed'
    assert result['details'] == ''  # Default value for missing field

@pytest.mark.asyncio
async def test_parse_step_result_malformed(qa_runner):
    """Test parsing malformed step execution results."""
    response = """Invalid response format"""
    
    result = qa_runner._parse_step_result(response)
    
    assert result['status'] == 'FAIL'  # Default value
    assert result['actual_result'] == ''
    assert result['details'] == ''

@pytest.mark.asyncio
async def test_run_test_suite_success(qa_runner, valid_test_suite, mock_deps):
    """Test running a complete test suite successfully."""
    # Mock successful responses for all steps
    mock_responses = [
        """Status: PASS
        Actual Result: Step completed successfully
        Details: None"""
    ] * 3  # One response for each step
    
    mock_deps.model.generate_response.side_effect = mock_responses
    
    results = await qa_runner.run_test_suite(valid_test_suite)
    
    assert len(results) == 1
    assert results[0].status == TestStatus.PASSED
    assert results[0].actual_result == valid_test_suite.test_cases[0].expected_result
    assert mock_deps.model.generate_response.call_count == 3

@pytest.mark.asyncio
async def test_run_test_suite_already_running(qa_runner, valid_test_suite):
    """Test error handling when attempting to run already running suite."""
    qa_runner.running = True
    
    with pytest.raises(ExternalServiceException) as exc_info:
        await qa_runner.run_test_suite(valid_test_suite)
    
    assert "already running" in str(exc_info.value)

@pytest.mark.asyncio
async def test_run_test_suite_with_exception(qa_runner, valid_test_suite, mock_deps):
    """Test test suite execution with an exception."""
    mock_deps.model.generate_response.side_effect = Exception("Fatal error")
    
    results = await qa_runner.run_test_suite(valid_test_suite)
    
    assert len(results) == 1
    assert results[0].status == TestStatus.ERROR
    assert not qa_runner.running  # Verify cleanup happened

@pytest.mark.asyncio
async def test_run_test_suite_empty(qa_runner):
    """Test running an empty test suite."""
    with pytest.raises(ValueError, match="Test suite must contain at least one test case"):
        empty_suite = TestSuite(
            story_id="empty123",
            title="Empty Suite",
            description="Empty test suite",
            test_cases=[]
        ) 
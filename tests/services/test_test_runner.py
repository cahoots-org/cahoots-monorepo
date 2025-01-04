"""Tests for test runner service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from src.services.test_runner import TestRunner
from src.models.test_suite import TestSuite, TestCase, TestStatus

@pytest.fixture
def test_runner():
    """Create test runner instance."""
    mock_model = AsyncMock()
    mock_model.generate_response = AsyncMock(return_value="Test passed successfully")
    mock_logger = Mock()
    return TestRunner(model=mock_model, logger=mock_logger)

@pytest.fixture
def valid_test_case():
    """Create a valid test case."""
    return TestCase(
        title="Test Feature",
        description="Test description",
        steps=["Step 1", "Step 2"],
        expected_result="Expected result"
    )

@pytest.fixture
def valid_test_suite(valid_test_case):
    """Create a valid test suite."""
    return TestSuite(
        story_id="story123",
        title="Test Suite",
        description="Test description",
        test_cases=[valid_test_case]
    )

@pytest.mark.asyncio
async def test_run_test_case_success(test_runner, valid_test_case):
    """Test successful test case execution."""
    # Mock successful execution
    test_runner.execute_test = AsyncMock(return_value=("Expected result", 1.5))
    
    result = await test_runner.run_test_case(valid_test_case)
    assert result.passed is True
    assert result.test_case.status == TestStatus.PASSED
    assert result.test_case.actual_result == "Expected result"
    assert result.test_case.execution_time == 1.5

@pytest.mark.asyncio
async def test_run_test_case_failure(test_runner, valid_test_case):
    """Test failed test case execution."""
    # Mock failed execution
    test_runner.execute_test = AsyncMock(return_value=("Unexpected result", 1.0))
    
    result = await test_runner.run_test_case(valid_test_case)
    assert result.passed is False
    assert result.test_case.status == TestStatus.FAILED
    assert result.test_case.actual_result == "Unexpected result"
    assert result.test_case.execution_time == 1.0

@pytest.mark.asyncio
async def test_run_test_case_error(test_runner, valid_test_case):
    """Test error in test case execution."""
    # Mock execution error
    error = ValueError("Test error")
    test_runner.execute_test = AsyncMock(side_effect=error)
    
    result = await test_runner.run_test_case(valid_test_case)
    assert result.passed is False
    assert result.test_case.status == TestStatus.ERROR
    assert result.test_case.error_details["type"] == "ValueError"
    assert result.test_case.error_details["message"] == "Test error"

@pytest.mark.asyncio
async def test_run_test_suite_success(test_runner, valid_test_suite):
    """Test successful test suite execution."""
    # Mock successful execution
    test_runner.execute_test = AsyncMock(return_value=("Expected result", 1.5))
    
    results = await test_runner.run_test_suite(valid_test_suite)
    assert len(results) == 1
    assert results[0].passed is True
    assert valid_test_suite.get_status() == TestStatus.PASSED

@pytest.mark.asyncio
async def test_run_test_suite_validation(test_runner):
    """Test test suite validation."""
    # Create invalid test suite
    with pytest.raises(ValueError):
        invalid_suite = TestSuite(
            story_id="",  # Invalid empty ID
            title="Invalid Suite",
            description="Invalid test suite",
            test_cases=[]  # No test cases
        )
        await test_runner.run_test_suite(invalid_suite) 
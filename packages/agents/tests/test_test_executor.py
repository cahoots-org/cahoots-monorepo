"""Unit tests for test execution functionality."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from agent_qa.execution import TestExecutor
from agent_qa.models import TestCase, TestResult, TestSuite

@pytest.fixture
async def test_executor():
    """Create a test executor instance."""
    executor = TestExecutor()
    await executor.initialize()
    yield executor
    await executor.shutdown()

@pytest.fixture
def sample_test_suite():
    """Create a sample test suite for testing."""
    test_cases = [
        TestCase(
            id="test-1",
            title="Test User API",
            description="Test user API endpoints",
            type="integration",
            priority="high",
            metadata={
                "validation_rules": ["status_code", "response_schema"],
                "expected_results": {
                    "status_code": 200,
                    "response": {"user_id": "string", "email": "string"}
                }
            }
        ),
        TestCase(
            id="test-2",
            title="Test User Model",
            description="Test user model validation",
            type="unit",
            priority="medium",
            metadata={
                "validation_rules": ["required_fields", "field_types"],
                "expected_results": {
                    "valid": True,
                    "fields": ["id", "email", "name"]
                }
            }
        )
    ]
    
    return TestSuite(
        id="suite-1",
        title="User System Tests",
        description="Test suite for user system",
        test_cases=test_cases,
        metadata={"priority": "high"}
    )

@pytest.mark.asyncio
async def test_execute_test_case(test_executor):
    """Test execution of a single test case."""
    test_case = TestCase(
        id="test-3",
        title="Test Simple Function",
        description="Test a simple function",
        type="unit",
        priority="low",
        metadata={
            "validation_rules": ["return_type"],
            "expected_results": {"value": True}
        }
    )
    
    result = await test_executor.execute_test_case(test_case)
    assert isinstance(result, TestResult)
    assert result.test_case_id == "test-3"
    assert result.status in ["passed", "failed", "error"]

@pytest.mark.asyncio
async def test_execute_test_suite(test_executor, sample_test_suite):
    """Test execution of a test suite."""
    results = await test_executor.execute_test_suite(sample_test_suite)
    assert len(results) == 2
    assert all(isinstance(r, TestResult) for r in results)
    assert all(r.test_case_id in ["test-1", "test-2"] for r in results)

@pytest.mark.asyncio
async def test_execute_parallel_tests(test_executor, sample_test_suite):
    """Test parallel execution of tests."""
    results = await test_executor.execute_parallel(sample_test_suite.test_cases)
    assert len(results) == 2
    assert all(isinstance(r, TestResult) for r in results)

@pytest.mark.asyncio
async def test_execute_with_dependencies(test_executor):
    """Test execution with dependencies."""
    test_cases = [
        TestCase(
            id="test-4",
            title="Create User",
            description="Create a new user",
            type="integration",
            priority="high",
            metadata={"validation_rules": ["user_created"]}
        ),
        TestCase(
            id="test-5",
            title="Update User",
            description="Update user details",
            type="integration",
            priority="medium",
            metadata={
                "dependencies": ["test-4"],
                "validation_rules": ["user_updated"]
            }
        )
    ]
    
    results = await test_executor.execute_with_dependencies(test_cases)
    assert len(results) == 2
    assert results[0].test_case_id == "test-4"
    assert results[1].test_case_id == "test-5"

@pytest.mark.asyncio
async def test_execute_with_retry(test_executor):
    """Test execution with retry logic."""
    test_case = TestCase(
        id="test-6",
        title="Flaky Test",
        description="Test with retry logic",
        type="integration",
        priority="medium",
        metadata={
            "max_retries": 3,
            "validation_rules": ["eventually_passes"]
        }
    )
    
    result = await test_executor.execute_with_retry(test_case)
    assert isinstance(result, TestResult)
    assert "retry_count" in result.metadata

@pytest.mark.asyncio
async def test_execute_with_timeout(test_executor):
    """Test execution with timeout."""
    test_case = TestCase(
        id="test-7",
        title="Long Running Test",
        description="Test with timeout",
        type="integration",
        priority="low",
        metadata={
            "timeout": 5.0,
            "validation_rules": ["completes_in_time"]
        }
    )
    
    result = await test_executor.execute_with_timeout(test_case)
    assert isinstance(result, TestResult)
    assert "execution_time" in result.metadata

@pytest.mark.asyncio
async def test_execute_with_cleanup(test_executor):
    """Test execution with cleanup."""
    test_case = TestCase(
        id="test-8",
        title="Resource Test",
        description="Test with resource cleanup",
        type="integration",
        priority="high",
        metadata={
            "cleanup_required": True,
            "validation_rules": ["resources_cleaned"]
        }
    )
    
    result = await test_executor.execute_with_cleanup(test_case)
    assert isinstance(result, TestResult)
    assert "cleanup_status" in result.metadata

@pytest.mark.asyncio
async def test_execute_with_mocks(test_executor):
    """Test execution with mocks."""
    test_case = TestCase(
        id="test-9",
        title="External API Test",
        description="Test with mocked dependencies",
        type="integration",
        priority="medium",
        metadata={
            "mock_config": {
                "external_api": {"return_value": {"status": "success"}},
                "database": {"side_effect": lambda x: x}
            },
            "validation_rules": ["mocks_called"]
        }
    )
    
    result = await test_executor.execute_with_mocks(test_case)
    assert isinstance(result, TestResult)
    assert "mock_calls" in result.metadata

@pytest.mark.asyncio
async def test_execute_error_handling(test_executor):
    """Test error handling during execution."""
    test_case = TestCase(
        id="test-10",
        title="Error Test",
        description="Test error handling",
        type="unit",
        priority="high",
        metadata={
            "should_fail": True,
            "validation_rules": ["handles_error"]
        }
    )
    
    result = await test_executor.execute_test_case(test_case)
    assert result.status == "error"
    assert "error_details" in result.metadata 
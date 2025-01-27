"""Tests for QA runner service."""
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from cahoots_core.models.qa_suite import (
    QASuite,
    QATest,
    QATestResult,
    QATestStatus,
    QATestType,
    QATestCase,
    TestStep,
    TestStatus
)
from cahoots_core.services.qa_runner import QARunner
from cahoots_core.utils.metrics.performance import PerformanceMetrics

@pytest.fixture
def qa_runner():
    """Create QA runner fixture."""
    metrics = Mock(spec=PerformanceMetrics)
    metrics.measure_time = Mock()
    metrics.measure_time.return_value.__aenter__ = AsyncMock()
    metrics.measure_time.return_value.__aexit__ = AsyncMock()
    metrics.increment = Mock()
    metrics.current_time = Mock(return_value=0)
    metrics.elapsed_time = Mock(return_value=1.0)
    return QARunner(metrics=metrics)

@pytest.fixture
def sample_test_case():
    """Create a sample test case."""
    return QATest(
        id=str(uuid4()),
        name="Sample Test",
        description="Sample test case",
        test_type=QATestType.API,
        steps=[
            TestStep(
                id=str(uuid4()),
                description="Test step",
                expected_result="Expected result"
            )
        ]
    )

@pytest.fixture
def sample_test_suite():
    """Create a sample test suite."""
    return QASuite(
        id=uuid4(),
        project_id="project1",
        title="Authentication Tests",
        description="Test authentication functionality",
        test_suites=[]
    )

@pytest.mark.asyncio
async def test_run_test_case(qa_runner, sample_test_case):
    """Test running a single test case."""
    qa_runner._execute_test_step = AsyncMock(return_value={
        "status": "passed",
        "actual_result": "Test passed successfully"
    })
    qa_runner._execute_step_action = AsyncMock(return_value="Test passed successfully")
    qa_runner._validate_step_result = AsyncMock(return_value=True)

    result = await qa_runner.run_test(sample_test_case, {})
    assert result.status.value == "passed"
    assert result.test_case_title == sample_test_case.name

@pytest.mark.asyncio
async def test_execute_test_step(qa_runner):
    """Test executing a test step."""
    step = TestStep(
        id="step1",
        description="Click login button",
        expected_result="Login form appears"
    )

    result = await qa_runner._execute_test_step(step, {})
    assert result["status"] == "passed"
    assert result["actual_result"] == "Login form appears"

@pytest.mark.asyncio
async def test_handle_test_failure(sample_test_case):
    """Test handling test failure."""
    sample_test_case.start_execution()
    sample_test_case.mark_error("Test failed")
    assert sample_test_case.status == TestStatus.ERROR
    assert sample_test_case.error_details["message"] == "Test failed"

@pytest.mark.asyncio
async def test_generate_test_report(qa_runner):
    """Test generating test report."""
    test_results = {
        "status": "passed",
        "test_cases": [
            {
                "id": "test1",
                "status": "passed",
                "duration": 1.5
            }
        ],
        "duration": 1.5,
        "total": 1,
        "passed": 1,
        "failed": 0
    }

    report = await qa_runner.generate_test_report(test_results)
    assert report["summary"] == "1/1 tests passed"
    assert report["duration"] == 1.5

@pytest.mark.asyncio
async def test_validate_test_results(qa_runner):
    """Test validating test results."""
    test_results = {
        "status": "passed",
        "test_cases": [
            {
                "id": "test1",
                "status": "passed",
                "steps": [
                    {
                        "id": "step1",
                        "status": "passed"
                    }
                ]
            }
        ]
    }

    validation = await qa_runner.validate_test_results(test_results)
    assert validation is True

@pytest.mark.asyncio
async def test_execute_test_plan(qa_runner):
    """Test executing a test plan."""
    # Mock the run_test method instead of _execute_test_step
    qa_runner.run_test = AsyncMock(return_value=QATestResult(
        test_case_title="Test Case 1",
        status=TestStatus.PASSED
    ))

    test_plan = {
        "test_types": ["api"],
        "coverage_targets": {"api": 80},
        "test_cases": [
            {
                "id": str(uuid4()),
                "type": "api",
                "title": "Test Case 1",
                "description": "API test case",
                "steps": [
                    {
                        "id": str(uuid4()),
                        "description": "Make API call",
                        "expected_result": "200 OK"
                    }
                ]
            }
        ]
    }

    results = await qa_runner.execute_plan(test_plan)
    assert results["executed"] == 1
    assert results["passed"] == 1
    assert results["failed"] == 0
    assert "api" in results["coverage"]

@pytest.mark.asyncio
async def test_get_run_status(qa_runner):
    """Test getting test run status."""
    run_id = "test-run-1"
    qa_runner._test_runs = {
        run_id: {
            "total": 5,
            "completed": 3,
            "status": "in_progress"
        }
    }

    status = await qa_runner.get_run_status(run_id)
    assert status["total"] == 5
    assert status["completed"] == 3

@pytest.mark.asyncio
async def test_cleanup_test_run(qa_runner):
    """Test cleaning up test run."""
    run_id = "test-run-1"
    qa_runner._test_runs = {run_id: {"status": "completed"}}

    await qa_runner._cleanup_test_run(run_id)
    assert run_id not in qa_runner._test_runs 
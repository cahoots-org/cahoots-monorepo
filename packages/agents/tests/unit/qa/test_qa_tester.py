"""Unit tests for the QA tester."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json
from uuid import uuid4

from cahoots_core.models.qa_suite import QASuite, QATestCase, TestStep
from cahoots_core.models.task import Task
from ....src.cahoots_agents.qa.qa_tester import QATester

@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = MagicMock()
    agent.provider = "test"  # This is the key property that AIProviderFactory checks
    agent.generate_response = AsyncMock()
    agent.stream_response = AsyncMock(return_value=["chunk1", "chunk2"])
    return agent

@pytest.fixture
def mock_qa_runner():
    runner = AsyncMock()
    runner.run_test = AsyncMock()
    runner.run_test_suite = AsyncMock()
    return runner

@pytest.fixture
def qa_tester(mock_agent, mock_qa_runner):
    """Create QA tester with mocked dependencies."""
    config = {
        "ai": {
            "provider": "test",
            "api_key": "test-key",
            "models": {
                "default": "test-model",
                "fallback": "test-model-fallback"
            }
        }
    }
    tester = QATester(
        event_system=MagicMock(),
        ai_provider=mock_agent,
        config=config
    )
    tester.qa_runner = mock_qa_runner
    return tester

@pytest.fixture
def sample_test_case():
    """Create sample test case."""
    return QATestCase(
        id="test1",
        title="User Authentication Test",
        description="Test user login functionality",
        steps=[
            TestStep(
                id="step1",
                description="Enter valid credentials",
                expected_result="User is logged in successfully"
            ),
            TestStep(
                id="step2",
                description="Enter invalid credentials",
                expected_result="Error message is displayed"
            )
        ],
        metadata={
            "priority": "high",
            "type": "functional"
        }
    )

@pytest.fixture
def sample_qa_suite():
    """Create sample QA suite."""
    return QASuite(
        id="suite1",
        title="Authentication Test Suite",
        description="Test user authentication features",
        test_cases=[],
        metadata={
            "priority": "high",
            "area": "security"
        }
    )

@pytest.mark.asyncio
async def test_generate_test_case_success(qa_tester):
    """Test successful test case generation."""
    expected_case = {
        "id": "test1",
        "title": "User Login Test",
        "steps": [],
        "metadata": {}
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_case)
    
    test_case = await qa_tester.generate_test_case(
        target="Test function",
        description="Test description"
    )
    assert test_case == expected_case

@pytest.mark.asyncio
async def test_generate_test_case_invalid_json(qa_tester):
    """Test handling of invalid JSON response."""
    qa_tester.ai.generate_response.return_value = "invalid json"
    
    with pytest.raises(json.JSONDecodeError):
        await qa_tester.generate_test_case(
            target="Test function",
            description="Test description"
        )

@pytest.mark.asyncio
async def test_run_test_case_success(qa_tester):
    """Test successful test case execution."""
    expected_result = {
        "status": "passed",
        "steps": [{"id": "step1", "status": "passed"}]
    }
    qa_tester.qa_runner.run_test.return_value = expected_result
    
    result = await qa_tester.run_test_case({
        "id": "test1",
        "title": "Test Case 1",
        "steps": ["Step 1"],
        "expected_result": "Pass"
    })
    
    assert result == expected_result

@pytest.mark.asyncio
async def test_run_test_case_failure(qa_tester, sample_test_case):
    """Test test case execution with failure."""
    expected_result = {
        "status": "failed",
        "steps": [
            {
                "id": "step1",
                "status": "passed",
                "actual_result": "User logged in successfully"
            },
            {
                "id": "step2",
                "status": "failed",
                "actual_result": "No error message displayed",
                "error": "Expected error message not shown"
            }
        ],
        "metadata": {}
    }
    qa_tester.qa_runner.run_test.return_value = expected_result
    
    result: Dict[str, Any] = await qa_tester.run_test_case(sample_test_case)
    
    assert result.get("status") == "failed"
    assert result.get("steps")[1].get("status") == "failed"

@pytest.mark.asyncio
async def test_generate_test_suite(qa_tester):
    """Test test suite generation."""
    tasks = [
        Task(
            id="task1",
            title="Implement user login",
            description="Add login functionality",
            metadata={}
        ),
        Task(
            id="task2",
            title="Implement password reset",
            description="Add password reset functionality",
            metadata={}
        )
    ]
    expected_suite = {
        "id": str(uuid4()),
        "title": "Authentication Test Suite",
        "description": "Test authentication features",
        "test_type": "api",
        "test_cases": [
            {
                "id": str(uuid4()),
                "title": "User Login Test",
                "description": "Test user login functionality",
                "steps": [
                    {
                        "id": str(uuid4()),
                        "description": "Enter valid credentials",
                        "expected_result": "User is logged in successfully"
                    }
                ]
            },
            {
                "id": str(uuid4()),
                "title": "Password Reset Test",
                "description": "Test password reset functionality",
                "steps": [
                    {
                        "id": str(uuid4()),
                        "description": "Request password reset",
                        "expected_result": "Password reset email sent successfully"
                    }
                ]
            }
        ]
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_suite)

    suite = await qa_tester.generate_test_suite(
        [t.model_dump() for t in tasks],
        "api"
    )
    
    # Only verify the essential fields
    assert str(suite.id) == expected_suite["id"]
    assert len(suite.test_cases) == len(expected_suite["test_cases"])

@pytest.mark.asyncio
async def test_run_test_suite(qa_tester):
    """Test running a test suite."""
    expected_result = {
        "status": "passed",
        "test_cases": [
            {"id": "test1", "status": "passed"}
        ]
    }
    qa_tester.qa_runner.run_test_suite.return_value = expected_result

    test_id = str(uuid4())
    suite = {
        "id": test_id,
        "title": "Test Suite 1",
        "description": "Test suite for testing functionality",
        "test_type": "api",
        "test_cases": [
            {
                "id": str(uuid4()),
                "title": "Test Case 1",
                "description": "Test case for testing functionality",
                "steps": [
                    {
                        "id": str(uuid4()),
                        "description": "Step 1",
                        "expected_result": "Pass"
                    }
                ]
            }
        ]
    }
    results = await qa_tester.run_test_suite(suite)
    assert results == expected_result

@pytest.mark.asyncio
async def test_analyze_test_results(qa_tester):
    """Test analyzing test results."""
    test_results = {
        "status": "failed",
        "test_results": [
            {
                "id": "test1",
                "status": "failed",
                "output": "Test failed",
                "metadata": {
                    "duration": 1.0,
                    "coverage": 60.0
                }
            }
        ],
        "metadata": {
            "total_duration": 1.0,
            "total_coverage": 60.0
        }
    }
    expected_analysis = {
        "status": "needs_fixes",
        "issues": ["Test execution failed"],
        "metrics": {
            "pass_rate": 0.0,
            "coverage": 60.0
        }
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_analysis)
    
    analysis = await qa_tester.analyze_test_results(test_results)
    assert analysis == expected_analysis

@pytest.mark.asyncio
async def test_generate_test_plan(qa_tester):
    """Test generating a test plan."""
    expected_plan = {
        "test_types": ["unit", "integration", "e2e"],
        "coverage_targets": {
            "unit": 80,
            "integration": 60,
            "e2e": 40
        },
        "priority_areas": ["auth", "data"]
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_plan)
    
    plan = await qa_tester.generate_test_plan(
        target="Authentication System",
        requirements=["Must handle OAuth", "Must support 2FA"]
    )
    assert plan == expected_plan

@pytest.mark.asyncio
async def test_execute_test_plan(qa_tester):
    """Test executing a test plan."""
    test_plan = {
        "test_types": ["unit"],
        "coverage_targets": {"unit": 80},
        "priority_areas": ["auth"]
    }
    expected_results = {
        "executed": 5,
        "passed": 4,
        "failed": 1,
        "coverage": 75.5
    }
    qa_tester.qa_runner.execute_plan.return_value = expected_results
    
    results = await qa_tester.execute_test_plan(test_plan)
    assert results == expected_results

@pytest.mark.asyncio
async def test_validate_test_coverage(qa_tester):
    """Test validating test coverage."""
    coverage_data = {
        "unit": 85.5,
        "integration": 70.2,
        "e2e": 45.8
    }
    expected_validation = {
        "meets_requirements": True,
        "gaps": [],
        "recommendations": ["Add more e2e tests"]
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_validation)
    
    validation = await qa_tester.validate_test_coverage(coverage_data)
    assert validation == expected_validation

@pytest.mark.asyncio
async def test_generate_test_report(qa_tester):
    """Test generating a test report."""
    test_results = {
        "executed": 10,
        "passed": 8,
        "failed": 2,
        "coverage": {
            "unit": 85.5,
            "integration": 70.2
        }
    }
    expected_report = {
        "summary": "8/10 tests passed",
        "coverage_analysis": "Good unit test coverage",
        "recommendations": ["Fix failing tests"]
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_report)
    
    report = await qa_tester.generate_test_report(test_results)
    assert report == expected_report

@pytest.mark.asyncio
async def test_monitor_test_execution(qa_tester):
    """Test monitoring test execution."""
    test_run = {
        "id": "test-run-1",
        "total": 5,
        "current": 2
    }
    expected_status = {
        "status": "in_progress",
        "completed": 2,
        "remaining": 3,
        "eta": "5 minutes"
    }
    qa_tester.qa_runner.get_run_status.return_value = expected_status
    
    status = await qa_tester.monitor_test_execution(test_run)
    assert status == expected_status

@pytest.mark.asyncio
async def test_analyze_test_failures(qa_tester):
    """Test analyzing test failures."""
    failures = [
        {
            "test_id": "test1",
            "error": "AssertionError",
            "stack_trace": "..."
        }
    ]
    expected_analysis = {
        "root_cause": "Data validation error",
        "suggested_fixes": ["Add input validation"],
        "priority": "high"
    }
    qa_tester.ai.generate_response.return_value = json.dumps(expected_analysis)
    
    analysis = await qa_tester.analyze_test_failures(failures)
    assert analysis == expected_analysis

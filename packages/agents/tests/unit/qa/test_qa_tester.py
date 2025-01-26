"""Unit tests for the QA tester."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json

from cahoots_core.models.qa_suite import QASuite, TestCase, TestStep
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
    return TestCase(
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
        "story_id": "story-123",
        "title": "Authentication Test Suite",
        "description": "Test authentication features",
        "test_cases": [
            {
                "id": "test1",
                "title": "User Login Test",
                "description": "Test user login functionality",
                "steps": [
                    {
                        "id": "step1",
                        "description": "Enter valid credentials",
                        "expected_result": "User is logged in successfully"
                    }
                ]
            },
            {
                "id": "test2",
                "title": "Password Reset Test",
                "description": "Test password reset functionality",
                "steps": [
                    {
                        "id": "step1",
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
        "unit"
    )
    
    # Only verify the essential fields
    assert suite.story_id == expected_suite["story_id"]
    assert suite.title == expected_suite["title"]
    assert suite.description == expected_suite["description"]
    assert len(suite.test_cases) == len(expected_suite["test_cases"])
    
    for i, test_case in enumerate(suite.test_cases):
        expected_case = expected_suite["test_cases"][i]
        assert test_case.id == expected_case["id"]
        assert test_case.title == expected_case["title"]
        assert test_case.description == expected_case["description"]
        assert len(test_case.steps) == len(expected_case["steps"])
        
        for j, step in enumerate(test_case.steps):
            expected_step = expected_case["steps"][j]
            assert step.id == expected_step["id"]
            assert step.description == expected_step["description"]
            assert step.expected_result == expected_step["expected_result"]

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
    
    suite = {
        "id": "suite1",
        "title": "Test Suite 1",
        "test_cases": [
            {
                "id": "test1",
                "title": "Test Case 1",
                "steps": ["Step 1"],
                "expected_result": "Pass"
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

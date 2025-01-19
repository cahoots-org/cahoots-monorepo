"""Unit tests for test runner implementation."""
import pytest
from unittest.mock import Mock, patch
from agent_qa.test_runner import TestRunner

@pytest.fixture
def test_config():
    """Create test configuration"""
    return {
        "frameworks": {
            "unit": ["pytest"],
            "integration": ["pytest"],
            "e2e": ["playwright"],
            "performance": ["k6"],
            "accessibility": ["axe-core"]
        }
    }

@pytest.fixture
def runner(test_config):
    """Create test runner instance"""
    return TestRunner(test_config)

@pytest.mark.asyncio
async def test_execute_tests(runner):
    """Test executing tests according to plan"""
    test_plan = {
        "strategies": ["unit", "integration"],
        "requirements": ["test_auth", "test_api"]
    }
    
    with patch("agent_qa.test_runner.UnitTestRunner") as mock_unit, \
         patch("agent_qa.test_runner.IntegrationTestRunner") as mock_int:
        
        # Configure mocks
        mock_unit.return_value.run_tests.return_value = {
            "passed": True,
            "coverage": 85
        }
        mock_int.return_value.run_tests.return_value = {
            "passed": True,
            "coverage": 75
        }
        
        results = await runner.execute_tests(test_plan)
        
        assert "unit" in results
        assert "integration" in results
        assert results["unit"]["passed"]
        assert results["integration"]["passed"]

@pytest.mark.asyncio
async def test_run_pr_tests(runner):
    """Test running tests for a PR"""
    pr_data = {
        "files": ["src/auth.py", "src/api.py"],
        "labels": {"performance": True}
    }
    test_scope = ["unit", "integration", "performance"]
    
    with patch("agent_qa.test_runner.UnitTestRunner") as mock_unit, \
         patch("agent_qa.test_runner.IntegrationTestRunner") as mock_int, \
         patch("agent_qa.test_runner.PerformanceTestRunner") as mock_perf:
        
        # Configure mocks
        mock_unit.return_value.run_tests.return_value = {"passed": True}
        mock_int.return_value.run_tests.return_value = {"passed": True}
        mock_perf.return_value.run_tests.return_value = {
            "passed": True,
            "metrics": {"load_time": "2.5s"}
        }
        
        results = await runner.run_pr_tests(test_scope, pr_data)
        
        assert all(test_type in results for test_type in test_scope)
        assert all(results[test_type]["passed"] for test_type in test_scope)
        assert "metrics" in results["performance"]

@pytest.mark.asyncio
async def test_execute_accessibility_tests(runner):
    """Test executing accessibility tests"""
    test_plan = {
        "standards": ["WCAG 2.1"],
        "checks": ["contrast", "aria"],
        "design_urls": ["http://localhost:3000"],
        "components": ["Button"]
    }
    
    with patch("agent_qa.test_runner.AccessibilityTestRunner") as mock_access:
        mock_access.return_value.run_tests.return_value = {
            "passed": True,
            "violations": []
        }
        
        results = await runner.execute_accessibility_tests(test_plan)
        
        assert results["passed"]
        assert "violations" in results
        mock_access.return_value.run_tests.assert_called_with(
            standards=test_plan["standards"],
            checks=test_plan["checks"],
            urls=test_plan["design_urls"],
            components=test_plan["components"]
        )

@pytest.mark.asyncio
async def test_run_test_strategy_error_handling(runner):
    """Test error handling in test strategy execution"""
    with patch("agent_qa.test_runner.UnitTestRunner") as mock_unit:
        mock_unit.return_value.run_tests.side_effect = Exception("Test error")
        mock_unit.return_value.framework = "pytest"
        
        result = await runner._run_test_strategy("unit", ["test_file.py"])
        
        assert result["status"] == "error"
        assert "Test error" in result["error"]
        assert result["framework"] == "pytest"

def test_invalid_test_type(runner):
    """Test handling invalid test type"""
    test_plan = {
        "strategies": ["invalid_type"],
        "requirements": []
    }
    
    with pytest.raises(KeyError):
        runner.runners["invalid_type"] 
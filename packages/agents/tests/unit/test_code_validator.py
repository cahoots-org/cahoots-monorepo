"""Unit tests for code validator."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pytest_mock import MockerFixture
from typing import Any, Dict

from packages.agent_developer.src.code_validator import CodeValidator
from src.models.task import Task

@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = Mock()
    agent.generate_response.return_value = '{"errors": []}'
    return agent

@pytest.fixture
def validator(mock_agent):
    """Create code validator instance."""
    return CodeValidator(mock_agent)

@pytest.fixture
def sample_code():
    """Sample code for testing."""
    return '''
def calculate_sum(numbers: list[int]) -> int:
    """Calculate sum of numbers.
    
    Args:
        numbers: List of numbers to sum
        
    Returns:
        int: Sum of numbers
    """
    return sum(numbers)
'''

@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return Task(
        id="test-task",
        title="Test Task",
        description="Test task description",
        requirements={"required_functions": ["calculate_sum"]}
    )

async def test_validate_implementation_success(validator, sample_code, sample_task):
    """Test successful code validation."""
    result = await validator.validate_implementation(sample_code, sample_task)
    
    assert result["valid"]
    assert not result["errors"]
    assert "metrics" in result
    assert "patterns" in result
    
    # Check metrics
    metrics = result["metrics"]
    assert metrics["loc"] > 0
    assert metrics["functions"] == 1
    assert metrics["complexity"] == 0  # No branches
    
async def test_validate_implementation_syntax_error(validator, sample_task):
    """Test validation with syntax error."""
    invalid_code = "def invalid_syntax("
    
    result = await validator.validate_implementation(invalid_code, sample_task)
    
    assert not result["valid"]
    assert len(result["errors"]) == 1
    assert "Syntax error" in result["errors"][0]
    
async def test_validate_implementation_missing_docstring(validator, sample_task):
    """Test validation with missing docstring."""
    code_without_docstring = '''
def calculate_sum(numbers: list[int]) -> int:
    return sum(numbers)
'''
    
    result = await validator.validate_implementation(code_without_docstring, sample_task)
    
    assert "warnings" in result
    assert any("docstring" in warning.lower() for warning in result["warnings"])
    
async def test_validate_implementation_missing_type_hints(validator, sample_task):
    """Test validation with missing type hints."""
    code_without_types = '''
def calculate_sum(numbers):
    """Calculate sum of numbers."""
    return sum(numbers)
'''
    
    result = await validator.validate_implementation(code_without_types, sample_task)
    
    assert "warnings" in result
    assert any("type hint" in warning.lower() for warning in result["warnings"])
    
async def test_validate_implementation_security_issue(validator, sample_task):
    """Test validation with security issue."""
    code_with_security_issue = '''
def dangerous_function():
    """Execute shell command."""
    import os
    os.system("rm -rf /")  # Dangerous!
'''
    
    result = await validator.validate_implementation(code_with_security_issue, sample_task)
    
    assert not result["valid"]
    assert any("shell" in error.lower() for error in result["errors"])
    
async def test_validate_implementation_pattern_detection(validator, sample_task):
    """Test pattern detection in validation."""
    factory_pattern = '''
class UserFactory:
    """Factory for creating users."""
    
    @classmethod
    def create(cls, user_type: str) -> 'User':
        if user_type == "admin":
            return AdminUser()
        return RegularUser()
'''
    
    result = await validator.validate_implementation(factory_pattern, sample_task)
    
    assert "patterns" in result
    assert any(p["name"] == "Factory Method" for p in result["patterns"])
    
async def test_metrics_calculation(validator, sample_code, sample_task):
    """Test code metrics calculation."""
    result = await validator.validate_implementation(sample_code, sample_task)
    
    metrics = result["metrics"]
    assert isinstance(metrics["loc"], int)
    assert isinstance(metrics["functions"], int)
    assert isinstance(metrics["classes"], int)
    assert isinstance(metrics["complexity"], int)
    assert metrics["functions"] == 1  # One function in sample code
    
async def test_llm_validation_integration(validator, sample_code, sample_task, mock_agent):
    """Test LLM validation integration."""
    mock_agent.generate_response.return_value = '{"errors": ["Potential design issue"]}'
    
    result = await validator.validate_implementation(sample_code, sample_task)
    
    assert not result["valid"]
    assert "Potential design issue" in result["errors"]
    assert mock_agent.generate_response.called
    
async def test_validation_with_requirements(validator, sample_task):
    """Test validation against task requirements."""
    code_missing_function = '''
def other_function():
    """Some other function."""
    pass
'''
    
    result = await validator.validate_implementation(code_missing_function, sample_task)
    
    assert not result["valid"]
    assert any("required function" in error.lower() for error in result["errors"]) 
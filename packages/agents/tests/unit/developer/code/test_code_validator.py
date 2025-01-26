"""Unit tests for code validator."""
from typing import Any, Dict
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
import ast
from unittest.mock import MagicMock

from cahoots_core.models.task import Task
from cahoots_core.utils.metrics.base import MetricsCollector
from .....src.cahoots_agents.developer.code.code_validator import CodeValidator

@pytest.fixture
def mock_agent():
    """Create mock developer agent."""
    agent = Mock()
    agent.generate_response = AsyncMock()
    return agent

@pytest.fixture
def mock_metrics_collector():
    """Create mock metrics collector."""
    collector = MagicMock()
    collector.record_counter = MagicMock()
    collector.record_gauge = MagicMock()
    collector.record_histogram = MagicMock()
    return collector

@pytest.fixture
def code_validator(mock_agent, mock_metrics_collector):
    """Create code validator with mocked agent."""
    validator = CodeValidator(mock_agent)
    validator.metrics_collector = mock_metrics_collector
    return validator

@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id="task123",
        title="Implement user authentication",
        description="Add user authentication using JWT tokens",
        metadata={}
    )

@pytest.fixture
def valid_code():
    """Create sample valid code."""
    return """
def authenticate_user(username: str, password: str) -> bool:
    \"\"\"Authenticate a user with username and password.\"\"\"
    if not username or not password:
        return False
    # Authentication logic here
    return True
"""

@pytest.fixture
def invalid_code():
    """Create sample invalid code."""
    return """
def authenticate_user(
    # Missing closing parenthesis
"""

@pytest.fixture
def complex_code():
    """Return complex code sample for testing."""
    return """
def calculate_fibonacci(n: int) -> list[int]:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []
    if n == 1:
        return [0]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

class DataProcessor:
    def __init__(self, data: list):
        self.data = data
        self.processed = False
        
    def process(self) -> dict:
        result = {}
        for item in self.data:
            if isinstance(item, (int, float)):
                result[str(item)] = item * 2
            elif isinstance(item, str):
                result[item] = len(item)
        self.processed = True
        return result
        
    @property
    def is_processed(self) -> bool:
        return self.processed
"""

@pytest.mark.asyncio
async def test_validate_implementation_success(code_validator, sample_task, valid_code):
    """Test successful code validation."""
    code_validator.agent.generate_response.return_value = json.dumps({
        "errors": [],
        "valid": True
    })
    
    results = await code_validator.validate_implementation(valid_code, sample_task)
    
    assert results.get("valid") is True
    assert len(results.get("errors", [])) == 0
    assert "metrics" in results
    code_validator.metrics_collector.record_counter.assert_called_with(
        "validation_warnings",
        len(results.get("warnings", []))
    )

@pytest.mark.asyncio
async def test_validate_implementation_syntax_error(code_validator, sample_task, invalid_code):
    """Test validation with syntax error."""
    code_validator.agent.generate_response.return_value = json.dumps({
        "errors": ["Syntax error: '(' was never closed (<unknown>, line 2)"],
        "valid": False
    })

    results = await code_validator.validate_implementation(invalid_code, sample_task)
    assert results.get("valid") is False
    assert any("Syntax error" in error for error in results.get("errors", []))

@pytest.mark.asyncio
async def test_validate_implementation_llm_errors(code_validator, sample_task, valid_code):
    """Test validation with LLM-reported errors."""
    code_validator.agent.generate_response.return_value = json.dumps({
        "errors": ["Missing error handling", "Insufficient input validation"]
    })
    
    results = await code_validator.validate_implementation(valid_code, sample_task)
    
    assert results.get("valid") is False
    assert len(results.get("errors")) == 2
    assert "Missing error handling" in results.get("errors")

@pytest.mark.asyncio
async def test_validate_implementation_llm_invalid_response(code_validator, sample_task, valid_code):
    """Test validation with invalid LLM response."""
    code_validator.agent.generate_response.return_value = "invalid json"
    
    results = await code_validator.validate_implementation(valid_code, sample_task)
    
    assert results.get("valid") is False
    assert "Failed to parse validation response" in results.get("errors")

def test_calculate_metrics(code_validator, valid_code):
    """Test code metrics calculation."""
    metrics = code_validator._calculate_metrics(valid_code)
    
    assert metrics.get("functions") == 1
    assert metrics.get("classes") == 0
    assert metrics.get("loc") > 0
    assert metrics.get("complexity") >= 1  # Due to if statement

def test_calculate_metrics_complex_code(code_validator, complex_code):
    """Test metrics calculation with complex code."""
    complex_code = """
class UserAuth:
    def __init__(self, db):
        self.db = db
        
    def authenticate(self, username: str, password: str) -> bool:
        if not username or not password:
            return False
        user = self.db.get_user(username)
        if not user:
            return False
        while retry_count < 3:
            if self.check_password(user, password):
                return True
            retry_count += 1
        return False
"""
    
    metrics = code_validator._calculate_metrics(complex_code)
    
    assert metrics.get("classes") == 1
    assert metrics.get("functions") == 2  # __init__ and authenticate
    assert metrics.get("complexity") > 2  # Multiple branches

def test_automated_validation_metrics(code_validator, valid_code, sample_task):
    """Test automated validation metrics collection."""
    results = code_validator._run_automated_validation(valid_code, sample_task)
    
    assert "metrics" in results
    assert "loc" in results.get("metrics")
    assert "complexity" in results.get("metrics")
    assert "functions" in results.get("metrics")
    assert "classes" in results.get("metrics")

def test_automated_validation_syntax_check(code_validator, invalid_code, sample_task):
    """Test automated validation syntax checking."""
    results: Dict[str, Any] = code_validator._run_automated_validation(invalid_code, sample_task)
    
    assert len(results.get("errors")) > 0
    assert "Syntax error" in results.get("errors")[0] 
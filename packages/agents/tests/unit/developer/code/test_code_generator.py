"""Unit tests for code generator."""
import pytest
from unittest.mock import Mock, AsyncMock
import json

from cahoots_core.models.task import Task
from .....src.cahoots_agents.developer.code.code_generator import CodeGenerator

@pytest.fixture
def mock_agent():
    """Create mock developer agent."""
    agent = Mock()
    agent.generate_response = AsyncMock()
    return agent

@pytest.fixture
def code_generator(mock_agent):
    """Create code generator with mocked agent."""
    return CodeGenerator(mock_agent)

@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id="task123",
        title="Implement user authentication",
        description="Add user authentication using JWT tokens",
        metadata={
            "requirements": {
                "auth_type": "jwt",
                "token_expiry": "24h"
            },
            "dependencies": [
                "python-jose",
                "passlib"
            ]
        }
    )

@pytest.mark.asyncio
async def test_generate_implementation_success(code_generator, sample_task):
    """Test successful code generation."""
    expected_implementation = {
        "code": "def authenticate_user(): pass",
        "file_path": "auth/jwt.py"
    }
    code_generator.agent.generate_response.return_value = json.dumps(expected_implementation)
    
    implementation = await code_generator.generate_implementation(sample_task)
    
    assert implementation == expected_implementation

@pytest.mark.asyncio
async def test_generate_implementation_invalid_json(code_generator, sample_task):
    """Test handling of invalid JSON response."""
    code_generator.agent.generate_response.return_value = "invalid json"
    
    with pytest.raises(ValueError, match="Failed to parse implementation response"):
        await code_generator.generate_implementation(sample_task)

@pytest.mark.asyncio
async def test_generate_implementation_empty_metadata(code_generator):
    """Test code generation with empty metadata."""
    task = Task(
        id="task123",
        title="Simple task",
        description="Task description",
        metadata={}
    )
    
    expected_implementation = {
        "code": "# Simple implementation",
        "file_path": "simple.py"
    }
    code_generator.agent.generate_response.return_value = json.dumps(expected_implementation)
    
    implementation = await code_generator.generate_implementation(task)
    
    assert implementation == expected_implementation # Empty JSON objects for missing metadata

@pytest.mark.asyncio
async def test_generate_implementation_complex_metadata(code_generator):
    """Test code generation with complex metadata."""
    task = Task(
        id="task123",
        title="Complex task",
        description="Task description",
        metadata={
            "requirements": {
                "nested": {
                    "deep": ["value1", "value2"]
                }
            },
            "dependencies": [
                {"name": "package1", "version": "1.0.0"},
                {"name": "package2", "version": "2.0.0"}
            ]
        }
    )
    
    expected_implementation = {
        "code": "# Complex implementation",
        "file_path": "complex.py"
    }
    code_generator.agent.generate_response.return_value = json.dumps(expected_implementation)
    
    implementation = await code_generator.generate_implementation(task)
    
    assert implementation == expected_implementation
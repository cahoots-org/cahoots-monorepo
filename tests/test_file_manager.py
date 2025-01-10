"""Tests for the file manager module."""
import pytest
from unittest.mock import Mock, mock_open, patch
import os

from src.agents.developer.file_manager import FileManager
from src.models.task import Task

@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    return Mock()

@pytest.fixture
def file_manager(mock_agent):
    """Create a file manager instance."""
    return FileManager(mock_agent)

@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    return [
        Task(
            id="task-1",
            title="Create User Model",
            description="Create a user model with basic fields",
            requires_ux=False,
            metadata={}
        ),
        Task(
            id="task-2",
            title="Implement Login API Endpoint",
            description="Create login endpoint with JWT auth",
            requires_ux=False,
            metadata={}
        ),
        Task(
            id="task-3",
            title="Design Login Component",
            description="Create React component for login form",
            requires_ux=True,
            metadata={}
        ),
        Task(
            id="task-4",
            title="Write Integration Tests",
            description="Add integration tests for auth flow",
            requires_ux=False,
            metadata={}
        ),
        Task(
            id="task-5",
            title="Custom Task Handler",
            description="Implement custom task handling logic",
            requires_ux=False,
            metadata={}
        )
    ]

def test_init(file_manager):
    """Test file manager initialization."""
    assert file_manager.logger is not None

def test_determine_file_path_model(file_manager, sample_tasks):
    """Test file path determination for model tasks."""
    path = file_manager.determine_file_path(sample_tasks[0])
    assert path == "src/models/model.py"
    
    # Test with database in title
    task = Task(
        id="task-db",
        title="Setup Database Schema",
        description="Create database schema",
        requires_ux=False,
        metadata={}
    )
    path = file_manager.determine_file_path(task)
    assert path == "src/models/model.py"

def test_determine_file_path_api(file_manager, sample_tasks):
    """Test file path determination for API tasks."""
    path = file_manager.determine_file_path(sample_tasks[1])
    assert path == "src/api/routes.py"
    
    # Test with endpoint in title
    task = Task(
        id="task-api",
        title="New Endpoint Creation",
        description="Create new endpoint",
        requires_ux=False,
        metadata={}
    )
    path = file_manager.determine_file_path(task)
    assert path == "src/api/routes.py"

def test_determine_file_path_ui(file_manager, sample_tasks):
    """Test file path determination for UI tasks."""
    path = file_manager.determine_file_path(sample_tasks[2])
    assert path == "src/ui/components.py"
    
    # Test with component in title
    task = Task(
        id="task-ui",
        title="Button Component",
        description="Create button component",
        requires_ux=True,
        metadata={}
    )
    path = file_manager.determine_file_path(task)
    assert path == "src/ui/components.py"

def test_determine_file_path_test(file_manager, sample_tasks):
    """Test file path determination for test tasks."""
    path = file_manager.determine_file_path(sample_tasks[3])
    assert path == "tests/test_main.py"

def test_determine_file_path_custom(file_manager, sample_tasks):
    """Test file path determination for custom tasks."""
    path = file_manager.determine_file_path(sample_tasks[4])
    assert path == "src/core/custom_task_handler.py"
    
    # Test with special characters
    task = Task(
        id="task-special",
        title="Handle @Special! Characters",
        description="Test special characters",
        requires_ux=False,
        metadata={}
    )
    path = file_manager.determine_file_path(task)
    assert path == "src/core/handle_special_characters.py"

def test_gather_implementation_context_existing_file(file_manager, sample_tasks):
    """Test gathering context with existing file."""
    existing_code = "def existing_function():\n    pass\n"
    
    with patch("builtins.open", mock_open(read_data=existing_code)):
        context = file_manager.gather_implementation_context(
            sample_tasks[0],
            "src/models/model.py"
        )
        
        assert "Existing file content" in context
        assert existing_code in context
        assert "existing model patterns" in context.lower()

def test_gather_implementation_context_new_file(file_manager, sample_tasks):
    """Test gathering context for new file."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        context = file_manager.gather_implementation_context(
            sample_tasks[0],
            "src/models/new_model.py"
        )
        
        assert "new file" in context.lower()
        assert "existing model patterns" in context.lower()

def test_gather_implementation_context_api(file_manager, sample_tasks):
    """Test gathering context for API tasks."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        context = file_manager.gather_implementation_context(
            sample_tasks[1],
            "src/api/routes.py"
        )
        
        assert "new file" in context.lower()
        assert "rest api" in context.lower()

def test_gather_implementation_context_error_handling(file_manager, sample_tasks):
    """Test error handling in context gathering."""
    with patch("builtins.open", side_effect=PermissionError):
        context = file_manager.gather_implementation_context(
            sample_tasks[0],
            "src/models/model.py"
        )
        
        assert "new file" not in context.lower()
        assert "existing model patterns" in context.lower()

def test_determine_file_path_case_insensitive(file_manager):
    """Test that file path determination is case insensitive."""
    task_lower = Task(
        id="task-lower",
        title="create model class",
        description="Create model",
        requires_ux=False,
        metadata={}
    )
    
    task_upper = Task(
        id="task-upper",
        title="CREATE MODEL CLASS",
        description="Create model",
        requires_ux=False,
        metadata={}
    )
    
    path_lower = file_manager.determine_file_path(task_lower)
    path_upper = file_manager.determine_file_path(task_upper)
    
    assert path_lower == path_upper
    assert path_lower == "src/models/model.py" 
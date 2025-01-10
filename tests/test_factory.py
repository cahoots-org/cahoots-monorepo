"""Tests for agent factory."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

from src.agents.factory import AgentFactory
from src.agents.project_manager import ProjectManager
from src.agents.developer import Developer
from src.agents.ux_designer import UXDesigner
from src.agents.qa_tester import QATester
from src.models.qa_suite import TestSuite, TestCase, QAResult, TestStatus
from src.utils.logger import Logger

@pytest.fixture
def mock_event_system():
    """Create mock event system."""
    return AsyncMock()

@pytest.fixture
def mock_model():
    """Create mock model."""
    return AsyncMock()

@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock(spec=Logger)

@pytest.fixture
def factory(mock_event_system, mock_model, mock_logger):
    """Create AgentFactory instance."""
    return AgentFactory(event_system=mock_event_system, model=mock_model, logger=mock_logger)

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict(os.environ, {
        'DESIGNER_ID': 'test-designer',
        'GITHUB_TOKEN': 'test-token',
        'GITHUB_USERNAME': 'test-user',
        'TRELLO_API_KEY': 'test-key',
        'TRELLO_API_TOKEN': 'test-token'
    }):
        yield

def test_create_project_manager(factory, mock_event_system):
    """Test creating ProjectManager agent."""
    with patch('src.agents.project_manager.GitHubService') as mock_github, \
         patch('src.services.task_management.trello.TrelloService') as mock_trello:
        mock_github.return_value = AsyncMock()
        mock_trello.return_value = AsyncMock()
        pm = factory.create_agent("project_manager")
        assert isinstance(pm, ProjectManager)
        assert pm.event_system == mock_event_system

def test_create_developer(factory, mock_event_system):
    """Test creating Developer agent."""
    with patch('src.agents.developer.GitHubService') as mock_github:
        mock_github.return_value = AsyncMock()
        dev = factory.create_agent("developer")
        assert isinstance(dev, Developer)
        assert dev.event_system == mock_event_system

def test_create_ux_designer(factory, mock_event_system):
    """Test creating UXDesigner agent."""
    with patch('src.agents.ux_designer.GitHubService') as mock_github:
        mock_github.return_value = AsyncMock()
        designer = factory.create_agent("ux_designer")
        assert isinstance(designer, UXDesigner)
        assert designer.event_system == mock_event_system

def test_create_qa_tester(factory, mock_event_system, mock_logger):
    """Test creating QATester agent."""
    with patch('src.agents.qa_tester.QASuiteGenerator') as mock_generator_cls, \
         patch('src.agents.qa_tester.QARunner') as mock_runner:
        mock_generator = AsyncMock()
        mock_generator_cls.return_value = mock_generator
        mock_runner.return_value = AsyncMock()
        tester = factory.create_agent("qa_tester")
        assert isinstance(tester, QATester)
        assert tester.event_system == mock_event_system
        mock_generator_cls.assert_called_once()

def test_create_invalid_agent_type(factory):
    """Test creating invalid agent type."""
    with pytest.raises(RuntimeError) as exc_info:
        factory.create_agent("invalid_type")
    assert "Invalid agent type: invalid_type" in str(exc_info.value) 
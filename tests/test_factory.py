"""Unit tests for the AgentFactory class."""
from typing import TYPE_CHECKING, Dict, Any
import pytest
from unittest.mock import AsyncMock, Mock, patch
import os
from unittest import mock
import traceback

from src.agents.factory import AgentFactory
from src.agents.project_manager import ProjectManager
from src.agents.developer import Developer
from src.agents.ux_designer import UXDesigner
from src.agents.tester import Tester

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from _pytest.logging import LogCaptureFixture

@pytest.fixture
def mock_logger(mocker: "MockerFixture") -> Mock:
    """Create a mock logger."""
    mock = Mock()
    mock.info = Mock()
    mock.debug = Mock()
    mock.error = Mock()
    mock.warning = Mock()
    return mock

@pytest.fixture
def mock_event_system(mocker: "MockerFixture") -> Mock:
    """Create a mock event system."""
    mock = Mock()
    mock.connect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.start_listening = AsyncMock()
    mock.pubsub = AsyncMock()
    mock.pubsub.get_message = AsyncMock()
    return mock

@pytest.fixture
def mock_project_manager(mocker: "MockerFixture", mock_event_system: Mock) -> Mock:
    """Mock ProjectManager class."""
    mock = Mock()
    mock.setup_events = AsyncMock()
    mock.start_listening = AsyncMock()
    mock.run = AsyncMock()
    mocker.patch("src.agents.factory.ProjectManager", return_value=mock)
    return mock

@pytest.fixture
def mock_developer(mocker: "MockerFixture", mock_event_system: Mock) -> Mock:
    """Mock Developer class."""
    mock = Mock()
    mock.setup_events = AsyncMock()
    mock.start_listening = AsyncMock()
    mock.run = AsyncMock()
    mocker.patch("src.agents.factory.Developer", return_value=mock)
    return mock

@pytest.fixture
def mock_ux_designer(mocker: "MockerFixture", mock_event_system: Mock) -> Mock:
    """Mock UXDesigner class."""
    mock = Mock()
    mock.setup_events = AsyncMock()
    mock.start_listening = AsyncMock()
    mock.run = AsyncMock()
    mocker.patch("src.agents.factory.UXDesigner", return_value=mock)
    return mock

@pytest.fixture
def mock_tester(mocker: "MockerFixture", mock_event_system: Mock) -> Mock:
    """Mock Tester class."""
    mock = Mock()
    mock.setup_events = AsyncMock()
    mock.start_listening = AsyncMock()
    mock.run = AsyncMock()
    mocker.patch("src.agents.factory.Tester", return_value=mock)
    return mock

def test_create_agent_pm_success(
    mock_project_manager: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test successful creation of project manager agent."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "pm",
        "TRELLO_API_KEY": "test-key",
        "TRELLO_API_SECRET": "test-secret"
    })
    
    agent = factory.create_agent()
    
    assert isinstance(agent, Mock)  # Since we mocked ProjectManager
    mock_logger.info.assert_called_with("Creating agent of type: pm")

def test_create_agent_pm_missing_trello_key(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test PM agent creation with missing Trello API key."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "pm",
        "TRELLO_API_SECRET": "test-secret"
    }, clear=True)
    
    with pytest.raises(RuntimeError) as exc_info:
        factory.create_agent()
    
    assert "TRELLO_API_KEY environment variable is missing" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("TRELLO_API_KEY environment variable is missing"),
        mock.call("Failed to create agent: TRELLO_API_KEY environment variable is missing"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_pm_missing_trello_secret(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test PM agent creation with missing Trello API secret."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "pm",
        "TRELLO_API_KEY": "test-key"
    }, clear=True)
    
    with pytest.raises(RuntimeError) as exc_info:
        factory.create_agent()
    
    assert "TRELLO_API_SECRET environment variable is missing" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("TRELLO_API_SECRET environment variable is missing"),
        mock.call("Failed to create agent: TRELLO_API_SECRET environment variable is missing"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_developer_success(
    mock_developer: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test successful creation of developer agent."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "developer",
        "DEVELOPER_ID": "test-dev"
    })
    
    agent = factory.create_agent()
    
    assert isinstance(agent, Mock)  # Since we mocked Developer
    mock_logger.info.assert_called_with("Creating agent of type: developer")

def test_create_agent_developer_missing_id(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test developer agent creation with missing developer ID."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "developer"
    }, clear=True)
    
    with pytest.raises(ValueError) as exc_info:
        factory.create_agent()
    
    assert "DEVELOPER_ID environment variable must be set for developer agents" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("DEVELOPER_ID environment variable must be set for developer agents"),
        mock.call("Failed to create agent: DEVELOPER_ID environment variable must be set for developer agents"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_ux_success(
    mock_ux_designer: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test successful creation of UX designer agent."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "ux",
        "DESIGNER_ID": "test-designer"
    })
    
    agent = factory.create_agent()
    
    assert isinstance(agent, Mock)  # Since we mocked UXDesigner
    mock_logger.info.assert_called_with("Creating agent of type: ux")

def test_create_agent_ux_missing_id(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test UX designer agent creation with missing designer ID."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "ux"
    }, clear=True)
    
    with pytest.raises(ValueError) as exc_info:
        factory.create_agent()
    
    assert "DESIGNER_ID environment variable must be set for UX designer" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("DESIGNER_ID environment variable must be set for UX designer"),
        mock.call("Failed to create agent: DESIGNER_ID environment variable must be set for UX designer"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_tester_success(
    mock_tester: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test successful creation of tester agent."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "tester",
        "TESTER_ID": "test-tester"
    })
    
    agent = factory.create_agent()
    
    assert isinstance(agent, Mock)  # Since we mocked Tester
    mock_logger.info.assert_called_with("Creating agent of type: tester")

def test_create_agent_tester_missing_id(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test tester agent creation with missing tester ID."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "tester"
    }, clear=True)
    
    with pytest.raises(ValueError) as exc_info:
        factory.create_agent()
    
    assert "TESTER_ID environment variable must be set for tester" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("TESTER_ID environment variable must be set for tester"),
        mock.call("Failed to create agent: TESTER_ID environment variable must be set for tester"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_unknown_type(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test handling of unknown agent type."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "unknown"
    })
    
    with pytest.raises(ValueError) as exc_info:
        factory.create_agent()
    
    assert "Unknown agent type: unknown" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("Unknown agent type: unknown"),
        mock.call("Failed to create agent: Unknown agent type: unknown"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_missing_type(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test handling of missing agent type."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {}, clear=True)
    
    with pytest.raises(ValueError) as exc_info:
        factory.create_agent()
    
    assert "AGENT_TYPE environment variable must be set" in str(exc_info.value)
    mock_logger.error.assert_has_calls([
        mock.call("AGENT_TYPE environment variable must be set"),
        mock.call("Failed to create agent: AGENT_TYPE environment variable must be set"),
        mock.call(mock.ANY)  # Accept any stack trace
    ])

def test_create_agent_explicit_type(
    mock_project_manager: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test agent creation with explicitly provided type."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "TRELLO_API_KEY": "test-key",
        "TRELLO_API_SECRET": "test-secret"
    })
    
    agent = factory.create_agent("pm")
    
    assert isinstance(agent, Mock)  # Since we mocked ProjectManager
    mock_logger.info.assert_called_with("Creating agent of type: pm")

def test_create_agent_case_insensitive(
    mock_project_manager: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test agent creation with case-insensitive type."""
    factory = AgentFactory(logger=mock_logger)
    mocker.patch.dict(os.environ, {
        "TRELLO_API_KEY": "test-key",
        "TRELLO_API_SECRET": "test-secret"
    })
    
    agent = factory.create_agent("PM")
    
    assert isinstance(agent, Mock)  # Since we mocked ProjectManager
    mock_logger.info.assert_called_with("Creating agent of type: pm")

@pytest.mark.asyncio
async def test_main_success(
    mock_project_manager: Mock,
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test successful main function execution."""
    from src.agents.factory import main
    
    mocker.patch("src.agents.factory.BaseLogger", return_value=mock_logger)
    mocker.patch.dict(os.environ, {
        "AGENT_TYPE": "pm",
        "TRELLO_API_KEY": "test-key",
        "TRELLO_API_SECRET": "test-secret"
    })
    
    # Mock asyncio.sleep to avoid infinite loop
    mocker.patch("asyncio.sleep", side_effect=KeyboardInterrupt)
    
    # Mock agent setup_events and run
    mock_project_manager.setup_events = AsyncMock()
    mock_project_manager.run = AsyncMock(side_effect=KeyboardInterrupt)
    
    with pytest.raises(KeyboardInterrupt):
        await main()

@pytest.mark.asyncio
async def test_main_failure(
    mock_logger: Mock,
    mocker: "MockerFixture"
) -> None:
    """Test main function failure handling."""
    from src.agents.factory import main
    
    mocker.patch("src.agents.factory.BaseLogger", return_value=mock_logger)
    mocker.patch.dict(os.environ, {}, clear=True)
    
    with pytest.raises(ValueError) as exc_info:
        await main()
    
    assert "AGENT_TYPE environment variable must be set" in str(exc_info.value) 
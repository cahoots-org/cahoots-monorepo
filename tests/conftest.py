"""Test configuration and fixtures."""
import pytest
import asyncio
from typing import Dict, Generator, AsyncGenerator
from unittest.mock import AsyncMock, Mock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from redis.asyncio import Redis
from datetime import datetime
import json
import copy
import os
from pytest_mock import MockerFixture

from src.api.main import app
from src.utils.event_system import get_event_system, _event_system
from src.agents.developer import Developer
from src.agents.project_manager import ProjectManager
from src.agents.tester import Tester
from src.agents.ux_designer import UXDesigner
from src.agents.base_agent import BaseAgent
from src.utils.event_system import EventSystem
from src.services.github_service import GitHubService
from src.utils.task_manager import TaskManager
from src.utils.model import Model

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("TESTER_ID", "test-tester-123")
    monkeypatch.setenv("DESIGNER_ID", "test-designer-123")
    monkeypatch.setenv("TRELLO_API_KEY", "test-trello-key")
    monkeypatch.setenv("TRELLO_API_SECRET", "test-trello-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")

@pytest.fixture(autouse=True)
def mock_event_system_singleton(monkeypatch):
    """Mock the event system singleton for all tests."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.redis = AsyncMock()
    mock.is_connected = Mock(return_value=True)
    mock.pubsub = Mock()
    mock.pubsub.subscribe = Mock()
    mock.pubsub.unsubscribe = Mock()
    mock.pubsub.close = Mock()
    
    # Replace the singleton instance and getter
    monkeypatch.setattr("src.utils.event_system._event_system", mock)
    monkeypatch.setattr("src.utils.event_system.get_event_system", lambda: mock)
    monkeypatch.setattr("src.api.core.get_event_system", lambda: mock)
    
    return mock

@pytest.fixture
async def mock_redis() -> AsyncMock:
    """Create a Redis mock for testing."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.close = AsyncMock()
    mock.aclose = AsyncMock()
    mock.connection_pool = AsyncMock()
    mock.connection_pool.disconnect = AsyncMock()
    
    # Create pubsub mock - CORRECTLY as synchronous
    pubsub_mock = Mock()  # Regular Mock, not AsyncMock
    pubsub_mock.subscribe = Mock()
    pubsub_mock.unsubscribe = Mock()
    pubsub_mock.close = Mock()
    mock.pubsub = Mock(return_value=pubsub_mock)
    
    return mock

@pytest.fixture(autouse=True)
def mock_base_logger(monkeypatch):
    """Mock BaseLogger for all tests."""
    mock = Mock()
    mock.debug = Mock()
    mock.info = Mock()
    mock.error = Mock()
    mock.warning = Mock()
    mock._logger = mock  # Support for bind() calls
    mock.bind = Mock(return_value=mock)
    
    monkeypatch.setattr("src.utils.base_logger.BaseLogger", lambda *args, **kwargs: mock)
    monkeypatch.setattr("src.agents.base_agent.BaseLogger", lambda *args, **kwargs: mock)
    
    return mock

@pytest.fixture
async def mock_event_system(mock_redis: AsyncMock) -> AsyncMock:
    """Create a mock event system."""
    mock = AsyncMock()
    mock.redis = mock_redis
    mock.connect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.get_message = AsyncMock(return_value=None)
    mock.start_listening = AsyncMock()
    mock.stop_listening = AsyncMock()
    mock.pubsub = mock_redis.pubsub()
    return mock

@pytest.fixture
async def task_manager() -> AsyncGenerator[TaskManager, None]:
    """Create a task manager for testing."""
    manager = TaskManager("test")
    yield manager
    await manager.cancel_all()

@pytest.fixture
async def base_agent(mock_event_system: AsyncMock, task_manager: TaskManager) -> AsyncGenerator[BaseAgent, None]:
    """Create a base agent for testing."""
    agent = BaseAgent("test-model", start_listening=False, event_system=mock_event_system)
    agent._task_manager = task_manager
    yield agent
    await agent.stop_listening()

@pytest.fixture
async def developer(mock_event_system: AsyncMock, task_manager: TaskManager) -> AsyncGenerator[Developer, None]:
    """Create a developer agent for testing."""
    dev = Developer("test-dev-1", start_listening=False, event_system=mock_event_system)
    dev._task_manager = task_manager
    yield dev
    await dev.stop_listening()

@pytest.fixture
async def tester(mock_event_system: AsyncMock, task_manager: TaskManager) -> AsyncGenerator[Tester, None]:
    """Create a tester agent for testing."""
    tester = Tester(event_system=mock_event_system)
    tester._task_manager = task_manager
    yield tester
    await tester.stop_listening()

@pytest.fixture
async def ux_designer(mock_event_system: AsyncMock, task_manager: TaskManager) -> AsyncGenerator[UXDesigner, None]:
    """Create a UX designer agent for testing."""
    designer = UXDesigner(event_system=mock_event_system)
    designer._task_manager = task_manager
    yield designer
    await designer.stop_listening()

@pytest.fixture
async def project_manager(mock_event_system: AsyncMock, task_manager: TaskManager) -> AsyncGenerator[ProjectManager, None]:
    """Create a project manager agent for testing."""
    pm = ProjectManager(event_system=mock_event_system)
    pm._task_manager = task_manager
    yield pm
    await pm.stop_listening()

@pytest.fixture
def sample_project() -> Dict:
    """Return a sample project for testing."""
    return {
        "id": "test-project-123",
        "name": "Test Project",
        "description": "A test project for unit testing"
    }

@pytest.fixture
def sample_message() -> Dict:
    """Return a sample message for testing."""
    return {
        "id": "test-1",
        "timestamp": datetime.utcnow(),
        "type": "test",
        "payload": {"key": "value"},
        "retry_count": 0,
        "max_retries": 3
    }

@pytest.fixture
def api_key_header() -> Dict:
    """Return API key header for testing."""
    return {"X-API-Key": "test-api-key-123"}

@pytest.fixture
async def redis_client(mock_redis: AsyncMock) -> AsyncGenerator[Redis, None]:
    """Return a Redis client for testing."""
    yield mock_redis

@pytest.fixture
def test_client(mock_event_system: AsyncMock) -> TestClient:
    """Return a test client."""
    client = TestClient(app)
    yield client

@pytest.fixture
async def async_client(mock_event_system: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Return an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client 

@pytest.fixture
def mock_model(mocker: "MockerFixture") -> Mock:
    """Create a mock model."""
    mock = Mock(spec=Model)
    mock.generate_response = AsyncMock(return_value="Test response")
    mocker.patch("src.agents.base_agent.Model", return_value=mock)
    return mock

@pytest.fixture
def mock_base_logger(mocker: "MockerFixture") -> Mock:
    """Create a mock logger."""
    mock = Mock()
    mock.debug = Mock()
    mock.info = Mock()
    mock.warning = Mock()
    mock.error = Mock()
    mocker.patch("src.utils.base_logger.BaseLogger", return_value=mock)
    return mock

@pytest.fixture
def mock_event_system(mocker: "MockerFixture") -> Mock:
    """Create a mock event system."""
    mock = Mock(spec=EventSystem)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.stop_listening = AsyncMock()
    return mock

@pytest.fixture
def mock_event_system_singleton(mocker: "MockerFixture") -> AsyncMock:
    """Create a mock event system singleton."""
    mock = AsyncMock(spec=EventSystem)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    mock.stop_listening = AsyncMock()
    mocker.patch("src.api.core._event_system", mock)
    return mock

@pytest.fixture
def mock_redis(mocker: "MockerFixture") -> Mock:
    """Create a mock Redis client."""
    mock = Mock()
    mock.ping = AsyncMock()
    mock.close = AsyncMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.get_message = AsyncMock()
    return mock

@pytest.fixture
def api_key_header() -> dict:
    """Create a valid API key header."""
    return {"X-API-Key": os.getenv("API_KEY", "test-key")} 
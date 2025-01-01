"""Test configuration and fixtures."""
import pytest
import asyncio
from typing import Dict, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from redis.asyncio import Redis
from datetime import datetime
import json
import copy

from src.api.main import app
from src.utils.event_system import EventSystem
from src.api.core import get_event_system
from src.agents.developer import Developer
from src.agents.project_manager import ProjectManager
from src.agents.tester import Tester
from src.agents.ux_designer import UXDesigner

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("TESTER_ID", "test-tester-123")
    monkeypatch.setenv("DESIGNER_ID", "test-designer-123")
    monkeypatch.setenv("TRELLO_API_KEY", "test-trello-key")
    monkeypatch.setenv("TRELLO_API_SECRET", "test-trello-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")

@pytest.fixture
async def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock(spec=Redis)
    pubsub_mock = MagicMock()
    pubsub_mock.subscribe = MagicMock()
    pubsub_mock.unsubscribe = MagicMock()
    pubsub_mock.listen = MagicMock()
    pubsub_mock.close = MagicMock()
    mock.pubsub.return_value = pubsub_mock
    mock.ping = AsyncMock()
    mock.publish = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.fixture
async def event_system(mock_redis):
    """Create an event system with mocked Redis."""
    es = EventSystem()
    es.redis = mock_redis
    es.pubsub = mock_redis.pubsub()
    es._connected = True
    return es

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    if loop.is_running():
        loop.stop()
    if not loop.is_closed():
        loop.close()
    asyncio.set_event_loop(None)

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
def redis_mock() -> AsyncMock:
    """Return a mock Redis client for testing.
    
    This mock simulates Redis behavior including connection failures
    and proper error handling for health checks.
    """
    mock = AsyncMock()
    
    # Basic Redis operations
    mock.ping = AsyncMock()
    mock.publish = AsyncMock()
    mock.close = AsyncMock()
    mock.incr = AsyncMock()
    mock.expire = AsyncMock()
    mock.ttl = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    
    # Connection pool metrics
    mock.connection_pool = AsyncMock()
    mock.connection_pool.size = 1
    mock.connection_pool.max_size = 10
    
    # Configure default behaviors
    mock.ping.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.ttl.return_value = 60
    
    # Add connection simulation
    mock._connected = True
    mock.is_connected = lambda: mock._connected
    
    # Add error simulation methods
    async def simulate_connection_error():
        mock._connected = False
        raise ConnectionError("Redis connection failed")
    
    async def simulate_timeout_error():
        mock._connected = False
        raise TimeoutError("Redis operation timed out")
        
    mock.simulate_connection_error = simulate_connection_error
    mock.simulate_timeout_error = simulate_timeout_error
    
    return mock

@pytest.fixture
def mock_event_system() -> Generator[AsyncMock, None, None]:
    """Return a mock event system."""
    mock = AsyncMock()
    
    # Set up Redis mock
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.publish = AsyncMock()
    redis_mock.close = AsyncMock()
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.ttl = AsyncMock(return_value=60)
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.delete = AsyncMock()
    
    # Set up PubSub mock
    pubsub_mock = MagicMock()
    pubsub_mock.subscribe = MagicMock()
    pubsub_mock.unsubscribe = MagicMock()
    pubsub_mock.close = AsyncMock()
    redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
    
    # Configure event system mock
    mock.redis = redis_mock
    mock.pubsub = pubsub_mock
    mock.is_connected = MagicMock(return_value=True)
    mock.connect = AsyncMock()
    mock.verify_connection = AsyncMock(return_value=True)
    mock.handlers = {}
    mock.dead_letter_queue = "dead_letter_queue"
    mock._connected = True

    # Configure publish method
    mock.publish = AsyncMock()
    mock.subscribe = MagicMock()
    mock.unsubscribe = MagicMock()
    
    yield mock

@pytest.fixture
async def redis_client(redis_mock: AsyncMock) -> AsyncGenerator[Redis, None]:
    """Return a Redis client for testing."""
    yield redis_mock

@pytest.fixture
def test_client(mock_event_system: AsyncMock) -> TestClient:
    """Return a test client."""
    from src.api import core
    core._event_system = mock_event_system
    client = TestClient(app)
    yield client
    core._event_system = None

@pytest.fixture
async def async_client(mock_event_system: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Return an async test client."""
    from src.api import core
    core._event_system = mock_event_system
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    core._event_system = None

@pytest.fixture
def config_override():
    """Override configuration for testing."""
    original_config = copy.deepcopy(config)
    config.auth.api_key = "test-api-key-123"
    config.api.request_timeout_seconds = 30
    yield config
    config.__dict__.update(original_config.__dict__) 

@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns predefined responses."""
    mock = AsyncMock()
    
    async def mock_generate_response(prompt: str) -> str:
        if "Break down this user story into tasks" in prompt:
            return json.dumps({
                "tasks": [
                    {
                        "title": "Setup FastAPI Project",
                        "description": "Initialize FastAPI project with basic configuration",
                        "type": "setup",
                        "complexity": 2,
                        "dependencies": [],
                        "required_skills": ["python", "fastapi", "devops"],
                        "risk_factors": ["dependency conflicts", "environment setup"]
                    },
                    {
                        "title": "Create Health Check Endpoint",
                        "description": "Implement basic health check endpoint",
                        "type": "implementation",
                        "complexity": 3,
                        "dependencies": ["Setup FastAPI Project"],
                        "required_skills": ["python", "fastapi", "rest-api"],
                        "risk_factors": ["error handling", "response time"]
                    },
                    {
                        "title": "Add Database Connectivity Check",
                        "description": "Add database connection status to health check",
                        "type": "implementation",
                        "complexity": 3,
                        "dependencies": ["Create Health Check Endpoint"],
                        "required_skills": ["python", "fastapi", "database", "sql"],
                        "risk_factors": ["database timeout", "connection pooling", "security"]
                    },
                    {
                        "title": "Implement Metrics Collection",
                        "description": "Add response time and other metrics",
                        "type": "implementation",
                        "complexity": 3,
                        "dependencies": ["Create Health Check Endpoint"],
                        "required_skills": ["python", "fastapi", "metrics"],
                        "risk_factors": ["performance overhead", "memory usage"]
                    },
                    {
                        "title": "Write Unit Tests",
                        "description": "Create comprehensive test suite",
                        "type": "testing",
                        "complexity": 2,
                        "dependencies": ["Create Health Check Endpoint", "Add Database Connectivity Check", "Implement Metrics Collection"],
                        "required_skills": ["python", "pytest", "testing"],
                        "risk_factors": ["test coverage", "mock complexity"]
                    }
                ]
            })
        elif "roadmap" in prompt.lower():
            return json.dumps({
                "tasks": [
                    {
                        "title": "Setup Project Structure",
                        "description": "Create initial project structure and configuration",
                        "priority": "high",
                        "dependencies": []
                    },
                    {
                        "title": "Implement Core Features",
                        "description": "Develop the main functionality",
                        "priority": "high",
                        "dependencies": ["Setup Project Structure"]
                    }
                ]
            })
        elif "requirements" in prompt.lower():
            return json.dumps({
                "requirements": [
                    {
                        "id": "REQ-001",
                        "title": "FastAPI Endpoint",
                        "description": "Create a health check endpoint using FastAPI",
                        "priority": "high"
                    },
                    {
                        "id": "REQ-002",
                        "title": "Database Check",
                        "description": "Implement database connectivity check",
                        "priority": "high"
                    }
                ]
            })
        elif "Implement code for this task" in prompt:
            if "Setup FastAPI Project" in prompt:
                return json.dumps({
                    "code": """
                    from fastapi import FastAPI, HTTPException
                    from pydantic import BaseModel
                    from typing import Dict
                    
                    app = FastAPI(title="Health Check API")
                    """,
                    "file_path": "src/api/main.py"
                })
            elif "Health Check Endpoint" in prompt:
                return json.dumps({
                    "code": """
                    from fastapi import FastAPI, HTTPException
                    from pydantic import BaseModel
                    from typing import Dict
                    import time
                    
                    @app.get("/health")
                    async def health_check() -> Dict:
                        return {
                            "status": "healthy",
                            "version": "1.0.0",
                            "timestamp": time.time()
                        }
                    """,
                    "file_path": "src/api/health.py"
                })
            elif "Database Connectivity" in prompt:
                return json.dumps({
                    "code": """
                    from fastapi import FastAPI, HTTPException
                    from sqlalchemy import create_engine
                    from typing import Dict
                    import os
                    
                    def check_db_connection() -> bool:
                        try:
                            engine = create_engine(os.getenv("DATABASE_URL"))
                            with engine.connect() as conn:
                                return True
                        except Exception:
                            return False
                    
                    @app.get("/health/db")
                    async def db_health_check() -> Dict:
                        return {
                            "database": "connected" if check_db_connection() else "disconnected"
                        }
                    """,
                    "file_path": "src/api/health.py"
                })
            elif "Metrics Collection" in prompt:
                return json.dumps({
                    "code": """
                    from fastapi import FastAPI, HTTPException
                    from typing import Dict
                    import time
                    
                    @app.middleware("http")
                    async def add_metrics(request: Request, call_next):
                        start_time = time.time()
                        response = await call_next(request)
                        response.headers["X-Response-Time"] = str(time.time() - start_time)
                        return response
                    """,
                    "file_path": "src/api/metrics.py"
                })
            elif "Unit Tests" in prompt:
                return json.dumps({
                    "code": """
                    import pytest
                    from fastapi.testclient import TestClient
                    from .main import app
                    
                    client = TestClient(app)
                    
                    def test_health_check():
                        response = client.get("/health")
                        assert response.status_code == 200
                        data = response.json()
                        assert "status" in data
                        assert "version" in data
                        assert "timestamp" in data
                    
                    def test_db_health_check():
                        response = client.get("/health/db")
                        assert response.status_code == 200
                        data = response.json()
                        assert "database" in data
                    """,
                    "file_path": "tests/test_health.py"
                })
            else:
                return json.dumps({
                    "code": "Not implemented",
                    "file_path": "src/api/unknown.py"
                })
        else:
            return "I don't understand the request"
    
    mock.generate_response = mock_generate_response
    return mock

@pytest.fixture
async def developer(event_system, mock_llm):
    """Create a developer agent."""
    dev = Developer("test_developer")
    dev.event_system = event_system
    dev.model = mock_llm
    await dev.setup_events()
    return dev

@pytest.fixture
async def project_manager(event_system, mock_llm):
    """Create a project manager agent."""
    pm = ProjectManager()
    pm.event_system = event_system
    pm.model = mock_llm
    await pm.setup_events()
    return pm

@pytest.fixture
async def tester(event_system, mock_llm):
    """Create a tester agent."""
    test = Tester()
    test.event_system = event_system
    test.model = mock_llm
    await test.setup_events()
    return test

@pytest.fixture
async def ux_designer(event_system, mock_llm):
    """Create a UX designer agent."""
    ux = UXDesigner()
    ux.event_system = event_system
    ux.model = mock_llm
    await ux.setup_events()
    return ux 
"""Tests for main API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
from httpx import AsyncClient

from cahoots_service.api.health import router as health_router
from cahoots_service.api.projects import router as projects_router
from cahoots_service.api.metrics import router as metrics_router
from cahoots_service.api.auth import verify_api_key
from cahoots_service.utils.config import get_settings
from cahoots_service.services.project_service import ProjectService

@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test"
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.MODEL_API_KEY = "test_model_key"
    settings.GITHUB_API_KEY = "test_github_key"
    settings.STRIPE_API_KEY = "test_stripe_key"
    settings.K8S_NAMESPACE = "test"
    return settings

@pytest.fixture
def api_key_header():
    """Mock API key header."""
    return {"X-API-Key": "test_api_key"}

@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "name": "Test Project",
        "description": "A test project"
    }

@pytest.fixture
def mock_project_service():
    """Mock project service."""
    mock = AsyncMock()
    mock.create_project = AsyncMock()
    return mock

@pytest.fixture
async def async_client(mock_deps, mock_settings, mock_db):
    """Create async test client with minimal setup."""
    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    app.include_router(projects_router, prefix="/api/projects") 
    app.include_router(metrics_router, prefix="/metrics")
    
    # Override dependencies
    app.dependency_overrides = {
        verify_api_key: lambda: "test_org_id",  # Simplified API key verification
        get_settings: lambda: mock_settings,
    }
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

@pytest.mark.asyncio
async def test_health_check(async_client, mock_deps, api_key_header):
    """Test health check returns 200 when all services are healthy."""
    mock_deps.db.execute.return_value = True
    mock_deps.event_system.verify_connection.return_value = True
    mock_deps.redis.ping.return_value = True
    
    response = await async_client.get("/health", headers=api_key_header)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_db_failure(async_client, mock_deps, api_key_header):
    """Test health check returns 503 when database is down."""
    mock_deps.db.execute.side_effect = Exception("Database error")
    
    response = await async_client.get("/health", headers=api_key_header)
    assert response.status_code == 503

@pytest.mark.asyncio
async def test_health_check_redis_failure(async_client, mock_deps, api_key_header):
    """Test health check returns 503 when Redis is down."""
    mock_deps.redis.ping.side_effect = Exception("Redis error")
    
    response = await async_client.get("/health", headers=api_key_header)
    assert response.status_code == 503

@pytest.mark.asyncio
async def test_metrics_endpoint(async_client, api_key_header):
    """Test metrics endpoint returns 200."""
    response = await async_client.get("/metrics", headers=api_key_header)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

@pytest.mark.asyncio
async def test_create_project_success(async_client, mock_deps, api_key_header, sample_project):
    """Test successful project creation returns 201."""
    # Mock project creation
    mock_project = AsyncMock()
    mock_project.id = "test_project_id"
    mock_project.name = sample_project["name"]
    mock_project.description = sample_project["description"]
    mock_project.created_at = datetime.now()
    mock_project.status = "active"
    mock_project.organization_id = "test_org_id"

    # Mock organization lookup and project uniqueness check
    mock_org = AsyncMock()
    mock_org.id = "test_org_id"
    
    async def mock_scalar_one_or_none():
        mock_scalar_one_or_none.call_count += 1
        return mock_org if mock_scalar_one_or_none.call_count == 1 else None
    mock_scalar_one_or_none.call_count = 0
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = mock_scalar_one_or_none
    mock_deps.db.execute = AsyncMock(return_value=mock_result)

    # Mock project service create method
    mock_deps.db.add = AsyncMock()
    mock_deps.db.commit = AsyncMock()
    mock_deps.event_system.publish = AsyncMock()
    
    # Mock the create_project method to return our mock project
    original_init = ProjectService.__init__
    original_create = ProjectService.create_project
    
    async def mock_create(self, *args, **kwargs):
        return mock_project
        
    def mock_init(self, *args, **kwargs):
        self.deps = args[0]
        
    ProjectService.__init__ = mock_init
    ProjectService.create_project = mock_create

    try:
        response = await async_client.post("/api/projects", headers=api_key_header, json=sample_project)
        print(f"Response content: {response.content}")
        print(f"Response json: {response.json()}")
        assert response.status_code == 201
        assert response.json()["name"] == sample_project["name"]
        assert response.json()["description"] == sample_project["description"]
        assert response.json()["status"] == "active"
    finally:
        # Restore original methods
        ProjectService.__init__ = original_init
        ProjectService.create_project = original_create

@pytest.mark.asyncio
async def test_create_project_invalid_data(async_client, mock_deps, api_key_header):
    """Test invalid project data returns 422."""
    # Mock organization lookup
    mock_org = AsyncMock()
    mock_org.id = "test_org_id"
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = mock_org
    
    invalid_project = {"name": "", "description": ""}
    response = await async_client.post("/api/projects", headers=api_key_header, json=invalid_project)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_project_duplicate_name(async_client, mock_deps, api_key_header, sample_project):
    """Test duplicate project name returns 400."""
    # Mock organization lookup
    mock_org = AsyncMock()
    mock_org.id = "test_org_id"
    mock_deps.db.execute.return_value.scalar_one_or_none.side_effect = [mock_org, mock_org]  # First for org lookup, then for project lookup
    
    response = await async_client.post("/api/projects", headers=api_key_header, json=sample_project)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower() 
"""Test organization management endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import uuid4

from cahoots_service.api.organizations import router
from cahoots_service.database.models import Organization
from cahoots_service.core.dependencies import BaseDeps
from cahoots_service.services.organization_service import OrganizationService
from cahoots_service.schemas.organizations import OrganizationResponse
from cahoots_service.api.auth import verify_api_key

@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = AsyncMock()
    mock.add = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.execute = AsyncMock()
    mock.delete = AsyncMock()
    return mock

@pytest.fixture
def mock_deps(mock_db):
    """Mock base dependencies."""
    deps = MagicMock(spec=BaseDeps)
    deps.db = mock_db
    return deps

@pytest.fixture
def client(mock_deps):
    """Test client."""
    app = FastAPI()
    app.include_router(router, prefix="/api/organizations")
    
    # Override dependencies
    app.dependency_overrides = {
        BaseDeps: lambda: mock_deps,
        verify_api_key: lambda: "test_org_id"
    }
    
    return TestClient(app)

@pytest.mark.asyncio
async def test_list_organizations(client, mock_db):
    """Test listing organizations."""
    # Create a mock organization
    mock_org = MagicMock()
    mock_org.id = str(uuid4())
    mock_org.name = "Test Org"
    mock_org.email = "test@example.com"
    mock_org.description = "Test organization"
    mock_org.created_at = datetime.utcnow()
    mock_org.updated_at = datetime.utcnow()
    
    # Mock the database response
    mock_result = MagicMock()
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value = MagicMock()
    mock_result.scalars.return_value.all = MagicMock(return_value=[mock_org])
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    response = client.get("/api/organizations", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == mock_org.name
    assert response.json()[0]["email"] == mock_org.email

@pytest.mark.asyncio
async def test_create_organization(client, mock_db):
    """Test creating an organization."""
    org_data = {
        "name": "Test Org",
        "email": "test@example.com",
        "description": "Test organization"
    }
    
    # Create a mock organization
    mock_org = MagicMock()
    mock_org.id = str(uuid4())
    mock_org.name = org_data["name"]
    mock_org.email = org_data["email"]
    mock_org.description = org_data["description"]
    mock_org.created_at = datetime.utcnow()
    mock_org.updated_at = datetime.utcnow()
    
    # Mock the database operations
    async def mock_refresh(org):
        org.id = mock_org.id
        org.created_at = mock_org.created_at
        org.updated_at = mock_org.updated_at
        return org
    
    mock_db.refresh.side_effect = mock_refresh
    
    response = client.post("/api/organizations", json=org_data, headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 201
    assert response.json()["name"] == org_data["name"]
    assert response.json()["email"] == org_data["email"]
    assert response.json()["description"] == org_data["description"] 
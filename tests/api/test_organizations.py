"""Test organization management endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.organizations import list_organizations, create_organization
from src.schemas.organizations import OrganizationCreate, OrganizationResponse
from src.database.models import Organization

@pytest.mark.asyncio
async def test_list_organizations(
    test_client: FastAPI,
    mock_db: AsyncSession
):
    """Test listing organizations."""
    # Mock the database query result
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch("src.api.organizations.get_session", return_value=mock_db):
        response = await list_organizations(db=mock_db)
        assert response == []

@pytest.mark.asyncio
async def test_create_organization(
    test_client: FastAPI,
    mock_db: AsyncSession
):
    """Test creating an organization."""
    org_data = {
        "name": "Test Org",
        "api_key": "test_key_123",
        "is_active": True,
        "subscription_tier": "free"
    }
    
    # Mock the database operations
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Mock the service to return a valid organization
    mock_org = Organization(
        name=org_data["name"],
        api_key=org_data["api_key"],
        is_active=org_data["is_active"],
        subscription_tier=org_data["subscription_tier"]
    )
    
    with patch("src.api.organizations.get_session", return_value=mock_db), \
         patch("src.services.organization_service.OrganizationService.create_organization", 
               new_callable=AsyncMock, return_value=mock_org):
        response = await create_organization(data=org_data, db=mock_db)
        assert isinstance(response, Organization)
        assert response.name == org_data["name"]
        assert response.api_key == org_data["api_key"]
        assert response.is_active == org_data["is_active"]
        assert response.subscription_tier == org_data["subscription_tier"] 
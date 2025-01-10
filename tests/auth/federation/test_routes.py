"""Tests for federation API routes."""
import pytest
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient

from src.models.federation import (
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)

@pytest.fixture
async def test_provider(db_session):
    """Create test identity provider."""
    provider = IdentityProvider(
        name="Test Provider",
        entity_id="test.provider",
        metadata={
            "sso_url": "https://test.provider/sso",
            "certificate": "test-cert"
        }
    )
    db_session.add(provider)
    await db_session.commit()
    return provider

@pytest.mark.asyncio
async def test_link_federated_identity(
    client: AsyncClient,
    test_user,
    test_provider
):
    """Test linking federated identity endpoint."""
    response = await client.post(
        "/federation/identities",
        json={
            "user_id": str(test_user.id),
            "external_id": "ext123",
            "provider_id": str(test_provider.id),
            "attributes": {
                "name": "Test User",
                "email": "test@example.com"
            }
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    
    # Verify mapping was created
    mapping = await FederatedIdentityMapping.get_by_user_provider(
        test_user.id,
        test_provider.id
    )
    assert mapping is not None
    assert mapping.external_id == "ext123"

@pytest.mark.asyncio
async def test_link_federated_identity_duplicate(
    client: AsyncClient,
    test_user,
    test_provider
):
    """Test linking duplicate identity."""
    # First link
    await client.post(
        "/federation/identities",
        json={
            "user_id": str(test_user.id),
            "external_id": "ext123",
            "provider_id": str(test_provider.id),
            "attributes": {"name": "Test User"}
        }
    )
    
    # Try to link again
    response = await client.post(
        "/federation/identities",
        json={
            "user_id": str(test_user.id),
            "external_id": "ext123",
            "provider_id": str(test_provider.id),
            "attributes": {"name": "Test User"}
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already linked" in response.json()["detail"]

@pytest.mark.asyncio
async def test_unlink_federated_identity(
    client: AsyncClient,
    test_user,
    test_provider,
    federation_service
):
    """Test unlinking federated identity endpoint."""
    # First link an identity
    identity = FederatedIdentity(
        external_id="ext123",
        provider_id=str(test_provider.id),
        attributes={"name": "Test User"}
    )
    await federation_service.link_identity(str(test_user.id), identity)
    
    # Then unlink it
    response = await client.delete(
        f"/federation/identities/{test_provider.id}",
        params={"user_id": str(test_user.id)}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    
    # Verify mapping is inactive
    mapping = await FederatedIdentityMapping.get_by_user_provider(
        test_user.id,
        test_provider.id
    )
    assert mapping is not None
    assert mapping.is_active is False

@pytest.mark.asyncio
async def test_sync_identity_attributes(
    client: AsyncClient,
    test_user,
    test_provider,
    federation_service,
    db_session
):
    """Test syncing identity attributes endpoint."""
    # Create attribute mappings
    mappings = [
        AttributeMapping(
            provider_id=test_provider.id,
            source_attribute="name",
            target_attribute="display_name"
        ),
        AttributeMapping(
            provider_id=test_provider.id,
            source_attribute="role",
            target_attribute="user_role"
        )
    ]
    for mapping in mappings:
        db_session.add(mapping)
    await db_session.commit()
    
    # Link identity
    identity = FederatedIdentity(
        external_id="ext123",
        provider_id=str(test_provider.id),
        attributes={"name": "Test User"}
    )
    await federation_service.link_identity(str(test_user.id), identity)
    
    # Sync attributes
    response = await client.put(
        f"/federation/identities/{test_provider.id}/attributes",
        params={"user_id": str(test_user.id)},
        json={
            "name": "Updated User",
            "role": "admin"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["attributes"]["display_name"] == "Updated User"
    assert data["attributes"]["user_role"] == "admin"

@pytest.mark.asyncio
async def test_establish_trust_relationship(
    client: AsyncClient,
    test_provider
):
    """Test establishing trust relationship endpoint."""
    trusted_provider = IdentityProvider(
        name="Trusted Provider",
        entity_id="trusted.provider",
        metadata={"sso_url": "https://trusted.provider/sso"}
    )
    
    response = await client.post(
        "/federation/trust",
        json={
            "provider_id": str(test_provider.id),
            "trusted_provider_id": str(trusted_provider.id),
            "trust_level": "direct",
            "valid_days": 30,
            "metadata": {"reason": "test"}
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["provider_id"] == str(test_provider.id)
    assert data["trusted_provider_id"] == str(trusted_provider.id)
    assert data["trust_level"] == "direct"
    assert "valid_from" in data
    assert "valid_until" in data

@pytest.mark.asyncio
async def test_revoke_trust_relationship(
    client: AsyncClient,
    test_provider,
    federation_service
):
    """Test revoking trust relationship endpoint."""
    trusted_provider = IdentityProvider(
        name="Trusted Provider",
        entity_id="trusted.provider",
        metadata={"sso_url": "https://trusted.provider/sso"}
    )
    
    # First establish trust
    await federation_service.establish_trust(
        str(test_provider.id),
        str(trusted_provider.id)
    )
    
    # Then revoke it
    response = await client.delete(
        f"/federation/trust/{test_provider.id}/{trusted_provider.id}"
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    
    # Verify relationship is inactive
    relationship = await TrustRelationship.get_by_providers(
        test_provider.id,
        trusted_provider.id
    )
    assert relationship is not None
    assert relationship.is_active is False

@pytest.mark.asyncio
async def test_validate_trust_relationship(
    client: AsyncClient,
    test_provider,
    federation_service
):
    """Test validating trust relationship endpoint."""
    # Set up chain: A -> B -> C
    provider_b = IdentityProvider(
        name="Provider B",
        entity_id="provider.b",
        metadata={"sso_url": "https://provider.b/sso"}
    )
    provider_c = IdentityProvider(
        name="Provider C",
        entity_id="provider.c",
        metadata={"sso_url": "https://provider.c/sso"}
    )
    
    await federation_service.establish_trust(
        str(test_provider.id),
        str(provider_b.id)
    )
    await federation_service.establish_trust(
        str(provider_b.id),
        str(provider_c.id)
    )
    
    # Test direct trust
    response = await client.get(
        "/federation/trust/validate",
        params={
            "source_id": str(test_provider.id),
            "target_id": str(provider_b.id)
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["trusted"] is True
    
    # Test transitive trust
    response = await client.get(
        "/federation/trust/validate",
        params={
            "source_id": str(test_provider.id),
            "target_id": str(provider_c.id)
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["trusted"] is True
    
    # Test no trust
    response = await client.get(
        "/federation/trust/validate",
        params={
            "source_id": str(provider_c.id),
            "target_id": str(test_provider.id)
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["trusted"] is False

@pytest.mark.asyncio
async def test_create_attribute_mapping(
    client: AsyncClient,
    test_provider
):
    """Test creating attribute mapping endpoint."""
    response = await client.post(
        "/federation/attributes/mapping",
        json={
            "provider_id": str(test_provider.id),
            "source_attribute": "name",
            "target_attribute": "display_name",
            "transform_function": None,
            "is_required": True
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["provider_id"] == str(test_provider.id)
    assert data["source_attribute"] == "name"
    assert data["target_attribute"] == "display_name" 
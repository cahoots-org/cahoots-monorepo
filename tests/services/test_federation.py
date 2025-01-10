"""Tests for federation service."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select

from src.services.federation import FederationService
from src.auth.federation.base import FederatedIdentity
from src.models.federation import (
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)

@pytest.fixture
async def federation_service(db_session):
    """Create federation service fixture."""
    service = FederationService(db_session)
    await service.initialize()
    return service

@pytest.fixture
async def test_identity():
    """Create test federated identity."""
    return FederatedIdentity(
        external_id=str(uuid4()),
        provider_id=str(uuid4()),
        attributes={
            "name": "Test User",
            "email": "test@example.com",
            "role": "user"
        }
    )

@pytest.fixture
async def test_user(db_session):
    """Create test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_get_federated_identity_not_found(
    federation_service,
    test_user
):
    """Test getting non-existent federated identity."""
    identity = await federation_service.get_federated_identity(
        str(test_user.id),
        str(uuid4())
    )
    assert identity is None

@pytest.mark.asyncio
async def test_link_identity(
    federation_service,
    test_user,
    test_identity
):
    """Test linking federated identity."""
    success = await federation_service.link_identity(
        str(test_user.id),
        test_identity
    )
    assert success is True
    
    # Verify mapping was created
    stmt = select(FederatedIdentityMapping).where(
        FederatedIdentityMapping.user_id == test_user.id,
        FederatedIdentityMapping.provider_id == test_identity.provider_id
    )
    result = await federation_service.db.execute(stmt)
    mapping = result.scalar_one_or_none()
    
    assert mapping is not None
    assert mapping.external_id == test_identity.external_id
    assert mapping.attributes == test_identity.attributes
    assert mapping.is_active is True

@pytest.mark.asyncio
async def test_link_identity_duplicate(
    federation_service,
    test_user,
    test_identity
):
    """Test linking duplicate identity."""
    # First link
    await federation_service.link_identity(str(test_user.id), test_identity)
    
    # Try to link again
    success = await federation_service.link_identity(
        str(test_user.id),
        test_identity
    )
    assert success is False

@pytest.mark.asyncio
async def test_unlink_identity(
    federation_service,
    test_user,
    test_identity
):
    """Test unlinking federated identity."""
    # First link
    await federation_service.link_identity(str(test_user.id), test_identity)
    
    # Then unlink
    success = await federation_service.unlink_identity(
        str(test_user.id),
        test_identity.provider_id
    )
    assert success is True
    
    # Verify mapping is inactive
    stmt = select(FederatedIdentityMapping).where(
        FederatedIdentityMapping.user_id == test_user.id,
        FederatedIdentityMapping.provider_id == test_identity.provider_id
    )
    result = await federation_service.db.execute(stmt)
    mapping = result.scalar_one_or_none()
    
    assert mapping is not None
    assert mapping.is_active is False

@pytest.mark.asyncio
async def test_sync_attributes(
    federation_service,
    test_user,
    test_identity,
    db_session
):
    """Test synchronizing identity attributes."""
    # Create attribute mappings
    mappings = [
        AttributeMapping(
            provider_id=test_identity.provider_id,
            source_attribute="name",
            target_attribute="display_name"
        ),
        AttributeMapping(
            provider_id=test_identity.provider_id,
            source_attribute="role",
            target_attribute="user_role"
        )
    ]
    for mapping in mappings:
        db_session.add(mapping)
    await db_session.commit()
    
    # Link identity
    await federation_service.link_identity(str(test_user.id), test_identity)
    
    # Sync attributes
    new_attrs = {
        "name": "Updated User",
        "role": "admin",
        "extra": "ignored"
    }
    mapped_attrs = await federation_service.sync_attributes(
        str(test_user.id),
        test_identity.provider_id,
        new_attrs
    )
    
    assert mapped_attrs == {
        "display_name": "Updated User",
        "user_role": "admin"
    }
    
    # Verify mapping was updated
    stmt = select(FederatedIdentityMapping).where(
        FederatedIdentityMapping.user_id == test_user.id,
        FederatedIdentityMapping.provider_id == test_identity.provider_id
    )
    result = await federation_service.db.execute(stmt)
    mapping = result.scalar_one_or_none()
    
    assert mapping.attributes["display_name"] == "Updated User"
    assert mapping.attributes["user_role"] == "admin"
    assert "extra" not in mapping.attributes

@pytest.mark.asyncio
async def test_establish_trust(federation_service):
    """Test establishing trust relationship."""
    provider_id = str(uuid4())
    trusted_id = str(uuid4())
    
    relationship = await federation_service.establish_trust(
        provider_id=provider_id,
        trusted_provider_id=trusted_id,
        trust_level="direct",
        valid_days=30,
        metadata={"reason": "test"}
    )
    
    assert relationship.provider_id == provider_id
    assert relationship.trusted_provider_id == trusted_id
    assert relationship.trust_level == "direct"
    assert relationship.metadata == {"reason": "test"}
    assert relationship.is_active is True
    assert relationship.valid_until > datetime.utcnow()
    
    # Verify trust chain was updated
    assert federation_service.trust_chain.validate_chain(
        provider_id,
        trusted_id
    ) is True

@pytest.mark.asyncio
async def test_revoke_trust(federation_service):
    """Test revoking trust relationship."""
    provider_id = str(uuid4())
    trusted_id = str(uuid4())
    
    # First establish trust
    await federation_service.establish_trust(
        provider_id=provider_id,
        trusted_provider_id=trusted_id
    )
    
    # Then revoke it
    success = await federation_service.revoke_trust(provider_id, trusted_id)
    assert success is True
    
    # Verify relationship is inactive
    stmt = select(TrustRelationship).where(
        TrustRelationship.provider_id == provider_id,
        TrustRelationship.trusted_provider_id == trusted_id
    )
    result = await federation_service.db.execute(stmt)
    relationship = result.scalar_one_or_none()
    
    assert relationship is not None
    assert relationship.is_active is False
    assert relationship.valid_until <= datetime.utcnow()
    
    # Verify trust chain was updated
    assert federation_service.trust_chain.validate_chain(
        provider_id,
        trusted_id
    ) is False

@pytest.mark.asyncio
async def test_validate_trust(federation_service):
    """Test trust validation."""
    # Set up chain: A -> B -> C
    provider_a = str(uuid4())
    provider_b = str(uuid4())
    provider_c = str(uuid4())
    
    await federation_service.establish_trust(provider_a, provider_b)
    await federation_service.establish_trust(provider_b, provider_c)
    
    # Direct trust
    assert await federation_service.validate_trust(provider_a, provider_b) is True
    assert await federation_service.validate_trust(provider_b, provider_c) is True
    
    # Transitive trust
    assert await federation_service.validate_trust(provider_a, provider_c) is True
    
    # No trust
    assert await federation_service.validate_trust(provider_c, provider_a) is False 
"""Test federation routes."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.auth.federation.base import FederatedIdentity
from src.models.user import User
from src.models.identity_provider import IdentityProvider
from src.models.federation import (
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)
from src.services.federation import FederationService

@pytest.mark.asyncio
async def test_link_federated_identity(
    test_user,
    test_provider,
    mock_deps
):
    """Test linking federated identity."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    federated_identity = FederatedIdentity(
        external_id="ext123",
        provider_id=test_provider.id,
        attributes={
            "name": "Test User",
            "email": "test@example.com"
        }
    )

    # Configure mock to return no existing mapping
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = None

    success = await service.link_identity(test_user.id, federated_identity)
    assert success is True

@pytest.mark.asyncio
async def test_link_federated_identity_duplicate(
    test_user,
    test_provider,
    mock_deps
):
    """Test duplicate linking of federated identity."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    # Create initial mapping
    mapping = FederatedIdentityMapping(
        user_id=test_user.id,
        provider_id=test_provider.id,
        external_id="ext123",
        attributes={},
        mapping_metadata={}
    )
    mock_deps.db.add(mapping)
    await mock_deps.db.commit()

    # Configure mock to return existing mapping
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = mapping

    federated_identity = FederatedIdentity(
        external_id="ext123",
        provider_id=test_provider.id,
        attributes={
            "name": "Test User",
            "email": "test@example.com"
        }
    )

    success = await service.link_identity(test_user.id, federated_identity)
    assert success is False

@pytest.mark.asyncio
async def test_unlink_federated_identity(
    test_user,
    test_provider,
    mock_deps
):
    """Test unlinking federated identity."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    # Create mapping to unlink
    mapping = FederatedIdentityMapping(
        user_id=test_user.id,
        provider_id=test_provider.id,
        external_id="ext123",
        attributes={},
        mapping_metadata={}
    )
    mock_deps.db.add(mapping)
    await mock_deps.db.commit()

    # Configure mock to return mapping
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = mapping

    success = await service.unlink_identity(str(mapping.id))
    assert success is True

@pytest.mark.asyncio
async def test_establish_trust_relationship(
    test_provider,
    mock_deps
):
    """Test establishing trust relationship."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    target_provider = IdentityProvider(
        name="Target Provider",
        type="saml",
        entity_id="test_entity",
        provider_metadata={}
    )
    mock_deps.db.add(target_provider)
    await mock_deps.db.commit()

    relationship = await service.establish_trust(
        provider_id=test_provider.id,
        trusted_provider_id=target_provider.id,
        trust_level="high"
    )
    assert relationship is not None
    assert relationship.provider_id == test_provider.id
    assert relationship.trusted_provider_id == target_provider.id

@pytest.mark.asyncio
async def test_revoke_trust_relationship(
    test_provider,
    mock_deps
):
    """Test revoking trust relationship."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    target_provider = IdentityProvider(
        name="Target Provider",
        type="saml",
        entity_id="test_entity",
        provider_metadata={}
    )
    mock_deps.db.add(target_provider)
    await mock_deps.db.commit()

    # Create relationship to revoke
    relationship = TrustRelationship(
        provider_id=test_provider.id,
        trusted_provider_id=target_provider.id,
        trust_level="high"
    )
    mock_deps.db.add(relationship)
    await mock_deps.db.commit()

    # Configure mock to return relationship
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = relationship

    success = await service.revoke_trust(str(relationship.id))
    assert success is True

@pytest.mark.asyncio
async def test_validate_trust_relationship(
    test_provider,
    mock_deps
):
    """Test validating trust relationship."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    target_provider = IdentityProvider(
        name="Target Provider",
        type="saml",
        entity_id="test_entity",
        provider_metadata={}
    )
    mock_deps.db.add(target_provider)
    await mock_deps.db.commit()

    # Create relationship to validate
    relationship = TrustRelationship(
        provider_id=test_provider.id,
        trusted_provider_id=target_provider.id,
        trust_level="high",
        is_active=True,
        valid_until=datetime.utcnow() + timedelta(days=1)
    )
    mock_deps.db.add(relationship)
    await mock_deps.db.commit()

    # Configure mock to return relationship for initialize()
    mock_deps.db.execute.return_value.scalars.return_value.all.return_value = [relationship]

    # Re-initialize to load the trust relationship
    await service.initialize()

    is_trusted = await service.validate_trust(
        provider_id=str(test_provider.id),
        target_provider_id=str(target_provider.id)
    )
    assert is_trusted is True

@pytest.mark.asyncio
async def test_create_attribute_mapping(
    test_provider,
    mock_deps
):
    """Test creating attribute mapping."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    # Configure mock to return provider
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = test_provider

    mapping = await service.create_attribute_mapping(
        provider_id=test_provider.id,
        source_attribute="email",
        target_attribute="user_email",
        transform_function="lowercase"
    )
    assert mapping is not None
    assert mapping.provider_id == test_provider.id
    assert mapping.source_attribute == "email"
    assert mapping.target_attribute == "user_email"

@pytest.mark.asyncio
async def test_sync_identity_attributes(
    test_user,
    test_provider,
    mock_deps
):
    """Test syncing identity attributes."""
    service = FederationService(deps=mock_deps)
    await service.initialize()

    # Create federated identity mapping
    mapping = FederatedIdentityMapping(
        user_id=test_user.id,
        provider_id=test_provider.id,
        external_id="ext123",
        attributes={
            "name": "Test User",
            "email": "test@example.com"
        },
        mapping_metadata={}
    )
    mock_deps.db.add(mapping)
    await mock_deps.db.commit()

    # Configure mock to return mapping and attribute mappings
    mock_deps.db.execute.return_value.scalar_one_or_none.return_value = mapping
    mock_deps.db.execute.return_value.scalars.return_value.all.return_value = [
        AttributeMapping(
            provider_id=test_provider.id,
            source_attribute="name",
            target_attribute="name"
        ),
        AttributeMapping(
            provider_id=test_provider.id,
            source_attribute="email",
            target_attribute="email"
        )
    ]

    new_attributes = {
        "name": "Updated User",
        "email": "updated@example.com"
    }

    updated_attrs = await service.sync_attributes(str(mapping.id), new_attributes)
    assert updated_attrs == new_attributes 
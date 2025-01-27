"""Federation service tests."""
from typing import cast
import pytest
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Select, Update, select, update, insert

from cahoots_core.services.federation import FederationService
from cahoots_core.models.federation import (
    FederatedIdentity,
    FederatedIdentityMapping,
    TrustRelationship,
    AttributeMapping
)
from cahoots_core.validation.trust_chain import TrustChainValidator

# Test constants
TEST_USER_ID = str(uuid.uuid4())
TEST_PROVIDER_ID = str(uuid.uuid4())
TEST_EXTERNAL_ID = "test-external-id"
TEST_ATTRIBUTES = {"name": "Test User"}
TEST_METADATA = {"source": "test"}

class MockModel:
    """Mock SQLAlchemy model."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockDB:
    """Mock database client."""
    def __init__(self):
        self.mappings = {}
        self.relationships = {}
        self.attr_mappings = {}
        self.call_count = 0

    async def execute(self, stmt):
        """Execute statement."""
        self.call_count += 1

        if isinstance(stmt, insert):
            # Handle insert
            table = stmt.table.name
            values = stmt.parameters
            model_id = values.get("id") or str(uuid.uuid4())
            values.setdefault("id", model_id)

            if table == "federated_identity_mappings":
                self.mappings[model_id] = MockModel(**values)
            elif table == "trust_relationships":
                self.relationships[model_id] = MockModel(**values)
            elif table == "attribute_mappings":
                self.attr_mappings[model_id] = MockModel(**values)

            return MockResult(model_id)

        elif isinstance(stmt, update):
            # Handle update
            table = stmt.table.name
            values = stmt.parameters
            where_clause = (cast(Update, stmt))._where_criteria[0]
            model_id = where_clause.right.value

            if table == "federated_identity_mappings":
                if model_id in self.mappings:
                    for key, value in values.items():
                        setattr(self.mappings[model_id], key, value)
            elif table == "trust_relationships":
                if model_id in self.relationships:
                    for key, value in values.items():
                        setattr(self.relationships[model_id], key, value)

            return MockResult(None)

        elif isinstance(stmt, select):
            # Handle select
            table = cast(Select, stmt).froms[0].name
            where_clauses = stmt._where_criteria

            if table == "federated_identity_mappings":
                for mapping in self.mappings.values():
                    matches = True
                    for clause in where_clauses:
                        if not hasattr(mapping, clause.left.key) or getattr(mapping, clause.left.key) != clause.right.value:
                            matches = False
                            break
                    if matches:
                        return MockResult(mapping)
                return MockResult(None)

            elif table == "trust_relationships":
                matching = []
                for rel in self.relationships.values():
                    matches = True
                    for clause in where_clauses:
                        if not hasattr(rel, clause.left.key) or getattr(rel, clause.left.key) != clause.right.value:
                            matches = False
                            break
                    if matches:
                        matching.append(rel)
                return MockResult(matching)

            elif table == "attribute_mappings":
                matching = []
                for mapping in self.attr_mappings.values():
                    matches = True
                    for clause in where_clauses:
                        if not hasattr(mapping, clause.left.key) or getattr(mapping, clause.left.key) != clause.right.value:
                            matches = False
                            break
                    if matches:
                        matching.append(mapping)
                return MockResult(matching)

        return MockResult(None)

    async def commit(self):
        """Commit transaction."""
        pass

class MockResult:
    """Mock database result."""
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        """Return scalar result."""
        return self.value

    def scalars(self):
        """Return self to allow chaining."""
        return self

    def all(self):
        """Return all results."""
        if isinstance(self.value, list):
            return self.value
        return []

@pytest.fixture
def mock_db():
    """Create mock database."""
    return MockDB()

@pytest.fixture
def mock_trust_chain():
    """Create mock trust chain validator."""
    return TrustChainValidator()

@pytest.fixture
def federation_service(mock_db, mock_trust_chain):
    """Create federation service."""
    return FederationService(mock_db, mock_trust_chain)

@pytest.mark.asyncio
async def test_initialize_loads_trust_relationships(federation_service, mock_db, mock_trust_chain):
    """Test initialize loads active trust relationships."""
    # Arrange
    mock_relationships = [
        {
            "provider_id": str(uuid.uuid4()),
            "trusted_provider_id": str(uuid.uuid4()),
            "is_active": True,
            "valid_until": datetime.utcnow() + timedelta(days=1)
        }
        for _ in range(2)
    ]
    for rel in mock_relationships:
        await mock_db.execute(insert(TrustRelationship).values(rel))

    # Act
    await federation_service.initialize()

    # Assert
    assert mock_db.call_count == 3  # 2 inserts + 1 select

@pytest.mark.asyncio
async def test_get_federated_identity_found(federation_service, mock_db):
    """Test get federated identity when found."""
    # Arrange
    mock_mapping = {
        "external_id": TEST_EXTERNAL_ID,
        "provider_id": TEST_PROVIDER_ID,
        "attributes": TEST_ATTRIBUTES,
        "metadata": TEST_METADATA,
        "is_active": True
    }
    result = await mock_db.execute(insert(FederatedIdentityMapping).values(mock_mapping))
    mapping_id = result.value

    # Act
    result = await federation_service.get_federated_identity(mapping_id)

    # Assert
    assert result is not None
    assert result.external_id == TEST_EXTERNAL_ID
    assert result.provider_id == TEST_PROVIDER_ID
    assert result.attributes == TEST_ATTRIBUTES
    assert result.metadata == TEST_METADATA

@pytest.mark.asyncio
async def test_get_federated_identity_not_found(federation_service, mock_db):
    """Test get federated identity when not found."""
    # Act
    result = await federation_service.get_federated_identity(str(uuid.uuid4()))

    # Assert
    assert result is None

@pytest.mark.asyncio
async def test_link_identity_success(federation_service, mock_db):
    """Test link identity success."""
    # Arrange
    identity = FederatedIdentity(
        provider_id=TEST_PROVIDER_ID,
        external_id=TEST_EXTERNAL_ID,
        attributes=TEST_ATTRIBUTES,
        metadata=TEST_METADATA
    )

    # Act
    result = await federation_service.link_identity(TEST_USER_ID, identity)

    # Assert
    assert result is True
    assert mock_db.call_count == 2  # 1 select + 1 insert

@pytest.mark.asyncio
async def test_link_identity_already_exists(federation_service, mock_db):
    """Test link identity when already exists."""
    # Arrange
    mock_mapping = {
        "external_id": TEST_EXTERNAL_ID,
        "provider_id": TEST_PROVIDER_ID,
        "attributes": TEST_ATTRIBUTES,
        "metadata": TEST_METADATA,
        "is_active": True
    }
    await mock_db.execute(insert(FederatedIdentityMapping).values(mock_mapping))

    identity = FederatedIdentity(
        provider_id=TEST_PROVIDER_ID,
        external_id=TEST_EXTERNAL_ID,
        attributes=TEST_ATTRIBUTES,
        metadata=TEST_METADATA
    )

    # Act
    result = await federation_service.link_identity(TEST_USER_ID, identity)

    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_unlink_identity_success(federation_service, mock_db):
    """Test unlink identity success."""
    # Arrange
    mock_mapping = {
        "external_id": TEST_EXTERNAL_ID,
        "provider_id": TEST_PROVIDER_ID,
        "attributes": TEST_ATTRIBUTES,
        "metadata": TEST_METADATA,
        "is_active": True
    }
    result = await mock_db.execute(insert(FederatedIdentityMapping).values(mock_mapping))
    mapping_id = result.value

    # Act
    result = await federation_service.unlink_identity(mapping_id)

    # Assert
    assert result is True
    assert mock_db.call_count == 3  # 1 insert + 1 select + 1 update

@pytest.mark.asyncio
async def test_unlink_identity_not_found(federation_service, mock_db):
    """Test unlink identity when not found."""
    # Act
    result = await federation_service.unlink_identity(str(uuid.uuid4()))

    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_sync_attributes_success(federation_service, mock_db):
    """Test sync attributes success."""
    # Arrange
    provider_id = TEST_PROVIDER_ID
    mock_mapping = {
        "provider_id": provider_id,
        "attributes": {"name": "Old Name"},
        "is_active": True
    }
    result = await mock_db.execute(insert(FederatedIdentityMapping).values(mock_mapping))
    mapping_id = result.value

    mock_attr_mapping = {
        "provider_id": provider_id,
        "source_attribute": "name",
        "target_attribute": "display_name",
        "transform_function": None
    }
    await mock_db.execute(insert(AttributeMapping).values(mock_attr_mapping))

    # Act
    result = await federation_service.sync_attributes(mapping_id, {"name": "New Name"})

    # Assert
    assert result == {"name": "Old Name", "display_name": "New Name"}
    assert mock_db.call_count == 4  # 2 inserts + 1 select + 1 update

@pytest.mark.asyncio
async def test_sync_attributes_mapping_not_found(federation_service, mock_db):
    """Test sync attributes when mapping not found."""
    # Act
    result = await federation_service.sync_attributes(str(uuid.uuid4()), {"name": "New Name"})

    # Assert
    assert result == {}

@pytest.mark.asyncio
async def test_establish_trust_success(federation_service, mock_db, mock_trust_chain):
    """Test establish trust success."""
    # Arrange
    provider_id = str(uuid.uuid4())
    trusted_provider_id = str(uuid.uuid4())
    trust_level = "direct"

    # Act
    result = await federation_service.establish_trust(
        provider_id,
        trusted_provider_id,
        trust_level=trust_level
    )

    # Assert
    assert result is not None
    assert result.provider_id == provider_id
    assert result.trusted_provider_id == trusted_provider_id
    assert result.trust_level == trust_level
    assert result.is_active is True
    assert mock_db.call_count == 1  # 1 insert

@pytest.mark.asyncio
async def test_revoke_trust_success(federation_service, mock_db, mock_trust_chain):
    """Test revoke trust success."""
    # Arrange
    provider_id = str(uuid.uuid4())
    trusted_provider_id = str(uuid.uuid4())
    mock_relationship = {
        "provider_id": provider_id,
        "trusted_provider_id": trusted_provider_id,
        "is_active": True
    }
    result = await mock_db.execute(insert(TrustRelationship).values(mock_relationship))
    relationship_id = result.value

    mock_trust_chain.add_trust(provider_id, trusted_provider_id)

    # Act
    result = await federation_service.revoke_trust(relationship_id)

    # Assert
    assert result is True
    assert mock_db.call_count == 3  # 1 insert + 1 select + 1 update

@pytest.mark.asyncio
async def test_revoke_trust_not_found(federation_service, mock_db):
    """Test revoke trust when not found."""
    # Act
    result = await federation_service.revoke_trust(str(uuid.uuid4()))

    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_validate_trust_direct(federation_service, mock_trust_chain):
    """Test validate trust with direct trust."""
    # Arrange
    provider_id = str(uuid.uuid4())
    trusted_provider_id = str(uuid.uuid4())
    mock_trust_chain.add_trust(provider_id, trusted_provider_id)

    # Act
    result = federation_service.validate_trust(provider_id, trusted_provider_id)

    # Assert
    assert result is True

@pytest.mark.asyncio
async def test_validate_trust_no_path(federation_service, mock_trust_chain):
    """Test validate trust with no trust path."""
    # Act
    result = federation_service.validate_trust(str(uuid.uuid4()), str(uuid.uuid4()))

    # Assert
    assert result is False 
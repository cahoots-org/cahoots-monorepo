"""Tests for FederationService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.federation import FederationService
from src.core.dependencies import ServiceDeps

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.db = AsyncMock()
    deps.event_system = AsyncMock()
    return deps

@pytest.fixture
def federation_service(mock_deps):
    """Create FederationService instance with mock dependencies."""
    return FederationService(deps=mock_deps)

@pytest.mark.asyncio
async def test_federation_service_init(mock_deps):
    """Test FederationService initialization."""
    service = FederationService(deps=mock_deps)
    assert service.db == mock_deps.db
    assert service.event_system == mock_deps.event_system 
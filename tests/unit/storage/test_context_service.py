import pytest
from uuid import uuid4
from datetime import datetime
from src.cahoots_context.storage.context_service import ContextEventService
from src.cahoots_context.models.context import ContextEvent
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def sample_context_event():
    """Create a sample context event."""
    return ContextEvent(
        id=str(uuid4()),
        project_id=str(uuid4()),
        event_type="requirement_added",
        event_data={"requirement": "Add authentication"},
        timestamp=datetime.utcnow(),
        version_vector={"node1": 1}
    )

@pytest.mark.asyncio
async def test_build_context_from_events(context_service, sample_context_event):
    """Test building context from event sequence."""
    events = [
        sample_context_event,
        ContextEvent(
            id=str(uuid4()),
            project_id=str(sample_context_event.project_id),
            event_type="architectural_decision",
            event_data={"decision": "Use microservices"},
            timestamp=datetime.utcnow(),
            version_vector={"node1": 2}
        ),
        ContextEvent(
            id=str(uuid4()),
            project_id=str(sample_context_event.project_id),
            event_type="standard_update",
            event_data={"coding_style": "PEP 8"},
            timestamp=datetime.utcnow(),
            version_vector={"node1": 3}
        )
    ]
    
    # Mock the get_events method to return our test events
    context_service._db_client.get_events = AsyncMock(return_value=events)
    
    # Build context from events
    context = await context_service.build_context(sample_context_event.project_id)
    
    # Verify the context contains all event data
    assert len(context["events"]) == 3
    assert context["events"][0]["event_type"] == "requirement_added"
    assert context["events"][1]["event_type"] == "architectural_decision"
    assert context["events"][2]["event_type"] == "standard_update"
    
    # Verify event data is preserved
    assert context["events"][0]["event_data"]["requirement"] == "Add authentication"
    assert context["events"][1]["event_data"]["decision"] == "Use microservices"
    assert context["events"][2]["event_data"]["coding_style"] == "PEP 8"

@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    manager = Mock()
    manager.get = AsyncMock()
    manager.set = AsyncMock()
    manager.delete = AsyncMock()
    return manager

@pytest.fixture
def mock_db_client():
    """Create a mock database client."""
    client = Mock()
    client.get_events = AsyncMock()
    client.add_event = AsyncMock()
    client.get_latest_version = AsyncMock(return_value={"node1": 0})
    return client

@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = Mock()
    client.get = AsyncMock()
    client.set = AsyncMock()
    client.delete = AsyncMock()
    return client

@pytest.fixture
def context_service(mock_db_client, mock_redis_client, mock_cache_manager):
    """Create a ContextEventService instance with mocked dependencies."""
    with patch("cahoots_context.storage.context_service.get_db_client", return_value=mock_db_client), \
         patch("cahoots_context.storage.context_service.get_redis_client", return_value=mock_redis_client), \
         patch("cahoots_context.storage.context_service.CacheManager", return_value=mock_cache_manager):
        service = ContextEventService()
        return service 
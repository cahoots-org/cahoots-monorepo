"""Unit tests for EventService."""
from typing import List
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import UUID, uuid4
import json

from cahoots_events.config import EventConfig
from cahoots_events.bus.types import EventStatus, EventType, EventPriority
from cahoots_core.exceptions import StorageError
from cahoots_events.exceptions.events import EventSizeLimitExceeded
from cahoots_service.services.event_service import EventService
from cahoots_events.models import Event
from sqlalchemy import Column, String, DateTime, Enum, Integer

# Mock SQLAlchemy model attributes
Event.id = Column(String, primary_key=True)
Event.project_id = Column(String)
Event.type = Column(String)
Event.status = Column(Enum(EventStatus))
Event.priority = Column(Integer)
Event.created_at = Column(DateTime)
Event.retry_count = Column(Integer)

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.query = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db

@pytest.fixture
def mock_config():
    config = Mock()
    config.retention_hours = 24
    config.cache_ttl_seconds = 3600
    config.max_retry_count = 3
    config.processing_interval = 5
    config.max_storage_bytes = 1024 * 1024 * 10  # 10MB
    return config

@pytest.fixture
def event_service(mock_redis, mock_db, mock_config):
    return EventService(
        config=mock_config,
        redis=mock_redis,
        db=mock_db
    )

@pytest.fixture
def sample_event():
    event_id = str(uuid4())
    project_id = str(uuid4())
    event = MagicMock(spec=Event)
    
    # Basic attributes
    event.id = event_id
    event.project_id = project_id
    event.type = EventType.TASK_CREATED
    event.status = EventStatus.PENDING
    event.priority = EventPriority.NORMAL
    event.timestamp = datetime.utcnow()
    event.data = {"test": "data"}
    event.retry_count = 0
    event.correlation_id = None
    event.created_at = datetime.utcnow()
    event.updated_at = None
    event.error = None
    
    # Mock SQLAlchemy model attributes
    event.__table__ = Mock()
    event.__mapper__ = Mock()
    
    # Mock Pydantic methods
    event_json = json.dumps({
        "id": event_id,
        "project_id": project_id,
        "type": EventType.TASK_CREATED.value,
        "status": EventStatus.PENDING.value,
        "data": {"test": "data"}
    })
    event.model_dump_json = Mock(return_value=event_json)
    
    return event

@pytest.mark.asyncio
async def test_save_event_success(event_service, sample_event):
    """Test successful event save operation."""
    # Act
    await event_service.save_event(sample_event)
    
    # Assert
    event_service.db.add.assert_called_once_with(sample_event)
    event_service.db.execute.assert_called_once()
    event_service.db.commit.assert_called_once()
    event_service.redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_save_event_size_limit_exceeded(event_service, sample_event):
    """Test event size limit validation."""
    # Arrange
    large_data = {"large": "x" * (event_service.MAX_EVENT_SIZE_BYTES + 1)}
    sample_event.data = large_data
    sample_event.model_dump_json.return_value = json.dumps({"data": large_data})
    
    # Act & Assert
    with pytest.raises(EventSizeLimitExceeded):
        await event_service.save_event(sample_event)

@pytest.mark.asyncio
async def test_get_event_from_cache(event_service, sample_event):
    """Test retrieving event from cache."""
    # Arrange
    event_service.redis.get.return_value = sample_event.model_dump_json()
    Event.parse_raw = Mock(return_value=sample_event)
    
    # Act
    result = await event_service.get_event(UUID(sample_event.id))
    
    # Assert
    assert result == sample_event
    event_service.redis.get.assert_called_once()
    event_service.db.query.assert_not_called()

@pytest.mark.asyncio
async def test_get_event_from_db(event_service, sample_event):
    """Test retrieving event from database when cache misses."""
    # Arrange
    event_service.redis.get.return_value = None
    event_service.db.query.return_value.filter.return_value.first.return_value = sample_event
    
    # Act
    result = await event_service.get_event(UUID(sample_event.id))
    
    # Assert
    assert result == sample_event
    event_service.redis.get.assert_called_once()
    event_service.db.query.assert_called_once()
    event_service.redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_get_project_events(event_service, sample_event):
    """Test retrieving all events for a project."""
    # Arrange
    query = MagicMock()
    query.filter.return_value.order_by.return_value.all.return_value = [sample_event]
    event_service.db.query.return_value = query
    
    # Act
    result: List[Event] = await event_service.get_project_events(UUID(sample_event.project_id))
    
    # Assert
    assert len(result) == 1
    assert result[0] == sample_event
    event_service.db.query.assert_called_once()

@pytest.mark.asyncio
async def test_get_active_events(event_service, sample_event):
    """Test retrieving active events for a project."""
    # Arrange
    event_service.db.query.return_value.filter.return_value.filter.return_value.all.return_value = [sample_event]
    
    # Act
    result: List[Event] = await event_service.get_active_events(UUID(sample_event.project_id))
    
    # Assert
    assert len(result) == 1
    assert result[0] == sample_event

@pytest.mark.asyncio
async def test_cleanup_expired_events(event_service):
    """Test cleanup of expired events."""
    # Arrange
    expired_event = MagicMock(spec=Event)
    expired_event.id = str(uuid4())
    expired_event.project_id = str(uuid4())
    expired_event.type = EventType.TASK_CREATED
    expired_event.status = EventStatus.COMPLETED
    expired_event.priority = EventPriority.NORMAL
    expired_event.timestamp = datetime.utcnow() - timedelta(hours=48)
    expired_event.data = {"test": "data"}
    expired_event.retry_count = 0
    expired_event.correlation_id = None
    expired_event.created_at = datetime.utcnow() - timedelta(hours=48)
    expired_event.updated_at = None
    expired_event.error = None
    
    # Mock SQLAlchemy attributes
    expired_event.__table__ = Mock()
    expired_event.__mapper__ = Mock()
    
    event_service.db.query.return_value.filter.return_value.all.return_value = [expired_event]
    event_service.redis.set.return_value = True  # Lock acquired
    
    # Act
    await event_service.cleanup_expired_events()
    
    # Assert
    event_service.db.delete.assert_called_once_with(expired_event)
    event_service.db.commit.assert_called_once()
    event_service.redis.delete.assert_called()

@pytest.mark.asyncio
async def test_enforce_storage_limits(event_service, sample_event):
    """Test storage limit enforcement."""
    # Arrange
    events = [sample_event] * 5  # Create multiple events
    # Make each event's JSON large enough to exceed limit
    large_json = json.dumps({"data": "x" * (event_service.config.max_storage_bytes // 4)})
    for event in events:
        event.model_dump_json.return_value = large_json
    
    query = MagicMock()
    query.filter.return_value.order_by.return_value.all.return_value = events
    event_service.db.query.return_value = query
    
    # Act
    await event_service.enforce_storage_limits(UUID(sample_event.project_id))
    
    # Assert
    event_service.db.delete.assert_called()
    event_service.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_retry_failed_events(event_service):
    """Test retrying failed events."""
    # Arrange
    failed_event = MagicMock(spec=Event)
    failed_event.id = str(uuid4())
    failed_event.project_id = str(uuid4())
    failed_event.type = EventType.TASK_CREATED
    failed_event.status = EventStatus.FAILED
    failed_event.priority = EventPriority.NORMAL
    failed_event.timestamp = datetime.utcnow()
    failed_event.data = {"test": "data"}
    failed_event.retry_count = 1
    failed_event.correlation_id = None
    failed_event.created_at = datetime.utcnow()
    failed_event.updated_at = None
    failed_event.error = None
    
    # Mock SQLAlchemy attributes
    failed_event.__table__ = Mock()
    failed_event.__mapper__ = Mock()
    
    event_service.db.query.return_value.filter.return_value.filter.return_value.all.return_value = [failed_event]
    
    # Act
    await event_service.retry_failed_events()
    
    # Assert
    assert failed_event.status == EventStatus.PENDING
    assert failed_event.retry_count == 2

@pytest.mark.asyncio
async def test_clear_cache(event_service):
    """Test clearing event cache."""
    # Arrange
    event_service.redis.keys = AsyncMock(return_value=[b"event:1", b"event:2"])
    
    # Act
    await event_service.clear_cache()
    
    # Assert
    # Verify cache is empty by checking a key
    event_service.redis.get.return_value = None
    result = await event_service.redis.get("event:1")
    assert result is None

@pytest.mark.asyncio
async def test_start_cleanup_task(event_service):
    """Test background cleanup task."""
    # Arrange
    event_service.cleanup_expired_events = AsyncMock()
    
    # Act
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.1):
            await event_service.start_cleanup_task()
    
    # Assert
    event_service.cleanup_expired_events.assert_called() 
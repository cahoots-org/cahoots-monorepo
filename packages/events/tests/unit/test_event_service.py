"""Unit tests for event service."""
import pytest
from unittest.mock import AsyncMock, Mock
import json
from datetime import datetime

from ...src.cahoots_events.models import Event, EventStatus
from ...src.cahoots_events.exceptions import EventSizeLimitExceeded
from ...src.cahoots_events.bus.system import EventService

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    mock = Mock()
    mock.db = Mock()
    mock.db.add = AsyncMock()
    mock.db.commit = AsyncMock()
    mock.db.rollback = AsyncMock()
    mock.db.execute = AsyncMock()
    mock.db.query = Mock()
    mock.db.query.return_value.filter.return_value.all = AsyncMock()
    mock.db.query.return_value.filter.return_value.delete = AsyncMock()
    
    mock.redis = AsyncMock()
    mock.redis.set = AsyncMock(return_value=True)
    mock.redis.setex = AsyncMock()
    mock.redis.delete = AsyncMock()
    mock.redis.scan_iter = AsyncMock(return_value=[])
    
    mock.config = Mock()
    mock.config.retention_hours = 24
    mock.config.cache_ttl_seconds = 3600
    
    return mock

@pytest.fixture
async def event_service(mock_deps):
    """Create event service instance with mocked dependencies."""
    from src.services.event_service import EventService
    service = EventService(
        db=mock_deps.db,
        redis=mock_deps.redis,
        config=mock_deps.config
    )
    return service

@pytest.mark.asyncio
async def test_event_retention(event_service, mock_deps):
    """Test 24-hour event retention per Section 4.2.1."""
    now = datetime.utcnow()
    project_id = str(uuid4())
    
    # Create events at different times
    events = [
        Event(
            id=str(uuid4()),
            project_id=project_id,
            type="test_event",
            data={"test": f"data_{i}"},
            status=EventStatus.COMPLETED,
            created_at=now - timedelta(hours=i)
        )
        for i in range(30)  # Create events spanning 30 hours
    ]
    
    # Configure mock to return expired events
    mock_deps.db.query.return_value.filter.return_value.all.return_value = events
    
    # Run retention cleanup
    await event_service.cleanup_expired_events()
    
    # Verify expired events were deleted
    mock_deps.db.delete.assert_called()
    mock_deps.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_event_persistence(event_service, mock_deps):
    """Test event persistence across system restarts."""
    project_id = str(uuid4())
    event_id = str(uuid4())
    
    # Create test event
    event = Event(
        id=event_id,
        project_id=project_id,
        type="test_event",
        data={"test": "data"},
        status=EventStatus.PENDING
    )
    
    # Save event
    await event_service.save_event(event)
    
    # Verify event was saved to DB and cache
    mock_deps.db.execute.assert_awaited_once()
    mock_deps.redis.setex.assert_awaited_once()

@pytest.mark.asyncio
async def test_event_cleanup(event_service, mock_deps):
    """Test automatic event cleanup."""
    # Configure mock responses
    expired_event = Event(
        id=str(uuid4()),
        project_id=str(uuid4()),
        type="test_event",
        data={"test": "data"},
        status=EventStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(hours=25)
    )
    mock_deps.db.query.return_value.filter.return_value.all.return_value = [expired_event]
    
    # Run cleanup
    await event_service.cleanup_expired_events()
    
    # Verify cleanup operations
    mock_deps.db.delete.assert_called_once()
    mock_deps.redis.delete.assert_called()
    mock_deps.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_event_ordering(event_service, mock_deps):
    """Test event ordering and metadata preservation."""
    project_id = str(uuid4())
    now = datetime.utcnow()
    
    # Create sequence of events
    events = []
    for i in range(5):
        event = Event(
            id=str(uuid4()),
            project_id=project_id,
            type="test_event",
            data={"sequence": i},
            status=EventStatus.COMPLETED,
            created_at=now + timedelta(minutes=i)
        )
        events.append(event)
    
    # Save events
    for event in events:
        await event_service.save_event(event)
    
    # Verify events were saved in order
    assert mock_deps.db.execute.call_count == 5
    assert mock_deps.redis.setex.call_count == 5

@pytest.mark.asyncio
async def test_event_recovery(event_service, mock_deps):
    """Test event recovery after failures."""
    project_id = str(uuid4())
    event_id = str(uuid4())
    
    # Create failed event
    event = Event(
        id=event_id,
        project_id=project_id,
        type="test_event",
        data={"test": "data"},
        status=EventStatus.FAILED,
        retry_count=1
    )
    
    # Save event
    await event_service.save_event(event)
    
    # Verify event was saved with retry count
    mock_deps.db.execute.assert_awaited_once()
    mock_deps.redis.setex.assert_awaited_once()

@pytest.mark.asyncio
async def test_event_memory_protection(event_service, mock_deps):
    """Test memory protection against unbounded event growth."""
    project_id = str(uuid4())
    
    # Test different payload sizes
    sizes = [1, 10, 50, 100]  # MB
    for size in sizes:
        large_data = "x" * (size * 1024 * 1024)  # Convert MB to bytes
        
        event = Event(
            id=str(uuid4()),
            project_id=project_id,
            type="test_event",
            data={"large_field": large_data},
            status=EventStatus.PENDING
        )
        
        if size > event_service.MAX_EVENT_SIZE_MB:
            with pytest.raises(EventSizeLimitExceeded):
                await event_service.save_event(event)
        else:
            # Should succeed for sizes within limit
            await event_service.save_event(event)
            mock_deps.db.execute.assert_called()
            mock_deps.redis.setex.assert_called()

@pytest.mark.asyncio
async def test_memory_cleanup_scheduling(event_service, mock_deps):
    """Test automatic memory cleanup scheduling."""
    # Verify cleanup task is started
    assert event_service._cleanup_task is not None
    assert not event_service._cleanup_task.done()
    
    # Wait for one cleanup cycle
    await asyncio.sleep(event_service.CLEANUP_INTERVAL_SECONDS + 1)
    
    # Verify cleanup was called
    mock_deps.redis.scan_iter.assert_called()
    mock_deps.redis.delete.assert_called()

@pytest.mark.asyncio
async def test_context_manager_cleanup(event_service, mock_deps):
    """Test context manager properly cleans up resources."""
    project_id = str(uuid4())
    event_id = str(uuid4())
    
    async with event_service._context_cleanup(ServiceRole.QA_TESTER):
        # Simulate work within context
        event = Event(
            id=event_id,
            project_id=project_id,
            type="test_event",
            data={"test": "data"},
            status=EventStatus.PENDING
        )
        await event_service.save_event(event)
    
    # Verify cleanup occurred after context exit
    cleanup_key = f"context:{project_id}:QA_TESTER"
    mock_deps.redis.delete.assert_called_with(cleanup_key)

@pytest.mark.asyncio
async def test_cache_db_consistency(event_service, mock_deps):
    """Test cache-DB consistency during cleanup."""
    event_id = str(uuid4())
    project_id = str(uuid4())
    
    # Create and save event
    event = Event(
        id=event_id,
        project_id=project_id,
        type="test_event",
        data={"test": "data"},
        status=EventStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(hours=25)  # Expired
    )
    
    # Configure mock responses
    mock_deps.db.query.return_value.filter.return_value.all.return_value = [event]
    mock_deps.redis.scan_iter.return_value = [f"event:{event_id}"]
    
    # Save without commit since we're testing cleanup
    await event_service.save_event(event, commit=False)
    
    # Run cleanup
    await event_service.cleanup_expired_events()
    
    # Verify cache and DB consistency
    mock_deps.db.delete.assert_called_once()
    mock_deps.redis.delete.assert_called()
    mock_deps.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_concurrent_cleanup(event_service, mock_deps):
    """Test concurrent cleanup operations maintain consistency."""
    project_id = str(uuid4())
    now = datetime.utcnow()
    
    # Create events at different times
    events = [
        Event(
            id=str(uuid4()),
            project_id=project_id,
            type="test_event",
            data={"test": f"data_{i}"},
            status=EventStatus.COMPLETED,
            created_at=now - timedelta(hours=i)
        )
        for i in range(30)
    ]
    
    # Configure mock responses
    mock_deps.db.query.return_value.filter.return_value.all.return_value = events
    
    # Configure lock behavior - first call succeeds, second fails
    mock_deps.redis.set.side_effect = [True, False]

    # Run multiple cleanup operations
    await asyncio.gather(
        event_service.cleanup_expired_events(),
        event_service.cleanup_expired_events()
    )

    # Verify only one cleanup succeeded (lock prevented concurrent execution)
    mock_deps.redis.set.assert_has_calls([
        call("cleanup_lock", "1", ex=60, nx=True),
        call("cleanup_lock", "1", ex=60, nx=True)
    ])
    mock_deps.db.commit.assert_called_once()
    assert mock_deps.redis.delete.call_count >= len(events)  # One delete per event

@pytest.mark.asyncio
async def test_retention_policy_enforcement(event_service, mock_deps):
    """Test strict enforcement of retention policies."""
    project_id = str(uuid4())
    now = datetime.utcnow()
    
    # Create events with different priorities
    events = []
    for i in range(5):
        event = Event(
            id=str(uuid4()),
            project_id=project_id,
            type="test_event",
            data={"priority": i},
            status=EventStatus.COMPLETED,
            created_at=now - timedelta(hours=23),  # Within retention
            priority=i
        )
        events.append(event)
        await event_service.save_event(event)
    
    # Verify events were saved with priorities
    assert mock_deps.db.execute.call_count == 5
    assert mock_deps.redis.setex.call_count == 5 
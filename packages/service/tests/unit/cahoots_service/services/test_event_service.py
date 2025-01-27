"""Tests for event service."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List

from redis.asyncio import Redis
from cahoots_events.config import EventConfig
from cahoots_events.bus.types import EventStatus
from cahoots_events.models import Event
from cahoots_events.exceptions.events import EventSizeLimitExceeded

from cahoots_service.services.event_service import EventService

class MockDB:
    def __init__(self):
        self.events: Dict[str, Event] = {}
        
    async def add(self, event: Event) -> None:
        self.events[str(event.id)] = event
        
    async def delete(self, event: Event) -> None:
        if str(event.id) in self.events:
            del self.events[str(event.id)]
            
    async def get_event(self, event_id: str) -> Event:
        return self.events.get(str(event_id))
        
    async def get_project_events(self, project_id: str = None) -> List[Event]:
        if project_id:
            return [e for e in self.events.values() if str(e.project_id) == str(project_id)]
        return list(self.events.values())

@pytest.fixture
def mock_redis():
    class MockRedis:
        def __init__(self):
            self.data = {}
            
        async def setex(self, key: str, ttl: int, value: str) -> None:
            self.data[key] = value
            
        async def get(self, key: str) -> str:
            return self.data.get(key)
            
        async def delete(self, key: str) -> None:
            if key in self.data:
                del self.data[key]
                
        async def set(self, key: str, value: str, ex: int = None, nx: bool = False) -> bool:
            if nx and key in self.data:
                return False
            self.data[key] = value
            return True
    
    return MockRedis()

@pytest.fixture
def mock_db():
    return MockDB()

@pytest.fixture
def config():
    return EventConfig(
        max_event_size=1024 * 1024,
        retention_hours=24,
        cache_ttl_seconds=3600,
        max_retry_count=3
    )

@pytest.fixture
def event_service(mock_redis, mock_db, config):
    return EventService(config, mock_redis, mock_db)

@pytest.fixture
def create_event():
    def _create_event(
        status: EventStatus = EventStatus.PENDING,
        retry_count: int = 0,
        created_at: datetime = None
    ) -> Event:
        return Event(
            id=uuid4(),
            project_id=uuid4(),
            type="test_event",
            status=status,
            retry_count=retry_count,
            priority=1,
            data={"test": "data"},
            created_at=created_at or datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    return _create_event

@pytest.mark.asyncio
async def test_save_and_retrieve_event(event_service, create_event):
    """Test saving and retrieving an event."""
    event = create_event()
    await event_service.save_event(event)
    
    # Get from cache
    retrieved = await event_service.get_event(event.id)
    assert retrieved.id == event.id
    
    # Clear cache and get from DB
    await event_service.clear_cache(event.id)
    retrieved = await event_service.get_event(event.id)
    assert retrieved.id == event.id

@pytest.mark.asyncio
async def test_storage_limits(event_service, create_event):
    """Test event size limits are enforced."""
    event = create_event()
    event.data = {"large": "x" * (event_service.MAX_EVENT_SIZE_BYTES + 1)}
    
    with pytest.raises(EventSizeLimitExceeded):
        await event_service.save_event(event)

@pytest.mark.asyncio
async def test_project_events(event_service, create_event):
    """Test retrieving events for a project."""
    event1 = create_event()
    event2 = create_event()
    event2.project_id = event1.project_id
    
    await event_service.save_event(event1)
    await event_service.save_event(event2)
    
    events = await event_service.get_project_events(event1.project_id)
    assert len(events) == 2
    assert all(e.project_id == event1.project_id for e in events)

@pytest.mark.asyncio
async def test_event_lifecycle(event_service, create_event):
    """Test event lifecycle with cleanup."""
    old_event = create_event(created_at=datetime.utcnow() - timedelta(hours=25))
    new_event = create_event()
    
    await event_service.save_event(old_event)
    await event_service.save_event(new_event)
    
    await event_service.cleanup_expired_events()
    
    # Old event should be gone
    assert await event_service.get_event(old_event.id) is None
    # New event should remain
    assert await event_service.get_event(new_event.id) is not None

@pytest.mark.asyncio
async def test_event_retry_behavior(event_service, create_event):
    """Test retry behavior for failed events."""
    event = create_event(status=EventStatus.FAILED, retry_count=1)
    await event_service.save_event(event)
    
    await event_service.retry_failed_events()
    
    updated = await event_service.get_event(event.id)
    assert updated.status == EventStatus.PENDING
    assert updated.retry_count == 2 
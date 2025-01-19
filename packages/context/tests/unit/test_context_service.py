"""Unit tests for context service."""
import pytest
from unittest.mock import AsyncMock, Mock
import json
from datetime import datetime
from uuid import UUID

from cahoots_events.models import ContextEvent
from cahoots_core.models.project import Project
from cahoots_core.exceptions import ValidationError, StorageError
from cahoots_context.storage import ContextEventService
from cahoots_core.utils.version_vector import VersionVector
from cahoots_core.utils.exceptions import ContextLimitExceeded

@pytest.fixture
async def mock_deps():
    """Create mock dependencies."""
    deps = Mock()
    
    # Set up DB mock
    mock_db = AsyncMock()
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.query = Mock(return_value=mock_db)
    mock_db.filter = Mock(return_value=mock_db)
    mock_db.first = Mock(return_value=None)  # Default to None
    mock_db.all = Mock(return_value=[])  # Default to empty list
    mock_db.order_by = Mock(return_value=mock_db)
    
    deps.db = mock_db
    
    # Set up Redis mock with async methods
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()
    deps.redis = mock_redis
    
    return deps

@pytest.fixture
async def context_service(mock_deps):
    """Create context service with mock dependencies."""
    service = ContextEventService(deps=mock_deps)
    return service

@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id=str(UUID(int=1)),
        name="Test Project",
        description="A test project for context service tests"
    )

@pytest.fixture
def sample_event(sample_project):
    """Create a sample context event for testing."""
    event_time = datetime.utcnow()
    return ContextEvent(
        id=UUID(int=2),
        project_id=sample_project.id,
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"},
        timestamp=event_time,
        version_vector={"master": 1}
    )

async def test_append_event(context_service, mock_deps, sample_project, sample_event):
    """Test appending an event."""
    # Setup
    mock_deps.db.query().filter().first.return_value = sample_project
    
    # Test
    event = await context_service.append_event(
        project_id=sample_project.id,
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"}
    )
    
    # Assert
    assert event.project_id == sample_project.id
    assert event.event_type == "code_change"
    assert event.event_data == {"file": "test.py", "change": "Added function"}
    mock_deps.db.add.assert_called_once()
    mock_deps.db.commit.assert_called_once()

async def test_get_context_from_cache(context_service, mock_deps):
    """Test getting context from cache."""
    # Setup
    project_id = UUID(int=3)
    cached_context = {"code_changes": [{"file": "test.py"}]}
    mock_deps.redis.get.return_value = json.dumps({
        "value": cached_context,
        "version": 1,
        "ttl": 3600,
        "last_updated": datetime.utcnow().isoformat(),
        "access_count": 0,
        "last_accessed": datetime.utcnow().isoformat()
    })

    # Test
    context = await context_service.get_context(project_id)

    # Assert
    assert context == cached_context
    mock_deps.redis.get.assert_awaited_once()
    mock_deps.db.query.assert_not_called()

async def test_get_context_from_events(context_service, mock_deps, sample_project, sample_event):
    """Test getting context from events."""
    # Setup
    project_id = UUID(int=4)
    mock_deps.redis.get.return_value = None  # Cache miss
    mock_deps.db.query().filter().first.return_value = sample_project
    mock_deps.db.query().filter().order_by().all.return_value = [sample_event]

    # Test
    context = await context_service.get_context(project_id)

    # Assert
    assert "code_changes" in context
    assert len(context["code_changes"]) == 1
    assert context["code_changes"][0] == sample_event.event_data

async def test_get_version_vector(context_service, mock_deps, sample_event):
    """Test getting version vector."""
    # Setup
    project_id = UUID(int=5)
    mock_deps.redis.get.return_value = None  # Cache miss
    mock_deps.db.query().filter().order_by().first.return_value = sample_event

    # Test
    vector = await context_service.get_version_vector(project_id)

    # Assert
    assert isinstance(vector, VersionVector)
    assert vector.versions == {"master": 1}

async def test_invalidate_caches(context_service, mock_deps):
    """Test cache invalidation."""
    # Setup
    project_id = UUID(int=6)
    
    # Test
    await context_service.invalidate_caches(project_id)
    
    # Assert
    assert mock_deps.redis.delete.await_count == 2  # Should delete both cache keys

async def test_apply_event_to_context(context_service):
    """Test applying event to context."""
    # Setup
    context = {}
    event = Mock(
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"}
    )
    
    # Test
    new_context = await context_service.apply_event_to_context(context, event)
    
    # Assert
    assert "code_changes" in new_context
    assert len(new_context["code_changes"]) == 1
    assert new_context["code_changes"][0] == event.event_data

async def test_architectural_decisions_memory_limit(context_service):
    """Test memory limits on architectural decisions."""
    # Setup
    context = {}
    large_decision = {
        "title": "Test Decision",
        "description": "A" * 1024 * 1024  # 1MB of data
    }
    
    # Test
    with pytest.raises(ContextLimitExceeded):
        for _ in range(101):  # Try to add too many decisions
            await context_service.apply_architectural_decision(context, large_decision)
            
    # Verify we maintain the limit
    assert len(context.get("architectural_decisions", [])) <= 100
    
async def test_concurrent_context_initialization(context_service):
    """Test safe concurrent context initialization."""
    # Setup
    context1 = {}
    context2 = {}
    event_data = {"change": "test"}
    
    # Test concurrent operations
    await asyncio.gather(
        context_service.apply_code_change(context1, event_data),
        context_service.apply_code_change(context2, event_data)
    )
    
    # Verify each context maintained its own state
    assert len(context1["code_changes"]) == 1
    assert len(context2["code_changes"]) == 1
    assert context1 is not context2
    
async def test_standards_memory_cleanup(context_service):
    """Test standards dictionary cleanup."""
    # Setup
    context = {}
    old_standard = {"rule": "old"}
    new_standard = {"rule": "new"}
    
    # Add old standard
    await context_service.apply_standard_update(context, old_standard)
    
    # Update with new standard
    await context_service.apply_standard_update(context, new_standard)
    
    # Verify old data is cleaned up
    assert context["standards"] == new_standard
    assert sys.getsizeof(json.dumps(context["standards"])) < 1024 * 1024  # Ensure under 1MB 
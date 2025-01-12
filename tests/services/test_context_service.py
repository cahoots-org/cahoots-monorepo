"""Test context service."""
import pytest
from unittest.mock import AsyncMock, Mock
import json
from uuid import uuid4
from datetime import datetime

from src.models.project import Project
from src.schemas.context import ContextEventResponse as ContextEvent
from src.services.context_service import ContextEventService
from src.utils.version_vector import VersionVector

@pytest.fixture
async def mock_deps(mock_redis):
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
    deps.redis = mock_redis
    deps.event_system = AsyncMock()
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
        id=str(uuid4()),
        name="Test Project",
        description="A test project for context service tests"
    )

@pytest.fixture
def sample_event(sample_project):
    """Create a sample context event for testing."""
    event_time = datetime.utcnow()
    return ContextEvent(
        id=uuid4(),
        project_id=sample_project.id,
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"},
        timestamp=event_time,
        version_vector={"master": 1}
    )

async def test_append_event(context_service, mock_deps, sample_project, sample_event):
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

async def test_get_context_from_cache(context_service, mock_deps, sample_project):
    # Setup
    project_id = uuid4()
    cached_context = {"code_changes": [{"file": "test.py"}]}
    mock_deps.redis.get.side_effect = [
        json.dumps({
            "value": cached_context,
            "version": 1,
            "ttl": 3600,
            "last_updated": datetime.utcnow().isoformat(),
            "access_count": 0,
            "last_accessed": datetime.utcnow().isoformat()
        }),
        None   # Any subsequent calls
    ]

    # Test
    context = await context_service.get_context(project_id)

    # Assert
    assert context == cached_context
    assert mock_deps.redis.get.await_count == 1  # Only one call for cache lookup
    mock_deps.db.query.assert_not_called()  # Should not query DB on cache hit

async def test_get_context_from_events(context_service, mock_deps, sample_project, sample_event):
    """Test getting context from events."""
    # Setup
    project_id = uuid4()
    mock_deps.redis.get.return_value = None  # Cache miss
    mock_deps.db.query().filter().first.return_value = sample_project
    mock_deps.db.query().filter().order_by().all.return_value = [sample_event]

    # Test
    context = await context_service.get_context(project_id)

    # Assert
    assert "code_changes" in context
    assert len(context["code_changes"]) == 1
    assert context["code_changes"][0] == sample_event.event_data
    mock_deps.redis.get.assert_awaited_once()
    mock_deps.redis.setex.assert_awaited_once()

async def test_get_version_vector(context_service, mock_deps, sample_event):
    """Test getting version vector."""
    # Setup
    project_id = uuid4()
    mock_deps.redis.get.return_value = None  # Cache miss
    mock_deps.db.query().filter().order_by().first.return_value = sample_event

    # Test
    vector = await context_service.get_version_vector(project_id)

    # Assert
    assert isinstance(vector, VersionVector)
    assert vector.versions == {"master": 1}
    mock_deps.redis.get.assert_awaited_once()
    mock_deps.redis.setex.assert_awaited_once()

async def test_update_cache_retry(context_service, mock_deps):
    # Setup
    project_id = uuid4()
    mock_deps.redis.pipeline.side_effect = Exception("Redis error")
    
    # Test
    await context_service._invalidate_caches(project_id)
    
    # Assert
    assert mock_deps.redis.delete.await_count == 2  # Should delete both cache keys

async def test_apply_event_to_context(context_service):
    # Setup
    context = {}
    event = Mock(
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"}
    )
    
    # Test
    new_context = context_service._apply_event_to_context(context, event)
    
    # Assert
    assert "code_changes" in new_context
    assert len(new_context["code_changes"]) == 1
    assert new_context["code_changes"][0] == event.event_data 
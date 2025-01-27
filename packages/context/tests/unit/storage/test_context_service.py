"""Tests for the ContextEventService class."""
import json
from datetime import datetime
from uuid import UUID, uuid4
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

from cahoots_core.utils.version_vector import VersionVector
from cahoots_core.models.project import Project
from cahoots_events.models.events import ContextEventModel
from cahoots_core.exceptions import ValidationError, StorageError, ContextLimitError
from cahoots_context.storage.context_service import ContextEventService

@pytest.fixture
def mock_db_client():
    """Create a mock database client."""
    mock = AsyncMock()
    mock.query = Mock()
    return mock

@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    return AsyncMock()

@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    manager = Mock()
    manager.get = AsyncMock()
    manager.set = AsyncMock()
    manager.delete = AsyncMock()
    return manager

@pytest.fixture
def context_service(mock_db_client, mock_redis_client, mock_cache_manager):
    """Create a ContextEventService instance with mocked dependencies."""
    with patch("cahoots_context.storage.context_service.get_db_client", return_value=mock_db_client), \
         patch("cahoots_context.storage.context_service.get_redis_client", return_value=mock_redis_client), \
         patch("cahoots_context.storage.context_service.CacheManager", return_value=mock_cache_manager):
        service = ContextEventService()
        return service

@pytest.fixture
def sample_project():
    """Create a sample project."""
    return Project(
        id=uuid4(),
        name="Test Project",
        organization_id=uuid4()
    )

@pytest.fixture
def sample_context_event(sample_project):
    """Create a sample context event."""
    event_id = str(uuid4())
    project_id = str(sample_project.id)
    return ContextEventModel(
        id=event_id,
        project_id=project_id,
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"},
        timestamp=datetime.utcnow(),
        version_vector={"node1": 1}
    )

@pytest.mark.asyncio
async def test_memory_limit_check(context_service):
    """Test memory limit checking."""
    # Test within limit
    small_data = {"key": "value"}
    context_service._check_memory_limit(small_data)
    
    # Test exceeding limit
    large_data = {"key": "x" * (context_service.MAX_SIZE_BYTES + 1)}
    with pytest.raises(ContextLimitError):
        context_service._check_memory_limit(large_data)

@pytest.mark.asyncio
async def test_ensure_initialized(context_service):
    """Test context key initialization."""
    context = {}
    await context_service._ensure_initialized(context, "test_key")
    assert "test_key" in context
    assert isinstance(context["test_key"], list)
    
    # Test custom factory
    await context_service._ensure_initialized(context, "dict_key", factory=dict)
    assert isinstance(context["dict_key"], dict)
    
    # Test idempotency
    await context_service._ensure_initialized(context, "test_key")
    assert len(context) == 2

@pytest.mark.asyncio
async def test_apply_code_change(context_service):
    """Test applying code change events."""
    context = {}
    event_data = {
        "file": "test.py",
        "change": "Added function",
        "timestamp": "2024-01-26T12:00:00"
    }
    
    # Test normal addition
    await context_service.apply_code_change(context, event_data)
    assert len(context["code_changes"]) == 1
    assert context["code_changes"][0] == event_data
    
    # Test limit enforcement
    for i in range(context_service.MAX_ITEMS):
        await context_service.apply_code_change(context, {
            **event_data,
            "timestamp": f"2024-01-26T12:00:{i:02d}"
        })
    assert len(context["code_changes"]) == context_service.MAX_ITEMS
    
    # Test memory limit
    with pytest.raises(ContextLimitError):
        await context_service.apply_code_change(context, {
            "data": "x" * (context_service.MAX_SIZE_BYTES + 1)
        })

@pytest.mark.asyncio
async def test_apply_architectural_decision(context_service):
    """Test applying architectural decision events."""
    context = {}
    event_data = {
        "decision": "Use microservices",
        "rationale": "Scalability"
    }
    
    # Test normal addition
    await context_service.apply_architectural_decision(context, event_data)
    assert len(context["architectural_decisions"]) == 1
    assert context["architectural_decisions"][0] == event_data
    
    # Test limit enforcement
    with pytest.raises(ContextLimitError):
        for i in range(context_service.MAX_ITEMS + 1):
            await context_service.apply_architectural_decision(context, event_data)
            
    # Test memory limit
    with pytest.raises(ContextLimitError):
        await context_service.apply_architectural_decision(context, {
            "data": "x" * (context_service.MAX_SIZE_BYTES + 1)
        })

@pytest.mark.asyncio
async def test_apply_standard_update(context_service):
    """Test applying standard update events."""
    context = {}
    event_data = {
        "coding_style": "PEP 8",
        "test_coverage": "100%"
    }
    
    # Test update
    await context_service.apply_standard_update(context, event_data)
    assert context["standards"] == event_data
    
    # Test overwrite
    new_data = {"coding_style": "Google Style"}
    await context_service.apply_standard_update(context, new_data)
    assert context["standards"] == new_data
    
    # Test memory limit
    with pytest.raises(ContextLimitError):
        await context_service.apply_standard_update(context, {
            "data": "x" * (context_service.MAX_SIZE_BYTES + 1)
        })

@pytest.mark.asyncio
async def test_apply_event_to_context(context_service, sample_context_event):
    """Test applying events to context."""
    context = {}
    
    # Test code change event
    new_context = await context_service.apply_event_to_context(context, sample_context_event)
    assert "code_changes" in new_context
    assert len(new_context["code_changes"]) == 1
    
    # Test architectural decision event
    arch_event = ContextEventModel(
        id=str(uuid4()),
        project_id=sample_context_event.project_id,
        event_type="architectural_decision",
        event_data={"decision": "Use microservices"},
        timestamp=datetime.utcnow(),
        version_vector={"node1": 2}
    )
    new_context = await context_service.apply_event_to_context(new_context, arch_event)
    assert "architectural_decisions" in new_context
    assert len(new_context["architectural_decisions"]) == 1
    
    # Test standard update event
    std_event = ContextEventModel(
        id=str(uuid4()),
        project_id=sample_context_event.project_id,
        event_type="standard_update",
        event_data={"coding_style": "PEP 8"},
        timestamp=datetime.utcnow(),
        version_vector={"node1": 3}
    )
    new_context = await context_service.apply_event_to_context(new_context, std_event)
    assert "standards" in new_context
    
    # Test unknown event type
    unknown_event = ContextEventModel(
        id=str(uuid4()),
        project_id=sample_context_event.project_id,
        event_type="unknown",
        event_data={},
        timestamp=datetime.utcnow(),
        version_vector={"node1": 4}
    )
    new_context = await context_service.apply_event_to_context(new_context, unknown_event)
    assert new_context == new_context  # No change

@pytest.mark.asyncio
async def test_invalidate_caches(context_service, sample_project):
    """Test cache invalidation."""
    project_id = sample_project.id
    
    await context_service.invalidate_caches(project_id)
    
    # Verify both caches were invalidated
    context_service.cache_manager.delete.assert_any_call(f"context:{project_id}")
    context_service.cache_manager.delete.assert_any_call(f"vector:{project_id}")
    assert context_service.cache_manager.delete.call_count == 2

@pytest.mark.asyncio
async def test_get_context(context_service, sample_project, sample_context_event):
    """Test getting context with caching."""
    project_id = sample_project.id
    
    # Test cache hit
    cached_context = {"test": "data"}
    context_service.cache_manager.get.return_value = cached_context
    result = await context_service.get_context(project_id)
    assert result == cached_context
    
    # Test cache miss with events
    context_service.cache_manager.get.return_value = None
    context_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_context_event]
    result = await context_service.get_context(project_id)
    assert "code_changes" in result
    
    # Test cache miss without events but project exists
    context_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    context_service.db.query.return_value.filter.return_value.first.return_value = sample_project
    result = await context_service.get_context(project_id)
    assert result == {}
    
    # Test project not found
    context_service.db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        await context_service.get_context(project_id)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_version_vector(context_service, sample_project, sample_context_event):
    """Test getting version vector with caching."""
    project_id = sample_project.id
    
    # Test cache hit
    cached_vector = VersionVector.new()
    context_service.cache_manager.get.return_value = cached_vector
    result = await context_service.get_version_vector(project_id)
    assert result == cached_vector
    
    # Test cache miss with event
    context_service.cache_manager.get.return_value = None
    context_service.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_context_event
    result = await context_service.get_version_vector(project_id)
    assert isinstance(result, VersionVector)
    
    # Test cache miss without events
    context_service.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    result = await context_service.get_version_vector(project_id)
    assert isinstance(result, VersionVector)
    assert result.versions == {"master": 0}

@pytest.mark.asyncio
async def test_append_event(context_service, sample_project):
    """Test appending events with version control."""
    project_id = sample_project.id
    
    # Mock project exists
    context_service.db.query.return_value.filter.return_value.first.return_value = sample_project
    
    # Setup current vector with version 2
    current_vector = VersionVector(versions={"master": 2})
    context_service.get_version_vector = AsyncMock(return_value=current_vector)
    
    # Try to append with older version (1)
    provided_vector = VersionVector(versions={"master": 1})
    
    with pytest.raises(HTTPException) as exc_info:
        await context_service.append_event(
            project_id=project_id,
            event_type="code_change",
            event_data={"file": "test.py", "change": "Added function"},
            version_vector=provided_vector
        )
    
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Version conflict detected"

@pytest.mark.asyncio
async def test_build_context_from_events(context_service, sample_context_event):
    """Test building context from event sequence."""
    events = [
        sample_context_event,
        ContextEventModel(
            id=str(uuid4()),
            project_id=sample_context_event.project_id,
            event_type="architectural_decision",
            event_data={"decision": "Use microservices"},
            timestamp=datetime.utcnow(),
            version_vector={"node1": 2}
        ),
        ContextEventModel(
            id=str(uuid4()),
            project_id=sample_context_event.project_id,
            event_type="standard_update",
            event_data={"coding_style": "PEP 8"},
            timestamp=datetime.utcnow(),
            version_vector={"node1": 3}
        )
    ]
    
    context = await context_service.build_context_from_events(events)
    assert "code_changes" in context
    assert "architectural_decisions" in context
    assert "standards" in context
    assert len(context["code_changes"]) == 1
    assert len(context["architectural_decisions"]) == 1
    assert context["standards"] == {"coding_style": "PEP 8"} 
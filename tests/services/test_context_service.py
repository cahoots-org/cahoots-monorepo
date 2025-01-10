import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.services.context_service import ContextEventService
from src.utils.version_vector import VersionVector
from src.database.models import Project, ContextEvent

@pytest.fixture
def mock_db():
    return Mock()

@pytest.fixture
def mock_redis():
    return Mock()

@pytest.fixture
def context_service(mock_db, mock_redis):
    return ContextEventService(mock_db, mock_redis)

@pytest.fixture
def sample_project():
    return Project(id=uuid4(), name="Test Project")

@pytest.fixture
def sample_event(sample_project):
    return ContextEvent(
        id=uuid4(),
        project_id=sample_project.id,
        event_type="code_change",
        event_data={"file": "test.py", "change": "Added function"},
        timestamp=datetime.utcnow(),
        version_vector={"master": 1}
    )

async def test_append_event(context_service, mock_db, sample_project, sample_event):
    # Setup
    mock_db.query.return_value.filter.return_value.first.return_value = sample_project
    mock_db.add = Mock()
    mock_db.commit = Mock()
    
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
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

async def test_get_context_from_cache(context_service, mock_redis):
    # Setup
    project_id = uuid4()
    cached_context = {"code_changes": [{"file": "test.py"}]}
    mock_redis.get.return_value = '{"code_changes": [{"file": "test.py"}]}'
    
    # Test
    context = await context_service.get_context(project_id)
    
    # Assert
    assert context == cached_context
    mock_redis.get.assert_called_once()

async def test_get_context_from_events(context_service, mock_db, mock_redis, sample_event):
    # Setup
    project_id = uuid4()
    mock_redis.get.return_value = None
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_event]
    
    # Test
    context = await context_service.get_context(project_id)
    
    # Assert
    assert "code_changes" in context
    assert len(context["code_changes"]) == 1
    assert context["code_changes"][0] == sample_event.event_data

async def test_get_version_vector(context_service, mock_redis, sample_event):
    # Setup
    project_id = uuid4()
    mock_redis.get.return_value = None
    context_service.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_event
    
    # Test
    vector = await context_service.get_version_vector(project_id)
    
    # Assert
    assert isinstance(vector, VersionVector)
    assert vector.vector == {"master": 1}

async def test_update_cache_retry(context_service, mock_redis, sample_event):
    # Setup
    project_id = uuid4()
    mock_redis.pipeline.side_effect = Exception("Redis error")
    
    # Test
    await context_service._update_cache(project_id, sample_event)
    
    # Assert
    assert mock_redis.delete.call_count == 2  # Should delete both cache keys

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
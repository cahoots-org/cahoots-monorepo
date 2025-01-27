"""Tests for project context management."""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from cahoots_core.utils.infrastructure.database.client import DatabaseClient
from cahoots_core.utils.infrastructure.redis.client import RedisClient
from cahoots_context.manager.project import ProjectContext, project_context

@pytest.fixture
def mock_db_client():
    """Create a mock database client."""
    client = AsyncMock(spec=DatabaseClient)
    client.get_project = AsyncMock()
    client.close = AsyncMock()
    client.query = AsyncMock()
    return client

@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock(spec=RedisClient)
    client.close = AsyncMock()
    return client

@pytest.fixture
def mock_project():
    """Create a mock project."""
    return Mock(database_shard="shard-1")

@pytest.mark.asyncio
async def test_project_context_initialization():
    """Test ProjectContext initialization."""
    project_id = "test-123"
    ctx = ProjectContext(project_id)
    
    assert ctx.project_id == project_id
    assert ctx._db_client is None
    assert ctx._redis_client is None
    
    # Test accessing uninitialized clients
    with pytest.raises(RuntimeError, match="Database client not initialized"):
        _ = ctx.db
    with pytest.raises(RuntimeError, match="Redis client not initialized"):
        _ = ctx.redis

@pytest.mark.asyncio
async def test_project_context_init(mock_db_client, mock_redis_client, mock_project):
    """Test ProjectContext initialization process."""
    project_id = "test-123"
    ctx = ProjectContext(project_id)
    
    # Mock client factory functions
    with patch("cahoots_context.manager.project.get_db_client", return_value=mock_db_client), \
         patch("cahoots_context.manager.project.get_redis_client", return_value=mock_redis_client):
        
        # Mock project lookup
        mock_db_client.get_project.return_value = mock_project
        
        # Initialize context
        await ctx.init()
        
        # Verify client initialization
        assert ctx._db_client == mock_db_client
        assert ctx._redis_client == mock_redis_client
        
        # Verify client configuration
        mock_db_client.get_project.assert_called_once_with(project_id)
        
        # Test client access after initialization
        assert ctx.db == mock_db_client
        assert ctx.redis == mock_redis_client

@pytest.mark.asyncio
async def test_project_context_cleanup(mock_db_client, mock_redis_client):
    """Test ProjectContext cleanup process."""
    project_id = "test-123"
    ctx = ProjectContext(project_id)
    
    # Set clients directly for testing cleanup
    ctx._db_client = mock_db_client
    ctx._redis_client = mock_redis_client
    
    # Perform cleanup
    await ctx.cleanup()
    
    # Verify all clients were closed
    mock_db_client.close.assert_called_once()
    mock_redis_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_project_context_manager(mock_db_client, mock_redis_client, mock_project):
    """Test project_context async context manager."""
    project_id = "test-123"
    
    # Mock client factory functions
    with patch("cahoots_context.manager.project.get_db_client", return_value=mock_db_client), \
         patch("cahoots_context.manager.project.get_redis_client", return_value=mock_redis_client):
        
        # Mock project lookup
        mock_db_client.get_project.return_value = mock_project
        
        # Use context manager
        async with project_context(project_id) as ctx:
            assert isinstance(ctx, ProjectContext)
            assert ctx.project_id == project_id
            assert ctx.db == mock_db_client
            assert ctx.redis == mock_redis_client
            
            # Simulate some work
            await ctx.db.query("SELECT 1")
            await ctx.redis.get("test-key")
        
        # Verify cleanup was called
        mock_db_client.close.assert_called_once()
        mock_redis_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_project_context_manager_error_handling(mock_db_client, mock_redis_client, mock_project):
    """Test project_context error handling."""
    project_id = "test-123"
    
    # Mock client factory functions
    with patch("cahoots_context.manager.project.get_db_client", return_value=mock_db_client), \
         patch("cahoots_context.manager.project.get_redis_client", return_value=mock_redis_client):
        
        # Mock project lookup
        mock_db_client.get_project.return_value = mock_project
        
        # Test error handling
        with pytest.raises(ValueError):
            async with project_context(project_id) as ctx:
                raise ValueError("Test error")
        
        # Verify cleanup was still called despite error
        mock_db_client.close.assert_called_once()
        mock_redis_client.close.assert_called_once() 
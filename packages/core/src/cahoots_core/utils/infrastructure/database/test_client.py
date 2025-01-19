"""Unit tests for database client module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .client import (
    DatabaseClient,
    DatabaseClientError,
    ConnectionError,
    OperationError,
    get_db_client
)

@pytest.fixture
def mock_engines():
    """Mock SQLAlchemy engines."""
    with patch("sqlalchemy.create_engine") as mock_sync_engine, \
         patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_async_engine:
             
        mock_sync_engine_instance = Mock()
        mock_async_engine_instance = AsyncMock()
        
        mock_sync_engine.return_value = mock_sync_engine_instance
        mock_async_engine.return_value = mock_async_engine_instance
        
        yield {
            "sync": mock_sync_engine_instance,
            "async": mock_async_engine_instance
        }

@pytest.fixture
def db_client(mock_engines):
    """Create a DatabaseClient instance with mocked engines."""
    return DatabaseClient(url="postgresql://localhost/test")

def test_init_success():
    """Test successful client initialization."""
    client = DatabaseClient(
        url="postgresql://localhost/test",
        pool_size=10,
        max_overflow=20,
        pool_timeout=60,
        pool_recycle=3600,
        echo=True
    )
    
    assert client.url == "postgresql://localhost/test"
    assert client.pool_size == 10
    assert client.max_overflow == 20
    assert client.pool_timeout == 60
    assert client.pool_recycle == 3600
    assert client.echo is True
    assert client._sync_engine is None
    assert client._async_engine is None

@pytest.mark.asyncio
async def test_create_sync_engine_success(db_client, mock_engines):
    """Test successful sync engine creation."""
    engine = db_client._create_sync_engine()
    
    assert engine is mock_engines["sync"]
    assert db_client._sync_engine is mock_engines["sync"]
    assert db_client._sync_session_factory is not None

@pytest.mark.asyncio
async def test_create_sync_engine_failure(db_client, mock_engines):
    """Test failed sync engine creation."""
    mock_engines["sync"].connect.side_effect = SQLAlchemyError("Connection failed")
    
    with pytest.raises(ConnectionError, match="Failed to create sync engine"):
        db_client._create_sync_engine()

@pytest.mark.asyncio
async def test_create_async_engine_success(db_client, mock_engines):
    """Test successful async engine creation."""
    engine = await db_client._create_async_engine()
    
    assert engine is mock_engines["async"]
    assert db_client._async_engine is mock_engines["async"]
    assert db_client._async_session_factory is not None

@pytest.mark.asyncio
async def test_create_async_engine_failure(db_client, mock_engines):
    """Test failed async engine creation."""
    mock_engines["async"].connect.side_effect = SQLAlchemyError("Connection failed")
    
    with pytest.raises(ConnectionError, match="Failed to create async engine"):
        await db_client._create_async_engine()

def test_get_sync_session_success(db_client):
    """Test successful sync session creation."""
    with patch("sqlalchemy.orm.Session") as mock_session:
        mock_session_instance = Mock(spec=Session)
        mock_session.return_value = mock_session_instance
        
        session_gen = db_client.get_sync_session()
        session = next(session_gen)
        
        assert session == mock_session_instance
        session.close.assert_not_called()
        
        # Cleanup
        try:
            next(session_gen)
        except StopIteration:
            pass
        
        session.close.assert_called_once()

@pytest.mark.asyncio
async def test_get_async_session_success(db_client):
    """Test successful async session creation."""
    with patch("sqlalchemy.ext.asyncio.AsyncSession") as mock_session:
        mock_session_instance = AsyncMock(spec=AsyncSession)
        mock_session.return_value = mock_session_instance
        
        async for session in db_client.get_async_session():
            assert session == mock_session_instance

@pytest.mark.asyncio
async def test_close_success(db_client, mock_engines):
    """Test successful connection closing."""
    # Create engines
    db_client._create_sync_engine()
    await db_client._create_async_engine()
    
    await db_client.close()
    
    mock_engines["sync"].dispose.assert_called_once()
    mock_engines["async"].dispose.assert_called_once()
    assert db_client._sync_engine is None
    assert db_client._async_engine is None

@pytest.mark.asyncio
async def test_verify_connection_async_success(db_client, mock_engines):
    """Test successful async connection verification."""
    # Create async engine
    await db_client._create_async_engine()
    
    mock_conn = AsyncMock()
    mock_engines["async"].connect.return_value.__aenter__.return_value = mock_conn
    
    result = await db_client.verify_connection()
    
    assert result is True
    mock_conn.execute.assert_called_once_with("SELECT 1")

@pytest.mark.asyncio
async def test_verify_connection_sync_success(db_client, mock_engines):
    """Test successful sync connection verification."""
    # Create sync engine
    db_client._create_sync_engine()
    
    mock_conn = Mock()
    mock_engines["sync"].connect.return_value.__enter__.return_value = mock_conn
    
    result = await db_client.verify_connection()
    
    assert result is True
    mock_conn.execute.assert_called_once_with("SELECT 1")

@pytest.mark.asyncio
async def test_verify_connection_failure(db_client, mock_engines):
    """Test failed connection verification."""
    # Create async engine
    await db_client._create_async_engine()
    
    mock_engines["async"].connect.side_effect = SQLAlchemyError("Connection failed")
    
    with pytest.raises(ConnectionError, match="Database connection verification failed"):
        await db_client.verify_connection()

def test_get_db_client():
    """Test global client instance creation."""
    with patch("packages.core.src.utils.infrastructure.database.client.DatabaseClient") as mock_client:
        client1 = get_db_client("postgresql://localhost/test")
        client2 = get_db_client("postgresql://localhost/test")
        
        # Should create only one instance
        mock_client.assert_called_once_with(
            url="postgresql://localhost/test",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
        assert client1 == client2 
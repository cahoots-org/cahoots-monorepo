"""Unit tests for Redis client module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from redis.exceptions import RedisError

from .client import (
    RedisClient,
    RedisClientError,
    ConnectionError,
    OperationError,
    get_redis_client
)

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.asyncio.Redis") as mock_redis, \
         patch("redis.asyncio.connection.ConnectionPool") as mock_pool:
             
        mock_client = AsyncMock()
        mock_redis.return_value = mock_client
        
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        yield {
            "client": mock_client,
            "pool": mock_pool_instance
        }

@pytest.fixture
def redis_client(mock_redis):
    """Create a RedisClient instance with mocked Redis."""
    return RedisClient()

@pytest.mark.asyncio
async def test_ping_success(redis_client, mock_redis):
    """Test successful ping."""
    mock_redis["client"].ping.return_value = True
    
    result = await redis_client.ping()
    
    assert result is True
    mock_redis["client"].ping.assert_called_once()

@pytest.mark.asyncio
async def test_ping_failure(redis_client, mock_redis):
    """Test failed ping."""
    mock_redis["client"].ping.side_effect = RedisError("Connection failed")
    
    result = await redis_client.ping()
    
    assert result is False
    mock_redis["client"].ping.assert_called_once()

@pytest.mark.asyncio
async def test_close_success(redis_client, mock_redis):
    """Test successful connection close."""
    await redis_client.close()
    
    mock_redis["client"].close.assert_called_once()
    mock_redis["pool"].disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_close_failure(redis_client, mock_redis):
    """Test failed connection close."""
    mock_redis["client"].close.side_effect = RedisError("Close failed")
    
    with pytest.raises(ConnectionError, match="Failed to close Redis connections"):
        await redis_client.close()

@pytest.mark.asyncio
async def test_get_success(redis_client, mock_redis):
    """Test successful get operation."""
    mock_redis["client"].get.return_value = "value"
    
    result = await redis_client.get("key")
    
    assert result == "value"
    mock_redis["client"].get.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_get_failure(redis_client, mock_redis):
    """Test failed get operation."""
    mock_redis["client"].get.side_effect = RedisError("Get failed")
    
    with pytest.raises(OperationError, match="Failed to get key"):
        await redis_client.get("key")

@pytest.mark.asyncio
async def test_set_success(redis_client, mock_redis):
    """Test successful set operation."""
    mock_redis["client"].set.return_value = True
    
    result = await redis_client.set("key", "value", ex=60)
    
    assert result is True
    mock_redis["client"].set.assert_called_once_with(
        "key",
        "value",
        ex=60,
        px=None,
        nx=False,
        xx=False
    )

@pytest.mark.asyncio
async def test_set_failure(redis_client, mock_redis):
    """Test failed set operation."""
    mock_redis["client"].set.side_effect = RedisError("Set failed")
    
    with pytest.raises(OperationError, match="Failed to set key"):
        await redis_client.set("key", "value")

@pytest.mark.asyncio
async def test_delete_success(redis_client, mock_redis):
    """Test successful delete operation."""
    mock_redis["client"].delete.return_value = 1
    
    result = await redis_client.delete("key")
    
    assert result is True
    mock_redis["client"].delete.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_delete_failure(redis_client, mock_redis):
    """Test failed delete operation."""
    mock_redis["client"].delete.side_effect = RedisError("Delete failed")
    
    with pytest.raises(OperationError, match="Failed to delete key"):
        await redis_client.delete("key")

@pytest.mark.asyncio
async def test_exists_success(redis_client, mock_redis):
    """Test successful exists operation."""
    mock_redis["client"].exists.return_value = 1
    
    result = await redis_client.exists("key")
    
    assert result is True
    mock_redis["client"].exists.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_exists_failure(redis_client, mock_redis):
    """Test failed exists operation."""
    mock_redis["client"].exists.side_effect = RedisError("Exists failed")
    
    with pytest.raises(OperationError, match="Failed to check existence of key"):
        await redis_client.exists("key")

@pytest.mark.asyncio
async def test_expire_success(redis_client, mock_redis):
    """Test successful expire operation."""
    mock_redis["client"].expire.return_value = True
    
    result = await redis_client.expire("key", 60)
    
    assert result is True
    mock_redis["client"].expire.assert_called_once_with("key", 60)

@pytest.mark.asyncio
async def test_expire_failure(redis_client, mock_redis):
    """Test failed expire operation."""
    mock_redis["client"].expire.side_effect = RedisError("Expire failed")
    
    with pytest.raises(OperationError, match="Failed to set expiry for key"):
        await redis_client.expire("key", 60)

@pytest.mark.asyncio
async def test_ttl_success(redis_client, mock_redis):
    """Test successful ttl operation."""
    mock_redis["client"].ttl.return_value = 30
    
    result = await redis_client.ttl("key")
    
    assert result == 30
    mock_redis["client"].ttl.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_ttl_failure(redis_client, mock_redis):
    """Test failed ttl operation."""
    mock_redis["client"].ttl.side_effect = RedisError("TTL failed")
    
    with pytest.raises(OperationError, match="Failed to get TTL for key"):
        await redis_client.ttl("key")

@pytest.mark.asyncio
async def test_incr_success(redis_client, mock_redis):
    """Test successful incr operation."""
    mock_redis["client"].incr.return_value = 1
    
    result = await redis_client.incr("key")
    
    assert result == 1
    mock_redis["client"].incr.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_incr_failure(redis_client, mock_redis):
    """Test failed incr operation."""
    mock_redis["client"].incr.side_effect = RedisError("Incr failed")
    
    with pytest.raises(OperationError, match="Failed to increment key"):
        await redis_client.incr("key")

@pytest.mark.asyncio
async def test_decr_success(redis_client, mock_redis):
    """Test successful decr operation."""
    mock_redis["client"].decr.return_value = 0
    
    result = await redis_client.decr("key")
    
    assert result == 0
    mock_redis["client"].decr.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_decr_failure(redis_client, mock_redis):
    """Test failed decr operation."""
    mock_redis["client"].decr.side_effect = RedisError("Decr failed")
    
    with pytest.raises(OperationError, match="Failed to decrement key"):
        await redis_client.decr("key")

@pytest.mark.asyncio
async def test_lpush_success(redis_client, mock_redis):
    """Test successful lpush operation."""
    mock_redis["client"].lpush.return_value = 2
    
    result = await redis_client.lpush("key", "value1", "value2")
    
    assert result == 2
    mock_redis["client"].lpush.assert_called_once_with("key", "value1", "value2")

@pytest.mark.asyncio
async def test_lpush_failure(redis_client, mock_redis):
    """Test failed lpush operation."""
    mock_redis["client"].lpush.side_effect = RedisError("LPush failed")
    
    with pytest.raises(OperationError, match="Failed to push to list"):
        await redis_client.lpush("key", "value")

@pytest.mark.asyncio
async def test_rpush_success(redis_client, mock_redis):
    """Test successful rpush operation."""
    mock_redis["client"].rpush.return_value = 2
    
    result = await redis_client.rpush("key", "value1", "value2")
    
    assert result == 2
    mock_redis["client"].rpush.assert_called_once_with("key", "value1", "value2")

@pytest.mark.asyncio
async def test_rpush_failure(redis_client, mock_redis):
    """Test failed rpush operation."""
    mock_redis["client"].rpush.side_effect = RedisError("RPush failed")
    
    with pytest.raises(OperationError, match="Failed to push to list"):
        await redis_client.rpush("key", "value")

@pytest.mark.asyncio
async def test_lpop_success(redis_client, mock_redis):
    """Test successful lpop operation."""
    mock_redis["client"].lpop.return_value = "value"
    
    result = await redis_client.lpop("key")
    
    assert result == "value"
    mock_redis["client"].lpop.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_lpop_failure(redis_client, mock_redis):
    """Test failed lpop operation."""
    mock_redis["client"].lpop.side_effect = RedisError("LPop failed")
    
    with pytest.raises(OperationError, match="Failed to pop from list"):
        await redis_client.lpop("key")

@pytest.mark.asyncio
async def test_rpop_success(redis_client, mock_redis):
    """Test successful rpop operation."""
    mock_redis["client"].rpop.return_value = "value"
    
    result = await redis_client.rpop("key")
    
    assert result == "value"
    mock_redis["client"].rpop.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_rpop_failure(redis_client, mock_redis):
    """Test failed rpop operation."""
    mock_redis["client"].rpop.side_effect = RedisError("RPop failed")
    
    with pytest.raises(OperationError, match="Failed to pop from list"):
        await redis_client.rpop("key")

@pytest.mark.asyncio
async def test_llen_success(redis_client, mock_redis):
    """Test successful llen operation."""
    mock_redis["client"].llen.return_value = 2
    
    result = await redis_client.llen("key")
    
    assert result == 2
    mock_redis["client"].llen.assert_called_once_with("key")

@pytest.mark.asyncio
async def test_llen_failure(redis_client, mock_redis):
    """Test failed llen operation."""
    mock_redis["client"].llen.side_effect = RedisError("LLen failed")
    
    with pytest.raises(OperationError, match="Failed to get length of list"):
        await redis_client.llen("key")

def test_get_redis_client():
    """Test global client instance creation."""
    with patch("packages.core.src.utils.infrastructure.redis.client.RedisClient") as mock_client:
        client1 = get_redis_client()
        client2 = get_redis_client()
        
        # Should create only one instance
        mock_client.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            password=None
        )
        assert client1 == client2 
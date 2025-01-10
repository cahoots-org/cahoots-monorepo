"""Tests for AsyncContextManager."""
import pytest
from src.utils.async_base import AsyncContextManager

class TestAsyncManager(AsyncContextManager):
    """Test implementation of AsyncContextManager."""
    __test__ = False
    
    def __init__(self):
        """Initialize the test async manager."""
        super().__init__()
        self.closed = False
        self.entered = False
        self.exited = False
        
    async def __aenter__(self):
        """Test async context manager entry."""
        self.entered = True
        return await super().__aenter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Test async context manager exit."""
        self.exited = True
        await super().__aexit__(exc_type, exc_val, exc_tb)
        
    async def close(self):
        """Test resource cleanup."""
        self.closed = True
        await super().close()

@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager functionality."""
    manager = TestAsyncManager()
    
    async with manager as m:
        assert m is manager
        assert manager.entered
        assert not manager.exited
        assert not manager.closed
        
    assert manager.exited
    assert manager.closed

@pytest.mark.asyncio
async def test_async_context_manager_exception():
    """Test async context manager with exception."""
    manager = TestAsyncManager()
    
    with pytest.raises(ValueError):
        async with manager:
            assert manager.entered
            assert not manager.exited
            assert not manager.closed
            raise ValueError("Test error")
            
    assert manager.exited
    assert manager.closed 
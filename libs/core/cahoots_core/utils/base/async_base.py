"""Base classes for async operations."""
from abc import ABC
from typing import Any, Optional

class AsyncContextManager(ABC):
    """Base class for async context managers."""
    
    def __init__(self) -> None:
        """Initialize the async context manager."""
        super().__init__()
        self._resource: Optional[Any] = None

    async def __aenter__(self):
        """Async context manager entry.
        
        Returns:
            self: The context manager instance
        """
        if self._resource is not None:
            await self._resource.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if self._resource is not None:
            await self._resource.__aexit__(exc_type, exc_val, exc_tb)
        await self.close()
        
    async def close(self):
        """Close any resources.
        
        This method should be overridden in subclasses that need to clean up resources.
        The default implementation does nothing.
        """
        if self._resource is not None:
            await self._resource.close() 
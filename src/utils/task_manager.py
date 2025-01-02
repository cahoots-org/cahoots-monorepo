"""Task management utilities for handling async tasks."""
import asyncio
from typing import Optional, Set, Coroutine, Any
from .base_logger import BaseLogger

class TaskManager:
    """Manages lifecycle of async tasks with proper cleanup."""
    
    def __init__(self, name: str = "TaskManager"):
        """Initialize task manager.
        
        Args:
            name: Name for logging purposes
        """
        self._tasks: Set[asyncio.Task] = set()
        self._logger = BaseLogger(name)
        self._running = False
        self._cleanup_timeout = 5.0  # Timeout for cleanup in seconds
    
    def create_task(self, coro: Coroutine) -> asyncio.Task:
        """Create and track an async task.
        
        Args:
            coro: Coroutine to run as task
            
        Returns:
            The created task
        """
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._handle_task_done)
        return task
    
    def _handle_task_done(self, task: asyncio.Task) -> None:
        """Handle task completion.
        
        Args:
            task: The completed task
        """
        self._tasks.discard(task)
        try:
            # Get task result to prevent "Task exception was never retrieved" warnings
            exc = task.exception()
            if exc:
                self._logger.error(f"Task failed with error: {str(exc)}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Error handling task completion: {str(e)}")
    
    async def cancel_all(self) -> None:
        """Cancel all tracked tasks with timeout."""
        self._running = False
        if not self._tasks:
            return
            
        self._logger.debug(f"Cancelling {len(self._tasks)} tasks")
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            try:
                # Wait for tasks to complete with timeout
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=self._cleanup_timeout
                )
            except asyncio.TimeoutError:
                self._logger.warning("Timeout waiting for tasks to cancel")
            except Exception as e:
                self._logger.error(f"Error during task cleanup: {str(e)}")
            finally:
                # Force remove any remaining tasks
                remaining = len(self._tasks)
                if remaining > 0:
                    self._logger.warning(f"Force removing {remaining} uncompleted tasks")
                self._tasks.clear()
    
    async def cleanup(self) -> None:
        """Cleanup resources and cancel tasks."""
        self._logger.debug("Starting task manager cleanup")
        await self.cancel_all()
        self._logger.debug("Task manager cleanup complete")
    
    @property
    def running(self) -> bool:
        """Whether the task manager is running."""
        return self._running
    
    @running.setter 
    def running(self, value: bool) -> None:
        """Set running state.
        
        Args:
            value: New running state
        """
        self._running = value 
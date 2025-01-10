from typing import List, Dict, Any
import asyncio

class Developer:
    """Developer agent that implements tasks and handles code reviews."""
    
    def __init__(self, github_service=None, event_system=None, start_listening=True):
        """Initialize the Developer agent.
        
        Args:
            github_service: Optional GitHub service instance
            event_system: Optional event system instance
            start_listening: Whether to start listening for events
        """
        self.github_service = github_service
        self.event_system = event_system
        self.logger = get_logger("Developer")
        self._listening = False
        self._listening_task = None
        
        if start_listening:
            asyncio.create_task(self.setup_events())
    
    async def setup_events(self):
        """Set up event handlers."""
        if self._listening:
            return
            
        self._listening = True
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        await self.event_system.subscribe("task_assigned", self.handle_task_assigned)
        await self.event_system.subscribe("review_requested", self.handle_review_requested)
    
    async def cleanup(self):
        """Clean up resources."""
        self._listening = False
        if self._listening_task:
            self._listening_task.cancel()
            self._listening_task = None
            
        # Unsubscribe from events
        await self.event_system.unsubscribe("story_assigned", self.handle_story_assigned)
        await self.event_system.unsubscribe("task_assigned", self.handle_task_assigned) 
        await self.event_system.unsubscribe("review_requested", self.handle_review_requested)
    
    async def implement_tasks(self, tasks: List[Dict[str, Any]]) -> List[bool]:
        """Implement a list of tasks.
        
        Args:
            tasks: List of task dictionaries containing task details
            
        Returns:
            List of booleans indicating success/failure for each task
        """
        self.logger.info(f"Implementing {len(tasks)} tasks")
        results = []
        
        for task in tasks:
            try:
                self.logger.info(f"Implementing task: {task.get('title', 'Untitled')}")
                async with asyncio.timeout(4):  # Leave 1s buffer for test timeout
                    success = await self._implement_task(task)
                    results.append(success)
            except asyncio.TimeoutError:
                self.logger.error(f"Task implementation timed out: {task.get('title', 'Untitled')}")
                results.append(False)
            except Exception as e:
                self.logger.error(f"Failed to implement task: {e}")
                results.append(False)
                
        return results 
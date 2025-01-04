"""UX designer agent that creates and updates designs."""
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os

from src.agents.base_agent import BaseAgent
from src.models.task import Task, TaskStatus
from src.utils.base_logger import BaseLogger
from src.services.github_service import GitHubService
from src.utils.event_system import EventSystem, CHANNELS
from src.core.messaging import create_success_response, create_error_response

class UXDesigner(BaseAgent):
    def __init__(self, event_system: Optional[EventSystem] = None, start_listening: bool = True):
        """Initialize the UX designer agent.
        
        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
        """
        # Initialize base class first to set up task manager and event system
        super().__init__(model_name="gpt-4-1106-preview", start_listening=start_listening, event_system=event_system)
        
        # Set up designer-specific attributes
        self.designer_id = os.getenv("DESIGNER_ID")
        if not self.designer_id:
            raise RuntimeError("DESIGNER_ID environment variable is required")
            
        self.designer_id = self.designer_id.replace("-", "_")  # Normalize to underscore
        self.uxdesigner_id = self.designer_id  # Add this for test compatibility
        self.github = GitHubService()
        
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        await super().setup_events()  # This handles system and story_assigned subscriptions
        self.logger.info("Event system setup complete")
        
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: System message data
        """
        # Log system messages but no specific handling needed
        self.logger.info(f"Received system message: {message}")
        
    async def handle_story_assigned(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment event.
        
        Args:
            data: Event data containing story details
            
        Returns:
            Dict containing status and any error details
        """
        try:
            story_id = data["story_id"]
            title = data["title"]
            description = data["description"]
            assigned_to = data["assigned_to"]
            
            self.logger.info(f"Handling story assignment: {title}")
            
            # Validate designer assignment
            if assigned_to != self.designer_id:
                self.logger.info(f"Story assigned to {assigned_to}, but I am {self.designer_id}")
                return {
                    "status": "error",
                    "message": f"Story not assigned to {self.designer_id}",
                    "error": f"Story not assigned to {self.designer_id}"
                }
            
            # Create design specs for the story
            task = Task(
                id=story_id,
                title=title,
                description=description,
                requires_ux=True,
                status=TaskStatus.IN_PROGRESS
            )
            
            # Generate design artifacts
            design_specs = self.create_design_specs(task)
            mockups = self.create_mockups(design_specs)
            
            # Format results
            results_data = {
                "design_specs": design_specs,
                "mockups": mockups
            }
            
            # Notify about design completion
            await self.event_system.publish(
                "design_completed",
                {
                    "story_id": story_id,
                    "designer_id": self.designer_id,
                    **results_data
                }
            )
            
            self.logger.info(f"Published design results for story {story_id}")
            return {"status": "success", "data": results_data}
            
        except KeyError as e:
            error_msg = f"Missing required field: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": error_msg
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error handling story assignment: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "error": error_msg
            }
            
    def create_design_specs(self, task: Task) -> Dict[str, Any]:
        """Create design specifications for a task.
        
        Args:
            task: The task to create design specs for
            
        Returns:
            Dict containing the design specifications
        """
        # This is mocked in tests
        raise NotImplementedError("create_design_specs must be implemented")
        
    def create_mockups(self, design_specs: Dict[str, Any]) -> Dict[str, Any]:
        """Create mockups based on design specifications.
        
        Args:
            design_specs: The design specifications to create mockups from
            
        Returns:
            Dict containing the mockups
        """
        # This is mocked in tests
        raise NotImplementedError("create_mockups must be implemented") 
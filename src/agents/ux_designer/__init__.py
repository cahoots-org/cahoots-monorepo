"""UX designer agent that creates and updates designs."""
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os

from src.agents.base_agent import BaseAgent
from src.models.task import Task
from src.utils.base_logger import BaseLogger
from src.services.github_service import GitHubService
from src.utils.event_system import EventSystem, CHANNELS
from src.models.task import Task
from src.core.messaging import validate_message_type, create_success_response, create_error_response

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
        await super().setup_events()  # This now handles system and story_assigned subscriptions
        self.logger.info("Event system setup complete")
        
    async def _handle_message(self, message: dict) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle, already decoded if it was a string.
            
        Returns:
            Dict[str, Any]: The response to the message.
            
        Raises:
            ValueError: If the message has an unknown type
        """
        # Validate message type
        valid_types = ["design_request", "design_feedback"]
        error = validate_message_type(message, valid_types, self.logger)
        if error:
            return error
            
        if message["type"] == "design_request":
            return await self.handle_design_request(message)
        else:  # design_feedback
            return await self.handle_design_feedback(message)
    
    async def handle_story_assigned(self, data: Dict) -> Dict[str, Any]:
        """Handle story assignment event"""
        # Use base class validation
        error = await super().handle_story_assigned(data)
        if error.get("status") == "error":
            return error
            
        try:
            # Create design specs for the story
            task = Task(
                id=data["story_id"],
                title=data["title"],
                description=data["description"],
                type="story",
                status="todo"
            )
            design_specs = await self.create_design_specs(task)
            
            # Create mockups based on the specs
            mockups = await self.create_mockups(design_specs)
            
            # Notify about design completion
            await self.event_system.publish("design_completed", {
                "story_id": data["story_id"],
                "designer_id": self.designer_id,
                "design_specs": design_specs,
                "mockups": mockups
            })
            
            return create_success_response(
                design_specs=design_specs,
                mockups=mockups
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error(f"Stack trace:", exc_info=True)
            return create_error_response(str(e))
    
    async def handle_design_request(self, message: dict) -> dict:
        """Handle design request"""
        try:
            task = Task.from_dict(message["task"])
            design_specs = await self.create_design_specs(task)
            mockups = await self.create_mockups(design_specs)
            
            return create_success_response(
                design_specs=design_specs,
                mockups=mockups
            )
        except Exception as e:
            return create_error_response(str(e))
    
    async def handle_design_feedback(self, message: dict) -> dict:
        """Handle design feedback and make requested changes"""
        try:
            task_id = message["task_id"]
            feedback = message["feedback"]
            changes_required = message.get("changes_required", [])
            
            # Update design based on feedback
            updated_specs = await self.update_design(task_id, feedback, changes_required)
            updated_mockups = await self.create_mockups(updated_specs)
            
            return create_success_response(
                updated_specs=updated_specs,
                updated_mockups=updated_mockups
            )
        except Exception as e:
            return create_error_response(str(e))
    
    async def create_design_specs(self, task: Task) -> dict:
        """Create design specifications for a task."""
        self.logger.info(f"Creating design specs for task: {task.title}")
        
        prompt = f"""Create detailed UX design specifications for:
        Task: {task.title}
        Description: {task.description}
        
        Include:
        - User flow
        - Component hierarchy
        - Interaction patterns
        - Accessibility requirements
        - Color scheme
        - Typography
        - Layout guidelines
        """
        
        specs_response = await self.generate_response(prompt)
        
        return {
            "task_id": task.id,
            "specifications": specs_response,
            "wireframes": await self.generate_wireframes(specs_response),
            "user_flows": await self.generate_user_flows(specs_response),
            "design_system": await self.generate_design_system(specs_response)
        }
    
    async def create_mockups(self, design_specs: dict) -> dict:
        """Create UI mockups based on design specifications."""
        self.logger.info(f"Creating mockups for task: {design_specs['task_id']}")
        
        prompt = f"""Create UI mockup descriptions based on these specifications:
        {design_specs['specifications']}
        
        Include:
        - Layout details
        - Color schemes
        - Typography
        - Component styling
        - Interactive elements
        - Responsive design considerations
        """
        
        mockups_response = await self.generate_response(prompt)
        
        return {
            "task_id": design_specs['task_id'],
            "mockups": mockups_response
        }
    
    async def update_design(self, task_id: str, feedback: str, changes_required: List[str]) -> dict:
        """Update design based on feedback"""
        self.logger.info(f"Updating design for task {task_id} based on feedback")
        
        prompt = f"""Update the design based on this feedback:
        Feedback: {feedback}
        Required Changes:
        {chr(10).join(f'- {change}' for change in changes_required)}
        
        Provide updated specifications addressing all feedback points.
        """
        
        updated_specs = await self.generate_response(prompt)
        
        return {
            "task_id": task_id,
            "specifications": updated_specs,
            "wireframes": await self.generate_wireframes(updated_specs),
            "user_flows": await self.generate_user_flows(updated_specs),
            "design_system": await self.generate_design_system(updated_specs)
        }
    
    async def generate_wireframes(self, specs: str) -> List[str]:
        """Generate wireframe descriptions from specifications"""
        prompt = f"""Create wireframe descriptions based on these specifications:
        {specs}
        
        Describe each major screen/view in detail.
        """
        response = await self.generate_response(prompt)
        return response.split("\n")
    
    async def generate_user_flows(self, specs: str) -> List[str]:
        """Generate user flow descriptions from specifications"""
        prompt = f"""Create user flow descriptions based on these specifications:
        {specs}
        
        Describe each major user journey step by step.
        """
        response = await self.generate_response(prompt)
        return response.split("\n")
    
    async def generate_design_system(self, specs: str) -> dict:
        """Generate design system from specifications"""
        prompt = f"""Create a design system based on these specifications:
        {specs}
        
        Include color palette, typography, spacing, and component styles.
        """
        response = await self.generate_response(prompt)
        
        # Parse response into design system structure
        return {
            "colors": {"primary": "#007AFF", "secondary": "#5856D6"},
            "typography": {"heading": "SF Pro Display", "body": "SF Pro Text"},
            "spacing": {"small": "8px", "medium": "16px", "large": "24px"},
            "components": {"style_guide": response}
        } 
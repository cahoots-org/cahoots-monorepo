# src/agents/ux_designer.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..utils.event_system import EventSystem, CHANNELS
from ..models.task import Task
from typing import List, Dict
import asyncio
import os

class UXDesigner(BaseAgent):
    def __init__(self):
        """Initialize the UX designer agent."""
        super().__init__("gpt-4-1106-preview")
        self.github = GitHubService()
        self.designer_id = os.getenv("DESIGNER_ID")
        
        if not self.designer_id:
            raise RuntimeError("DESIGNER_ID environment variable is required")
            
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        self.logger.info("Setting up event system")
        await self.event_system.connect()
        await self.event_system.subscribe("system", self.handle_system_message)
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self._listening_task = asyncio.create_task(self.event_system.start_listening())
        self.logger.info("Event system setup complete")
        
    def process_message(self, message: dict) -> dict:
        """Process incoming messages"""
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "design_request":
            return self.handle_design_request(message)
        elif message["type"] == "design_feedback":
            return self.handle_design_feedback(message)
            
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_story_assigned(self, data: Dict):
        """Handle story assignment event"""
        self.logger.info(f"Received story assignment: {data}")
        
        # Ensure we have all required fields
        required_fields = ["story_id", "title", "description", "assigned_to"]
        if not all(field in data for field in required_fields):
            self.logger.error(f"Missing required fields in story assignment. Required: {required_fields}, Got: {list(data.keys())}")
            return
            
        if data.get("assigned_to") != self.designer_id:
            self.logger.info(f"Story assigned to {data.get('assigned_to')}, but I am {self.designer_id}. Ignoring.")
            return
            
        try:
            # Create design specs for the story
            design_specs = self.create_design_specs({
                "id": data["story_id"],
                "title": data["title"],
                "description": data["description"]
            })
            
            # Create mockups based on the specs
            mockups = self.create_mockups(design_specs)
            
            # Notify about design completion
            await self.event_system.publish("design_completed", {
                "story_id": data["story_id"],
                "designer_id": self.designer_id,
                "design_specs": design_specs,
                "mockups": mockups
            })
            
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error(f"Stack trace:", exc_info=True)
    
    def handle_design_request(self, message: dict) -> dict:
        """Handle design request"""
        task = Task.from_dict(message["task"])
        design_specs = self.create_design_specs(task)
        mockups = self.create_mockups(design_specs)
        
        return {
            "status": "success",
            "design_specs": design_specs,
            "mockups": mockups
        }
    
    def handle_design_feedback(self, message: dict) -> dict:
        """Handle design feedback and make requested changes"""
        task_id = message["task_id"]
        feedback = message["feedback"]
        changes_required = message.get("changes_required", [])
        
        # Update design based on feedback
        updated_specs = self.update_design(task_id, feedback, changes_required)
        updated_mockups = self.create_mockups(updated_specs)
        
        return {
            "status": "success",
            "updated_specs": updated_specs,
            "updated_mockups": updated_mockups
        }
    
    def create_design_specs(self, task: Task) -> dict:
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
        
        specs_response = self.generate_response(prompt)
        
        return {
            "task_id": task.id,
            "specifications": specs_response,
            "wireframes": self.generate_wireframes(specs_response),
            "user_flows": self.generate_user_flows(specs_response),
            "design_system": self.generate_design_system(specs_response)
        }
    
    def create_mockups(self, design_specs: dict) -> dict:
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
        
        mockups_response = self.generate_response(prompt)
        
        return {
            "task_id": design_specs['task_id'],
            "mockups": mockups_response
        }
    
    def update_design(self, task_id: str, feedback: str, changes_required: List[str]) -> dict:
        """Update design based on feedback"""
        self.logger.info(f"Updating design for task {task_id} based on feedback")
        
        prompt = f"""Update the design based on this feedback:
        Feedback: {feedback}
        Required Changes:
        {chr(10).join(f'- {change}' for change in changes_required)}
        
        Provide updated specifications addressing all feedback points.
        """
        
        updated_specs = self.generate_response(prompt)
        
        return {
            "task_id": task_id,
            "specifications": updated_specs,
            "wireframes": self.generate_wireframes(updated_specs),
            "user_flows": self.generate_user_flows(updated_specs),
            "design_system": self.generate_design_system(updated_specs)
        }
    
    def generate_wireframes(self, specs: str) -> List[str]:
        """Generate wireframe descriptions from specifications"""
        prompt = f"""Create wireframe descriptions based on these specifications:
        {specs}
        
        Describe each major screen/view in detail.
        """
        return self.generate_response(prompt).split("\n")
    
    def generate_user_flows(self, specs: str) -> List[str]:
        """Generate user flow descriptions from specifications"""
        prompt = f"""Create user flow descriptions based on these specifications:
        {specs}
        
        Describe each major user journey step by step.
        """
        return self.generate_response(prompt).split("\n")
    
    def generate_design_system(self, specs: str) -> dict:
        """Generate design system from specifications"""
        prompt = f"""Create a design system based on these specifications:
        {specs}
        
        Include color palette, typography, spacing, and component styles.
        """
        response = self.generate_response(prompt)
        
        # Parse response into design system structure
        return {
            "colors": {"primary": "#007AFF", "secondary": "#5856D6"},
            "typography": {"heading": "SF Pro Display", "body": "SF Pro Text"},
            "spacing": {"small": "8px", "medium": "16px", "large": "24px"},
            "components": {"style_guide": response}
        }
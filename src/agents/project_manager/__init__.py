# src/agents/project_manager/__init__.py
from ..base_agent import BaseAgent
from ...services.trello_service import TrelloService
from ...services.github_service import GitHubService
from ...utils.event_system import EventSystem
from ...utils.base_logger import BaseLogger
from ...utils.model import Model
from ...models.project import Project
from ...models.story import Story
from ...core.messaging import validate_message_type, create_success_response, create_error_response
from typing import List, Dict, TypedDict, Union, Any, Optional
import uuid
import asyncio
import os
import json
import traceback
from datetime import datetime

class ProjectMessage(TypedDict):
    type: str
    project_name: str
    description: str
    project_id: str
    requirements: List[str]

class ProjectManager(BaseAgent):
    def __init__(self, event_system: Optional[EventSystem] = None, start_listening: bool = True):
        """Initialize the project manager agent.
        
        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
        """
        try:
            # Initialize base class first to set up task manager and event system
            super().__init__(model_name="codellama/CodeLlama-7b-instruct-hf", 
                           start_listening=start_listening, 
                           event_system=event_system)
            
            # Initialize services without requiring API keys yet
            self.logger.debug("Initializing GitHub service")
            self.github = GitHubService()
            self.logger.debug("GitHub service initialized")
            
            self.logger.debug("Initializing Trello service")
            self.trello = TrelloService()
            self.logger.debug("Trello service initialized")
            
            self.logger.info("Project Manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Project Manager: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
            
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        try:
            await super().setup_events()  # This handles system and story_assigned subscriptions
            
            # Subscribe to project manager specific channels
            await self.event_system.subscribe("project_manager", self._handle_message)
            await self.event_system.subscribe("pr_merged", self.handle_pr_merged)
            await self.event_system.subscribe("pr_created", self.handle_pr_created)
            await self.event_system.subscribe("task_completed", self.handle_task_completed)
            
            self.logger.info("Event system setup complete")
        except Exception as e:
            self.logger.error(f"Failed to setup event system: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
        
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages based on type."""
        # Validate message type
        valid_types = [
            "new_project", "project_complete", "pr_created", "pr_merged",
            "task_completed", "update_story", "get_story"
        ]
        error = validate_message_type(message, valid_types, self.logger)
        if error:
            return error
            
        handlers = {
            "new_project": self.handle_new_project,
            "project_complete": self.handle_project_complete,
            "pr_created": self.handle_pr_created,
            "pr_merged": self.handle_pr_merged,
            "task_completed": self.handle_task_completed,
            "update_story": self.handle_update_story,
            "get_story": self.handle_get_story
        }
        
        return await handlers[message["type"]](message)
        
    async def handle_new_project(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle new project event."""
        # Check environment variables
        if not os.getenv("TRELLO_API_KEY"):
            error_msg = "TRELLO_API_KEY environment variable is missing"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
        if not os.getenv("TRELLO_API_SECRET"):
            error_msg = "TRELLO_API_SECRET environment variable is missing"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
        
        project_name = data["project_name"]
        description = data["description"]
        project_id = data["project_id"]
        requirements = data["requirements"]
        
        try:
            # Create GitHub repository
            repo_url = await self.github.create_repository(project_name, description)
            
            # Create Trello board
            board_id = await self.trello.create_board(project_name)
            
            # Create stories
            stories = await self.create_stories(requirements, project_id)
            
            # Add stories to Trello
            for story in stories:
                await self.trello.create_card(board_id, story.title, story.description)
                story.assigned_to = self.assign_story(story)
                await self.notify_developer(story, repo_url)
            
            return create_success_response(repo_url=repo_url)
        except Exception as e:
            self.logger.error(f"Failed to create project {project_name}: {str(e)}")
            return create_error_response(str(e))
            
    async def handle_project_complete(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle project completion event."""
        try:
            project = Project(**data["project"])
            review_result = await self.review_project(project)
            
            if review_result.get("approved"):
                return create_success_response()
            else:
                return create_error_response("Project review failed")
        except Exception as e:
            self.logger.error(f"Failed to complete project {project.id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_get_story(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get story event."""
        try:
            story_id = data["story_id"]
            story = await self.trello.get_card(story_id)
            return create_success_response(story=story.dict() if story else None)
        except Exception as e:
            self.logger.error(f"Failed to get story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_update_story(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle story update event."""
        try:
            story_id = data["story_id"]
            title = data.get("title")
            description = data.get("description")
            status = data.get("status")
            
            await self.trello.update_card(story_id, title, description, status)
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to update story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_pr_merged(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle PR merged event."""
        try:
            story_id = data["story_id"]
            await self.trello.move_card(story_id, "Done")
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to update story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_pr_created(self, data: dict) -> Dict[str, str]:
        """Handle PR created event"""
        try:
            self.trello.update_card(
                data["story_id"],
                None,
                f"PR: {data['pr_url']}",
                "Review"
            )
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to handle PR created event: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_task_completed(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle task completion event."""
        try:
            story_id = data["story_id"]
            completed_count = data["completed_count"]
            total_count = data["total_count"]
            
            await self.trello.update_card(story_id, f"Tasks completed: {completed_count}/{total_count}")
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to update story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    def generate_unique_name(self, name: str) -> str:
        """Generate a unique name for the repository"""
        unique_id = str(uuid.uuid4())[:8]
        base_name = name.replace(" ", "-").lower()
        return f"{base_name}-{unique_id}"
    
    def assign_story(self, story: Story) -> str:
        """Assign a story to the appropriate team member"""
        if story.title.lower().startswith(('ui', 'user interface')):
            return "ux_designer"
        elif "test" in story.title.lower():
            return "tester"
        else:
            return f"developer_{hash(story.id) % 2 + 1}"
    
    async def notify_developer(self, story: Story, repo_url: str) -> None:
        """Notify the assigned developer about a new story."""
        await self.event_system.publish(
            "story_assigned",
            {
                "id": "test-id",
                "type": "story_assigned",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "story_id": story.id,
                    "title": story.title,
                    "description": story.description,
                    "repo_url": repo_url,
                    "assigned_to": story.assigned_to
                }
            }
        )
    
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages."""
        self.logger.info(f"Received system message: {message}")
        # Handle system messages here
        pass 
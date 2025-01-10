# src/agents/project_manager/__init__.py
from ..base_agent import BaseAgent
from ...services.task_management.trello import TrelloTaskManagementService
from ...services.github_service import GitHubService
from ...utils.event_system import EventSystem
from ...utils.base_logger import BaseLogger
from ...utils.model import Model
from ...models.project import Project
from ...models.story import Story
from ...core.messaging import validate_message_type, create_success_response, create_error_response
from ...core.messaging.messages import SystemMessage
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
    """Project Manager agent responsible for coordinating development activities."""

    def __init__(self,
                 event_system: Optional[EventSystem] = None,
                 start_listening: bool = True,
                 github_service: Optional[GitHubService] = None,
                 github_config: Optional[Any] = None):
        """Initialize the project manager agent.

        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
            github_service: Optional GitHub service instance for testing
            github_config: Optional GitHub config for testing
        """
        # Initialize base class first to set up task manager and event system
        super().__init__(model_name="gpt-4-1106-preview", start_listening=start_listening, event_system=event_system)

        # Set up project manager-specific attributes
        self.github = github_service or GitHubService(github_config)
        self.logger = BaseLogger(self.__class__.__name__)
        self.logger.info("Project Manager initialized successfully")

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
            
    async def handle_system_message(self, message: SystemMessage) -> None:
        """Handle system messages."""
        try:
            if message.command == "project_created":
                # Create board and list for new project
                board = await self.task_management.create_board(
                    name=message.payload["name"],
                    description=message.payload["description"]
                )
                self._board_id = board["id"]
                
                list_obj = await self.task_management.create_list(
                    board_id=self._board_id,
                    name="Backlog"
                )
                self._list_id = list_obj["id"]
                
            elif message.command == "story_created":
                # Create card for new story
                if not self._list_id:
                    raise RuntimeError("No list ID available")
                    
                await self.task_management.create_card(
                    list_id=self._list_id,
                    name=message.payload["title"],
                    description=message.payload["description"],
                    position=message.payload["priority"]
                )
                
        except Exception as e:
            self.logger.error(f"Error handling system message: {str(e)}")
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
            
            # Create board
            board_id = await self.task_management.create_board(project_name, description)
            
            # Create stories
            stories = await self.create_stories(requirements, project_id)
            
            # Add stories to board
            for story in stories:
                await self.task_management.create_card(story.title, story.description, board_id)
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
            story = await self.task_management.get_card(story_id)
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
            
            # Create a new list for the status if needed
            if status:
                await self.task_management.create_list(story_id, status)
            
            # Update the card
            await self.task_management.create_card(
                title or "Untitled",
                description or "",
                story_id,
                status or "Backlog"
            )
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to update story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_pr_merged(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle PR merged event."""
        try:
            story_id = data["story_id"]
            await self.task_management.create_card(
                "Story completed",
                "PR has been merged",
                story_id,
                "Done"
            )
            return create_success_response()
        except Exception as e:
            self.logger.error(f"Failed to update story {story_id}: {str(e)}")
            return create_error_response(str(e))
    
    async def handle_pr_created(self, data: dict) -> Dict[str, str]:
        """Handle PR created event"""
        try:
            await self.task_management.create_card(
                "PR Created",
                f"PR: {data['pr_url']}",
                data["story_id"],
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
            
            await self.task_management.create_card(
                "Task Progress",
                f"Tasks completed: {completed_count}/{total_count}",
                story_id,
                "In Progress"
            )
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
    
    async def handle_story_assigned(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment event.
        
        Args:
            data: Story assignment data
            
        Returns:
            Dict[str, Any]: Response indicating success or failure
        """
        try:
            story_id = data["story_id"]
            title = data["title"]
            description = data["description"]
            assigned_to = data["assigned_to"]
            
            self.logger.info(f"Story {story_id} assigned to {assigned_to}")
            
            # Update story status in task management system
            await self.task_management.create_card(
                title,
                description,
                story_id,
                "In Progress"
            )
            
            return create_success_response()
        except KeyError as e:
            error_msg = f"Missing required field: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
        except Exception as e:
            error_msg = f"Error handling story assignment: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg) 
    
    async def create_roadmap(self, project_name: str, description: str, requirements: List[str]) -> Dict[str, Any]:
        """Create a project roadmap.
        
        Args:
            project_name: Name of the project
            description: Project description
            requirements: List of project requirements
            
        Returns:
            Dict containing the roadmap structure
            
        Raises:
            ValueError: If input parameters are invalid
        """
        try:
            # Validate input parameters
            if not project_name or not description or not requirements:
                raise ValueError("Project name, description and requirements cannot be empty")
                
            # Generate roadmap using model
            prompt = f"""Create a detailed project roadmap for:
            Project: {project_name}
            Description: {description}
            Requirements: {requirements}
            
            Break this down into milestones and tasks. Format as JSON with:
            - milestones: List of major project phases
            - tasks: List of specific tasks under each milestone
            - dependencies: Task dependencies
            - estimates: Time estimates for each task
            """
            
            roadmap_json = await self.model.generate_response(prompt)
            roadmap = json.loads(roadmap_json)
            
            # Validate roadmap structure
            required_keys = ["milestones", "tasks", "dependencies", "estimates"]
            missing_keys = [key for key in required_keys if key not in roadmap]
            if missing_keys:
                raise ValueError(f"Invalid roadmap structure generated. Missing keys: {missing_keys}")
                
            # Create board and lists
            board = await self.task_management.create_board(project_name, description)
            backlog = await self.task_management.create_list(board_id=board["id"], name="Backlog")
            
            # Create cards for stories and tasks
            for milestone in roadmap["milestones"]:
                for story in milestone["stories"]:
                    await self.task_management.create_card(
                        list_id=backlog["id"],
                        name=story["title"],
                        description=story["description"]
                    )
            
            for task in roadmap["tasks"]:
                await self.task_management.create_card(
                    list_id=backlog["id"],
                    name=task["title"],
                    description=task["description"]
                )
            
            # Publish success event
            await self.event_system.publish(
                "project_manager",
                {
                    "id": str(uuid.uuid4()),
                    "type": "roadmap_created",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "project_name": project_name,
                        "description": description,
                        "roadmap": roadmap,
                        "board_id": board["id"]
                    }
                }
            )
                
            return roadmap
            
        except Exception as e:
            # Publish error event
            await self.event_system.publish(
                "project_manager",
                {
                    "id": str(uuid.uuid4()),
                    "type": "roadmap_failed",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "project_name": project_name,
                        "error": str(e)
                    },
                    "status": "error"
                }
            )
            self.logger.error(f"Failed to create roadmap for {project_name}: {str(e)}")
            raise 
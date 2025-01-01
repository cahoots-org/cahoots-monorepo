# src/agents/project_manager.py
from .base_agent import BaseAgent
from ..services.trello_service import TrelloService
from ..services.github_service import GitHubService
from ..utils.event_system import EventSystem
from ..utils.logger import Logger
from ..models.project import Project
from ..models.story import Story
from typing import List, Dict, TypedDict, Union, Any
import uuid
import asyncio
import os
import json

class ProjectMessage(TypedDict):
    type: str
    project_name: str
    description: str
    project_id: str
    requirements: List[str]

class ProjectManager(BaseAgent):
    def __init__(self):
        """Initialize the project manager agent."""
        try:
            self.logger = Logger(self.__class__.__name__)
            self.logger.debug("Starting ProjectManager initialization")
            
            # Initialize base class first
            self.logger.debug("Initializing base agent")
            super().__init__("codellama/CodeLlama-7b-instruct-hf")
            
            # Initialize services without requiring API keys yet
            self.logger.debug("Initializing GitHub service")
            self.github = GitHubService()
            self.logger.debug("GitHub service initialized")
            
            self.logger.debug("Initializing Trello service")
            self.trello = TrelloService()
            self.logger.debug("Trello service initialized")
            
            self.logger.info("Project Manager initialized successfully")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to initialize Project Manager: {str(e)}")
                self.logger.error("Stack trace:", exc_info=True)
            raise
            
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        try:
            self.logger.info("Setting up event system")
            await self.event_system.connect()
            self.logger.debug("Event system connected")
            
            await self.event_system.subscribe("system", self.handle_system_message)
            await self.event_system.subscribe("project_manager", self.process_message)
            await self.event_system.subscribe("pr_merged", self.handle_pr_merged)
            await self.event_system.subscribe("pr_created", self.handle_pr_created)
            await self.event_system.subscribe("task_completed", self.handle_task_completed)
            
            self._listening_task = asyncio.create_task(self.start_listening())
            self.logger.info("Event system setup complete")
        except Exception as e:
            self.logger.error(f"Failed to setup event system: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise
        
    async def _handle_message(self, message: dict) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle, already decoded if it was a string.
            
        Returns:
            Dict[str, Any]: The response to the message.
            
        Raises:
            ValueError: If the message has an unknown type
            RuntimeError: If required environment variables are missing
        """
        if message["type"] == "new_project":
            if not os.getenv("TRELLO_API_KEY"):
                error_msg = "TRELLO_API_KEY environment variable is missing"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            if not os.getenv("TRELLO_API_SECRET"):
                error_msg = "TRELLO_API_SECRET environment variable is missing"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            await self.handle_new_project(message)
            return {"status": "success"}
        elif message["type"] == "project_complete":
            await self.handle_project_complete(message)
            return {"status": "success"}
        elif message["type"] == "get_story":
            story = await self.handle_get_story(message)
            return {"status": "success", "story": story}
        elif message["type"] == "update_story":
            await self.handle_update_story(message)
            return {"status": "success"}
        else:
            error_msg = f"Unknown message type: {message['type']}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
    async def handle_new_project(self, message: dict):
        """Handle new project creation"""
        try:
            self.logger.info(f"Creating new project: {message['project_name']}")
            
            # Create GitHub repository
            repo_name = self.generate_unique_name(message["project_name"])
            self.logger.info(f"Creating GitHub repository: {repo_name}")
            repo_url = self.github.create_repository(repo_name, message["description"])
            self.logger.info(f"Created GitHub repository: {repo_url}")
            
            # Create Trello board
            self.logger.info("Creating Trello board")
            board = self.trello.create_board(message["project_name"])
            
            # Create default lists
            self.logger.info("Creating Trello lists")
            self.trello.create_list(board.id, "Backlog")
            self.trello.create_list(board.id, "In Progress")
            self.trello.create_list(board.id, "Review")
            self.trello.create_list(board.id, "Testing")
            self.trello.create_list(board.id, "Done")
            
            # Generate stories
            self.logger.info("Generating user stories")
            stories = self.create_stories(message["description"])
            
            # Create Trello cards for stories
            self.logger.info("Creating Trello cards for stories")
            for story in stories:
                card = self.trello.add_story_to_board(board, story)
                story.id = card.id
                
                # Assign story based on type
                story.assigned_to = self.assign_story(story)
                self.logger.info(f"Assigned story {story.id} to {story.assigned_to}")
                
                # Notify assigned developer
                await self.notify_developer(story, repo_url)
            
            self.logger.info("Project creation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create project: {str(e)}")
            raise
            
    async def handle_project_complete(self, message: dict):
        """Handle project completion review"""
        project = Project.from_dict(message["project"])
        review_result = self.review_project(project)
        
        if not review_result["approved"]:
            raise ValueError(review_result["feedback"])
            
    async def handle_get_story(self, message: dict):
        """Handle story retrieval"""
        try:
            card = self.trello.get_card(message["story_id"])
            self.logger.info(f"Retrieved story {message['story_id']}")
        except Exception as e:
            self.logger.error(f"Failed to get story: {str(e)}")
            raise
            
    async def handle_update_story(self, message: dict):
        """Handle story updates"""
        try:
            self.trello.update_card(
                message["story_id"],
                message.get("title"),
                message.get("description"),
                message.get("status")
            )
            self.logger.info(f"Updated story {message['story_id']}")
        except Exception as e:
            self.logger.error(f"Failed to update story: {str(e)}")
            raise
    
    async def handle_pr_merged(self, data: dict):
        """Handle PR merged event"""
        try:
            self.trello.update_card(
                data["story_id"],
                None,
                None,
                "Done"
            )
        except Exception as e:
            self.logger.error(f"Failed to handle PR merged event: {str(e)}")
    
    async def handle_pr_created(self, data: dict):
        """Handle PR created event"""
        try:
            self.trello.update_card(
                data["story_id"],
                None,
                f"PR: {data['pr_url']}",
                "Review"
            )
        except Exception as e:
            self.logger.error(f"Failed to handle PR created event: {str(e)}")
    
    async def handle_task_completed(self, data: dict):
        """Handle task completion event"""
        try:
            card = self.trello.get_card(data["story_id"])
            current_desc = card.description or ""
            
            # Update task progress
            task_section = f"\n\n## Tasks Progress\nCompleted: {data['completed_count']}/{data['total_count']} tasks"
            if "## Tasks Progress" in current_desc:
                new_desc = current_desc[:current_desc.find("## Tasks Progress")] + task_section
            else:
                new_desc = current_desc + task_section
            
            self.trello.update_card(
                data["story_id"],
                None,
                new_desc,
                "In Progress"
            )
        except Exception as e:
            self.logger.error(f"Failed to handle task completion event: {str(e)}")
    
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
    
    async def notify_developer(self, story: Story, repo_url: str):
        """Notify assigned developer about the story"""
        try:
            await self.event_system.publish("story_assigned", {
                "story_id": story.id,
                "title": story.title,
                "description": story.description,
                "repo_url": repo_url,
                "assigned_to": story.assigned_to
            })
        except Exception as e:
            self.logger.error(f"Failed to notify developer: {str(e)}")
    
    async def create_roadmap(self, description: str) -> dict:
        """Create a project roadmap"""
        prompt = f"""Create a detailed project roadmap based on this description:
        {description}
        
        Include:
        - Project phases
        - Major milestones
        - Timeline estimates
        - Dependencies
        """
        
        roadmap_response = await self.generate_response(prompt)
        tasks = [task.strip() for task in roadmap_response.split("\n") if task.strip()]
        return {
            "tasks": tasks,
            "raw": roadmap_response
        }
    
    async def create_requirements(self, description: str) -> dict:
        """Create project requirements"""
        prompt = f"""Create detailed requirements based on this description:
        {description}
        
        Include:
        - Functional requirements
        - Technical requirements
        - Non-functional requirements
        - Constraints
        """
        
        requirements_response = await self.generate_response(prompt)
        return {
            "requirements": requirements_response.split("\n"),
            "raw": requirements_response
        }
    
    async def create_stories(self, description: str) -> List[Story]:
        """Create user stories"""
        prompt = f"""Break down this project into user stories:
        {description}
        
        Format each story as:
        Title: <title>
        Description: <description>
        ---
        """
        
        stories_response = await self.generate_response(prompt)
        stories = []
        
        for story_text in stories_response.split("---"):
            if not story_text.strip():
                continue
                
            lines = story_text.strip().split("\n")
            title = lines[0].replace("Title:", "").strip()
            description = "\n".join(lines[1:]).replace("Description:", "").strip()
            
            story = Story(
                id=str(uuid.uuid4()),
                title=title,
                description=description
            )
            stories.append(story)
        
        return stories
    
    def review_project(self, project: Project) -> dict:
        """Review the completed project"""
        prompt = f"""Review this project for completion and quality:
        Name: {project.name}
        Description: {project.description}
        Stories: {len(project.stories)} total
        
        Check for:
        - All requirements met
        - Code quality
        - Documentation
        - Test coverage
        """
        
        review_response = self.generate_response(prompt)
        approved = "approved" in review_response.lower() or "complete" in review_response.lower()
        
        return {
            "approved": approved,
            "feedback": review_response
        }
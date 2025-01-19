"""Project Manager Agent implementation."""

# src/agents/project_manager/__init__.py
from ..base_agent import BaseAgent
from ...services.task_management.trello import TrelloTaskManagementService
from ...services.github_service import GitHubService
from ...utils.event_system import EventSystem
from ...utils.base_logger import BaseLogger
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
from ...models.team_config import TeamConfig, ServiceRole

class ProjectMessage(TypedDict):
    type: str
    project_name: str
    description: str
    project_id: str
    requirements: List[str]

class ProjectManager(BaseAgent):
    """Project Manager agent responsible for coordinating development activities."""

    def __init__(self,
                 github_service: GitHubService,
                 event_system: Optional[EventSystem] = None,
                 start_listening: bool = True):
        """Initialize the project manager agent."""
        # Load team configuration
        self.team_config = TeamConfig.load_from_file()
        self.role_config = self.team_config.roles[ServiceRole.PROJECT_MANAGER]
        
        # Initialize base class with model name from config
        super().__init__(
            model_name=self.role_config.model_name,
            start_listening=start_listening,
            event_system=event_system
        )

        # Set up project manager-specific attributes
        self._github = github_service
        self.logger = BaseLogger(self.__class__.__name__)
        
        # Set up board structure from config
        self.board_lists = self.role_config.board_structure["default_lists"]
        
        self.logger.info("Project Manager initialized successfully")
        
    def assign_story(self, story: Story) -> str:
        """Assign a story to the appropriate team member based on configured rules."""
        title_lower = story.title.lower()
        
        # Check UI/UX assignments
        for prefix in self.role_config.task_assignment_rules["ui_prefixes"]:
            if title_lower.startswith(prefix):
                return "ux_designer"
                
        # Check test assignments
        for keyword in self.role_config.task_assignment_rules["test_keywords"]:
            if keyword in title_lower:
                return "tester"
                
        # Default developer assignment
        return self.role_config.task_assignment_rules["default_assignment"].format(
            hash=hash(story.id) % 2 + 1
        )
        
    async def create_roadmap(self, project_name: str, description: str, requirements: List[str]) -> Dict[str, Any]:
        """Create project roadmap with validation from config."""
        try:
            # Generate roadmap using LLM
            roadmap_json = await self.llm.generate_roadmap(project_name, description, requirements)
            roadmap = json.loads(roadmap_json)
            
            # Validate roadmap structure using config
            required_keys = self.role_config.roadmap_validation["required_keys"]
            missing_keys = [key for key in required_keys if key not in roadmap]
            if missing_keys:
                raise ValueError(f"Invalid roadmap structure generated. Missing keys: {missing_keys}")
                
            # Create board and lists from config
            board = await self.task_management.create_board(project_name, description)
            lists = {}
            for list_name in self.board_lists:
                lists[list_name] = await self.task_management.create_list(
                    board_id=board["id"],
                    name=list_name
                )
            
            # Create cards for stories and tasks
            for milestone in roadmap["milestones"]:
                for story in milestone["stories"]:
                    await self.task_management.create_card(
                        list_id=lists["Backlog"]["id"],
                        name=story["title"],
                        description=story["description"]
                    )
            
            for task in roadmap["tasks"]:
                await self.task_management.create_card(
                    list_id=lists["Backlog"]["id"],
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
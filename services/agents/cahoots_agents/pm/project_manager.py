"""Project Manager Agent implementation."""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from cahoots_core.ai import AIProvider
from cahoots_core.models.story import Story
from cahoots_core.models.team_config import TeamConfig
from cahoots_core.services.github_service import GitHubService
from cahoots_core.utils.metrics import MetricsCollector
from cahoots_events.bus.system import EventSystem

from ..base import BaseAgent


class ProjectMessage(TypedDict):
    type: str
    project_name: str
    description: str
    project_id: str
    requirements: List[str]


class ProjectManager(BaseAgent):
    """Project manager agent responsible for managing stories and tasks."""

    def __init__(
        self,
        event_system: EventSystem,
        config: Optional[Dict[str, Any]] = None,
        ai_provider: Optional[AIProvider] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the project manager.

        Args:
            event_system: Event system for communication
            config: Optional configuration dictionary
            ai_provider: Optional AI provider for generating responses
            **kwargs: Additional arguments to pass to the base class
        """
        super().__init__(
            agent_type="project_manager",
            event_system=event_system,
            config=config,
            ai_provider=ai_provider,
            **kwargs,
        )
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsCollector(service_name="project_manager")
        self.agent = ai_provider  # Store AI provider as agent for compatibility

    async def start(self) -> None:
        """Start the project manager agent."""
        self.logger.info("Starting project manager agent")
        await super().start()
        await self.event_system.subscribe("story.*", self.handle_story_event)

    async def handle_story_event(self, event: Dict[str, Any]) -> None:
        """Handle story-related events.

        Args:
            event: Event data
        """
        event_type = event.get("type")
        if event_type == "story.created":
            await self.handle_story_created(event)
        elif event_type == "story.feedback":
            await self.handle_story_feedback(event)
        elif event_type == "story.completed":
            await self.handle_story_completed(event)

    async def handle_story_created(self, event: Dict[str, Any]) -> None:
        """Handle story creation event.

        Args:
            event: Event data containing story details
        """
        story_data = event.get("data", {})
        story = Story.from_dict(story_data)

        # Estimate complexity and assign story
        complexity = await self.estimate_story_complexity(story)
        await self.assign_story(story.id, complexity)

    async def handle_story_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story feedback.

        Args:
            feedback_data: Story feedback data

        Returns:
            Response with actions to take
        """
        try:
            prompt = f"Handle story feedback: {json.dumps(feedback_data)}"
            response = await self.agent.generate_response(prompt)
            result = json.loads(response)

            # Publish feedback processed event
            event_data = {
                "story_id": feedback_data["story_id"],
                "feedback": feedback_data["feedback"],
                "actions": result.get("actions", []),
            }
            try:
                await self.event_system.publish("story.feedback.processed", event_data)
            except Exception as e:
                self.logger.error(f"Error publishing feedback event: {str(e)}")

            return result
        except json.JSONDecodeError:
            raise ValueError("Failed to parse feedback response")

    async def estimate_story_complexity(self, story: Story) -> Dict[str, Any]:
        """Estimate story complexity.

        Args:
            story: Story to estimate

        Returns:
            Dictionary containing complexity estimation
        """
        prompt = f"""
        Story Title: {story.title}
        Description: {story.description}
        Priority: {story.priority}
        
        Analyze this story and estimate its complexity. Return as JSON:
        {{
            "complexity": "low|medium|high",
            "estimated_hours": number,
            "factors": ["factor1", "factor2"]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error estimating complexity: {str(e)}")
            raise

    async def assign_story(self, story_id: str, developer_id: str) -> Dict[str, Any]:
        """Assign a story to a developer.

        Args:
            story_id: Story ID
            developer_id: Developer ID

        Returns:
            Assignment details
        """
        try:
            prompt = f"Assign story {story_id} to developer {developer_id}"
            response = await self.agent.generate_response(prompt)
            result = json.loads(response)

            # Publish story assigned event
            event_data = {
                "story_id": story_id,
                "developer_id": developer_id,
                "status": result.get("status"),
            }
            try:
                await self.event_system.publish("story.assigned", event_data)
            except Exception as e:
                self.logger.error(f"Error publishing assignment event: {str(e)}")

            return result
        except json.JSONDecodeError:
            raise ValueError("Failed to parse assignment response")

    async def create_task(self, story_id: str, details: Dict[str, Any]) -> None:
        """Create a new task for a story.

        Args:
            story_id: ID of the story
            details: Task details
        """
        # TODO: Implement task creation
        pass

    async def update_story(self, story_id: str, details: Dict[str, Any]) -> None:
        """Update story details.

        Args:
            story_id: ID of the story to update
            details: Updated details
        """
        # TODO: Implement story update
        pass

    async def notify_team(self, story_id: str, details: Dict[str, Any]) -> None:
        """Notify team about story updates.

        Args:
            story_id: ID of the story
            details: Notification details
        """
        # TODO: Implement team notification
        pass

    async def handle_system_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system messages.

        Args:
            message: System message to handle

        Returns:
            Response with operation status
        """
        command = message.get("command")
        payload = message.get("payload", {})

        if command == "create_project":
            return await self.handle_project_created(payload)
        elif command == "create_story":
            return await self.handle_story_created(payload)
        else:
            self.logger.warning(f"Unknown command: {command}")
            return {"status": "error", "message": f"Unknown command: {command}"}

    async def handle_project_created(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project creation.

        Args:
            project_data: Project creation data

        Returns:
            Response with created project details
        """
        try:
            # Create board
            board = await self.task_management.create_board(
                name=project_data["name"], description=project_data["description"]
            )
            self.board_id = board.get("id")
            board_url = board.get("url")  # Get board URL from Trello response

            # Create backlog list
            backlog = await self.task_management.create_list(board_id=self.board_id, name="Backlog")
            self.list_id = backlog.get("id")

            # Get GitHub repository URL
            repo_url = await self.github_service.get_repository_url(project_data["name"])

            # Prepare project resources information
            project_resources = {
                "name": project_data["name"],
                "description": project_data["description"],
                "task_board_url": board_url,
                "repository_url": repo_url,
                "board_id": self.board_id,
                "list_id": self.list_id,
            }

            # Notify about project creation and resources
            await self.event_system.publish(
                "project_resources_ready",
                {"project_id": project_data.get("id"), "resources": project_resources},
            )

            return {"status": "success", **project_resources}
        except Exception as e:
            self.logger.error(f"Error creating project: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def handle_task_completed(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task completion.

        Args:
            task_data: Task completion data

        Returns:
            Response with updated task status
        """
        try:
            # Update task status
            task = {
                "id": task_data["id"],
                "status": "completed",
                "completion_data": task_data["completion_data"],
            }

            # Notify about task completion
            await self.event_system.publish("task_completed", {"task": task})

            return {"status": "success", "task": task}

        except Exception as e:
            self.logger.error(f"Failed to handle task completion: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_pr_created(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull request creation.

        Args:
            pr_data: Pull request data

        Returns:
            Response with reviewer assignments
        """
        try:
            # Determine reviewers based on PR content
            reviewers = ["qa_tester"]  # Always include QA

            # Add UX designer for UI changes
            if any(
                "ui" in file.lower() or "frontend" in file.lower()
                for file in pr_data.get("files", [])
            ):
                reviewers.append("ux_designer")

            # Update PR with reviewers
            await self.github_service.update_pr(pr_data["id"], {"reviewers": reviewers})

            # Notify about PR assignment
            await self.event_system.publish("pr_assigned", {"pr": pr_data, "reviewers": reviewers})

            return {"status": "success", "pr": pr_data, "reviewers": reviewers}

        except Exception as e:
            self.logger.error(f"Failed to handle PR creation: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_design_completed(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle design completion.

        Args:
            design_data: Design completion data

        Returns:
            Response with implementation tasks
        """
        try:
            # Create implementation tasks for each component
            tasks = []
            assignments = {}

            for component in design_data["components"]:
                task = {
                    "id": str(uuid.uuid4()),
                    "type": "development",
                    "title": f"Implement {component['name']}",
                    "description": component["specs"],
                    "design_url": design_data["design_url"],
                }
                tasks.append(task)
                assignments[task["id"]] = "developer"

            # Notify about implementation tasks
            await self.event_system.publish(
                "design_implementation_tasks_created", {"tasks": tasks, "assignments": assignments}
            )

            return {"tasks": tasks, "assignments": assignments}

        except Exception as e:
            self.logger.error(f"Failed to handle design completion: {e}")
            return {"status": "error", "message": str(e)}

    async def create_roadmap(
        self, project_name: str, description: str, requirements: List[str]
    ) -> Dict[str, Any]:
        """Create project roadmap.

        Args:
            project_name: Name of the project
            description: Project description
            requirements: List of project requirements

        Returns:
            Generated roadmap with milestones and tasks
        """
        try:
            # Generate roadmap using AI model
            prompt = self._generate_roadmap_prompt(project_name, description, requirements)
            response = await self.model.generate_response(prompt)
            roadmap = json.loads(response)

            return roadmap

        except Exception as e:
            self.logger.error(f"Failed to create roadmap: {e}")
            return None

    def _generate_roadmap_prompt(
        self, project_name: str, description: str, requirements: List[str]
    ) -> str:
        """Generate prompt for roadmap creation.

        Args:
            project_name: Name of the project
            description: Project description
            requirements: List of project requirements

        Returns:
            Generated prompt for the AI model
        """
        return f"""Create a detailed project roadmap for:
Project: {project_name}
Description: {description}
Requirements:
{chr(10).join(f'- {req}' for req in requirements)}

The roadmap should include:
1. Milestones with descriptions and estimates
2. Stories for each milestone
3. Tasks with dependencies
4. Time estimates for each task

Format the response as a JSON object with:
- milestones: List of milestone objects
- tasks: List of task objects
- dependencies: List of dependency objects
- estimates: Dictionary of task estimates"""

    async def create_story(self, story: Story) -> Dict[str, Any]:
        """Create a new story.

        Args:
            story: Story to create

        Returns:
            Created story details
        """
        prompt = f"""
        Story: {json.dumps(story.model_dump())}

        Create a story with tasks. Return as JSON:
        {{
            "status": "success",
            "story": {{...story details...}},
            "tasks": [
                {{
                    "id": "task1",
                    "title": "Task title",
                    "description": "Task description"
                }}
            ]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse story creation response")
        except Exception as e:
            self.logger.error(f"Error creating story: {str(e)}")
            raise

    async def review_story_completion(self, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review story completion.

        Args:
            completion_data: Story completion data

        Returns:
            Review results
        """
        prompt = f"""
        Completion Data: {json.dumps(completion_data)}

        Review the story completion. Return as JSON:
        {{
            "status": "approved|changes_needed",
            "feedback": "Review feedback",
            "required_changes": [
                {{
                    "task_id": "task1",
                    "description": "Change description"
                }}
            ]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error reviewing story completion: {str(e)}")
            raise

    async def prioritize_stories(self, stories: List[Story]) -> Dict[str, Any]:
        """Prioritize stories.

        Args:
            stories: List of stories to prioritize

        Returns:
            Prioritized stories
        """
        prompt = f"""
        Stories: {json.dumps([s.model_dump() for s in stories])}

        Prioritize these stories. Return as JSON:
        {{
            "status": "success",
            "prioritized_stories": [
                {{
                    "id": "story_id",
                    "priority": priority_number
                }}
            ]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error prioritizing stories: {str(e)}")
            raise

"""Developer agent implementation."""

import logging
import os
from typing import Any, Dict, List, NamedTuple, Optional

from cahoots_core.ai import AIProvider
from cahoots_core.models.story import Story
from cahoots_core.models.task import Task
from cahoots_core.services.github_service import GitHubService
from cahoots_events.bus import EventSystem

from ...base import BaseAgent
from ..code.code_generator import CodeGenerator
from ..code.code_validator import CodeValidator
from ..feedback.feedback_manager import FeedbackManager
from ..file.file_manager import FileManager
from ..pr.pr_manager import PRManager
from ..task.task_manager import TaskManager


class FailedTask(NamedTuple):
    """Represents a failed task implementation."""

    task_id: str
    error: str


class Developer(BaseAgent):
    """Developer agent responsible for implementing code changes."""

    def __init__(
        self,
        event_system: Optional[EventSystem] = None,
        github_service: Optional[GitHubService] = None,
        start_listening: bool = True,
        config: Dict[str, Any] = None,
        ai_provider: Optional[AIProvider] = None,
        workspace_dir: Optional[str] = None,
    ):
        """Initialize the developer agent.

        Args:
            event_system: Optional event system for communication
            github_service: Optional GitHub service for repository operations
            start_listening: Whether to start listening for events immediately
            config: Optional configuration dictionary
            ai_provider: Optional AI provider
            workspace_dir: Optional workspace directory path
        """
        # Get developer ID from environment
        self.developer_id = os.getenv("DEVELOPER_ID", "dev-1")

        # Initialize base class
        super().__init__(
            agent_type="developer",
            config=config or {},
            event_system=event_system,
            ai_provider=ai_provider,
        )

        # Initialize services
        self.github_service = github_service or GitHubService()

        # Set workspace directory
        self.workspace_dir = workspace_dir or os.getcwd()

        # Initialize managers
        self.task_manager = TaskManager(self)
        self.code_generator = CodeGenerator(self)
        self.code_validator = CodeValidator(self)
        self.feedback_manager = FeedbackManager(self)
        self.file_manager = FileManager(self, workspace_dir=self.workspace_dir)
        self.pr_manager = PRManager(self, github_service=self.github_service)

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Store start_listening flag
        self._start_listening = start_listening
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            await self.start()
            self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    def __await__(self):
        """Make the class awaitable."""

        async def _async_init():
            if not self._initialized and self._start_listening:
                await self.start()
                self._initialized = True
            return self

        return _async_init().__await__()

    async def start(self) -> None:
        """Start the developer agent."""
        await self.setup_events()
        self.logger.info(f"Developer {self.developer_id} started successfully")

    async def setup_events(self) -> None:
        """Set up event subscriptions."""
        if not self.event_system:
            return

        await self.event_system.connect()

        # Subscribe to relevant events
        await self.event_system.subscribe("story_assigned", self.handle_story_assignment)
        await self.event_system.subscribe("feedback_received", self.handle_feedback)
        await self.event_system.subscribe("review_requested", self.handle_review_request)

    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment event.

        Args:
            message: Event message containing story details

        Returns:
            Response with implementation status
        """
        story_data = message.get("story", {})

        # Validate assignment
        if story_data.get("assigned_to") != self.developer_id:
            return {"status": "error", "message": "Story not assigned to this developer"}

        try:
            # Clone repository if URL provided
            if repo_url := story_data.get("repo_url"):
                await self.github_service.clone_repository(repo_url)

            # Break down story into tasks
            tasks = await self.task_manager.break_down_story(story_data)

            # Notify implementation started
            await self.event_system.publish(
                "implementation_started",
                {"story_id": story_data["id"], "developer_id": self.developer_id},
            )

            # Implement tasks
            implementation_result = await self.implement_tasks(tasks)

            # Create pull request
            pr_url = await self.create_pr(implementation_result)

            # Notify implementation completed
            await self.event_system.publish(
                "implementation_completed",
                {"story_id": story_data["id"], "developer_id": self.developer_id, "pr_url": pr_url},
            )

            return {
                "status": "success",
                "pr_url": pr_url,
                "implementations": implementation_result["implementations"],
            }

        except Exception as e:
            self.logger.error(f"Failed to implement story: {e}")
            await self.event_system.publish(
                "implementation_failed",
                {
                    "story_id": story_data["id"],
                    "developer_id": self.developer_id,
                    "error": str(e),
                    "status": "error",
                },
            )
            return {"status": "error", "message": str(e)}

    async def handle_story_assignment(self, story: Story) -> Dict[str, Any]:
        """Handle a story assignment.

        Args:
            story: Story to implement

        Returns:
            Dictionary containing assignment results
        """
        try:
            # Notify about starting implementation
            await self.event_system.publish(
                "implementation_started", {"story_id": story.id, "developer_id": self.developer_id}
            )

            # Break down story into tasks
            tasks = await self.task_manager.break_down_story(story)

            # Implement tasks
            implementation_result = await self.implement_tasks(tasks)

            # Create PR if implementation was successful
            if implementation_result.get("implementations"):
                pr_url = await self.create_pr(implementation_result)
                implementation_result["pr_url"] = pr_url

            # Notify about completion
            await self.event_system.publish(
                "implementation_completed",
                {
                    "story_id": story.id,
                    "developer_id": self.developer_id,
                    "result": implementation_result,
                },
            )

            return {"status": "success", "story_id": story.id, "result": implementation_result}
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            return {"status": "error", "story_id": story.id, "error": str(e)}

    async def implement_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """Implement a list of tasks.

        Args:
            tasks: List of tasks to implement

        Returns:
            Dictionary containing successful implementations and failed tasks
        """
        implementations = {}
        failed_tasks = []

        for task in tasks:
            try:
                # Generate implementation
                implementation = await self.code_generator.generate_implementation(task)

                # Validate implementation
                validation = await self.code_validator.validate_implementation(implementation)

                if not validation.get("valid", False):
                    raise ValueError(f"Validation failed: {validation.get('errors', [])}")

                implementations[task.id] = {
                    "code": implementation["code"],
                    "file_path": implementation["file_path"],
                    "task": task.model_dump(),
                    "validation": validation,
                }

            except Exception as e:
                self.logger.error(f"Failed to implement task {task.id}: {e}")
                failed_tasks.append(FailedTask(task_id=task.id, error=str(e)))

        return {"implementations": implementations, "failed_tasks": failed_tasks}

    async def create_pr(self, implementation_result: Dict[str, Any]) -> str:
        """Create a pull request with implemented changes.

        Args:
            implementation_result: Result from implement_tasks

        Returns:
            URL of created pull request
        """
        # Validate all implementations before creating PR
        for impl in implementation_result["implementations"].values():
            if not impl["validation"]["valid"]:
                raise ValueError(f"Invalid implementation: {impl['validation']['errors']}")

        # Create branch and commit changes
        branch_name = await self.github_service.create_branch()
        await self.github_service.commit_changes(implementation_result["implementations"])

        # Create pull request
        pr_url = await self.github_service.create_pr(
            title="Implementation",
            body=self._generate_pr_description(implementation_result),
            branch=branch_name,
        )

        return pr_url

    def _generate_pr_description(self, implementation_result: Dict[str, Any]) -> str:
        """Generate pull request description from implementation result."""
        description = ["# Implementation Details\n"]

        for impl in implementation_result["implementations"].values():
            task = impl["task"]
            title = task.title if hasattr(task, "title") else task["title"]
            desc = task.description if hasattr(task, "description") else task["description"]
            description.extend(
                [
                    f"## {title}\n",
                    f"{desc}\n",
                    "### Changes\n",
                    f"- File: `{impl['file_path']}`\n",
                    "```python\n",
                    impl["code"],
                    "```\n",
                ]
            )

        if implementation_result.get("failed_tasks"):
            description.append("\n## Failed Tasks\n")
            for task in implementation_result["failed_tasks"]:
                title = task.title if hasattr(task, "title") else task["title"]
                description.append(f"- {title}\n")

        return "".join(description)

    async def handle_feedback(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback received event."""
        return await self.feedback_manager.process_feedback(message)

    async def handle_review_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code review request event."""
        return await self.pr_manager.handle_review_request(message)

    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Check if any tasks require UX design.

        Args:
            tasks: List of tasks to check

        Returns:
            True if any task requires UX design
        """
        return any(task.requires_ux for task in tasks)

    async def implement_task(self, task: Task) -> Dict[str, Any]:
        """Implement a single task.

        Args:
            task: Task to implement

        Returns:
            Dictionary containing implementation details
        """
        try:
            implementation = await self.code_generator.generate_implementation(task)
            validation = await self.code_validator.validate_implementation(implementation)

            if not validation.get("valid"):
                return {"status": "error", "task_id": task.id, "error": validation.get("error")}

            return {
                "status": "success",
                "task_id": task.id,
                "implementation": implementation,
                "validation": validation,
            }
        except Exception as e:
            self.logger.error(f"Failed to implement task {task.id}: {str(e)}")
            return {"status": "error", "task_id": task.id, "error": str(e)}

    async def handle_review_comments(self, pr_number: str, comments: List[str]) -> Dict[str, Any]:
        """Handle review comments.

        Args:
            pr_number: Pull request number
            comments: List of review comments

        Returns:
            Dictionary containing response to comments
        """
        return await self.pr_manager.handle_review_comments(pr_number, comments)

    async def create_pull_request(self, task: Task) -> str:
        """Create a pull request for a task.

        Args:
            task: Task to create PR for

        Returns:
            URL of the created pull request
        """
        implementation = await self.implement_task(task)
        if implementation["status"] == "error":
            raise ValueError(f"Failed to implement task: {implementation['error']}")

        pr_data = {
            "implementations": {
                task.id: {
                    "code": implementation["implementation"]["code"],
                    "file_path": implementation["implementation"]["file_path"],
                    "task": task,
                    "validation": implementation["validation"],
                }
            },
            "failed_tasks": [],
        }

        return await self.create_pr(pr_data)

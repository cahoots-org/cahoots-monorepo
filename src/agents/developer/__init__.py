"""Developer agent that implements code based on tasks."""
from typing import List, Dict, Any, Optional

from ..base_agent import BaseAgent
from ...models.task import Task
from ...services.github_service import GitHubService
from ...utils.base_logger import BaseLogger
from ...utils.event_system import EventSystem
from .task_manager import TaskManager
from .code_generator import CodeGenerator
from .code_validator import CodeValidator
from .feedback_manager import FeedbackManager
from .file_manager import FileManager
from .pr_manager import PRManager

class Developer(BaseAgent):
    """Developer agent that implements code based on tasks."""
    
    def __init__(self, developer_id: str, start_listening: bool = True, focus: str = "backend", event_system: Optional[EventSystem] = None):
        """Initialize the developer agent.
        
        Args:
            developer_id: The unique identifier for this developer
            start_listening: Whether to start listening for events immediately
            focus: The developer's focus area ("frontend" or "backend")
            event_system: Optional event system instance. If not provided, will get from singleton.
        """
        super().__init__("gpt-4-1106-preview", start_listening=False, event_system=event_system)  # Don't start listening until fully initialized
        self.github = GitHubService()
        self.developer_id = developer_id
        self.logger = BaseLogger(self.__class__.__name__)
        self.focus = focus
        self.feedback_history = []
        
        if not self.developer_id:
            raise RuntimeError("developer_id is required")
            
        # Initialize managers with shared task manager
        self.code_generator = CodeGenerator(self)
        self.code_validator = CodeValidator(self)
        self.feedback_manager = FeedbackManager(self)
        self.file_manager = FileManager(self)
        self.pr_manager = PRManager(self)
        
        # Ensure all managers use the same task manager instance
        for manager in [
            self.code_generator,
            self.code_validator,
            self.feedback_manager,
            self.file_manager,
            self.pr_manager
        ]:
            if hasattr(manager, "_task_manager"):
                manager._task_manager = self._task_manager
        
        # Start listening after initialization if requested
        if start_listening:
            self._task_manager.create_task(self.start_listening())
            
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        await super().setup_events()
        await self.event_system.subscribe("task_assigned", self._handle_message)
        await self.event_system.subscribe("story_assigned", self._handle_message)
        await self.event_system.subscribe("review_requested", self._handle_message)
        
    async def stop_listening(self) -> None:
        """Stop listening for events and cleanup all tasks."""
        self.logger.info("Stopping developer agent")
        
        # Stop event listener first
        await super().stop_listening()
        
        # Then cleanup manager tasks
        for manager in [
            self.code_generator,
            self.code_validator,
            self.feedback_manager,
            self.file_manager,
            self.pr_manager
        ]:
            if hasattr(manager, "cleanup"):
                try:
                    await manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up manager {manager.__class__.__name__}: {str(e)}")
        
        self.logger.info("Developer agent stopped")
        
    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Check if any tasks require UX design.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            bool: True if any task needs UX design, False otherwise
        """
        for task in tasks:
            if "ui" in task.title.lower() or "ux" in task.title.lower():
                return True
        return False
        
    def _get_relevant_feedback(self, context: str) -> List[Dict[str, Any]]:
        """Get relevant feedback for the given context.
        
        Args:
            context: The context to get feedback for
            
        Returns:
            List[Dict[str, Any]]: List of relevant feedback items
        """
        # Get feedback from manager and ensure it's a list
        feedback = self.feedback_manager.get_relevant_feedback(context)
        if not isinstance(feedback, list):
            return []
        return feedback
        
    def _integrate_feedback(self, feedback: List[Dict[str, Any]]) -> None:
        """Integrate feedback into the implementation process.
        
        Args:
            feedback: List of feedback items to integrate
        """
        self.feedback_history.append(feedback)
        self.feedback_manager.integrate_feedback(feedback)
        
    def _determine_file_path(self, task: Task) -> str:
        """Determine the appropriate file path for a task implementation.
        
        Args:
            task: The task to determine the file path for
            
        Returns:
            str: The determined file path
        """
        return self.file_manager.determine_file_path(task)
        
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle
            
        Returns:
            Dict[str, Any]: The response to the message
        """
        handlers = {
            "task_assigned": self.handle_task_assigned,
            "story_assigned": self.handle_story_assigned,
            "review_requested": self.handle_review_request
        }
        
        handler = handlers.get(message["type"])
        if not handler:
            raise ValueError(f"Unknown message type: {message['type']}")
            
        return await handler(message)

    async def __aenter__(self) -> "Developer":
        """Async context manager entry."""
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await super().__aexit__(exc_type, exc_val, exc_tb)
        
    async def implement_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """Implement a list of tasks in order.
        
        Args:
            tasks: List of tasks to implement
            
        Returns:
            Dict[str, Any]: Implementation results including code and metadata
        """
        self.logger.info(f"Implementing {len(tasks)} tasks")
        implementations = {}
        failed_tasks = []
        
        for task in tasks:
            try:
                self.logger.info(f"Implementing task: {task.title}")
                implementation = await self.code_generator.generate_implementation(task)
                
                validation_result = await self.code_validator.validate_implementation(
                    implementation["code"],
                    task
                )
                
                if validation_result["valid"]:
                    implementations[task.id] = {
                        "code": implementation["code"],
                        "file_path": implementation["file_path"],
                        "task": task.dict(),
                        "validation": validation_result
                    }
                else:
                    raise ValueError(f"Implementation validation failed: {validation_result['errors']}")
                    
            except Exception as e:
                self.logger.error(f"Failed to implement task {task.id}: {str(e)}")
                failed_tasks.append({
                    "task_id": task.id,
                    "error": str(e)
                })
                
        return {
            "implementations": implementations,
            "failed_tasks": failed_tasks
        }
        
    async def break_down_story(self, story: Dict[str, Any]) -> List[Task]:
        """Break down a user story into smaller technical tasks.
        
        Args:
            story: Dictionary containing story details
            
        Returns:
            List[Task]: List of tasks to implement the story
        """
        return await self.task_manager.break_down_story(story)
        
    async def create_pr(self, implementation_result: Dict[str, Any]) -> str:
        """Create a pull request with the implemented changes.
        
        Args:
            implementation_result: Results from implement_tasks
            
        Returns:
            str: URL of the created pull request
            
        Raises:
            ValueError: If any implementation has validation errors
        """
        # Check for validation errors
        for impl in implementation_result["implementations"].values():
            if not impl["validation"]["valid"]:
                raise ValueError(f"Implementation validation failed: {impl['validation']['errors']}")
                
        # Get first task ID for branch name
        first_task_id = next(iter(implementation_result["implementations"]))
        branch_name = f"feature/implementation-{first_task_id}"
        
        # Create branch
        await self.github.create_branch(branch_name)
        
        # Prepare changes
        changes = []
        for task_id, details in implementation_result["implementations"].items():
            changes.append({
                "file_path": details["file_path"],
                "content": details["code"]
            })
            
        # Commit changes
        await self.github.commit_changes(
            changes,
            f"Implement tasks: {', '.join(details['task']['title'] for details in implementation_result['implementations'].values())}"
        )
        
        # Prepare PR description with validation results
        pr_description = "## Implementation Details\n\n"
        for task_id, details in implementation_result["implementations"].items():
            pr_description += f"### {details['task']['title']}\n"
            pr_description += f"{details['task']['description']}\n\n"
            pr_description += "```python\n"
            pr_description += details['code']
            pr_description += "\n```\n\n"
            
        # Add validation results
        pr_description += "## Validation Results\n\n"
        pr_description += "✅ All implementations passed validation checks\n\n"
        
        # Create PR using GitHub API
        pr_url = await self.github.create_pr(
            title=f"Implementation of {len(implementation_result['implementations'])} tasks",
            body=pr_description,
            base="main",
            head=branch_name
        )
        
        return pr_url
        
    async def handle_task_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task assignment message.
        
        Args:
            message: Task assignment message
            
        Returns:
            Dict[str, Any]: Response indicating success/failure
        """
        try:
            task = Task(**message["task"])
            implementation = await self.implement_tasks([task])
            
            if implementation["failed_tasks"]:
                return {
                    "status": "error",
                    "message": f"Failed to implement task: {implementation['failed_tasks'][0]['error']}"
                }
                
            return {
                "status": "success",
                "implementation": implementation["implementations"][task.id]
            }
        except Exception as e:
            self.logger.error(f"Failed to handle task assignment: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment message.
        
        Args:
            message: Story assignment message
            
        Returns:
            Dict[str, Any]: Response indicating success/failure
        """
        story = None
        try:
            if not isinstance(message, dict) or "story" not in message:
                return {
                    "status": "error",
                    "message": "Invalid message format: missing story data"
                }
                
            story = message["story"]
            if not isinstance(story, dict):
                return {
                    "status": "error",
                    "message": "Invalid story format: expected dictionary"
                }
            
            # Check for required fields
            required_fields = ["story_id", "title", "description", "repo_url"]
            missing_fields = [field for field in required_fields if field not in story]
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Check if story is assigned to this developer
            if story.get("assigned_to") != self.developer_id:
                return {
                    "status": "error",
                    "message": f"Wrong developer: story is assigned to {story.get('assigned_to', 'unknown')}, not {self.developer_id}"
                }
            
            # Clone repository
            await self.github.clone_repository(story["repo_url"])
            
            # Publish implementation started event
            await self.event_system.publish("implementation_started", {
                "story_id": story["story_id"],
                "developer_id": self.developer_id
            })
            
            tasks = await self.break_down_story(story)
            implementation = await self.implement_tasks(tasks)
            
            if implementation["failed_tasks"]:
                error_messages = [f"{task['task_id']}: {task['error']}" for task in implementation["failed_tasks"]]
                await self.event_system.publish("implementation_failed", {
                    "story_id": story["story_id"],
                    "developer_id": self.developer_id,
                    "error": '; '.join(error_messages),
                    "status": "error"
                })
                return {
                    "status": "error",
                    "message": f"Implementation failed: {'; '.join(error_messages)}"
                }
                
            pr_url = await self.create_pr(implementation)
            
            # Publish implementation completed event
            await self.event_system.publish("implementation_completed", {
                "story_id": story["story_id"],
                "developer_id": self.developer_id,
                "pr_url": pr_url
            })
            
            return {
                "status": "success",
                "pr_url": pr_url,
                "implementation": implementation
            }
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            if story:
                await self.event_system.publish("implementation_failed", {
                    "story_id": story.get("story_id", "unknown"),
                    "developer_id": self.developer_id,
                    "error": str(e),
                    "status": "error"
                })
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def handle_review_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code review request.
        
        Args:
            message: Review request message
            
        Returns:
            Dict[str, Any]: Review results
        """
        try:
            # TODO: Implement code review logic
            return {
                "status": "success",
                "approved": True,
                "comments": []
            }
        except Exception as e:
            self.logger.error(f"Failed to handle review request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            } 
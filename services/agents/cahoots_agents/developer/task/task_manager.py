"""Task management functionality for the developer agent."""

import json
import logging
import uuid
from typing import Any, Dict, List

from cahoots_core.models.story import Story
from cahoots_core.models.task import Task


class TaskManager:
    """Handles task breakdown and management."""

    def __init__(self, agent):
        """Initialize the task manager.

        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)

    async def break_down_story(
        self, story: Story, *, requirements: List[str] = None, dependencies: List[str] = None
    ) -> List[Task]:
        """Break down a user story into smaller technical tasks.

        Args:
            story: Story object to break down
            requirements: Optional list of specific requirements to consider
            dependencies: Optional list of external dependencies to consider

        Returns:
            List[Task]: List of tasks to implement the story

        Raises:
            ValueError: If task breakdown fails or response is invalid
        """
        self.logger.info(f"Breaking down story: {story.title}")

        # Generate tasks using AI
        prompt = f"""
        Story Title: {story.title}
        Description: {story.description}
        Priority: {story.priority}
        Status: {story.status}
        Metadata: {story.metadata}
        Requirements: {requirements or []}
        Dependencies: {dependencies or []}

        Break this story down into technical tasks that need to be implemented.
        Return the tasks as a JSON array with the following structure for each task:
        {{
            "id": "unique_id",
            "title": "task title",
            "description": "detailed description",
            "requires_ux": boolean,
            "metadata": {{
                "dependencies": ["task_id1", "task_id2"],
                "acceptance_criteria": ["criteria1", "criteria2"]
            }}
        }}
        """

        try:
            response = await self.agent.generate_response(prompt)
            try:
                tasks_data = json.loads(response)
            except json.JSONDecodeError:
                raise ValueError("Failed to parse tasks from AI response")

            if not tasks_data:
                raise ValueError("No tasks generated")

            tasks = []
            for task_data in tasks_data:
                if "title" not in task_data or "description" not in task_data:
                    raise ValueError("Invalid task format - missing required fields")

                task = Task(
                    id=task_data.get("id", str(uuid.uuid4())),
                    title=task_data["title"],
                    description=task_data["description"],
                    requires_ux=task_data.get("requires_ux", False),
                    metadata={
                        **task_data.get("metadata", {}),
                        "requirements": requirements or [],
                        "dependencies": dependencies or [],
                    },
                )
                tasks.append(task)

            return tasks

        except ValueError as e:
            self.logger.error(f"Error breaking down story: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error breaking down story: {str(e)}")
            raise ValueError("Failed to break down story into tasks")

    def _validate_task_breakdown(self, tasks: List[Task]) -> None:
        """Validate the task breakdown for completeness and consistency.

        Args:
            tasks: List of tasks to validate

        Raises:
            ValueError: If validation fails
        """
        if not tasks:
            self.logger.error("No tasks found in breakdown")
            raise ValueError("Task breakdown validation failed: No tasks found")

        # Check for minimum required tasks
        if not any(t.metadata["type"] == "setup" for t in tasks):
            self.logger.warning("No setup tasks found in breakdown")

        if not any(t.metadata["type"] == "testing" for t in tasks):
            self.logger.warning("No testing tasks found in breakdown")

        # Check complexity distribution
        complexities = [t.metadata["complexity"] for t in tasks]
        avg_complexity = sum(complexities) / len(complexities)
        if avg_complexity > 3:
            self.logger.warning(f"High average task complexity: {avg_complexity}")

        # Check for balanced skill requirements
        all_skills = set()
        for task in tasks:
            all_skills.update(task.metadata["required_skills"])

        if len(all_skills) < 2:
            self.logger.warning("Limited skill requirements in task breakdown")

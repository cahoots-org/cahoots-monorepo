"""Task management functionality for the developer agent."""
from typing import List, Dict, Any
import json
import logging
import uuid

from src.models.task import Task

class TaskManager:
    """Handles task breakdown and management."""
    
    def __init__(self, agent):
        """Initialize the task manager.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
    async def break_down_story(self, story: Dict[str, Any]) -> List[Task]:
        """Break down a user story into smaller technical tasks.
        
        Args:
            story: Dictionary containing story details
            
        Returns:
            List[Task]: List of tasks to implement the story
        """
        self.logger.info(f"Breaking down story: {story['title']}")
        
        prompt = f"""Break down this user story into tasks. For each task, provide a JSON object with these fields:
        - title: task title
        - description: detailed task description
        - type: one of [setup, implementation, testing]
        - complexity: number 1-5
        - dependencies: list of task titles this task depends on
        - required_skills: list of technical skills needed for this task
        - risk_factors: list of potential risks (e.g., performance, security, reliability)

        Story Title: {story['title']}
        Story Description: {story['description']}

        Return the tasks as a JSON array with format:
        {{
            "tasks": [
                {{"title": "...", "description": "...", "type": "...", "complexity": 1, "dependencies": [], "required_skills": [], "risk_factors": []}},
                ...
            ]
        }}
        """
        
        response = await self.agent.generate_response(prompt)
        
        try:
            # Try to clean up the response if it's not pure JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1]
            if response.endswith('```'):
                response = response.rsplit('```', 1)[0]
            response = response.strip()
            
            tasks_data = json.loads(response)
            if not isinstance(tasks_data, dict) or "tasks" not in tasks_data:
                self.logger.error("LLM response is not a valid JSON object with tasks array")
                return []
                
            tasks = []
            for task_data in tasks_data["tasks"]:
                try:
                    task = Task(
                        id=str(uuid.uuid4()),
                        title=task_data["title"], 
                        description=task_data["description"],
                        requires_ux=self.agent.focus == "frontend",
                        metadata={
                            "type": task_data["type"],
                            "complexity": task_data["complexity"],
                            "dependencies": task_data.get("dependencies", []),
                            "required_skills": task_data.get("required_skills", ["python"]),
                            "risk_factors": task_data.get("risk_factors", [])
                        }
                    )
                    tasks.append(task)
                except KeyError as e:
                    self.logger.error(f"Missing required field in task data: {e}")
                    self.logger.debug(f"Task data: {task_data}")
                    continue
                    
            if not tasks:
                self.logger.error("No valid tasks could be created from LLM response")
                
            self._validate_task_breakdown(tasks)
            return tasks
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response that failed to parse: {response}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error parsing tasks: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            return []
            
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
        if not any(t.metadata['type'] == 'setup' for t in tasks):
            self.logger.warning("No setup tasks found in breakdown")
            
        if not any(t.metadata['type'] == 'testing' for t in tasks):
            self.logger.warning("No testing tasks found in breakdown")
            
        # Check complexity distribution
        complexities = [t.metadata['complexity'] for t in tasks]
        avg_complexity = sum(complexities) / len(complexities)
        if avg_complexity > 3:
            self.logger.warning(f"High average task complexity: {avg_complexity}")
            
        # Check for balanced skill requirements
        all_skills = set()
        for task in tasks:
            all_skills.update(task.metadata['required_skills'])
            
        if len(all_skills) < 2:
            self.logger.warning("Limited skill requirements in task breakdown") 
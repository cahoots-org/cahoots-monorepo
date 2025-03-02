"""Code generation functionality for the developer agent."""

import json
import logging
from typing import Any, Dict

from cahoots_core.models.task import Task


class CodeGenerator:
    """Handles code generation for tasks."""

    def __init__(self, agent):
        """Initialize the code generator.

        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)

    async def generate_implementation(self, task: Task) -> Dict[str, Any]:
        """Generate code implementation for a task.

        Args:
            task: Task to implement

        Returns:
            Dict[str, Any]: Implementation details including code and file path
        """
        prompt = f"""Implement code for this task:
        {task.title}
        
        Description:
        {task.description}
        
        Requirements:
        {json.dumps(task.metadata.get('requirements', {}), indent=2)}
        
        Dependencies:
        {json.dumps(task.metadata.get('dependencies', []), indent=2)}
        
        Generate implementation in the following format:
        {{
            "code": "... code here ...",
            "file_path": "path/to/file.py"
        }}
        """

        response = await self.agent.generate_response(prompt)

        try:
            implementation = json.loads(response)
            return implementation
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse implementation response: {str(e)}")

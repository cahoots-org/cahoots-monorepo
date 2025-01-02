"""File management functionality for the developer agent."""
from typing import Dict, Any
import logging
import os

from src.models.task import Task

class FileManager:
    """Handles file paths and implementation context."""
    
    def __init__(self, agent):
        """Initialize the file manager.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
    def determine_file_path(self, task: Task) -> str:
        """Determine the appropriate file path for a task.
        
        Args:
            task: Task to determine file path for
            
        Returns:
            str: Appropriate file path for the task
        """
        title_lower = task.title.lower()
        
        if "model" in title_lower or "database" in title_lower:
            return "src/models/model.py"
        elif "endpoint" in title_lower or "api" in title_lower:
            return "src/api/routes.py"
        elif "component" in title_lower or "ui" in title_lower:
            return "src/ui/components.py"
        elif "test" in title_lower:
            return "tests/test_main.py"
        else:
            # Create a valid Python module name
            module_name = "_".join(word.lower() for word in task.title.split() if word.isalnum())
            return f"src/core/{module_name}.py"
            
    def gather_implementation_context(self, task: Task, file_path: str) -> str:
        """Gather context for implementation including existing code and dependencies.
        
        Args:
            task: Task to gather context for
            file_path: Path to the file being modified
            
        Returns:
            str: Implementation context
        """
        context_parts = []
        
        # Add existing file content if it exists
        try:
            with open(file_path, 'r') as f:
                existing_code = f.read()
                context_parts.append(f"Existing file content:\n{existing_code}")
        except FileNotFoundError:
            context_parts.append("This will be a new file.")
            
        # Add related files based on task type
        if "model" in task.title.lower():
            context_parts.append("This should follow the existing model patterns.")
        elif "api" in task.title.lower():
            context_parts.append("This should follow REST API best practices.")
            
        return "\n".join(context_parts) 
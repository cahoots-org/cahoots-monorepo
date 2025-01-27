"""File management functionality for the developer agent."""
import logging
import os
from enum import Enum
from typing import List, Optional

from cahoots_core.models.task import Task

class FileOperation(Enum):
    """Enum for file operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"

class FileStatus(Enum):
    """Enum for file status."""
    NEW = "new"
    EXISTING = "existing"
    DELETED = "deleted"
    ERROR = "error"

class FileManager:
    """Handles file paths and implementation context."""
    
    def __init__(self, agent, workspace_dir: str):
        """Initialize the file manager.
        
        Args:
            agent: The developer agent instance
            workspace_dir: Path to the workspace directory
        """
        self.agent = agent
        self.workspace_dir = workspace_dir
        self.logger = logging.getLogger(__name__)
        
    def create_file(self, file_path: str, content: str) -> None:
        """Create a new file with content.
        
        Args:
            file_path: Path to the file relative to workspace
            content: Content to write to the file
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
            
    def read_file(self, file_path: str) -> str:
        """Read content from a file.
        
        Args:
            file_path: Path to the file relative to workspace
            
        Returns:
            str: Content of the file
            
        Raises:
            FileNotFoundError: If file does not exist
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        with open(full_path, 'r') as f:
            return f.read()
            
    def update_file(self, file_path: str, content: str) -> None:
        """Update an existing file with new content.
        
        Args:
            file_path: Path to the file relative to workspace
            content: New content for the file
            
        Raises:
            FileNotFoundError: If file does not exist
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        with open(full_path, 'w') as f:
            f.write(content)
            
    def delete_file(self, file_path: str) -> None:
        """Delete a file.
        
        Args:
            file_path: Path to the file relative to workspace
            
        Raises:
            FileNotFoundError: If file does not exist
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        os.remove(full_path)
            
    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """List files in the workspace.
        
        Args:
            pattern: Optional glob pattern to filter files
            
        Returns:
            List[str]: List of file paths relative to workspace
        """
        result = []
        for root, _, files in os.walk(self.workspace_dir):
            for file in files:
                if pattern is None or file.endswith(pattern.replace('*', '')):
                    rel_path = os.path.relpath(os.path.join(root, file), self.workspace_dir)
                    result.append(rel_path)
        return result
        
    def create_directory(self, dir_path: str) -> None:
        """Create a directory.
        
        Args:
            dir_path: Path to the directory relative to workspace
        """
        full_path = os.path.join(self.workspace_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        
    def delete_directory(self, dir_path: str) -> None:
        """Delete a directory and its contents.
        
        Args:
            dir_path: Path to the directory relative to workspace
        """
        full_path = os.path.join(self.workspace_dir, dir_path)
        if os.path.exists(full_path):
            import shutil
            shutil.rmtree(full_path)
            
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
            module_name = "_".join(word.lower() for word in "".join(c if c.isalnum() or c.isspace() else " " for c in task.title).split())
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
            full_path = os.path.join(self.workspace_dir, file_path)
            with open(full_path, 'r') as f:
                existing_code = f.read()
                context_parts.append(f"Existing file content:\n{existing_code}")
        except FileNotFoundError:
            context_parts.append("This will be a new file.")
        except PermissionError:
            self.logger.warning(f"Permission denied when trying to read {file_path}")
            
        # Add related files based on task type
        if "model" in task.title.lower():
            context_parts.append("This should follow the existing model patterns.")
        elif "api" in task.title.lower():
            context_parts.append("This should follow REST API best practices.")
            
        return "\n".join(context_parts) 
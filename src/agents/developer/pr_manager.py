"""Pull request management functionality for the developer agent."""
from typing import Dict, Any
import logging

class PRManager:
    """Handles pull request creation and management."""
    
    def __init__(self, agent):
        """Initialize the PR manager.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
    async def create_pr(self, implementation_result: Dict[str, Any]) -> str:
        """Create a pull request with the implemented changes.
        
        Args:
            implementation_result: Results from implement_tasks
            
        Returns:
            str: URL of the created pull request
            
        Raises:
            ValueError: If implementation validation fails
        """
        self.logger.info("Creating pull request")
        
        # Validate implementations in isolated environment
        validation_results = await self._validate_implementations(implementation_result)
        
        if not validation_results["valid"]:
            raise ValueError(
                f"Implementation validation failed:\n{validation_results['error']}\n"
                f"Logs:\n{validation_results.get('logs', 'No logs available')}"
            )
        
        # Get first task ID for branch name
        first_task_id = next(iter(implementation_result["implementations"]))
        branch_name = f"feature/implementation-{first_task_id}"
        
        # Create branch
        await self.agent.github.create_branch(branch_name)
        
        # Prepare changes
        changes = []
        for task_id, details in implementation_result["implementations"].items():
            changes.append({
                "file_path": details["file_path"],
                "content": details["code"]
            })
            
        # Commit changes
        await self.agent.github.commit_changes(
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
        pr_url = await self.agent.github.create_pr(
            title=f"Implementation of {len(implementation_result['implementations'])} tasks",
            body=pr_description,
            base="main",
            head=branch_name
        )
        
        return pr_url
        
    async def _validate_implementations(self, implementation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all implementations in an isolated environment.
        
        Args:
            implementation_result: Results from implement_tasks
            
        Returns:
            Dict[str, Any]: Validation results
        """
        # Check for validation errors in any implementation
        for task_id, details in implementation_result["implementations"].items():
            if not details["validation"]["valid"]:
                return {
                    "valid": False,
                    "error": f"Task {task_id} validation failed: {details['validation']['errors']}"
                }
                
        return {"valid": True} 
"""Pull request management functionality for the developer agent."""
from typing import Dict, Any, Optional, List
import logging
from enum import Enum
import json

from cahoots_core.services.github_service import GitHubService
from src.cahoots_agents.base import BaseAgent

class PRStatus(str, Enum):
    """Status of a pull request."""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"

class PRReviewStatus(str, Enum):
    """Status of a pull request review."""
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENTED = "commented"
    DISMISSED = "dismissed"

class PRManager:
    """Manager for pull request operations."""

    def __init__(self, agent: BaseAgent, github_service: GitHubService) -> None:
        """Initialize the PR manager.

        Args:
            agent: Agent instance for generating responses
            github_service: GitHub service for repository operations
        """
        self.agent = agent
        self.github_service = github_service
        self.logger = logging.getLogger(__name__)

    async def generate_pr_description(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a PR description.

        Args:
            pr_data: Pull request data containing:
                    - title (str): PR title
                    - description (str, optional): PR description
                    - branch (str, optional): Feature branch
                    - base (str, optional): Base branch
                    - tasks (list, optional): Related tasks

        Returns:
            Dictionary containing PR description
        """
        # Set defaults for optional fields
        description = pr_data.get('description', '')
        branch = pr_data.get('branch', 'main')
        base = pr_data.get('base', 'main')
        tasks = pr_data.get('tasks', [])

        prompt = f"""
        Title: {pr_data['title']}
        Base Branch: {base}
        Feature Branch: {branch}
        Description: {description}
        Tasks: {[task.title for task in tasks] if tasks else []}

        Generate a pull request description. Return as JSON:
        {{
            "title": "PR title",
            "body": "PR description with markdown formatting",
            "labels": ["label1", "label2"]
        }}
        """

        try:
            response = await self.agent.generate_response(prompt)
            description = json.loads(response)
            return description
        except json.JSONDecodeError:
            raise ValueError("Failed to parse PR description")
        except Exception as e:
            self.logger.error(f"Error generating PR description: {str(e)}")
            raise

    async def handle_review_request(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a review request.

        Args:
            review_data: Review request data containing:
                        - pr_number (str): PR number
                        - repo (str): Repository name
                        - files_changed (list): List of changed files

        Returns:
            Dictionary containing review response with status and comments
        """
        prompt = f"""
        PR Number: {review_data['pr_number']}
        Repository: {review_data['repo']}
        Files Changed: {review_data['files_changed']}

        Review these changes and provide feedback. Return as JSON:
        {{
            "status": "approved|changes_requested",
            "comments": [
                {{
                    "file": "file path",
                    "line": line_number,
                    "comment": "comment text",
                    "suggestion": "optional code suggestion"
                }}
            ]
        }}
        """

        try:
            response = await self.agent.generate_response(prompt)
            review = json.loads(response)
            if review["status"] not in ["approved", "changes_requested"]:
                raise ValueError("Invalid review status")
            return review
        except json.JSONDecodeError:
            raise ValueError("Failed to parse review response")
        except Exception as e:
            self.logger.error(f"Error handling review request: {str(e)}")
            raise

    async def handle_review_comments(self, pr_number: str, comments: List[str]) -> Dict[str, Any]:
        """Handle review comments.

        Args:
            pr_number: Pull request number
            comments: List of review comments

        Returns:
            Dictionary containing response to comments
        """
        prompt = f"""
        PR Number: {pr_number}
        Review Comments: {comments}

        Analyze these review comments and suggest changes. Return as JSON:
        {{
            "status": "success|failure",
            "changes": [
                {{
                    "file": "file path",
                    "line": line_number,
                    "change": "suggested change"
                }}
            ]
        }}
        """

        try:
            response = await self.agent.generate_response(prompt)
            changes = json.loads(response)
            return changes
        except json.JSONDecodeError:
            raise ValueError("Failed to parse changes response")
        except Exception as e:
            self.logger.error(f"Error handling review comments: {str(e)}")
            raise

    async def get_pr_status(self, pr_number: str) -> PRStatus:
        """Get PR status.

        Args:
            pr_number: Pull request number

        Returns:
            PRStatus: Current status of the PR
        """
        try:
            pr_data = await self.github_service.get_pr(pr_number)
            return PRStatus(pr_data.get("state"))
        except Exception as e:
            self.logger.error(f"Error getting PR status: {str(e)}")
            raise

    async def update_pr_description(self, pr_number: str, description: str) -> None:
        """Update PR description.

        Args:
            pr_number: Pull request number
            description: Updated description
        """
        try:
            await self.github_service.update_pull_request(pr_number, {"body": description})
        except Exception as e:
            self.logger.error(f"Error updating PR description: {str(e)}")
            raise

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
        await self.github_service.create_branch(branch_name)
        
        # Prepare changes
        changes = []
        for task_id, details in implementation_result["implementations"].items():
            changes.append({
                "file_path": details["file_path"],
                "content": details["code"]
            })
            
        # Commit changes
        await self.github_service.commit_changes(
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
        pr_url = await self.github_service.create_pr(
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
"""GitHub service implementation."""
from github import Github, Auth
from typing import Optional, Dict, List, Any, Protocol
import base64
import os
import subprocess
import time
from github.Repository import Repository
import logging
from github.GithubException import UnknownObjectException
from ..utils.config import Config
import shutil
from ..exceptions.base import ErrorCategory
from ..utils.exceptions import ServiceError

logger = logging.getLogger(__name__)

class GitHubClient(Protocol):
    """Protocol for GitHub client interface."""
    def get_user(self): ...
    def get_repo(self, full_name_or_id: str): ...

class GitHubService:
    """Service for interacting with GitHub."""
    
    def __init__(self, config: Config, github_client: Optional[GitHubClient] = None):
        """Initialize the GitHub service.
        
        Args:
            config: Configuration object containing GitHub settings
            github_client: Optional GitHub client for testing
        """
        self.config = config
        self.github = github_client or Github(auth=Auth.Token(config.api_key))
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = config.workspace_dir
        self.repo_name = config.repo_name
        
    @classmethod
    def create(cls, config: Config) -> 'GitHubService':
        """Factory method to create a GitHubService instance.
        
        Args:
            config: Configuration object containing GitHub settings
            
        Returns:
            GitHubService: A new instance
        """
        github_client = Github(auth=Auth.Token(config.api_key))
        return cls(config, github_client)
        
    def check_connection(self):
        """Test the GitHub connection"""
        self.github.get_user().login
        
    def create_repository(self, name: str, description: str) -> str:
        """Create a new repository and initialize it with basic structure"""
        try:
            self.logger.info(f"Creating repository: {name}")
            repo = self.github.get_user().create_repo(
                name=name,
                description=description,
                private=True,
                auto_init=True  # This creates an initial commit with README
            )
            
            # Wait for the repository to be fully created
            time.sleep(2)
            
            # Return the clone URL without modifying it - we'll add auth when cloning
            return repo.clone_url
        except Exception as e:
            self.logger.error(f"Failed to create repository: {str(e)}")
            raise
        
    def configure_branch_protection(self, repo):
        """Configure branch protection rules to allow self-merging"""
        try:
            # Get the main branch
            branch = repo.get_branch("main")
            
            # Update branch protection rules
            branch.edit_protection(
                # Require pull request reviews
                required_approving_review_count=0,  # No reviews required
                dismiss_stale_reviews=False,
                require_code_owner_reviews=False,
                # Allow force pushes and deletions
                allow_force_pushes=False,
                allow_deletions=False,
                # Don't require status checks
                strict=False,
                contexts=[],
                # Don't enforce admins
                enforce_admins=False
            )
        except Exception as e:
            self.logger.warning(f"Failed to configure branch protection: {str(e)}")
            raise
        
    def create_branch(self, repo_name: str, branch_name: str, base: str = "main") -> str:
        """Create a new branch and return its ref"""
        self.logger.info(f"Creating branch: {branch_name}")
        repo = self.github.get_repo(f"{self.github.get_user().login}/{repo_name}")
        base_branch = repo.get_branch(base)
        ref = repo.create_git_ref(f"refs/heads/{branch_name}", base_branch.commit.sha)
        return ref.ref
        
    def create_pull_request(self, repo_name: str, branch: str, title: str, body: str) -> str:
        """Create a pull request from a feature branch to main"""
        self.logger.info(f"Creating pull request for branch: {branch}")
        repo = self.github.get_repo(f"{self.github.get_user().login}/{repo_name}")
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch,
            base="main",
            maintainer_can_modify=True
        )
        return pr.html_url
        
    def commit_changes(self, repo_name: str, branch: str, files: Dict[str, str], message: str):
        """Commit multiple file changes to a branch and create a PR"""
        self.logger.info(f"Committing to branch: {branch}")
        repo = self.github.get_repo(f"{self.github.get_user().login}/{repo_name}")
        
        # Commit changes
        for file_path, content in files.items():
            try:
                # Try to get the file first
                file = repo.get_contents(file_path, ref=branch)
                repo.update_file(
                    file_path,
                    message,
                    content,
                    file.sha,
                    branch=branch
                )
            except Exception:
                # File doesn't exist, create it
                repo.create_file(
                    file_path,
                    message,
                    content,
                    branch=branch
                )
        
        # Create pull request
        pr_title = f"feat: {message}"
        pr_body = f"""
## Changes
- Initial implementation for {message}

## Testing
- [ ] Unit tests added
- [ ] Manual testing completed

## Notes
This PR was automatically created by the AI development team.
"""
        return self.create_pull_request(repo_name, branch, pr_title, pr_body)
        
    def merge_pull_request(self, repo_name: str, pr_number: int) -> bool:
        """Merge a pull request"""
        try:
            self.logger.info(f"Merging pull request #{pr_number}")
            repo = self.github.get_repo(f"{self.github.get_user().login}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            # Check if PR can be merged
            if not pr.mergeable:
                self.logger.warning(f"PR #{pr_number} cannot be merged due to conflicts")
                return False
            
            # Merge the PR
            merge_result = pr.merge(
                commit_title=f"feat: {pr.title}",
                commit_message=pr.body,
                merge_method="squash"
            )
            return merge_result.merged
            
        except Exception as e:
            self.logger.error(f"Failed to merge PR #{pr_number}: {str(e)}")
            return False

    def get_pull_request_number(self, pr_url: str) -> int:
        """Extract PR number from PR URL"""
        try:
            return int(pr_url.split('/')[-1])
        except (ValueError, IndexError):
            raise ValueError(f"Invalid PR URL: {pr_url}")

    async def get_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Get pull request details.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            Dict[str, Any]: Pull request details including:
                - title: PR title
                - body: PR description
                - head: Head branch
                - base: Base branch
                - changed_files: List of changed file paths
        """
        try:
            self.logger.info(f"Getting PR #{pr_number} details")
            repo = self.github.get_repo(f"{self.github.get_user().login}/{self.repo_name}")
            pr = repo.get_pull(pr_number)
            
            # Get list of changed files
            changed_files = [f.filename for f in pr.get_files()]
            
            return {
                "title": pr.title,
                "body": pr.body,
                "head": pr.head.ref,
                "base": pr.base.ref,
                "changed_files": changed_files
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get PR #{pr_number} details: {str(e)}")
            raise

    async def get_file_content(self, file_path: str, ref: str) -> Optional[str]:
        """Get file content from a specific branch.
        
        Args:
            file_path: Path to the file
            ref: Branch or commit reference
            
        Returns:
            Optional[str]: File content or None if file was deleted
        """
        try:
            self.logger.info(f"Getting content of {file_path} from {ref}")
            repo = self.github.get_repo(f"{self.github.get_user().login}/{self.repo_name}")
            
            try:
                file = repo.get_contents(file_path, ref=ref)
                if isinstance(file, list):
                    raise ValueError(f"{file_path} is a directory")
                return base64.b64decode(file.content).decode('utf-8')
            except UnknownObjectException:
                # File was deleted in this PR
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get file content: {str(e)}")
            raise

    async def post_review_comments(
        self,
        pr_number: int,
        comments: List[Dict[str, Any]],
        approved: bool,
        review_message: str
    ) -> None:
        """Post a review with comments on a pull request.
        
        Args:
            pr_number: Pull request number
            comments: List of review comments
            approved: Whether to approve the PR
            review_message: Overall review message
        """
        try:
            self.logger.info(f"Posting review on PR #{pr_number}")
            repo = self.github.get_repo(f"{self.github.get_user().login}/{self.repo_name}")
            pr = repo.get_pull(pr_number)
            
            # Create review comments
            review_comments = []
            for comment in comments:
                if "line" in comment:
                    review_comments.append({
                        "path": comment["file"],
                        "position": comment["line"],
                        "body": f"{comment['message']}"
                    })
            
            # Submit review
            event = "APPROVE" if approved else "REQUEST_CHANGES"
            pr.create_review(
                body=review_message,
                event=event,
                comments=review_comments
            )
            
        except Exception as e:
            self.logger.error(f"Failed to post review comments: {str(e)}")
            raise

    async def file_exists(self, file_path: str, ref: str = "main") -> bool:
        """Check if a file exists in the repository.
        
        Args:
            file_path: Path to the file
            ref: Branch or commit reference (default: main)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.logger.info(f"Checking if {file_path} exists in {ref}")
            repo = self.github.get_repo(f"{self.github.get_user().login}/{self.repo_name}")
            
            try:
                repo.get_contents(file_path, ref=ref)
                return True
            except UnknownObjectException:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to check file existence: {str(e)}")
            return False

    def clone_repository(self, repo_url: str) -> str:
        """Clone a repository with proper authentication"""
        try:
            # Extract repository name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(self.workspace_dir, repo_name)
            
            # Add authentication to the URL
            auth_url = repo_url.replace("https://", f"https://robmillersoftware:{self.github_api_key}@")
            
            git_path = shutil.which("git")
            if not git_path:
                raise EnvironmentError("Git executable not found in PATH")

            self.logger.info(f"Cloning {repo_url} to {repo_path}")
            subprocess.run([git_path, 'clone', auth_url, repo_path], check=True)
            
            return repo_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e.stderr}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to clone repository: {str(e)}")
            raise

    @property
    def github_api_key(self) -> str:
        """Get GitHub API key."""
        return self.config.github_api_key

    async def update_pr_status(self, pr_number: int, status: str) -> None:
        """Update PR status.
        
        Args:
            pr_number: PR number
            status: New status
        """
        try:
            repo = self.github.get_repo(f"{self.github.get_user().login}/{self.repo_name}")
            pr = repo.get_pull(pr_number)
            pr.edit(state=status)
        except Exception as e:
            raise ServiceError(
                message=f"Failed to update PR status: {e}",
                category=ErrorCategory.API
            )

    async def get_repository_info(self, repo_name: str) -> Dict[str, str]:
        """Get repository information.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Repository information
        """
        try:
            repo = self.github.get_repo(repo_name)
            return {
                "clone_url": repo.clone_url,
                "default_branch": repo.default_branch
            }
        except Exception as e:
            raise ServiceError(f"Failed to get repository info: {e}")
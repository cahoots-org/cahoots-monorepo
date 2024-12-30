# src/services/github_service.py
from github import Github
from typing import Optional, Dict, List, Any
import base64
import os
import subprocess
from ..utils.config import Config
from ..utils.logger import Logger
import time
from github.Repository import Repository

class GitHubService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("GitHubService")
        if not self.config.github_api_key:
            raise RuntimeError("GITHUB_API_KEY environment variable is required for GitHub integration")
        self.github = Github(self.config.github_api_key)
        self.workspace_dir = os.getenv("WORKSPACE_DIR", "/workspace")
        
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

    def clone_repository(self, repo_url: str) -> str:
        """Clone a repository with proper authentication"""
        try:
            # Extract repository name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(self.workspace_dir, repo_name)
            
            # Add authentication to the URL
            auth_url = repo_url.replace("https://", f"https://robmillersoftware:{self.config.github_api_key}@")
            
            self.logger.info(f"Cloning {repo_url} to {repo_path}")
            subprocess.run(['git', 'clone', auth_url, repo_path], check=True)
            
            return repo_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e.stderr}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to clone repository: {str(e)}")
            raise
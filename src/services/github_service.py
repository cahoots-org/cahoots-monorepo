# src/services/github_service.py
from github import Github
from typing import Optional, Dict, List
import base64
from ..utils.config import Config
from ..utils.logger import Logger

class GitHubService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("GitHubService")
        if not self.config.github_api_key:
            raise RuntimeError("GITHUB_API_KEY environment variable is required for GitHub integration")
        self.github = Github(self.config.github_api_key)
        
    def check_connection(self):
        """Test the GitHub connection"""
        self.github.get_user().login
        
    def create_repository(self, name: str, description: str = "") -> str:
        """Create a new repository with initial structure and branch protection rules"""
        self.logger.info(f"Creating repository: {name}")
        
        # Create the repository
        repo = self.github.get_user().create_repo(
            name,
            description=description,
            auto_init=True,  # Initialize with README
            private=False
        )
        
        # Initialize with basic project structure
        files = {
            "README.md": self._generate_readme(name, description),
            ".gitignore": self._generate_gitignore(),
            "requirements.txt": self._generate_requirements(),
            "src/__init__.py": "",
            "src/main.py": self._generate_main_py(),
            "tests/__init__.py": "",
            "tests/test_main.py": self._generate_test_main(),
            ".env.example": self._generate_env_example(),
        }
        
        # Create all files in the main branch
        for file_path, content in files.items():
            self.commit_file(repo, file_path, content, "Initial project structure")
        
        # Configure branch protection rules for main branch
        self.configure_branch_protection(repo)
            
        return repo.clone_url
        
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
                
    def commit_file(self, repo, file_path: str, content: str, message: str, branch: str = "main"):
        """Commit a single file to a repository"""
        try:
            repo.create_file(
                file_path,
                message,
                content,
                branch=branch
            )
        except Exception as e:
            self.logger.warning(f"Failed to create file {file_path}: {str(e)}")
            
    def _generate_readme(self, name: str, description: str) -> str:
        return f"""# {name}

{description}

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\\Scripts\\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your environment variables
6. Run the application: `python src/main.py`

## Testing

Run tests with: `python -m pytest tests/`

## License

MIT
"""

    def _generate_gitignore(self) -> str:
        return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# Environment Variables
.env

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/
"""

    def _generate_requirements(self) -> str:
        return """fastapi==0.68.0
uvicorn==0.15.0
python-dotenv==0.19.0
requests==2.26.0
pytest==6.2.5
"""

    def _generate_main_py(self) -> str:
        return """from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

    def _generate_test_main(self) -> str:
        return """from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
"""

    def _generate_env_example(self) -> str:
        return """# API Configuration
PORT=8000
HOST=0.0.0.0

# Add your environment variables here
# API_KEY=your_api_key
"""

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
# src/services/github_service.py
from github import Github
from typing import Optional
from ..utils.config import Config
from ..utils.logger import Logger

class GitHubService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("GitHubService")
        self.github = Github(self.config.github_token)
        
    def create_repository(self, name: str) -> str:
        self.logger.info(f"Creating repository: {name}")
        repo = self.github.get_user().create_repo(name)
        return repo.clone_url
        
    def create_pull_request(self, repo_name: str, title: str, body: str,
                          base: str = "main", head: str = "feature") -> str:
        self.logger.info(f"Creating PR in repository: {repo_name}")
        repo = self.github.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, base=base, head=head)
        return pr.html_url
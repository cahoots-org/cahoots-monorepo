"""GitHub API Client

Wrapper around GitHub REST API for repository analysis.
Handles authentication, rate limiting, and common operations.
"""

import re
import base64
from typing import Optional, Dict, Any, List
import aiohttp
from urllib.parse import urlparse


class GitHubClient:
    """GitHub API client for repository analysis."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token for authenticated requests
        """
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_call_count = 0

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cahoots-TaskManager"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name.

        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        # Handle different URL formats
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # github.com/owner/repo
        # owner/repo

        # Remove .git suffix if present
        repo_url = repo_url.rstrip("/").replace(".git", "")

        # Try to parse as URL
        if "github.com" in repo_url:
            parsed = urlparse(repo_url)
            path = parsed.path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]

        # Try as owner/repo format
        parts = repo_url.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional request parameters

        Returns:
            JSON response from API

        Raises:
            aiohttp.ClientError: On request failure
        """
        if not self.session:
            raise RuntimeError("GitHubClient must be used as async context manager")

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        self.api_call_count += 1

        async with self.session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def get_tree(self, owner: str, repo: str, sha: str = "HEAD", recursive: bool = True) -> Dict[str, Any]:
        """
        Get repository file tree.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Tree SHA or branch name (default: HEAD)
            recursive: Whether to fetch recursively

        Returns:
            Tree object with file listing
        """
        # First get the default branch if sha is HEAD
        if sha == "HEAD":
            repo_info = await self._request("GET", f"/repos/{owner}/{repo}")
            default_branch = repo_info.get("default_branch", "main")
            sha = default_branch

        # Get the tree
        endpoint = f"/repos/{owner}/{repo}/git/trees/{sha}"
        params = {"recursive": "1"} if recursive else {}

        return await self._request("GET", endpoint, params=params)

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> str:
        """
        Get content of a specific file.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in repository
            ref: Branch/tag/commit reference (default: HEAD)

        Returns:
            Decoded file content as string
        """
        # Get default branch if ref is HEAD
        if ref == "HEAD":
            repo_info = await self._request("GET", f"/repos/{owner}/{repo}")
            ref = repo_info.get("default_branch", "main")

        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}

        response = await self._request("GET", endpoint, params=params)

        # Decode base64 content
        if "content" in response and response.get("encoding") == "base64":
            content = base64.b64decode(response["content"]).decode("utf-8")
            return content

        return ""

    async def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository metadata.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository information
        """
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def check_repo_access(self, owner: str, repo: str) -> tuple[bool, bool]:
        """
        Check if repository exists and is accessible.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (exists, is_public)
        """
        try:
            repo_info = await self.get_repo_info(owner, repo)
            return True, not repo_info.get("private", False)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return False, False
            raise

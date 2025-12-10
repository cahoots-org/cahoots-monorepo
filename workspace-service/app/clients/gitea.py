"""
Gitea API client for repository operations.

Uses a hybrid approach:
- giteapy SDK for PR merge operations (handles field name mapping correctly)
- httpx for other operations where giteapy is incomplete

Provides programmatic access to Gitea for:
- Repository creation and deletion
- Branch management
- File operations (via Git API)
- Merge operations
- Webhook configuration
"""

import logging
import httpx
import base64
import asyncio
from functools import partial
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import giteapy
from giteapy.rest import ApiException

logger = logging.getLogger(__name__)

# Thread pool for running sync SDK calls
_executor = ThreadPoolExecutor(max_workers=10)


@dataclass
class GiteaFile:
    """File content from Gitea."""
    path: str
    content: str
    sha: str
    encoding: str = "base64"


class GiteaClient:
    """Client for Gitea API operations using hybrid giteapy SDK + httpx."""

    def __init__(self, base_url: str, api_token: str, bot_username: str = "cahoots-bot"):
        self.base_url = base_url.rstrip("/")
        self.bot_username = bot_username
        self.api_token = api_token

        # HTTP headers for direct API calls
        self.headers = {
            "Authorization": f"token {api_token}",
            "Content-Type": "application/json"
        }

        # Configure giteapy for PR operations
        self.configuration = giteapy.Configuration()
        self.configuration.host = f"{self.base_url}/api/v1"
        self.configuration.api_key['access_token'] = api_token

        # Create API client for PR operations
        self.api_client = giteapy.ApiClient(self.configuration)
        self.repo_api = giteapy.RepositoryApi(self.api_client)

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: float = 60.0
    ) -> httpx.Response:
        """Make an HTTP request to Gitea API."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=30.0)) as client:
            url = f"{self.base_url}/api/v1{path}"
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json,
                params=params
            )
            return response

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in the thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            partial(func, *args, **kwargs)
        )

    # ========================================================================
    # Repository Operations
    # ========================================================================

    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = True,
        default_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a new repository.

        Returns the repo info on success or if it already exists (409).
        """
        response = await self._request(
            "POST",
            "/user/repos",
            json={
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
                "default_branch": default_branch
            }
        )

        # Handle 409 Conflict - repository already exists
        if response.status_code == 409:
            # Return the existing repository info
            return await self.get_repository(self.bot_username, name)

        response.raise_for_status()
        return response.json()

    async def delete_repository(self, owner: str, repo: str) -> None:
        """Delete a repository."""
        response = await self._request(
            "DELETE",
            f"/repos/{owner}/{repo}"
        )
        response.raise_for_status()

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}"
        )
        response.raise_for_status()
        return response.json()

    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List all repositories for the authenticated user."""
        response = await self._request(
            "GET",
            "/user/repos"
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Branch Operations
    # ========================================================================

    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a new branch."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/branches",
            json={
                "new_branch_name": branch_name,
                "old_branch_name": from_branch
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_branch(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """Get branch information."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/branches/{branch}"
        )
        response.raise_for_status()
        return response.json()

    async def list_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List all branches in a repository."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/branches"
        )
        response.raise_for_status()
        return response.json()

    async def delete_branch(self, owner: str, repo: str, branch: str) -> None:
        """Delete a branch."""
        response = await self._request(
            "DELETE",
            f"/repos/{owner}/{repo}/branches/{branch}"
        )
        response.raise_for_status()

    # ========================================================================
    # File Operations
    # ========================================================================

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> Optional[GiteaFile]:
        """Get file content from repository."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

        # Content is base64 encoded
        content = base64.b64decode(data["content"]).decode("utf-8")
        return GiteaFile(
            path=data["path"],
            content=content,
            sha=data["sha"],
            encoding=data.get("encoding", "base64")
        )

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None,
        author_name: str = "Cahoots Bot",
        author_email: str = "bot@cahoots.dev"
    ) -> Dict[str, Any]:
        """Create or update a file in the repository."""
        encoded_content = base64.b64encode(content.encode()).decode()

        payload = {
            "content": encoded_content,
            "message": message,
            "branch": branch,
            "author": {
                "name": author_name,
                "email": author_email
            },
            "committer": {
                "name": author_name,
                "email": author_email
            }
        }

        # Use POST for new files, PUT for updates (PUT requires SHA)
        if sha:
            payload["sha"] = sha
            method = "PUT"
        else:
            method = "POST"

        response = await self._request(
            method,
            f"/repos/{owner}/{repo}/contents/{path}",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def delete_file(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        sha: str,
        branch: str = "main",
        author_name: str = "Cahoots Bot",
        author_email: str = "bot@cahoots.dev"
    ) -> Dict[str, Any]:
        """Delete a file from the repository."""
        response = await self._request(
            "DELETE",
            f"/repos/{owner}/{repo}/contents/{path}",
            json={
                "message": message,
                "sha": sha,
                "branch": branch,
                "author": {
                    "name": author_name,
                    "email": author_email
                },
                "committer": {
                    "name": author_name,
                    "email": author_email
                }
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_directory_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """Get contents of a directory."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref}
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()

        # If it's a file, wrap in list
        if isinstance(data, dict):
            return [data]
        return data

    # ========================================================================
    # Pull Request / Merge Operations (using giteapy SDK)
    # ========================================================================

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = ""
    ) -> Dict[str, Any]:
        """Create a pull request."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific pull request by number."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def _wait_for_mergeable(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        max_wait: int = 30,
        poll_interval: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Wait for PR to become mergeable.

        Gitea runs a background task to compute merge status after PR creation.
        We need to poll until mergeable is computed (not None).

        Returns:
            PR data if mergeable becomes True, None if not mergeable after waiting.
        """
        waited = 0
        while waited < max_wait:
            pr = await self.get_pull_request(owner, repo, pr_number)
            if not pr:
                return None

            # Already merged - return it
            if pr.get("merged"):
                return pr

            # Closed without merge - can't continue
            if pr.get("state") == "closed":
                return pr

            # mergeable can be: True, False, or None (still computing)
            mergeable = pr.get("mergeable")

            if mergeable is True:
                logger.info(f"PR #{pr_number} is mergeable after {waited}s")
                return pr
            elif mergeable is False:
                # Explicitly not mergeable (conflicts)
                logger.warning(f"PR #{pr_number} has conflicts (mergeable=False), not mergeable")
                return pr
            else:
                # None - still computing, keep waiting
                logger.info(f"PR #{pr_number} mergeable={mergeable} (still computing), waiting... ({waited}s)")
                await asyncio.sleep(poll_interval)
                waited += poll_interval

        logger.warning(f"PR #{pr_number} mergeable status not computed after {max_wait}s")
        # Return the last PR state anyway
        return await self.get_pull_request(owner, repo, pr_number)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        message: str = "",
        merge_style: str = "merge",
        max_retries: int = 5
    ) -> Dict[str, Any]:
        """Merge a pull request using giteapy SDK for proper field mapping.

        Returns:
            Dict with merge result. If already merged, returns success with already_merged=True.

        Raises:
            Exception: If merge fails for reasons other than already merged.
        """
        # Wait for PR to be ready for merge (Gitea computes this in background)
        # See: https://github.com/go-gitea/gitea/issues/32111
        pr = await self._wait_for_mergeable(owner, repo, pr_number)

        if pr:
            # Check if already merged
            if pr.get("merged"):
                logger.info(f"PR #{pr_number} already merged, returning success")
                return {"sha": pr.get("merge_commit_sha", ""), "merged": True, "already_merged": True}

            # Check if closed without merge
            if pr.get("state") == "closed" and not pr.get("merged"):
                raise Exception(f"PR #{pr_number} is closed but not merged - cannot merge")

            # Check if mergeable is explicitly False (conflicts)
            if pr.get("mergeable") is False:
                raise Exception(f"PR #{pr_number} has conflicts and cannot be merged")

        # Log pre-merge state for debugging
        logger.info(
            f"PR #{pr_number} pre-merge state: "
            f"state={pr.get('state') if pr else 'N/A'}, "
            f"mergeable={pr.get('mergeable') if pr else 'N/A'}, "
            f"merged={pr.get('merged') if pr else 'N/A'}"
        )

        # Use giteapy SDK for merge - it handles the field name mapping correctly
        merge_body = giteapy.MergePullRequestOption(
            do=merge_style,
            merge_message_field=message
        )

        last_error = None
        for attempt in range(max_retries):
            try:
                # Use giteapy SDK for the merge call
                await self._run_sync(
                    self.repo_api.repo_merge_pull_request,
                    owner=owner,
                    repo=repo,
                    index=pr_number,
                    body=merge_body
                )

                # If we get here, merge was successful
                # Fetch PR again to get the merge commit SHA
                merged_pr = await self.get_pull_request(owner, repo, pr_number)
                return {
                    "sha": merged_pr.get("merge_commit_sha", "") if merged_pr else "",
                    "merged": True
                }

            except ApiException as e:
                # Handle 405 - PR not mergeable
                if e.status == 405:
                    # Double-check if it was already merged
                    pr = await self.get_pull_request(owner, repo, pr_number)
                    if pr and pr.get("merged"):
                        logger.info(f"PR #{pr_number} was merged by another request, returning success")
                        return {"sha": pr.get("merge_commit_sha", ""), "merged": True, "already_merged": True}

                    error_text = str(e.body) if e.body else str(e)
                    # Check for "try again later" which is a transient error
                    if "try again later" in error_text.lower():
                        # Log detailed PR state to help debug
                        if pr:
                            logger.warning(
                                f"PR #{pr_number} 'try again later' debug: "
                                f"state={pr.get('state')}, "
                                f"mergeable={pr.get('mergeable')}, "
                                f"merged={pr.get('merged')}, "
                                f"head={pr.get('head', {}).get('ref')}, "
                                f"base={pr.get('base', {}).get('ref')}, "
                                f"merge_base={pr.get('merge_base')}, "
                                f"diff_url={pr.get('diff_url')}"
                            )
                        last_error = f"PR #{pr_number} not mergeable (405): {error_text}"
                        wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                        logger.warning(f"PR #{pr_number} merge got 'try again later', retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    # Otherwise, raise with helpful message
                    raise Exception(f"PR #{pr_number} not mergeable (405): {error_text}")

                logger.error(f"Merge API error: {e}")
                raise

        # All retries exhausted
        raise Exception(f"PR #{pr_number} merge failed after {max_retries} retries: {last_error}")

    async def get_open_pull_request(
        self,
        owner: str,
        repo: str,
        head: str,
        base: str,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Get an existing open PR for the given head/base branches.

        Note: Gitea's API doesn't reliably filter by head/base params,
        so we do client-side filtering to ensure we get the correct PR.
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                # Fetch all open PRs - Gitea's head/base filters are unreliable
                response = await self._request(
                    "GET",
                    f"/repos/{owner}/{repo}/pulls",
                    params={"state": "open"}
                )
                if response.status_code != 200:
                    return None
                prs = response.json()

                # Client-side filter to find exact match
                for pr in prs:
                    pr_head = pr.get('head', {}).get('ref', '')
                    pr_base = pr.get('base', {}).get('ref', '')
                    if pr_head == head and pr_base == base:
                        logger.info(
                            f"Found existing PR #{pr.get('number')} for {head} -> {base}"
                        )
                        return pr

                logger.debug(f"No open PR found for {head} -> {base}")
                return None
            except httpx.TimeoutException as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(f"Timeout getting open PRs (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

        logger.error(f"Failed to get open PRs after {max_retries} retries: {last_error}")
        # Return None instead of raising - we'll create a new PR if needed
        return None

    async def merge_branches(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
        message: str,
        merge_style: str = "merge"
    ) -> Dict[str, Any]:
        """Merge head branch into base branch via pull request.

        Args:
            merge_style: One of "merge", "rebase", or "squash"

        If a PR already exists for this branch, reuses it instead of creating a new one.
        """
        logger.info(f"merge_branches called: {head} -> {base}")

        # Check for existing PR first
        existing_pr = await self.get_open_pull_request(owner, repo, head, base)

        if existing_pr:
            pr = existing_pr
        else:
            # Create new PR
            pr = await self.create_pull_request(
                owner=owner,
                repo=repo,
                title=message,
                head=head,
                base=base,
                body=f"Auto-merge: {message}"
            )

        # Merge PR with specified style
        merge_result = await self.merge_pull_request(
            owner=owner,
            repo=repo,
            pr_number=pr["number"],
            message=message,
            merge_style=merge_style
        )

        return {
            "ok": True,
            "pr_number": pr["number"],
            "commit": merge_result.get("sha", ""),
            "merged": True
        }

    # ========================================================================
    # Webhook Operations
    # ========================================================================

    async def setup_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        secret: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """Setup webhook for repository events."""
        if events is None:
            events = ["push"]

        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/hooks",
            json={
                "type": "gitea",
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret
                },
                "events": events,
                "active": True
            }
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Commit Operations
    # ========================================================================

    async def get_commit(
        self,
        owner: str,
        repo: str,
        sha: str
    ) -> Dict[str, Any]:
        """Get commit information."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/commits/{sha}"
        )
        response.raise_for_status()
        return response.json()

    async def list_commits(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List recent commits on a branch."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits",
            params={
                "sha": branch,
                "limit": limit
            }
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Search Operations
    # ========================================================================

    async def search_code(
        self,
        owner: str,
        repo: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Search for code in repository."""
        response = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/search",
            params={"q": query}
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json().get("data", [])

    # ========================================================================
    # Mirror Operations (for GitHub import)
    # ========================================================================

    async def create_mirror(
        self,
        name: str,
        clone_url: str,
        description: str = "",
        private: bool = True
    ) -> Dict[str, Any]:
        """Create a mirror of an external repository."""
        response = await self._request(
            "POST",
            "/repos/migrate",
            json={
                "repo_name": name,
                "clone_addr": clone_url,
                "description": description,
                "private": private,
                "mirror": False,  # One-time clone, not continuous mirror
                "service": "git"
            }
        )
        response.raise_for_status()
        return response.json()

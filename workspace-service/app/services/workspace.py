"""
Workspace Service - Orchestrates file operations with Git and Context Engine.

This service:
1. Manages file operations through Gitea
2. Extracts AST metadata for semantic search
3. Updates the Context Engine with file changes
4. Handles local filesystem operations for grep/search
"""

import os
import re
import fnmatch
import asyncio
import logging
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
from datetime import datetime, timezone

from app.clients.gitea import GiteaClient

logger = logging.getLogger(__name__)
from app.clients.context_engine import ContextEngineClient
from app.services.ast_extractor import ASTExtractor, detect_language
from app.config import settings


class WorkspaceService:
    """Orchestrates workspace operations with Git and Context Engine."""

    # Class-level tracking for repo/branch initialization
    _repo_init_locks: Dict[str, asyncio.Lock] = {}
    _initialized_repos: Set[str] = set()
    _initialized_branches: Set[str] = set()  # "project_id:branch" keys
    _lock_manager = asyncio.Lock()

    # Per-branch write locks to serialize file writes (prevents Git race conditions)
    # Key format: "project_id:branch"
    _branch_write_locks: Dict[str, asyncio.Lock] = {}

    # Per-project merge locks to serialize merges to main (prevents conflicts when
    # multiple branches try to merge simultaneously)
    _merge_locks: Dict[str, asyncio.Lock] = {}

    def __init__(
        self,
        gitea_client: GiteaClient,
        context_engine_client: Optional[ContextEngineClient] = None
    ):
        self.gitea = gitea_client
        self.context_engine = context_engine_client
        self.ast_extractor = ASTExtractor()
        self.workspaces_root = settings.workspaces_root

    def _get_workspace_path(self, project_id: str) -> Path:
        """Get the local workspace path for a project."""
        return Path(self.workspaces_root) / project_id

    def _get_repo_owner(self) -> str:
        """Get the repository owner (bot username)."""
        return settings.gitea_bot_username

    async def _get_repo_lock(self, project_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific project."""
        async with self._lock_manager:
            if project_id not in self._repo_init_locks:
                self._repo_init_locks[project_id] = asyncio.Lock()
            return self._repo_init_locks[project_id]

    async def _get_branch_write_lock(self, project_id: str, branch: str) -> asyncio.Lock:
        """
        Get or create a write lock for a specific branch.

        This ensures that file writes to the same branch are serialized,
        preventing Git race conditions where concurrent writes cause
        'non-fast-forward' push errors.
        """
        branch_key = f"{project_id}:{branch}"
        async with self._lock_manager:
            if branch_key not in self._branch_write_locks:
                self._branch_write_locks[branch_key] = asyncio.Lock()
            return self._branch_write_locks[branch_key]

    async def _get_merge_lock(self, project_id: str) -> asyncio.Lock:
        """
        Get or create a merge lock for a specific project.

        This ensures that merges to main are serialized, preventing conflicts
        when multiple branches complete their TDD cycles simultaneously.
        """
        async with self._lock_manager:
            if project_id not in self._merge_locks:
                self._merge_locks[project_id] = asyncio.Lock()
            return self._merge_locks[project_id]

    async def ensure_repository_exists(self, project_id: str) -> bool:
        """
        Ensure a repository exists for the project, creating it if needed.

        Uses per-project locking to prevent race conditions when multiple
        concurrent requests try to create the same repo.

        Returns True if repo exists (or was created), False on error.
        """
        # Fast path: already initialized this session
        if project_id in self._initialized_repos:
            return True

        # Get per-project lock
        lock = await self._get_repo_lock(project_id)

        async with lock:
            # Double-check after acquiring lock
            if project_id in self._initialized_repos:
                return True

            owner = self._get_repo_owner()

            # Check if repo already exists in Gitea
            try:
                repo_info = await self.gitea.get_repository(owner, project_id)
                if repo_info:
                    logger.info(f"Repository {owner}/{project_id} already exists")
                    self._initialized_repos.add(project_id)
                    return True
            except Exception as e:
                # 404 means repo doesn't exist, which is fine
                if "404" not in str(e):
                    logger.warning(f"Error checking repo existence: {e}")

            # Create the repository
            try:
                logger.info(f"Creating repository {owner}/{project_id}")
                await self.gitea.create_repository(
                    name=project_id,
                    description=f"Generated code for project {project_id}",
                    private=True,
                    auto_init=True
                )
                self._initialized_repos.add(project_id)
                logger.info(f"Repository {owner}/{project_id} created successfully")
                return True
            except Exception as e:
                # Check if it's a "repo already exists" error (race condition with another instance)
                if "already exists" in str(e).lower():
                    logger.info(f"Repository {owner}/{project_id} was created by another request")
                    self._initialized_repos.add(project_id)
                    return True
                logger.error(f"Failed to create repository {owner}/{project_id}: {e}")
                return False

    async def ensure_branch_exists(self, project_id: str, branch: str) -> bool:
        """
        Ensure a branch exists, creating it from main if needed.

        Uses per-branch locking to prevent race conditions.
        Returns True if branch exists (or was created), False on error.
        """
        # main branch always exists after repo init
        if branch == "main":
            return True

        branch_key = f"{project_id}:{branch}"

        # Fast path: already initialized this session
        if branch_key in self._initialized_branches:
            return True

        # Get per-branch lock
        lock = await self._get_repo_lock(branch_key)

        async with lock:
            # Double-check after acquiring lock
            if branch_key in self._initialized_branches:
                return True

            owner = self._get_repo_owner()

            # Check if branch already exists
            try:
                branch_info = await self.gitea.get_branch(owner, project_id, branch)
                if branch_info:
                    logger.info(f"Branch {branch} already exists in {owner}/{project_id}")
                    self._initialized_branches.add(branch_key)
                    return True
            except Exception as e:
                # 404 means branch doesn't exist, which is fine
                if "404" not in str(e):
                    logger.warning(f"Error checking branch existence: {e}")

            # Create the branch from main
            try:
                logger.info(f"Creating branch {branch} in {owner}/{project_id}")
                await self.gitea.create_branch(owner, project_id, branch, "main")
                self._initialized_branches.add(branch_key)
                logger.info(f"Branch {branch} created successfully")
                return True
            except Exception as e:
                # Check if it's a "branch already exists" error (race condition)
                if "already exists" in str(e).lower():
                    logger.info(f"Branch {branch} was created by another request")
                    self._initialized_branches.add(branch_key)
                    return True
                logger.error(f"Failed to create branch {branch}: {e}")
                return False

    # ========================================================================
    # Repository Operations
    # ========================================================================

    async def create_repository(
        self,
        project_id: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Create a new repository for a project."""
        repo = await self.gitea.create_repository(
            name=project_id,
            description=description,
            private=True,
            auto_init=True
        )

        return {
            "ok": True,
            "repo_url": repo.get("html_url", ""),
            "clone_url": repo.get("clone_url", ""),
            "name": repo.get("name", project_id)
        }

    async def delete_repository(self, project_id: str) -> bool:
        """Delete a project repository."""
        try:
            await self.gitea.delete_repository(
                owner=self._get_repo_owner(),
                repo=project_id
            )
            return True
        except Exception:
            return False

    # ========================================================================
    # File Read Operations
    # ========================================================================

    async def read_file(
        self,
        project_id: str,
        path: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Read a file from the repository."""
        file = await self.gitea.get_file_content(
            owner=self._get_repo_owner(),
            repo=project_id,
            path=path,
            ref=branch
        )

        if file is None:
            return {
                "content": "",
                "path": path,
                "exists": False
            }

        return {
            "content": file.content,
            "path": file.path,
            "exists": True
        }

    async def list_files(
        self,
        project_id: str,
        path: str = "",
        pattern: str = "*",
        branch: str = "main"
    ) -> List[str]:
        """List files in a directory matching a pattern."""
        contents = await self.gitea.get_directory_contents(
            owner=self._get_repo_owner(),
            repo=project_id,
            path=path,
            ref=branch
        )

        files = []
        for item in contents:
            name = item.get("name", "")
            item_type = item.get("type", "")

            if item_type == "file" and fnmatch.fnmatch(name, pattern):
                files.append(item.get("path", name))
            elif item_type == "dir":
                # Recursively list subdirectories
                subfiles = await self.list_files(
                    project_id=project_id,
                    path=item.get("path", name),
                    pattern=pattern,
                    branch=branch
                )
                files.extend(subfiles)

        return files

    async def grep(
        self,
        project_id: str,
        pattern: str,
        path: str = "",
        branch: str = "main",
        max_matches: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for a pattern in files."""
        matches = []

        try:
            regex = re.compile(pattern)
        except re.error:
            # Invalid regex, try as literal
            regex = re.compile(re.escape(pattern))

        # Get all files
        files = await self.list_files(
            project_id=project_id,
            path=path,
            pattern="*",
            branch=branch
        )

        for file_path in files:
            if len(matches) >= max_matches:
                break

            # Skip binary files and non-code files
            ext = Path(file_path).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz']:
                continue

            try:
                result = await self.read_file(project_id, file_path, branch)
                if not result.get("exists"):
                    continue

                content = result.get("content", "")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    if len(matches) >= max_matches:
                        break
                    if regex.search(line):
                        matches.append({
                            "file": file_path,
                            "line": line_num,
                            "content": line.strip()[:200]  # Truncate long lines
                        })
            except Exception:
                continue

        return matches

    # ========================================================================
    # File Write Operations
    # ========================================================================

    async def write_file(
        self,
        project_id: str,
        path: str,
        content: str,
        message: Optional[str] = None,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Write a file to the repository.

        Uses per-branch locking to serialize writes and prevent Git race conditions.
        Without this, concurrent writes to the same branch cause 'non-fast-forward'
        push errors in Gitea.
        """
        # Ensure repository exists (idempotent, with locking)
        if not await self.ensure_repository_exists(project_id):
            raise Exception(f"Failed to ensure repository exists for {project_id}")

        # Ensure branch exists (creates from main if needed)
        if not await self.ensure_branch_exists(project_id, branch):
            raise Exception(f"Failed to ensure branch {branch} exists for {project_id}")

        if not message:
            message = f"Update {path}"

        # Get branch write lock to serialize writes
        write_lock = await self._get_branch_write_lock(project_id, branch)

        async with write_lock:
            # Check if file exists to get SHA for update (inside lock!)
            existing = await self.gitea.get_file_content(
                owner=self._get_repo_owner(),
                repo=project_id,
                path=path,
                ref=branch
            )

            sha = existing.sha if existing else None

            result = await self.gitea.create_or_update_file(
                owner=self._get_repo_owner(),
                repo=project_id,
                path=path,
                content=content,
                message=message,
                branch=branch,
                sha=sha,
                author_name=settings.commit_author_name,
                author_email=settings.commit_author_email
            )

            commit_sha = result.get("commit", {}).get("sha", "")

        # Update Context Engine (outside lock to avoid blocking)
        await self._update_context_engine(project_id, path, content, commit_sha)

        return {
            "ok": True,
            "path": path,
            "commit": commit_sha
        }

    async def edit_file(
        self,
        project_id: str,
        path: str,
        old_text: str,
        new_text: str,
        message: Optional[str] = None,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Make a surgical edit to an existing file."""
        # Read current content
        result = await self.read_file(project_id, path, branch)
        if not result.get("exists"):
            return {
                "ok": False,
                "error": f"File not found: {path}"
            }

        content = result["content"]

        # Check if old_text exists
        if old_text not in content:
            return {
                "ok": False,
                "error": f"Could not find text to replace in {path}"
            }

        # Replace text
        new_content = content.replace(old_text, new_text, 1)

        if not message:
            message = f"Edit {path}"

        # Write updated content
        return await self.write_file(
            project_id=project_id,
            path=path,
            content=new_content,
            message=message,
            branch=branch
        )

    async def delete_file(
        self,
        project_id: str,
        path: str,
        message: Optional[str] = None,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Delete a file from the repository.

        Uses per-branch locking to prevent Git race conditions.
        """
        if not message:
            message = f"Delete {path}"

        # Get branch write lock to serialize operations
        write_lock = await self._get_branch_write_lock(project_id, branch)

        async with write_lock:
            # Get file SHA (inside lock!)
            existing = await self.gitea.get_file_content(
                owner=self._get_repo_owner(),
                repo=project_id,
                path=path,
                ref=branch
            )

            if not existing:
                return {
                    "ok": False,
                    "error": f"File not found: {path}"
                }

            result = await self.gitea.delete_file(
                owner=self._get_repo_owner(),
                repo=project_id,
                path=path,
                message=message,
                sha=existing.sha,
                branch=branch,
                author_name=settings.commit_author_name,
                author_email=settings.commit_author_email
            )

            commit_sha = result.get("commit", {}).get("sha", "")

        # Remove from Context Engine (outside lock)
        if self.context_engine:
            await self.context_engine.delete_file(project_id, path)

        return {
            "ok": True,
            "path": path,
            "commit": commit_sha
        }

    # ========================================================================
    # Branch Operations
    # ========================================================================

    async def create_branch(
        self,
        project_id: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a new branch."""
        await self.gitea.create_branch(
            owner=self._get_repo_owner(),
            repo=project_id,
            branch_name=branch_name,
            from_branch=from_branch
        )

        return {
            "ok": True,
            "branch": branch_name,
            "from_branch": from_branch
        }

    async def merge_branch(
        self,
        project_id: str,
        source: str,
        target: str = "main",
        message: Optional[str] = None,
        style: str = "merge"
    ) -> Dict[str, Any]:
        """Merge source branch into target branch.

        Uses a per-project lock to serialize merges and prevent conflicts
        when multiple branches complete their TDD cycles simultaneously.

        Args:
            style: One of "merge", "rebase", or "squash"
        """
        if not message:
            message = f"Merge {source} into {target}"

        # Acquire merge lock to serialize merges to main
        merge_lock = await self._get_merge_lock(project_id)

        logger.info(f"Waiting for merge lock: {source} -> {target}")

        async with merge_lock:
            logger.info(f"Acquired merge lock, merging: {source} -> {target}")

            try:
                result = await self.gitea.merge_branches(
                    owner=self._get_repo_owner(),
                    repo=project_id,
                    base=target,
                    head=source,
                    message=message,
                    merge_style=style
                )

                logger.info(f"Merge successful: {source} -> {target}")
                return {
                    "ok": True,
                    "commit": result.get("commit", ""),
                    "conflicts": None
                }
            except Exception as e:
                # Check for merge conflicts
                error_str = str(e).lower()
                if "conflict" in error_str:
                    logger.warning(f"Merge conflict: {source} -> {target}: {e}")
                    return {
                        "ok": False,
                        "commit": None,
                        "conflicts": [str(e)]
                    }
                logger.error(f"Merge failed: {source} -> {target}: {e}")
                raise

    async def get_status(
        self,
        project_id: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Get repository status."""
        try:
            branch_info = await self.gitea.get_branch(
                owner=self._get_repo_owner(),
                repo=project_id,
                branch=branch
            )

            commits = await self.gitea.list_commits(
                owner=self._get_repo_owner(),
                repo=project_id,
                branch=branch,
                limit=1
            )

            last_commit = commits[0] if commits else {}

            return {
                "branch": branch,
                "clean": True,  # Git API doesn't have uncommitted changes concept
                "last_commit": last_commit.get("sha", ""),
                "last_commit_message": last_commit.get("commit", {}).get("message", ""),
                "uncommitted_files": []
            }
        except Exception as e:
            return {
                "branch": branch,
                "clean": True,
                "last_commit": "",
                "last_commit_message": "",
                "uncommitted_files": [],
                "error": str(e)
            }

    async def get_diff(
        self,
        project_id: str,
        base: str = "main",
        head: str = "HEAD"
    ) -> Dict[str, Any]:
        """Get diff between two refs."""
        # Gitea doesn't have a direct diff API, return placeholder
        return {
            "diff": "",
            "files_changed": []
        }

    async def update_branch_from_main(
        self,
        project_id: str,
        branch: str
    ) -> Dict[str, Any]:
        """
        Update a feature branch by merging main into it.

        This is the reverse of merge_branch - we're pulling main INTO the feature branch.
        If there are conflicts, we return them so MergeAgent can resolve them.

        Uses Gitea's merge API to merge main into the feature branch via a temporary PR.
        """
        owner = self._get_repo_owner()

        try:
            # Check if branches have diverged by comparing commits
            main_info = await self.gitea.get_branch(owner, project_id, "main")
            feature_info = await self.gitea.get_branch(owner, project_id, branch)

            main_sha = main_info.get("commit", {}).get("id", "")
            feature_sha = feature_info.get("commit", {}).get("id", "")

            if not main_sha:
                return {
                    "ok": True,
                    "has_conflicts": False,
                    "message": "Main branch has no commits"
                }

            # Create a PR from main to feature branch (reverse direction)
            # This lets us use Gitea's merge machinery to detect conflicts
            pr = await self.gitea.create_pull_request(
                owner=owner,
                repo=project_id,
                title=f"Update {branch} from main",
                head="main",
                base=branch,
                body="Automated update to sync feature branch with main"
            )

            pr_number = pr.get("number")

            # Check if PR is mergeable
            if not pr.get("mergeable", True):
                # Get conflicting files from PR
                conflicts = await self._get_pr_conflicts(owner, project_id, pr_number)
                return {
                    "ok": False,
                    "has_conflicts": True,
                    "conflicts": conflicts,
                    "message": f"Conflicts detected when merging main into {branch}",
                    "pr_number": pr_number
                }

            # Merge the PR (main into feature)
            try:
                result = await self.gitea.merge_pull_request(
                    owner=owner,
                    repo=project_id,
                    pr_number=pr_number,
                    message=f"Update {branch} with latest main",
                    merge_style="merge"
                )

                return {
                    "ok": True,
                    "has_conflicts": False,
                    "commit": result.get("sha", ""),
                    "message": f"Successfully merged main into {branch}"
                }
            except Exception as merge_error:
                error_str = str(merge_error).lower()
                if "conflict" in error_str or "405" in str(merge_error):
                    conflicts = await self._get_pr_conflicts(owner, project_id, pr_number)
                    return {
                        "ok": False,
                        "has_conflicts": True,
                        "conflicts": conflicts,
                        "message": f"Conflicts detected: {merge_error}",
                        "pr_number": pr_number
                    }
                raise

        except Exception as e:
            error_str = str(e).lower()
            # If "no commits between" or similar, the branch is already up to date
            if "no commits" in error_str or "nothing to compare" in error_str:
                return {
                    "ok": True,
                    "has_conflicts": False,
                    "message": f"Branch {branch} is already up to date with main"
                }
            # Handle 409 Conflict - means PR already exists or branches are identical
            if "409" in str(e) or "conflict" in error_str:
                logger.info(f"No PR needed: {branch} may already be up to date with main or PR exists")
                return {
                    "ok": True,
                    "has_conflicts": False,
                    "message": f"Branch {branch} is up to date with main (no merge needed)"
                }
            logger.error(f"Failed to update {branch} from main: {e}")
            raise

    async def _get_pr_conflicts(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[str]:
        """Get list of files with conflicts from a PR."""
        try:
            # Get PR files to identify conflicts
            # Gitea API: GET /repos/{owner}/{repo}/pulls/{index}/files
            response = await self.gitea._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
            )
            if response.status_code != 200:
                return ["Unknown conflicts - could not fetch PR files"]

            files = response.json()
            # Files with conflicts typically have status "conflicted" or similar
            conflicts = []
            for f in files:
                filename = f.get("filename", "")
                status = f.get("status", "")
                # Gitea marks conflicting files differently
                if status in ["conflicted", "conflict"] or f.get("conflicted"):
                    conflicts.append(filename)

            # If we couldn't detect specific conflicts, return all changed files
            if not conflicts:
                conflicts = [f.get("filename", "unknown") for f in files]

            return conflicts
        except Exception as e:
            logger.warning(f"Could not get PR conflicts: {e}")
            return ["Unknown conflicts"]

    async def resolve_conflict(
        self,
        project_id: str,
        branch: str,
        path: str,
        resolved_content: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve a merge conflict by writing the resolved content.

        This is called by MergeAgent after it uses LLM to resolve conflicts.
        Simply writes the resolved content to the branch.
        """
        if not message:
            message = f"Resolve merge conflict in {path}"

        # Write the resolved content
        result = await self.write_file(
            project_id=project_id,
            path=path,
            content=resolved_content,
            message=message,
            branch=branch
        )

        return {
            "ok": result.get("ok", True),
            "commit": result.get("commit"),
            "remaining_conflicts": []  # MergeAgent tracks this
        }

    # ========================================================================
    # Context Engine Integration
    # ========================================================================

    async def _update_context_engine(
        self,
        project_id: str,
        path: str,
        content: str,
        commit_sha: str
    ) -> None:
        """Update Context Engine with file metadata."""
        if not self.context_engine:
            return

        try:
            # Extract AST metadata
            ast_metadata = self.ast_extractor.extract(path, content)

            # Build metadata
            metadata = {
                "language": detect_language(path),
                "ast_metadata": ast_metadata.to_dict() if ast_metadata else {},
                "commit": commit_sha,
                "last_modified": datetime.now(timezone.utc).isoformat()
            }

            # Upsert to Context Engine
            await self.context_engine.upsert_file(
                project_id=project_id,
                path=path,
                content=content,
                metadata=metadata
            )
        except Exception as e:
            # Log but don't fail the operation
            print(f"Context Engine update failed for {path}: {e}")

    async def index_repository(
        self,
        project_id: str,
        branch: str = "main"
    ) -> int:
        """Index all files in a repository for Context Engine."""
        if not self.context_engine:
            return 0

        files = await self.list_files(project_id, "", "*", branch)
        indexed = 0

        batch = []
        for file_path in files:
            # Skip non-code files
            ext = Path(file_path).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz']:
                continue

            try:
                result = await self.read_file(project_id, file_path, branch)
                if not result.get("exists"):
                    continue

                content = result["content"]
                ast_metadata = self.ast_extractor.extract(file_path, content)

                batch.append({
                    "path": file_path,
                    "content": content,
                    "metadata": {
                        "language": detect_language(file_path),
                        "ast_metadata": ast_metadata.to_dict() if ast_metadata else {},
                        "last_modified": datetime.now(timezone.utc).isoformat()
                    }
                })

                indexed += 1

                # Batch publish every 50 files
                if len(batch) >= 50:
                    await self.context_engine.batch_publish(project_id, batch)
                    batch = []

            except Exception as e:
                print(f"Failed to index {file_path}: {e}")
                continue

        # Publish remaining
        if batch:
            await self.context_engine.batch_publish(project_id, batch)

        return indexed

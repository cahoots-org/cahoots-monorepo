"""
Merge Agent

A dedicated agent that orchestrates merging feature branches to main with:
- Serialized merge queue (one at a time, no race conditions)
- Full project context from Contex for intelligent conflict resolution
- LLM-powered conflict resolution
- Post-merge test verification
- Automatic fix attempts if tests fail after merge

This agent is called by TaskAgent after tests pass on a feature branch.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.codegen.agents.base import CodeGenerationAgent, AgentTask
from app.services.context_engine_client import ContextEngineClient
from app.metrics import merge_attempts_total, merge_duration_seconds, merge_conflicts_total

logger = logging.getLogger(__name__)


# System prompt for LLM-based conflict resolution
CONFLICT_RESOLUTION_PROMPT = """You are resolving merge conflicts between parallel feature branches.
Your task is to intelligently merge conflicting changes.

CRITICAL RULES:
- Prefer ADDITIVE merges - keep both changes if possible
- For contradictions, choose the more complete version
- Preserve functionality from both branches
- Make sure the result is valid, working code
- Remove ALL conflict markers (<<<<<<, ======, >>>>>>)

Output ONLY the resolved file content, nothing else.
"""


@dataclass
class MergeRequest:
    """A request to merge a branch to main."""
    project_id: str
    branch: str
    task_id: str
    task_description: str
    tech_stack: str = "nodejs-api"
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # File tracking for fast-path optimization
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of a merge operation."""
    ok: bool
    branch: str
    commit_sha: str = ""
    error: str = ""
    conflicts_resolved: int = 0
    tests_rerun: bool = False


@dataclass
class MergeAgentConfig:
    """Configuration for the merge agent."""
    workspace_url: str
    runner_url: str
    llm_model: str = "llama-3.3-70b"
    max_conflict_resolution_attempts: int = 3
    max_test_fix_attempts: int = 2


class MergeAgent:
    """
    Agent that orchestrates merging feature branches to main.

    Maintains a serialized queue to prevent race conditions and uses
    LLM intelligence to resolve conflicts and fix test failures.

    IMPORTANT: This is designed as a singleton - use get_merge_agent() to get
    the shared instance rather than creating new instances.

    Flow:
    1. TaskAgent calls request_merge() after tests pass
    2. MergeAgent acquires project lock (serializes merges)
    3. Updates branch from main (detects conflicts)
    4. If conflicts: uses LLM + project context to resolve
    5. Runs tests again
    6. If tests fail: attempts fixes
    7. Finally merges to main via PR
    """

    # Class-level locks per project (shared across all instances)
    _locks: Dict[str, asyncio.Lock] = {}

    # Singleton instance
    _instance: Optional["MergeAgent"] = None
    _instance_lock = asyncio.Lock()

    def __init__(
        self,
        config: MergeAgentConfig,
        contex_client: Optional[ContextEngineClient] = None,
        llm_client: Any = None,
    ):
        self.config = config
        self.contex = contex_client
        self._llm_client = llm_client

    @classmethod
    async def get_instance(
        cls,
        config: Optional[MergeAgentConfig] = None,
        contex_client: Optional[ContextEngineClient] = None,
        llm_client: Any = None,
    ) -> "MergeAgent":
        """
        Get the singleton MergeAgent instance.

        Creates the instance on first call with the provided config.
        Subsequent calls return the same instance (config is ignored).
        """
        if cls._instance is None:
            async with cls._instance_lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    if config is None:
                        raise ValueError("config required for first MergeAgent initialization")
                    cls._instance = cls(
                        config=config,
                        contex_client=contex_client,
                        llm_client=llm_client
                    )
                    logger.info("[MergeAgent] Singleton instance created")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    @property
    def llm(self):
        """Get or create the LLM client."""
        if self._llm_client is None:
            import os
            from app.analyzer.llm_client import CerebrasLLMClient

            api_key = os.getenv("CEREBRAS_API_KEY")
            if api_key:
                self._llm_client = CerebrasLLMClient(api_key=api_key)
        return self._llm_client

    @classmethod
    def _get_lock(cls, project_id: str) -> asyncio.Lock:
        """Get or create the merge lock for a project."""
        if project_id not in cls._locks:
            cls._locks[project_id] = asyncio.Lock()
        return cls._locks[project_id]

    async def request_merge(
        self,
        project_id: str,
        branch: str,
        task_id: str,
        task_description: str = "",
        tech_stack: str = "nodejs-api",
        files_created: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None
    ) -> MergeResult:
        """
        Request a merge of a feature branch to main.

        This is the main entry point. Acquires a per-project lock to
        ensure merges are processed serially.

        Args:
            project_id: The project ID
            branch: The feature branch to merge
            task_id: ID of the task being merged
            task_description: Description of what the task implements
            files_created: List of new files created by this task
            files_modified: List of existing files modified by this task

        Returns:
            MergeResult with success/failure info
        """
        request = MergeRequest(
            project_id=project_id,
            branch=branch,
            task_id=task_id,
            task_description=task_description,
            tech_stack=tech_stack,
            files_created=files_created or [],
            files_modified=files_modified or []
        )

        # Use a lock to serialize merges for this project
        lock = self._get_lock(project_id)

        logger.info(f"[MergeAgent] Merge requested for {branch} -> main, waiting for lock...")

        async with lock:
            logger.info(f"[MergeAgent] Acquired merge lock for {branch}, starting merge process")
            merge_start = time.time()
            result = await self._process_merge(request)
            merge_duration = time.time() - merge_start

            # Record metrics
            status = "success" if result.ok else ("conflict" if result.conflicts_resolved > 0 else "failure")
            merge_attempts_total.labels(status=status).inc()
            merge_duration_seconds.observe(merge_duration)
            if result.conflicts_resolved > 0:
                merge_conflicts_total.labels(conflict_type="textual").inc(result.conflicts_resolved)

            return result

    async def _process_merge(self, request: MergeRequest) -> MergeResult:
        """Process a single merge request through the full workflow.

        This method implements a retry loop for conflict resolution:
        1. Check if fast-path eligible (only new files created)
        2. If not fast-path: Update branch from main (detect conflicts)
        3. If conflicts: resolve with LLM, then run tests
        4. If clean merge: skip tests (they already passed on the branch)
        5. Merge to main
        6. If merge fails due to conflicts (main changed while we tested): retry from step 1
        """
        project_id = request.project_id
        branch = request.branch
        conflicts_resolved = 0
        max_retry_attempts = 3  # Max times to retry if conflicts detected at merge time

        # Fast-path: If task only created new files (no modifications), conflicts are impossible
        # We can skip the update-from-main step entirely
        is_new_files_only = (
            len(request.files_created) > 0 and
            len(request.files_modified) == 0
        )

        if is_new_files_only:
            logger.info(
                f"[MergeAgent] Fast-path: {branch} only created new files "
                f"({len(request.files_created)} files), skipping conflict check"
            )

        for attempt in range(max_retry_attempts):
            try:
                had_conflicts = False

                # Step 1: Update branch from main (skip for new-files-only tasks)
                if is_new_files_only and attempt == 0:
                    # First attempt with new files only - skip update from main
                    logger.info(f"[MergeAgent] Step 1: Skipping update from main (new files only)")
                else:
                    # Normal path or retry after merge conflict
                    logger.info(f"[MergeAgent] Step 1: Updating {branch} from main (attempt {attempt + 1})")
                    update_result = await self._update_branch_from_main(project_id, branch)

                    if not update_result.get("ok", False):
                        # Check if there are conflicts to resolve
                        if update_result.get("has_conflicts"):
                            had_conflicts = True
                            logger.info(f"[MergeAgent] Conflicts detected during update, attempting resolution...")
                            conflicted_files = update_result.get("conflicted_files", [])

                            resolved = await self._resolve_conflicts(
                                project_id,
                                branch,
                                conflicted_files,
                                request.task_description
                            )

                            if not resolved:
                                return MergeResult(
                                    ok=False,
                                    branch=branch,
                                    error="Failed to resolve merge conflicts during update from main"
                                )
                            conflicts_resolved += len(conflicted_files)
                        else:
                            return MergeResult(
                                ok=False,
                                branch=branch,
                                error=f"Failed to update from main: {update_result.get('error', 'Unknown error')}"
                            )

                # Step 2: Run tests ONLY if we had conflicts
                # For clean merges, tests already passed on the branch - no need to re-run
                if had_conflicts:
                    logger.info(f"[MergeAgent] Step 2: Running tests on {branch} (conflicts were resolved)")
                    test_result = await self._run_tests(project_id, branch, request.tech_stack)

                    if not test_result.get("passed", False):
                        logger.info(f"[MergeAgent] Tests failed after merge, attempting fixes...")
                        fixed = await self._fix_test_failures(
                            project_id,
                            branch,
                            test_result.get("output", ""),
                            request.task_description,
                            request.tech_stack
                        )
                        if not fixed:
                            return MergeResult(
                                ok=False,
                                branch=branch,
                                error=f"Tests failed after merge: {test_result.get('output', '')[:500]}"
                            )
                else:
                    logger.info(f"[MergeAgent] Step 2: Skipping tests (clean merge, no conflicts)")

                # Step 3: Merge to main via PR
                logger.info(f"[MergeAgent] Step 3: Merging {branch} to main")
                merge_result = await self._merge_to_main(project_id, branch, request.task_description)

                if merge_result.get("ok", False):
                    # Success!
                    logger.info(f"[MergeAgent] Successfully merged {branch} to main")
                    return MergeResult(
                        ok=True,
                        branch=branch,
                        commit_sha=merge_result.get("commit", ""),
                        conflicts_resolved=conflicts_resolved,
                        tests_rerun=had_conflicts  # Only rerun tests if we had conflicts
                    )

                # Merge failed - check if it's a conflict error
                error_msg = merge_result.get("error", "").lower()
                is_conflict_error = any(word in error_msg for word in
                    ["conflict", "not mergeable", "405", "diverged", "out of date"])

                if is_conflict_error and attempt < max_retry_attempts - 1:
                    # Conflicts detected at merge time - retry the full flow
                    logger.warning(
                        f"[MergeAgent] Merge to main failed due to conflicts, retrying... "
                        f"(attempt {attempt + 1}/{max_retry_attempts})"
                    )
                    continue
                else:
                    # Non-conflict error or max retries reached
                    return MergeResult(
                        ok=False,
                        branch=branch,
                        error=f"Failed to merge PR: {merge_result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                logger.error(f"[MergeAgent] Merge failed for {branch}: {e}", exc_info=True)
                return MergeResult(
                    ok=False,
                    branch=branch,
                    error=str(e)
                )

        # Should not reach here, but just in case
        return MergeResult(
            ok=False,
            branch=branch,
            error=f"Failed to merge after {max_retry_attempts} attempts"
        )

    async def _update_branch_from_main(self, project_id: str, branch: str) -> Dict[str, Any]:
        """Update the feature branch with latest changes from main."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Call workspace service to merge main into the feature branch
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{project_id}/branch/update-from-main",
                    json={"branch": branch}
                )

                data = response.json()

                if response.status_code == 200:
                    # Check response content for conflicts
                    if data.get("has_conflicts"):
                        return {
                            "ok": False,
                            "has_conflicts": True,
                            "conflicted_files": data.get("conflicts", []),
                            "error": data.get("message", "Merge conflicts detected")
                        }
                    return {"ok": True, **data}
                elif response.status_code == 409:
                    # Conflict response
                    return {
                        "ok": False,
                        "has_conflicts": True,
                        "conflicted_files": data.get("conflicts", []),
                        "error": data.get("message", "Merge conflicts detected")
                    }
                else:
                    return {
                        "ok": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
            except Exception as e:
                return {"ok": False, "error": str(e)}

    async def _resolve_conflicts(
        self,
        project_id: str,
        branch: str,
        conflicted_files: List[str],
        task_description: str
    ) -> bool:
        """Resolve merge conflicts using LLM."""
        if not self.llm:
            logger.error("[MergeAgent] No LLM client available for conflict resolution")
            return False

        for attempt in range(self.config.max_conflict_resolution_attempts):
            try:
                resolved_count = 0

                for file_path in conflicted_files:
                    # Get the conflicted file content
                    file_content = await self._get_file_content(project_id, branch, file_path)
                    if not file_content:
                        logger.warning(f"[MergeAgent] Could not read conflicted file: {file_path}")
                        continue

                    # Get context from Contex for related files
                    context_files = {}
                    if self.contex:
                        context_files = await self._get_related_context(project_id, file_path)

                    # Build prompt for conflict resolution
                    prompt = self._build_conflict_resolution_prompt(
                        file_path=file_path,
                        conflicted_content=file_content,
                        task_description=task_description,
                        context_files=context_files
                    )

                    # Ask LLM to resolve
                    llm_response = await self.llm.chat_completion(
                        messages=[
                            {"role": "system", "content": CONFLICT_RESOLUTION_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=8000
                    )

                    # Extract content from LLM response (OpenAI format)
                    resolved_content = self._extract_llm_content(llm_response)

                    # Clean up the response (remove any markdown code blocks)
                    resolved_content = self._clean_llm_response(resolved_content)

                    # Write resolved content
                    success = await self._write_file(project_id, branch, file_path, resolved_content)
                    if success:
                        resolved_count += 1
                        logger.info(f"[MergeAgent] Resolved conflict in {file_path}")

                if resolved_count == len(conflicted_files):
                    # Commit the resolution
                    await self._commit_changes(
                        project_id,
                        branch,
                        f"Resolve merge conflicts: {task_description}"
                    )
                    return True

            except Exception as e:
                logger.warning(f"[MergeAgent] Conflict resolution attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_conflict_resolution_attempts - 1:
                    return False

        return False

    def _get_test_command(self, tech_stack: str) -> str:
        """Get test command for tech stack."""
        commands = {
            "nodejs-api": "npm test",
            "python-api": "pytest",
        }
        return commands.get(tech_stack, "npm test")

    async def _run_tests(self, project_id: str, branch: str, tech_stack: str = "nodejs-api") -> Dict[str, Any]:
        """Run tests on the branch via the runner service."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Create test run (matching TaskAgent pattern)
                response = await client.post(
                    f"{self.config.runner_url}/runs",
                    json={
                        "project_id": project_id,
                        "command": self._get_test_command(tech_stack),
                        "branch": branch,
                    }
                )

                if response.status_code != 200:
                    return {"passed": False, "output": f"Failed to create test run: {response.text}"}

                run_id = response.json().get("run_id")

                # Poll for completion
                for _ in range(60):
                    await asyncio.sleep(5)
                    status_resp = await client.get(f"{self.config.runner_url}/runs/{run_id}")
                    if status_resp.status_code == 200:
                        data = status_resp.json()
                        run_status = data.get("status", "").lower()
                        # Handle both "passed"/"failed" and "completed" status values
                        if run_status == "passed":
                            return {"passed": True, "output": data.get("output", "")}
                        elif run_status in ("completed",):
                            return data.get("results", {"passed": True, "output": ""})
                        elif run_status in ("failed", "error", "timeout"):
                            return {"passed": False, "output": data.get("error", data.get("output", f"Test run {run_status}"))}

                return {"passed": False, "output": "Test run timed out"}

            except Exception as e:
                return {"passed": False, "output": str(e)}

    async def _fix_test_failures(
        self,
        project_id: str,
        branch: str,
        errors: str,
        task_description: str,
        tech_stack: str = "nodejs-api"
    ) -> bool:
        """Attempt to fix test failures after merge."""
        if not self.llm:
            return False

        for attempt in range(self.config.max_test_fix_attempts):
            try:
                # Get context about the failing tests
                context = {}
                if self.contex:
                    context = await self._get_related_context(project_id, task_description)

                # Ask LLM for fixes
                fix_prompt = f"""Tests are failing after merging main into the feature branch.

Feature being implemented: {task_description}

Test errors:
```
{errors[:3000]}
```

Relevant files from codebase:
{self._format_context_files(context)}

Analyze the errors and provide fixes. For each file that needs changes, output:
FILE: <path>
```
<complete fixed content>
```

Focus on:
1. Import errors (missing or wrong imports after merge)
2. Type mismatches introduced by merge
3. Missing function arguments
4. Duplicated code that needs cleanup
"""

                llm_response = await self.llm.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are an expert at fixing test failures after merge conflicts. Output complete fixed files."},
                        {"role": "user", "content": fix_prompt}
                    ],
                    max_tokens=8000
                )

                # Extract content from LLM response and parse file fixes
                response_content = self._extract_llm_content(llm_response)
                fixes = self._parse_file_fixes(response_content)
                for file_path, content in fixes.items():
                    await self._write_file(project_id, branch, file_path, content)

                if fixes:
                    await self._commit_changes(project_id, branch, "Fix test failures after merge")

                # Re-run tests
                test_result = await self._run_tests(project_id, branch, tech_stack)
                if test_result.get("passed", False):
                    return True

                errors = test_result.get("output", "")

            except Exception as e:
                logger.warning(f"[MergeAgent] Fix attempt {attempt + 1} failed: {e}")

        return False

    async def _merge_to_main(self, project_id: str, branch: str, message: str) -> Dict[str, Any]:
        """Merge the branch to main via PR."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{project_id}/branch/merge",
                    json={
                        "source": branch,
                        "target": "main",
                        "message": f"Merge: {message}",
                        "style": "merge"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return {"ok": True, **data}
                else:
                    return {"ok": False, "error": response.text}
            except Exception as e:
                return {"ok": False, "error": str(e)}

    async def _get_file_content(self, project_id: str, branch: str, path: str) -> Optional[str]:
        """Get file content from the workspace."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.config.workspace_url}/workspace/{project_id}/file",
                    params={"path": path, "branch": branch}
                )
                if response.status_code == 200:
                    return response.json().get("content", "")
            except Exception:
                pass
            return None

    async def _write_file(self, project_id: str, branch: str, path: str, content: str) -> bool:
        """Write file content to the workspace."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{project_id}/file",
                    json={
                        "path": path,
                        "content": content,
                        "branch": branch
                    }
                )
                return response.status_code == 200
            except Exception:
                return False

    async def _commit_changes(self, project_id: str, branch: str, message: str) -> bool:
        """Commit changes on the branch."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{project_id}/commit",
                    json={
                        "branch": branch,
                        "message": message
                    }
                )
                return response.status_code == 200
            except Exception:
                return False

    async def _get_related_context(self, project_id: str, query: str) -> Dict[str, str]:
        """Get related file context from Contex."""
        if not self.contex:
            return {}

        try:
            results = await self.contex.query(
                project_id=project_id,
                query=query,
                limit=5
            )

            context = {}
            for result in results:
                # ContextEngineClient returns: data_key, data, similarity_score
                path = result.get("data_key", "")
                data = result.get("data", {})
                content = data.get("content", "") if isinstance(data, dict) else str(data)
                if path and content:
                    context[path] = content
            return context
        except Exception as e:
            logger.warning(f"[MergeAgent] Failed to get context from Contex: {e}")
            return {}

    def _build_conflict_resolution_prompt(
        self,
        file_path: str,
        conflicted_content: str,
        task_description: str,
        context_files: Dict[str, str]
    ) -> str:
        """Build prompt for conflict resolution."""
        context_str = ""
        for path, content in list(context_files.items())[:3]:
            context_str += f"\n--- {path} ---\n{content[:2000]}\n"

        return f"""Resolve the merge conflicts in this file:

File: {file_path}

Feature being merged: {task_description}

Conflicted content (contains <<<<<<, ======, >>>>>> markers):
```
{conflicted_content}
```

Related files for context:
{context_str}

Output ONLY the resolved file content with NO conflict markers.
"""

    def _format_context_files(self, context: Dict[str, str]) -> str:
        """Format context files for prompt."""
        result = ""
        for path, content in list(context.items())[:5]:
            result += f"\n--- {path} ---\n{content[:1500]}\n"
        return result if result else "(no context available)"

    def _extract_llm_content(self, response: Dict[str, Any]) -> str:
        """Extract text content from LLM response (OpenAI format)."""
        if isinstance(response, str):
            return response
        # OpenAI/Cerebras format: response['choices'][0]['message']['content']
        try:
            return response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (IndexError, AttributeError):
            # Ollama format: response['message']['content']
            try:
                return response.get("message", {}).get("content", "")
            except AttributeError:
                return str(response)

    def _clean_llm_response(self, response: str) -> str:
        """Clean up LLM response, removing markdown code blocks."""
        lines = response.strip().split("\n")

        # Remove leading/trailing markdown code block markers
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines)

    def _parse_file_fixes(self, response: str) -> Dict[str, str]:
        """Parse file fixes from LLM response."""
        fixes = {}
        current_file = None
        current_content = []
        in_code_block = False

        for line in response.split("\n"):
            if line.startswith("FILE:"):
                if current_file and current_content:
                    fixes[current_file] = "\n".join(current_content)
                current_file = line[5:].strip()
                current_content = []
                in_code_block = False
            elif line.startswith("```") and current_file:
                if in_code_block:
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block and current_file:
                current_content.append(line)

        # Don't forget the last file
        if current_file and current_content:
            fixes[current_file] = "\n".join(current_content)

        return fixes


# Legacy support: keep the old simple conflict resolution agent
class LegacyMergeAgent(CodeGenerationAgent):
    """Legacy agent for simple file-level conflict resolution (deprecated)."""

    LEGACY_SYSTEM_PROMPT = """You are resolving merge conflicts between parallel feature branches.
Your task is to intelligently merge conflicting changes.

CRITICAL RULES:
- Prefer ADDITIVE merges - keep both changes if possible
- For contradictions, choose the more complete version
- Act DECISIVELY - merge and move on
"""

    def _get_system_prompt(self) -> str:
        return self.LEGACY_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        task_context = task.task_context or {}
        conflict_info = task_context.get('conflict', {})
        file_path = conflict_info.get('file_path', 'unknown')
        branch_a_diff = conflict_info.get('branch_a_diff', '')
        branch_b_diff = conflict_info.get('branch_b_diff', '')

        return f"""Resolve the merge conflict in: {file_path}

Branch A changes:
```
{branch_a_diff}
```

Branch B changes:
```
{branch_b_diff}
```

Read the file, resolve the conflict, and call done().
"""

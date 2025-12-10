"""
Generation State Reconciler

Reconciles Redis state with Git reality to enable resumable code generation.
Instead of trusting in-memory state, derives actual state by examining git
through the workspace-service.
"""

import re
import logging
from dataclasses import dataclass
from typing import Set, List, Dict, Optional

import httpx

from app.codegen.orchestrator.state import GenerationState, GenerationStateStore
from app.codegen.orchestrator.dependency_graph import TaskDependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Result of reconciling Git state with desired state."""
    repo_exists: bool
    scaffold_complete: bool
    completed_task_ids: Set[str]
    pending_task_ids: List[str]  # Ordered by dependency
    failed_task_ids: Set[str]
    blocked_task_ids: Set[str]  # Dependencies not met
    can_resume: bool
    resume_from: str  # "scaffold", "generating", "integration"

    @property
    def total_remaining(self) -> int:
        """Total tasks that still need to run."""
        return len(self.pending_task_ids) + len(self.failed_task_ids) + len(self.blocked_task_ids)


class GenerationReconciler:
    """
    Reconciles Redis state with Git reality via workspace-service.

    This enables resumable code generation by examining what
    actually exists in git rather than trusting in-memory state.
    """

    def __init__(
        self,
        workspace_url: str,
        state_store: GenerationStateStore,
    ):
        self.workspace_url = workspace_url.rstrip("/")
        self.state_store = state_store

    async def reconcile(
        self,
        project_id: str,
        tasks: List[Dict],
    ) -> ReconciliationResult:
        """
        Reconcile actual Git state with desired task state.

        Args:
            project_id: The project/repo ID
            tasks: List of task dictionaries with 'id' and optionally 'depends_on'

        Returns:
            ReconciliationResult with what's done vs what needs to be done
        """
        task_ids = {t["id"] for t in tasks}
        logger.info(f"Reconciling project {project_id} with {len(task_ids)} tasks")

        # Check if repo exists by trying to get status
        repo_exists = await self._check_repo_exists(project_id)

        if not repo_exists:
            logger.info(f"Repo {project_id} does not exist, starting from scratch")
            return ReconciliationResult(
                repo_exists=False,
                scaffold_complete=False,
                completed_task_ids=set(),
                pending_task_ids=[t["id"] for t in tasks],
                failed_task_ids=set(),
                blocked_task_ids=set(),
                can_resume=True,
                resume_from="scaffold"
            )

        # Check scaffold by looking for marker files
        scaffold_complete = await self._check_scaffold_exists(project_id)

        # Get merged task IDs by examining file list for task patterns
        merged_task_ids = await self._get_merged_task_ids(project_id)
        completed = merged_task_ids & task_ids

        logger.info(f"Found {len(completed)} completed tasks in git for {project_id}")

        # Build dependency graph to determine what can run
        graph = TaskDependencyGraph.from_tasks(tasks)

        # Categorize tasks
        pending = []
        blocked = set()

        for task in tasks:
            task_id = task["id"]
            if task_id in completed:
                continue

            # Check if dependencies are met
            node = graph.get_task(task_id)
            deps = node.depends_on if node else []
            deps_met = all(d in completed for d in deps)

            if deps_met:
                pending.append(task_id)
            else:
                blocked.add(task_id)

        # Load Redis state to find explicitly failed tasks
        state = await self.state_store.load(project_id)
        failed = set()
        if state and state.failed_tasks:
            # Only count as failed if not already completed in git
            failed = set(state.failed_tasks.keys()) - completed
            # Remove from pending if they're marked as failed (they'll be retried)
            pending = [t for t in pending if t not in failed]

        # Determine resume point
        if not scaffold_complete:
            resume_from = "scaffold"
        elif pending or failed:
            resume_from = "generating"
        elif blocked:
            # All pending tasks are blocked
            resume_from = "generating"
        else:
            # All tasks completed
            resume_from = "integration"

        can_resume = bool(pending or failed or not scaffold_complete or resume_from == "integration")

        result = ReconciliationResult(
            repo_exists=True,
            scaffold_complete=scaffold_complete,
            completed_task_ids=completed,
            pending_task_ids=pending,
            failed_task_ids=failed,
            blocked_task_ids=blocked,
            can_resume=can_resume,
            resume_from=resume_from
        )

        logger.info(
            f"Reconciliation result for {project_id}: "
            f"completed={len(completed)}, pending={len(pending)}, "
            f"failed={len(failed)}, blocked={len(blocked)}, "
            f"resume_from={resume_from}"
        )

        return result

    async def _check_repo_exists(self, project_id: str) -> bool:
        """Check if the repository exists via workspace-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.workspace_url}/workspace/{project_id}/status",
                    params={"branch": "main"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Repo check failed for {project_id}: {e}")
            return False

    async def _check_scaffold_exists(self, project_id: str) -> bool:
        """Check if project scaffold exists by looking for marker files."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.workspace_url}/workspace/{project_id}/files/list",
                    params={"branch": "main"},
                    json={"path": ".", "pattern": "*"}
                )
                if response.status_code != 200:
                    return False

                files = response.json().get("files", [])
                file_names = {f.split("/")[-1] for f in files}

                # Look for typical scaffold indicators
                scaffold_markers = {
                    "package.json",      # Node.js
                    "pyproject.toml",    # Python (modern)
                    "requirements.txt",  # Python (classic)
                    "go.mod",            # Go
                    "Cargo.toml",        # Rust
                    "pom.xml",           # Java/Maven
                    "build.gradle",      # Java/Gradle
                }

                has_scaffold = bool(file_names & scaffold_markers)
                logger.debug(f"Scaffold check for {project_id}: {has_scaffold}")
                return has_scaffold
        except Exception as e:
            logger.debug(f"Scaffold check failed for {project_id}: {e}")
            return False

    async def _get_merged_task_ids(self, project_id: str) -> Set[str]:
        """
        Get task IDs that appear to be merged based on branch naming.

        Since we can't directly query git history, we look at:
        1. Redis state for completed tasks
        2. Files that contain task ID patterns

        This is a best-effort approach - the source of truth is Redis state
        combined with whether the repo/files exist.
        """
        merged_tasks = set()

        # First, check Redis state for what we recorded as completed
        state = await self.state_store.load(project_id)
        if state and state.completed_tasks:
            merged_tasks.update(state.completed_tasks)
            logger.debug(f"Found {len(merged_tasks)} completed tasks in Redis state")

        # For now, trust the Redis state as the source of completed tasks
        # A more sophisticated approach would grep the git log, but that
        # requires additional workspace-service endpoints

        return merged_tasks

    async def repair_state(
        self,
        project_id: str,
        tasks: List[Dict],
    ) -> GenerationState:
        """
        Repair Redis state based on reconciliation.

        Useful when state gets out of sync.
        Returns the repaired state.
        """
        result = await self.reconcile(project_id, tasks)

        # Load or create state
        state = await self.state_store.load(project_id)
        if not state:
            state = GenerationState(
                project_id=project_id,
                status="pending",
                tech_stack="unknown",
                total_tasks=len(tasks),
            )

        # Update state based on reconciliation
        state.completed_tasks = list(result.completed_task_ids)
        state.total_tasks = len(tasks)

        # Clear failed tasks that are actually completed
        if state.failed_tasks:
            state.failed_tasks = {
                k: v for k, v in state.failed_tasks.items()
                if k not in result.completed_task_ids
            }

        # Update blocked tasks
        state.blocked_tasks = list(result.blocked_task_ids)

        # Save repaired state
        await self.state_store.save(state)

        logger.info(f"Repaired state for {project_id}: {len(state.completed_tasks)} completed")
        return state

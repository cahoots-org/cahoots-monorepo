"""
Task-Based Code Generator

Generates code from implementation tasks with clear descriptions
and implementation details from the decomposition phase.

Flow:
1. Initialize repository and project structure
2. Build dependency graph from task depends_on relationships
3. Process tasks in dependency order (with parallelization)
4. Run integration pass
5. Report completion
"""

import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass

import httpx

from app.metrics import (
    MetricsCollector,
    scaffold_duration_seconds,
    scaffold_attempts_total,
    slices_in_progress,
    merge_attempts_total,
    merge_duration_seconds,
)

from app.codegen.orchestrator.state import (
    GenerationState,
    GenerationStatus,
    GenerationStateStore,
)
from app.codegen.orchestrator.dependency_graph import TaskDependencyGraph, TaskNode
from app.codegen.agents.base import AgentTask, AgentResult
from app.codegen.agents.scaffold import ScaffoldAgent
from app.codegen.agents.task_agent import TaskAgent, TaskAgentConfig
from app.codegen.agents.integration_agent import IntegrationAgent
from app.services.context_engine_client import ContextEngineClient

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for code generation."""
    tech_stack: str  # e.g., "nodejs-api", "python-api"
    max_parallel_tasks: int = 3
    max_fix_attempts: int = 3
    workspace_service_url: str = "http://workspace-service:8001"
    runner_service_url: str = "http://runner-service:8002"
    context_engine_url: str = "http://context-engine:8001"
    llm_model: str = "llama-3.3-70b"


class CodeGenerator:
    """
    Task-based orchestrator for code generation.

    Uses implementation tasks (with descriptions and implementation_details)
    for clear user understanding and higher quality output.

    Flow:
    1. ScaffoldAgent creates project structure
    2. For each task (in dependency order):
       - TaskAgent implements the task using TDD
    3. IntegrationAgent wires everything together
    """

    def __init__(
        self,
        config: GenerationConfig,
        state_store: GenerationStateStore,
        event_callback: Optional[Callable[[str, Dict], Any]] = None,
    ):
        self.config = config
        self.state_store = state_store
        self.event_callback = event_callback

        # Metrics collector (initialized per-generation in generate())
        self.metrics: Optional[MetricsCollector] = None

        # Initialize Contex client for semantic file discovery
        self.contex_client = ContextEngineClient(config.context_engine_url)

        # Task agent config (shared by all task agents)
        self.task_agent_config = TaskAgentConfig(
            workspace_url=config.workspace_service_url,
            runner_url=config.runner_service_url,
            llm_model=config.llm_model,
            max_fix_attempts=config.max_fix_attempts,
        )

        # Initialize agents
        self.scaffold_agent = ScaffoldAgent(
            workspace_url=config.workspace_service_url,
            llm_model=config.llm_model,
        )
        self.integration_agent = IntegrationAgent(
            workspace_url=config.workspace_service_url,
            llm_model=config.llm_model,
        )

    async def generate(
        self,
        project_id: str,
        tasks: List[Dict],
        repo_url: str,
        tech_stack_info: Optional[Dict] = None,
        # Resume parameters
        skip_scaffold: bool = False,
        skip_task_ids: Optional[Set[str]] = None,
        start_phase: str = "scaffold",
    ) -> GenerationState:
        """
        Run the full code generation pipeline using tasks.

        Args:
            project_id: Unique identifier for this generation
            tasks: List of implementation tasks with description, implementation_details, depends_on
            repo_url: Git repository URL for the project
            tech_stack_info: Optional tech stack configuration details
            skip_scaffold: If True, skip scaffold phase (repo already set up)
            skip_task_ids: Task IDs to skip (already completed)
            start_phase: Which phase to start from ("scaffold", "generating", "integration")

        Returns:
            Final GenerationState
        """
        skip_task_ids = skip_task_ids or set()
        is_resuming = skip_scaffold or bool(skip_task_ids) or start_phase != "scaffold"

        # Load existing state if resuming, otherwise create new
        state = await self.state_store.load(project_id)
        if not state:
            state = GenerationState(
                project_id=project_id,
                status=GenerationStatus.PENDING,
                tech_stack=self.config.tech_stack,
                repo_url=repo_url,
            )

        # Initialize metrics collector for this generation
        self.metrics = MetricsCollector(project_id, self.config.tech_stack)
        self.metrics.record_project_start(source="api" if not is_resuming else "resume")

        try:
            # Phase 1: Initialize
            state.start()
            await self._save_and_emit(state, "generation_started", {
                "resumed": is_resuming,
                "skipped_tasks": len(skip_task_ids),
                "start_phase": start_phase,
            })

            # Build dependency graph from ALL tasks (need full graph for dependencies)
            graph = TaskDependencyGraph.from_tasks(tasks)
            state.total_tasks = len(graph)
            await self._save_and_emit(state, "graph_built", {
                "total_tasks": len(graph),
                "levels": len(graph.levels),
                "tasks_per_level": [len(level) for level in graph.levels],
            })

            # Phase 1a: Scaffold (skip if resuming past it)
            if start_phase == "scaffold" and not skip_scaffold:
                # Create repository before scaffolding
                await self._create_repository(state, project_id)
                # Scaffold project
                await self._run_scaffold(state, tasks, tech_stack_info)
            elif skip_scaffold:
                logger.info(f"Skipping scaffold for {project_id} (already complete)")
                await self._save_and_emit(state, "scaffold_skipped")

            # Phase 2: Generate from tasks
            if start_phase in ("scaffold", "generating"):
                state.start_generating()

                # Mark skipped tasks as completed in state
                for task_id in skip_task_ids:
                    if task_id not in state.completed_tasks:
                        state.completed_tasks.append(task_id)

                skipping_count = len(skip_task_ids)
                if skipping_count > 0:
                    logger.info(f"Skipping {skipping_count} already-completed tasks for {project_id}")
                    await self._save_and_emit(state, "tasks_skipped", {
                        "count": skipping_count,
                        "progress": state.progress_percent,
                    })

                await self._save_and_emit(state, "generation_phase_started")

                # Process remaining tasks
                await self._process_tasks(state, graph, tasks, skip_task_ids)

            # Check if we can proceed to integration
            if state.status == GenerationStatus.FAILED:
                return state

            # Phase 3: Integration
            if start_phase in ("scaffold", "generating", "integration"):
                state.start_integrating()
                await self._save_and_emit(state, "integration_started")

                await self._run_integration(state, graph)

            # Phase 4: Complete
            if state.status != GenerationStatus.FAILED:
                state.complete()
                await self._save_and_emit(state, "generation_complete", {
                    "completed_tasks": len(state.completed_tasks),
                    "failed_tasks": len(state.failed_tasks),
                    "resumed": is_resuming,
                })
                # Record successful completion
                if self.metrics:
                    self.metrics.record_completion(status="success")

        except Exception as e:
            logger.exception(f"Generation failed for project {project_id}")
            state.fail(str(e))
            await self._save_and_emit(state, "generation_error", {"error": str(e)})
            # Record failed completion
            if self.metrics:
                self.metrics.record_completion(status="failed")

        return state

    async def _create_repository(self, state: GenerationState, project_id: str) -> None:
        """Create the Gitea repository for this project."""
        logger.info(f"Creating repository for project {project_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.config.workspace_service_url}/workspace/{project_id}/repo/create",
                    json={
                        "name": project_id,
                        "description": f"Generated project for {project_id}"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Repository created: {data.get('repo_url', project_id)}")
                    await self._save_and_emit(state, "repo_created", {
                        "repo_url": data.get("repo_url", ""),
                    })
                elif response.status_code == 409:
                    logger.info(f"Repository {project_id} already exists, continuing")
                else:
                    error = response.json().get("detail", f"HTTP {response.status_code}")
                    raise Exception(f"Failed to create repository: {error}")

            except httpx.RequestError as e:
                raise Exception(f"Failed to connect to workspace service: {e}")

    async def _run_scaffold(
        self,
        state: GenerationState,
        tasks: List[Dict],
        tech_stack_info: Optional[Dict],
    ) -> None:
        """Run the scaffold agent to create project structure."""
        logger.info(f"Scaffolding project {state.project_id}")
        scaffold_start = time.time()

        # Build a summary of what will be implemented for scaffolding context
        task_summaries = []
        for task in tasks[:20]:  # First 20 tasks for context
            summary = task.get("description", "")[:100]
            if task.get("implementation_details"):
                summary += f" ({task['implementation_details'][:50]}...)"
            task_summaries.append(summary)

        task = AgentTask(
            task_id=f"{state.project_id}::scaffold",
            task_type="scaffold",
            project_id=state.project_id,
            repo_url=state.repo_url,
            branch="main",
            task_context={
                "tech_stack": self.config.tech_stack,
                "tech_stack_info": tech_stack_info or {},
                "task_summaries": task_summaries,
                "total_tasks": len(tasks),
            },
        )

        result = await self.scaffold_agent.run(task)
        scaffold_duration = time.time() - scaffold_start

        if not result.success:
            scaffold_attempts_total.labels(status="failure", tech_stack=self.config.tech_stack).inc()
            scaffold_duration_seconds.labels(tech_stack=self.config.tech_stack).observe(scaffold_duration)
            state.fail(f"Scaffold failed: {result.error}")
            await self._save_and_emit(state, "scaffold_failed", {"error": result.error})
            raise Exception(f"Scaffold failed: {result.error}")

        # Record scaffold success
        scaffold_attempts_total.labels(status="success", tech_stack=self.config.tech_stack).inc()
        scaffold_duration_seconds.labels(tech_stack=self.config.tech_stack).observe(scaffold_duration)

        await self._save_and_emit(state, "scaffold_complete")

    async def _process_tasks(
        self,
        state: GenerationState,
        graph: TaskDependencyGraph,
        tasks: List[Dict],
        skip_task_ids: Optional[Set[str]] = None,
    ) -> None:
        """
        Process all tasks using event-driven dispatch.

        When a task completes, immediately check for newly unblocked tasks
        and dispatch them.
        """
        # Initialize completed set with pre-completed tasks (from resume)
        completed: Set[str] = set(skip_task_ids or [])
        in_progress: Set[str] = set()
        retry_counts: Dict[str, int] = {}
        completed_results: Dict[str, Dict] = {}  # task_id -> result data for context
        max_consecutive_failures = 5

        # Build lookup from task_id to full task data
        task_lookup = {t.get("id", t.get("task_id", "")): t for t in tasks}

        # Queue for pending asyncio tasks
        pending_tasks: Dict[asyncio.Task, str] = {}

        def get_ready_tasks() -> List[TaskNode]:
            """Get tasks ready to dispatch (deps met, not in progress, not blocked)."""
            ready = graph.get_ready_tasks(completed)
            return [
                node for node in ready
                if node.task_id not in completed
                and node.task_id not in in_progress
                and node.task_id not in state.blocked_tasks
            ]

        def dispatch_ready_tasks():
            """Dispatch all ready tasks up to max parallel limit."""
            available_slots = self.config.max_parallel_tasks - len(pending_tasks)
            if available_slots <= 0:
                return

            ready = get_ready_tasks()[:available_slots]
            for node in ready:
                task_id = node.task_id
                in_progress.add(task_id)
                task_data = task_lookup.get(task_id, {})

                # Get context from completed dependencies
                context = graph.get_context_for_task(task_id, completed_results)

                asyncio_task = asyncio.create_task(
                    self._process_single_task(state, node, task_data, context),
                    name=f"task:{task_id}"
                )
                pending_tasks[asyncio_task] = task_id
                logger.info(f"Dispatched task: {node.description[:50]}... (parallel: {len(pending_tasks)})")

        # Initial dispatch
        dispatch_ready_tasks()

        if not pending_tasks and len(graph) > 0:
            logger.error("No tasks ready to process - check dependency graph")
            state.fail("No tasks could be processed - dependency issue")
            return

        # Event loop: wait for completions, dispatch newly unblocked tasks
        while pending_tasks:
            done, _ = await asyncio.wait(
                pending_tasks.keys(),
                return_when=asyncio.FIRST_COMPLETED
            )

            for asyncio_task in done:
                task_id = pending_tasks.pop(asyncio_task)
                in_progress.discard(task_id)

                try:
                    result = asyncio_task.result()
                    if result:
                        # Success!
                        completed.add(task_id)
                        retry_counts.pop(task_id, None)

                        # Store result for context passing
                        if isinstance(result, dict):
                            completed_results[task_id] = result
                        else:
                            completed_results[task_id] = {"success": True}

                        node = graph.get_task(task_id)
                        task_desc = node.description[:40] if node else task_id

                        state.complete_task(task_id, f"task/{task_id[:8]}")
                        await self._save_and_emit(state, "task_complete", {
                            "task_id": task_id,
                            "task_description": task_desc,
                            "progress": state.progress_percent,
                        })
                        logger.info(f"Task completed: {task_desc}... ({len(completed)}/{len(graph)})")

                        # Record task success metric
                        if self.metrics:
                            files_created = result.get("files", []) if isinstance(result, dict) else []
                            self.metrics.record_slice_complete(
                                slice_type="task",
                                duration=0,  # Duration tracked in _process_single_task
                                fix_iterations=0,
                                tests=0,
                                loc=0,
                                files=len(files_created),
                            )
                    else:
                        # Returned False - schedule retry
                        await self._handle_task_failure(
                            state, graph, task_lookup, task_id,
                            retry_counts, max_consecutive_failures, pending_tasks, in_progress,
                            completed_results,
                        )
                except Exception as e:
                    logger.exception(f"Task {task_id} raised exception: {e}")
                    await self._handle_task_failure(
                        state, graph, task_lookup, task_id,
                        retry_counts, max_consecutive_failures, pending_tasks, in_progress,
                        completed_results,
                        error=str(e)
                    )

            # Dispatch any newly unblocked tasks
            dispatch_ready_tasks()

            # Check if we're done
            total_handled = len(completed) + len(state.blocked_tasks)
            if total_handled >= len(graph) and not pending_tasks:
                break

        # Final status
        blocked_count = len(state.blocked_tasks)
        if blocked_count > 0:
            logger.warning(f"Generation complete with {blocked_count} blocked tasks")
            state.fail(f"{blocked_count} tasks could not be completed")

    async def _handle_task_failure(
        self,
        state: GenerationState,
        graph: TaskDependencyGraph,
        task_lookup: Dict[str, Dict],
        task_id: str,
        retry_counts: Dict[str, int],
        max_failures: int,
        pending_tasks: Dict[asyncio.Task, str],
        in_progress: Set[str],
        completed_results: Dict[str, Dict],
        error: Optional[str] = None,
    ) -> None:
        """Handle a task failure - retry or block."""
        retry_counts[task_id] = retry_counts.get(task_id, 0) + 1
        retry_count = retry_counts[task_id]

        node = graph.get_task(task_id)
        task_desc = node.description[:40] if node else task_id

        if error:
            logger.warning(f"Task '{task_desc}' failed (attempt {retry_count}): {error}")
        else:
            logger.warning(f"Task '{task_desc}' returned failure (attempt {retry_count})")

        await self._save_and_emit(state, "task_retry_scheduled", {
            "task_id": task_id,
            "task_description": task_desc,
            "error": error or "Unknown failure",
            "retry_count": retry_count,
        })

        if retry_count >= max_failures:
            logger.error(f"Task '{task_desc}' failed {max_failures} times - blocking")
            state.block_task(task_id)
            await self._save_and_emit(state, "task_blocked", {
                "task_id": task_id,
                "task_description": task_desc,
                "reason": f"Failed {max_failures} consecutive times",
            })
        else:
            # Schedule retry with backoff
            backoff = min(5 * (2 ** (retry_count - 1)), 30)
            logger.info(f"Retrying task '{task_desc}' in {backoff}s")

            if node:
                async def delayed_retry():
                    await asyncio.sleep(backoff)
                    task_data = task_lookup.get(task_id, {})
                    context = graph.get_context_for_task(task_id, completed_results)
                    return await self._process_single_task(state, node, task_data, context, retry_count)

                in_progress.add(task_id)
                asyncio_task = asyncio.create_task(delayed_retry(), name=f"task:{task_id}:retry")
                pending_tasks[asyncio_task] = task_id

    async def _process_single_task(
        self,
        state: GenerationState,
        node: TaskNode,
        task_data: Dict,
        context: Dict,
        retry_count: int = 0,
    ) -> bool:
        """
        Process a single task through the TaskAgent.

        The TaskAgent handles the full TDD cycle:
        1. Generate tests based on task description
        2. Generate code to pass tests
        3. Run tests and fix failures
        4. Merge to main

        Returns True if successful, False otherwise.
        """
        task_id = node.task_id
        # Use unique branch name for each attempt to avoid git ref conflicts
        if retry_count > 0:
            branch = f"task/{task_id[:8]}-r{retry_count}"
        else:
            branch = f"task/{task_id[:8]}"

        logger.info(f"Processing task: {node.description[:60]}...")
        state.start_task(task_id, branch)
        await self._save_and_emit(state, "task_started", {
            "task_id": task_id,
            "task_description": node.description,
            "story_points": node.story_points,
        })

        try:
            # Create a TaskAgent instance for this task
            task_agent = TaskAgent(
                config=self.task_agent_config,
                contex_client=self.contex_client,
            )

            # Build the agent task with full task context
            agent_task = AgentTask(
                task_id=f"{state.project_id}::{task_id}",
                task_type="task",
                project_id=state.project_id,
                repo_url=state.repo_url,
                branch=branch,
                task_context={
                    "task_id": task_id,
                    "description": node.description,
                    "implementation_details": node.implementation_details,
                    "story_points": node.story_points,
                    "keywords": node.keywords,
                    "tech_stack": self.config.tech_stack,
                    # Context from completed dependencies
                    "related_files": context.get("related_files", []),
                    "related_code": context.get("related_code", []),
                    # Full task data if available
                    "full_task": task_data,
                },
            )

            # Run the task agent
            result = await task_agent.run(agent_task)

            if result.success:
                logger.info(f"Task '{node.description[:40]}' completed successfully")
                await self._save_and_emit(state, "task_merged", {
                    "task_id": task_id,
                    "task_description": node.description,
                    "files_created": result.files_created,
                    "files_modified": result.files_modified,
                    "iterations": result.iterations,
                })
                return {
                    "success": True,
                    "files": result.files_created + result.files_modified,
                }
            else:
                logger.error(f"Task '{node.description[:40]}' failed: {result.error}")
                state.fail_task(task_id, result.error or "Unknown error")
                await self._save_and_emit(state, "task_failed", {
                    "task_id": task_id,
                    "task_description": node.description,
                    "error": result.error,
                    "iterations": result.iterations,
                })
                return False

        except Exception as e:
            logger.exception(f"Error processing task {task_id}")
            state.fail_task(task_id, str(e))
            await self._save_and_emit(state, "task_failed", {
                "task_id": task_id,
                "task_description": node.description,
                "error": str(e),
                "phase": "exception",
            })
            return False

    async def _run_integration(
        self,
        state: GenerationState,
        graph: TaskDependencyGraph,
    ) -> None:
        """Run integration agent to wire everything together."""
        logger.info(f"Running integration for project {state.project_id}")

        # Gather info about completed tasks
        completed_task_info = []
        for task_id in state.completed_tasks:
            node = graph.get_task(task_id)
            if node:
                completed_task_info.append({
                    "task_id": task_id,
                    "description": node.description,
                    "implementation_details": node.implementation_details,
                    "keywords": node.keywords,
                })

        integration_task = AgentTask(
            task_id=f"{state.project_id}::integration",
            task_type="integrate",
            project_id=state.project_id,
            repo_url=state.repo_url,
            branch="main",
            task_context={
                "completed_tasks": completed_task_info,
                "tech_stack": self.config.tech_stack,
                "failed_tasks": list(state.failed_tasks.keys()),
                "blocked_tasks": state.blocked_tasks,
            },
        )

        result = await self.integration_agent.run(integration_task)

        if not result.success:
            logger.error(f"Integration failed: {result.error}")
            await self._save_and_emit(state, "integration_warning", {
                "error": result.error,
            })
        else:
            await self._save_and_emit(state, "integration_complete")

    async def _save_and_emit(
        self,
        state: GenerationState,
        event_type: str,
        data: Optional[Dict] = None,
    ) -> None:
        """Save state and emit event."""
        await self.state_store.save(state)

        if self.event_callback:
            event_data = {
                "type": event_type,
                "project_id": state.project_id,
                "status": state.status.value,
                "progress": state.progress_percent,
                **(data or {}),
            }
            try:
                await self.event_callback(event_type, event_data)
            except Exception as e:
                logger.error(f"Failed to emit event {event_type}: {e}")

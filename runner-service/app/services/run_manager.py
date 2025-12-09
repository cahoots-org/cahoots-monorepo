"""
Run Manager - Orchestrates test run lifecycle.

Manages the full lifecycle of test runs:
- Creating and tracking runs
- Dispatching to Local Docker or Cloud Run
- Polling for completion
- Parsing results
- Cleanup

By default, uses local Docker for development.
Uses Cloud Run Jobs when GCP_PROJECT_ID is configured.
"""

import uuid
import json
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

import redis.asyncio as redis

from app.config import settings
from app.models.schemas import (
    RunStatus, TestResults, CreateRunRequest,
    RunStatusResponse, RunLogsResponse
)
from app.services.cloud_run import CloudRunJobExecutor
from app.services.local_docker import LocalDockerExecutor
from app.services.test_parser import parse_test_results

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """Stored record of a test run."""
    run_id: str
    project_id: str
    status: str
    command: str
    image: str
    sidecars: list
    branch: str
    timeout: int

    # Execution details
    execution_id: Optional[str] = None
    exit_code: Optional[int] = None
    duration: Optional[float] = None

    # Timestamps
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Results
    stdout: str = ""
    stderr: str = ""
    test_results: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        return cls(**data)


class RunManager:
    """Manages test run lifecycle."""

    def __init__(
        self,
        redis_client: redis.Redis,
        executor: Union[CloudRunJobExecutor, LocalDockerExecutor, None] = None
    ):
        self.redis = redis_client
        self.run_ttl = 86400 * 7  # 7 days

        # Choose executor: Cloud Run if configured, otherwise Local Docker
        if executor:
            self.executor = executor
        elif settings.gcp_project_id:
            logger.info(f"Using Cloud Run executor (project: {settings.gcp_project_id})")
            self.executor = CloudRunJobExecutor(
                project_id=settings.gcp_project_id,
                region=settings.gcp_region
            )
        else:
            logger.info("Using Local Docker executor (GCP not configured)")
            self.executor = LocalDockerExecutor()

        self.use_local = isinstance(self.executor, LocalDockerExecutor)

    def _run_key(self, run_id: str) -> str:
        return f"run:{run_id}"

    async def create_run(self, request: CreateRunRequest) -> str:
        """Create a new test run and queue it for execution."""
        run_id = str(uuid.uuid4())

        record = RunRecord(
            run_id=run_id,
            project_id=request.project_id,
            status=RunStatus.PENDING.value,
            command=request.command,
            image=request.image,
            sidecars=request.sidecars,
            branch=request.branch,
            timeout=request.timeout,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        # Store in Redis
        await self.redis.set(
            self._run_key(run_id),
            json.dumps(record.to_dict()),
            ex=self.run_ttl
        )

        return run_id

    async def start_run(self, run_id: str, repo_url: str) -> bool:
        """Start executing a run."""
        record = await self._get_record(run_id)
        if not record:
            return False

        try:
            # Update status to starting
            record.status = RunStatus.STARTING.value
            record.started_at = datetime.now(timezone.utc).isoformat()
            await self._save_record(record)

            # Execute on Cloud Run
            execution_id = await self.executor.execute_test_run(
                project_id=record.project_id,
                repo_url=repo_url,
                branch=record.branch,
                test_command=record.command,
                image=record.image,
                sidecars=record.sidecars,
                timeout=record.timeout
            )

            # Update with execution ID
            record.execution_id = execution_id
            record.status = RunStatus.RUNNING.value
            await self._save_record(record)

            return True

        except Exception as e:
            record.status = RunStatus.ERROR.value
            record.stderr = str(e)
            record.completed_at = datetime.now(timezone.utc).isoformat()
            await self._save_record(record)
            return False

    async def get_status(self, run_id: str) -> Optional[RunStatusResponse]:
        """Get the current status of a run."""
        record = await self._get_record(run_id)
        if not record:
            return None

        # If running, poll Cloud Run for updates
        if record.status == RunStatus.RUNNING.value and record.execution_id:
            await self._update_from_execution(record)

        return RunStatusResponse(
            run_id=record.run_id,
            status=RunStatus(record.status),
            exit_code=record.exit_code,
            duration=record.duration,
            started_at=datetime.fromisoformat(record.started_at) if record.started_at else None,
            completed_at=datetime.fromisoformat(record.completed_at) if record.completed_at else None
        )

    async def get_logs(self, run_id: str) -> Optional[RunLogsResponse]:
        """Get logs and test results for a run."""
        record = await self._get_record(run_id)
        if not record:
            return None

        # If running, try to get latest logs
        if record.status == RunStatus.RUNNING.value and record.execution_id:
            logs = await self.executor.get_execution_logs(record.execution_id)
            record.stdout = logs.get("stdout", record.stdout)
            record.stderr = logs.get("stderr", record.stderr)

        # Parse test results if available
        test_results = None
        if record.test_results:
            test_results = TestResults(**record.test_results)
        elif record.stdout and record.status in [RunStatus.PASSED.value, RunStatus.FAILED.value]:
            # Try to parse from stdout
            framework = self._detect_framework(record.image)
            test_results = parse_test_results(record.stdout, framework)
            record.test_results = test_results.model_dump()
            await self._save_record(record)

        return RunLogsResponse(
            run_id=record.run_id,
            stdout=record.stdout,
            stderr=record.stderr,
            test_results=test_results
        )

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running run."""
        record = await self._get_record(run_id)
        if not record:
            return False

        if record.status not in [RunStatus.PENDING.value, RunStatus.STARTING.value, RunStatus.RUNNING.value]:
            return False  # Can't cancel completed runs

        if record.execution_id:
            await self.executor.cancel_execution(record.execution_id)

        record.status = RunStatus.CANCELLED.value
        record.completed_at = datetime.now(timezone.utc).isoformat()
        await self._save_record(record)

        return True

    async def _get_record(self, run_id: str) -> Optional[RunRecord]:
        """Get a run record from Redis."""
        data = await self.redis.get(self._run_key(run_id))
        if not data:
            return None
        return RunRecord.from_dict(json.loads(data))

    async def _save_record(self, record: RunRecord) -> None:
        """Save a run record to Redis."""
        await self.redis.set(
            self._run_key(record.run_id),
            json.dumps(record.to_dict()),
            ex=self.run_ttl
        )

    async def _update_from_execution(self, record: RunRecord) -> None:
        """Update record from Cloud Run execution status."""
        execution = await self.executor.get_execution_status(record.execution_id)

        if execution.status != RunStatus.RUNNING:
            record.status = execution.status.value
            record.exit_code = execution.exit_code
            record.duration = execution.duration
            record.completed_at = datetime.now(timezone.utc).isoformat()

            # Get final logs
            logs = await self.executor.get_execution_logs(record.execution_id)
            record.stdout = logs.get("stdout", "")
            record.stderr = logs.get("stderr", "")

            # Parse test results
            framework = self._detect_framework(record.image)
            test_results = parse_test_results(record.stdout, framework)
            record.test_results = test_results.model_dump()

            # Update status based on test results
            if test_results.failed > 0:
                record.status = RunStatus.FAILED.value
            elif test_results.passed > 0:
                record.status = RunStatus.PASSED.value

            await self._save_record(record)

    def _detect_framework(self, image: str) -> str:
        """Detect test framework from runner image."""
        if "node" in image or "npm" in image:
            return "jest"
        elif "python" in image or "pytest" in image:
            return "pytest"
        elif "go" in image:
            return "go"
        return "unknown"

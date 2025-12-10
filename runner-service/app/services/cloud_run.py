"""
Google Cloud Run Jobs Executor.

Executes test runs in isolated Cloud Run Jobs with sidecar support.
"""

import json
import time
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import RunStatus, SidecarConfig, DEFAULT_SIDECARS

try:
    from google.cloud import run_v2
    from google.protobuf import duration_pb2
    CLOUD_RUN_AVAILABLE = True
except ImportError:
    CLOUD_RUN_AVAILABLE = False


@dataclass
class JobExecution:
    """Result of a Cloud Run Job execution."""
    execution_id: str
    job_name: str
    status: RunStatus
    exit_code: Optional[int] = None
    duration: Optional[float] = None
    stdout: str = ""
    stderr: str = ""


class CloudRunJobExecutor:
    """Execute test runs as Cloud Run Jobs with sidecars."""

    def __init__(
        self,
        project_id: str,
        region: str = "us-central1"
    ):
        self.project_id = project_id
        self.region = region
        self.parent = f"projects/{project_id}/locations/{region}"

        if CLOUD_RUN_AVAILABLE and project_id:
            self.client = run_v2.JobsClient()
            self.executions_client = run_v2.ExecutionsClient()
        else:
            self.client = None
            self.executions_client = None

    async def execute_test_run(
        self,
        project_id: str,
        repo_url: str,
        branch: str,
        test_command: str,
        image: str,
        sidecars: List[str],
        timeout: int = 300,
        env_vars: Dict[str, str] = None
    ) -> str:
        """
        Execute a test run as a Cloud Run Job.

        Returns the execution ID for tracking.
        """
        if not self.client:
            # Return mock execution ID for local development
            return f"mock-{uuid.uuid4().hex[:8]}"

        # Build container configuration
        containers = []

        # Main test runner container
        main_env = [
            run_v2.EnvVar(name="REPO_URL", value=repo_url),
            run_v2.EnvVar(name="BRANCH", value=branch),
            run_v2.EnvVar(name="DATABASE_URL", value="postgresql://test:test@localhost:5432/testdb"),
            run_v2.EnvVar(name="REDIS_URL", value="redis://localhost:6379"),
        ]

        # Add custom env vars
        if env_vars:
            for key, value in env_vars.items():
                main_env.append(run_v2.EnvVar(name=key, value=value))

        # Build the test script
        test_script = f"""
            set -e
            git clone --depth=1 --branch={branch} $REPO_URL /workspace/repo
            cd /workspace/repo

            # Install dependencies based on project type
            if [ -f "package.json" ]; then
                npm ci || npm install
            elif [ -f "requirements.txt" ]; then
                pip install -r requirements.txt
            elif [ -f "go.mod" ]; then
                go mod download
            fi

            # Wait for sidecars to be ready
            sleep {settings.sidecar_startup_seconds}

            # Run tests
            {test_command} || exit $?
        """

        containers.append(run_v2.Container(
            name="test-runner",
            image=self._get_full_image_name(image),
            command=["/bin/sh", "-c"],
            args=[test_script],
            env=main_env,
            resources=run_v2.ResourceRequirements(
                limits={"memory": "2Gi", "cpu": "2"}
            )
        ))

        # Add sidecar containers
        for sidecar_name in sidecars:
            sidecar_config = DEFAULT_SIDECARS.get(sidecar_name)
            if sidecar_config:
                sidecar_container = self._build_sidecar_container(sidecar_config)
                containers.append(sidecar_container)

        # Create unique job name
        job_name = f"test-{project_id}-{int(time.time())}"

        # Create the job
        job = run_v2.Job(
            template=run_v2.ExecutionTemplate(
                template=run_v2.TaskTemplate(
                    containers=containers,
                    timeout=duration_pb2.Duration(seconds=timeout),
                    service_account=f"cahoots-runner-sa@{self.project_id}.iam.gserviceaccount.com"
                )
            )
        )

        # Create and execute
        try:
            operation = self.client.create_job(
                parent=self.parent,
                job=job,
                job_id=job_name
            )
            created_job = operation.result()

            # Execute the job
            execution = self.client.run_job(name=created_job.name)

            return execution.name.split("/")[-1]  # Return execution ID

        except Exception as e:
            raise RuntimeError(f"Failed to create/execute Cloud Run Job: {e}")

    async def get_execution_status(self, execution_id: str) -> JobExecution:
        """Get the status of a job execution."""
        if not self.executions_client or execution_id.startswith("mock-"):
            # Return mock status for local development
            return JobExecution(
                execution_id=execution_id,
                job_name="mock-job",
                status=RunStatus.PASSED,
                exit_code=0,
                duration=5.0,
                stdout="Tests passed",
                stderr=""
            )

        try:
            execution = self.executions_client.get_execution(
                name=f"{self.parent}/jobs/-/executions/{execution_id}"
            )

            # Map Cloud Run status to our status
            status = self._map_execution_status(execution)

            return JobExecution(
                execution_id=execution_id,
                job_name=execution.job.split("/")[-1],
                status=status,
                exit_code=execution.exit_code if hasattr(execution, 'exit_code') else None,
                duration=self._calculate_duration(execution),
                stdout="",  # Logs fetched separately
                stderr=""
            )

        except Exception as e:
            return JobExecution(
                execution_id=execution_id,
                job_name="unknown",
                status=RunStatus.ERROR,
                exit_code=None,
                duration=None,
                stdout="",
                stderr=str(e)
            )

    async def get_execution_logs(self, execution_id: str) -> Dict[str, str]:
        """Get logs from a job execution."""
        if not self.client or execution_id.startswith("mock-"):
            return {
                "stdout": "Mock test output: All tests passed",
                "stderr": ""
            }

        # In production, use Cloud Logging to fetch logs
        # For now, return placeholder
        return {
            "stdout": "",
            "stderr": ""
        }

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if not self.client or execution_id.startswith("mock-"):
            return True

        try:
            self.executions_client.cancel_execution(
                name=f"{self.parent}/jobs/-/executions/{execution_id}"
            )
            return True
        except Exception:
            return False

    async def cleanup_job(self, job_name: str) -> bool:
        """Delete a job after completion."""
        if not self.client:
            return True

        try:
            self.client.delete_job(
                name=f"{self.parent}/jobs/{job_name}"
            )
            return True
        except Exception:
            return False

    def _get_full_image_name(self, image: str) -> str:
        """Get full GCR image name."""
        if image.startswith("gcr.io/") or image.startswith("us-docker.pkg.dev/"):
            return image
        return f"gcr.io/{self.project_id}/{image}"

    def _build_sidecar_container(self, config: SidecarConfig) -> "run_v2.Container":
        """Build a sidecar container configuration."""
        env = [
            run_v2.EnvVar(name=k, value=v)
            for k, v in config.env.items()
        ]

        return run_v2.Container(
            name=config.name,
            image=config.image,
            env=env,
            resources=run_v2.ResourceRequirements(
                limits={
                    "memory": config.memory_limit,
                    "cpu": config.cpu_limit
                }
            )
        )

    def _map_execution_status(self, execution) -> RunStatus:
        """Map Cloud Run execution status to our status enum."""
        # Cloud Run execution states:
        # - EXECUTION_STATE_UNSPECIFIED
        # - PENDING
        # - RUNNING
        # - SUCCEEDED
        # - FAILED
        # - CANCELLED

        state = str(execution.reconciling) if hasattr(execution, 'reconciling') else ""

        if execution.succeeded_count and execution.succeeded_count > 0:
            return RunStatus.PASSED
        elif execution.failed_count and execution.failed_count > 0:
            return RunStatus.FAILED
        elif execution.cancelled_count and execution.cancelled_count > 0:
            return RunStatus.CANCELLED
        elif execution.running_count and execution.running_count > 0:
            return RunStatus.RUNNING
        else:
            return RunStatus.PENDING

    def _calculate_duration(self, execution) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if hasattr(execution, 'completion_time') and hasattr(execution, 'start_time'):
            if execution.completion_time and execution.start_time:
                delta = execution.completion_time - execution.start_time
                return delta.total_seconds()
        return None

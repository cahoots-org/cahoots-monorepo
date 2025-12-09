"""
Local Docker Executor.

Executes test runs in local Docker containers for development.
This is the default executor when Cloud Run is not configured.
"""

import asyncio
import uuid
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import RunStatus, DEFAULT_SIDECARS

logger = logging.getLogger(__name__)

try:
    import docker
    from docker.errors import DockerException, ContainerError, ImageNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None


@dataclass
class LocalExecution:
    """Result of a local Docker execution."""
    execution_id: str
    container_id: Optional[str]
    status: RunStatus
    exit_code: Optional[int] = None
    duration: Optional[float] = None
    stdout: str = ""
    stderr: str = ""


class LocalDockerExecutor:
    """Execute test runs in local Docker containers."""

    def __init__(self):
        self.executions: Dict[str, LocalExecution] = {}
        self.containers: Dict[str, List[str]] = {}  # execution_id -> container_ids

        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                # Test connection
                self.client.ping()
                logger.info("Local Docker executor initialized")
            except DockerException as e:
                logger.warning(f"Docker not available: {e}")
                self.client = None
        else:
            logger.warning("Docker SDK not installed")
            self.client = None

    @property
    def is_available(self) -> bool:
        """Check if local Docker is available."""
        return self.client is not None

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
        Execute a test run in a local Docker container.

        Returns the execution ID for tracking.
        """
        execution_id = f"local-{uuid.uuid4().hex[:12]}"

        if not self.client:
            # Store mock execution
            self.executions[execution_id] = LocalExecution(
                execution_id=execution_id,
                container_id=None,
                status=RunStatus.PASSED,
                exit_code=0,
                stdout="Mock: Tests passed (Docker not available)",
                stderr=""
            )
            return execution_id

        # Initialize execution tracking
        self.executions[execution_id] = LocalExecution(
            execution_id=execution_id,
            container_id=None,
            status=RunStatus.PENDING
        )
        self.containers[execution_id] = []

        # Run in background
        asyncio.create_task(
            self._run_execution(
                execution_id=execution_id,
                project_id=project_id,
                repo_url=repo_url,
                branch=branch,
                test_command=test_command,
                image=image,
                sidecars=sidecars,
                timeout=timeout,
                env_vars=env_vars or {}
            )
        )

        return execution_id

    async def _run_execution(
        self,
        execution_id: str,
        project_id: str,
        repo_url: str,
        branch: str,
        test_command: str,
        image: str,
        sidecars: List[str],
        timeout: int,
        env_vars: Dict[str, str]
    ):
        """Run the actual Docker execution."""
        start_time = datetime.now(timezone.utc)
        sidecar_containers = []
        network = None

        try:
            # Create a network for sidecars to communicate
            network_name = f"test-network-{execution_id[:8]}"
            network = self.client.networks.create(network_name, driver="bridge")

            # Start sidecars first
            for sidecar_name in sidecars:
                sidecar_config = DEFAULT_SIDECARS.get(sidecar_name)
                if sidecar_config:
                    try:
                        container = self._start_sidecar(
                            sidecar_config,
                            network_name,
                            execution_id
                        )
                        sidecar_containers.append(container)
                        self.containers[execution_id].append(container.id)
                        logger.info(f"Started sidecar {sidecar_name}: {container.id[:12]}")
                    except Exception as e:
                        logger.error(f"Failed to start sidecar {sidecar_name}: {e}")

            # Wait for sidecars to be ready
            await asyncio.sleep(settings.sidecar_startup_seconds)

            # Update status to running
            self.executions[execution_id].status = RunStatus.RUNNING

            # Build the test script
            test_script = f"""
set -e
echo "Cloning repository..."
git clone --depth=1 --branch={branch} {repo_url} /workspace/repo || git clone --depth=1 {repo_url} /workspace/repo
cd /workspace/repo

echo "Installing dependencies..."
if [ -f "package.json" ]; then
    npm ci || npm install
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "go.mod" ]; then
    go mod download
fi

echo "Running tests..."
{test_command}
"""

            # Determine the image to use
            run_image = self._resolve_image(image)

            # Build environment variables
            environment = {
                "REPO_URL": repo_url,
                "BRANCH": branch,
                "DATABASE_URL": "postgresql://test:test@postgres:5432/testdb",
                "REDIS_URL": "redis://redis:6379",
                **env_vars
            }

            # Run the test container
            logger.info(f"Starting test container with image: {run_image}")
            container = self.client.containers.run(
                image=run_image,
                command=["/bin/sh", "-c", test_script],
                environment=environment,
                network=network_name,
                detach=True,
                remove=False,  # Keep for logs
                mem_limit="2g",
                cpu_period=100000,
                cpu_quota=200000,  # 2 CPUs
            )

            self.executions[execution_id].container_id = container.id
            self.containers[execution_id].append(container.id)

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", 1)
            except Exception as e:
                logger.error(f"Container wait failed: {e}")
                exit_code = 1

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Update execution result
            self.executions[execution_id] = LocalExecution(
                execution_id=execution_id,
                container_id=container.id,
                status=RunStatus.PASSED if exit_code == 0 else RunStatus.FAILED,
                exit_code=exit_code,
                duration=duration,
                stdout=stdout,
                stderr=stderr
            )

            logger.info(f"Execution {execution_id} completed with exit code {exit_code}")

        except ImageNotFound as e:
            logger.error(f"Image not found: {e}")
            self.executions[execution_id] = LocalExecution(
                execution_id=execution_id,
                container_id=None,
                status=RunStatus.ERROR,
                exit_code=None,
                stdout="",
                stderr=f"Image not found: {e}"
            )

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            self.executions[execution_id] = LocalExecution(
                execution_id=execution_id,
                container_id=None,
                status=RunStatus.ERROR,
                exit_code=None,
                stdout="",
                stderr=str(e)
            )

        finally:
            # Cleanup containers
            await self._cleanup_containers(execution_id, sidecar_containers)

            # Cleanup network
            if network:
                try:
                    network.remove()
                except Exception as e:
                    logger.warning(f"Failed to remove network: {e}")

    def _start_sidecar(self, sidecar_config, network_name: str, execution_id: str):
        """Start a sidecar container."""
        return self.client.containers.run(
            image=sidecar_config.image,
            name=f"{sidecar_config.name}-{execution_id[:8]}",
            environment=sidecar_config.env,
            network=network_name,
            detach=True,
            remove=False,
            mem_limit=sidecar_config.memory_limit,
        )

    def _resolve_image(self, image: str) -> str:
        """Resolve image name for local use."""
        # Replace GCR references with local equivalents
        if "${PROJECT_ID}" in image:
            # Use standard images locally
            if "node" in image.lower():
                return "node:20-alpine"
            elif "python" in image.lower():
                return "python:3.11-slim"
            elif "golang" in image.lower() or "go" in image.lower():
                return "golang:1.21-alpine"

        # If it's already a standard image, use it
        if not image.startswith("gcr.io/") and not image.startswith("us-docker.pkg.dev/"):
            return image

        # Default fallback
        return "node:20-alpine"

    async def _cleanup_containers(self, execution_id: str, sidecar_containers: List):
        """Clean up all containers for an execution."""
        container_ids = self.containers.get(execution_id, [])

        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=5)
                container.remove()
                logger.debug(f"Removed container {container_id[:12]}")
            except Exception as e:
                logger.warning(f"Failed to cleanup container {container_id[:12]}: {e}")

        # Also clean up any sidecar containers passed directly
        for container in sidecar_containers:
            try:
                container.stop(timeout=5)
                container.remove()
            except Exception:
                pass

        # Clear tracking
        if execution_id in self.containers:
            del self.containers[execution_id]

    async def get_execution_status(self, execution_id: str) -> LocalExecution:
        """Get the status of an execution."""
        if execution_id in self.executions:
            return self.executions[execution_id]

        return LocalExecution(
            execution_id=execution_id,
            container_id=None,
            status=RunStatus.ERROR,
            stderr="Execution not found"
        )

    async def get_execution_logs(self, execution_id: str) -> Dict[str, str]:
        """Get logs from an execution."""
        execution = self.executions.get(execution_id)
        if execution:
            return {
                "stdout": execution.stdout,
                "stderr": execution.stderr
            }
        return {"stdout": "", "stderr": "Execution not found"}

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        container_ids = self.containers.get(execution_id, [])

        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=5)
            except Exception as e:
                logger.warning(f"Failed to stop container: {e}")

        if execution_id in self.executions:
            self.executions[execution_id].status = RunStatus.CANCELLED

        return True

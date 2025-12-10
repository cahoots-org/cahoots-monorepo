"""Pydantic schemas for Runner Service API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RunStatus(str, Enum):
    """Status of a test run."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"


class SidecarType(str, Enum):
    """Available sidecar types."""
    POSTGRES = "postgres"
    REDIS = "redis"
    MONGODB = "mongodb"
    KAFKA = "kafka"
    LOCALSTACK = "localstack"
    ELASTICSEARCH = "elasticsearch"


# ============================================================================
# Test Runs
# ============================================================================

class CreateRunRequest(BaseModel):
    """Request to create a new test run."""
    project_id: str = Field(..., description="Project ID")
    command: str = Field(..., description="Test command to run (e.g., 'npm test')")
    image: str = Field("cahoots-runner-node:20", description="Runner image to use")
    sidecars: List[str] = Field(default_factory=list, description="Sidecar services (postgres, redis, etc.)")
    timeout: int = Field(300, description="Timeout in seconds")
    branch: str = Field("main", description="Git branch to test")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Additional environment variables")


class CreateRunResponse(BaseModel):
    """Response after creating a test run."""
    run_id: str
    status: RunStatus = RunStatus.PENDING


class RunStatusResponse(BaseModel):
    """Response for run status query."""
    run_id: str
    status: RunStatus
    exit_code: Optional[int] = None
    duration: Optional[float] = None  # Seconds
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TestFailure(BaseModel):
    """Details of a single test failure."""
    test: str = Field(..., description="Full test name")
    file: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    error: str = Field(..., description="Error message")


class TestResults(BaseModel):
    """Parsed test results."""
    passed: int = Field(0, description="Number of passed tests")
    failed: int = Field(0, description="Number of failed tests")
    skipped: int = Field(0, description="Number of skipped tests")
    duration: float = Field(0.0, description="Total duration in seconds")
    failures: List[TestFailure] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class RunLogsResponse(BaseModel):
    """Response containing run logs and test results."""
    run_id: str
    stdout: str = ""
    stderr: str = ""
    test_results: Optional[TestResults] = None


class CancelRunResponse(BaseModel):
    """Response after cancelling a run."""
    run_id: str
    cancelled: bool


# ============================================================================
# Sidecar Configuration
# ============================================================================

class SidecarConfig(BaseModel):
    """Configuration for a sidecar container."""
    name: str
    image: str
    env: Dict[str, str] = Field(default_factory=dict)
    ports: Dict[int, int] = Field(default_factory=dict)  # container_port -> host_port
    memory_limit: str = "512Mi"
    cpu_limit: str = "0.5"


# Default sidecar configurations
DEFAULT_SIDECARS: Dict[str, SidecarConfig] = {
    "postgres": SidecarConfig(
        name="postgres",
        image="postgres:15-alpine",
        env={
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB": "testdb"
        },
        ports={5432: 5432},
        memory_limit="512Mi",
        cpu_limit="0.5"
    ),
    "redis": SidecarConfig(
        name="redis",
        image="redis:7-alpine",
        env={},
        ports={6379: 6379},
        memory_limit="256Mi",
        cpu_limit="0.25"
    ),
    "mongodb": SidecarConfig(
        name="mongodb",
        image="mongo:7",
        env={},
        ports={27017: 27017},
        memory_limit="512Mi",
        cpu_limit="0.5"
    ),
    "kafka": SidecarConfig(
        name="kafka",
        image="confluentinc/cp-kafka:7.5.0",
        env={
            "KAFKA_ZOOKEEPER_CONNECT": "localhost:2181",
            "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://localhost:9092"
        },
        ports={9092: 9092},
        memory_limit="1Gi",
        cpu_limit="1.0"
    ),
    "localstack": SidecarConfig(
        name="localstack",
        image="localstack/localstack:latest",
        env={
            "SERVICES": "s3,sqs,dynamodb"
        },
        ports={4566: 4566},
        memory_limit="1Gi",
        cpu_limit="1.0"
    ),
    "elasticsearch": SidecarConfig(
        name="elasticsearch",
        image="elasticsearch:8.11.0",
        env={
            "discovery.type": "single-node",
            "xpack.security.enabled": "false"
        },
        ports={9200: 9200},
        memory_limit="1Gi",
        cpu_limit="1.0"
    )
}

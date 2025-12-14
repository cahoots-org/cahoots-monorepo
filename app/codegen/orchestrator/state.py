"""
Generation State Management

Manages the state machine for code generation:
PENDING → INITIALIZING → GENERATING → INTEGRATING → COMPLETE
                                    ↘ FAILED
"""

import json
import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from datetime import datetime, timezone


class GenerationStatus(str, Enum):
    """Status of a code generation run."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    GENERATING = "generating"
    INTEGRATING = "integrating"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _generate_short_id() -> str:
    """Generate a short unique ID for generation versioning."""
    return uuid.uuid4().hex[:8]


@dataclass
class GenerationState:
    """
    Persisted state for a code generation run.

    Stored in Redis with a 7-day TTL.
    """
    project_id: str
    status: GenerationStatus
    tech_stack: str
    generation_id: str = field(default_factory=_generate_short_id)  # Unique ID per generation
    repo_url: str = ""

    @property
    def repo_name(self) -> str:
        """Get the versioned repository name for this generation."""
        return f"{self.project_id}-{self.generation_id}"

    # Progress tracking (task-based generation)
    total_tasks: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)  # Multiple if parallel
    failed_tasks: Dict[str, str] = field(default_factory=dict)  # task_id -> error
    blocked_tasks: List[str] = field(default_factory=list)

    # Timing
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Git state
    main_branch: str = "main"
    active_branches: List[str] = field(default_factory=list)

    # Error tracking
    last_error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    additional_retries: int = 0  # From "Keep Trying" button

    def to_json(self) -> str:
        """Serialize to JSON for Redis storage."""
        data = asdict(self)
        data['status'] = self.status.value
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "GenerationState":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        data['status'] = GenerationStatus(data['status'])
        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict) -> "GenerationState":
        """Deserialize from dictionary (when Redis client auto-parses JSON)."""
        data = data.copy()  # Don't modify original
        data['status'] = GenerationStatus(data['status'])
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_tasks == 0:
            return 0.0
        completed = len(self.completed_tasks)
        return (completed / self.total_tasks) * 100

    @property
    def can_retry(self) -> bool:
        """Check if retries are available."""
        return self.retry_count < (self.max_retries + self.additional_retries)

    def start(self) -> None:
        """Mark generation as started."""
        self.status = GenerationStatus.INITIALIZING
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.started_at

    def start_generating(self) -> None:
        """Move to generating phase."""
        self.status = GenerationStatus.GENERATING
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def start_integrating(self) -> None:
        """Move to integration phase."""
        self.status = GenerationStatus.INTEGRATING
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def complete(self) -> None:
        """Mark generation as complete."""
        self.status = GenerationStatus.COMPLETE
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.completed_at

    def fail(self, error: str) -> None:
        """Mark generation as failed."""
        self.status = GenerationStatus.FAILED
        self.last_error = error
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def cancel(self) -> None:
        """Mark generation as cancelled."""
        self.status = GenerationStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def start_task(self, task_id: str, branch: str) -> None:
        """Mark a task as started."""
        if task_id not in self.current_tasks:
            self.current_tasks.append(task_id)
        if branch not in self.active_branches:
            self.active_branches.append(branch)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def complete_task(self, task_id: str, branch: str) -> None:
        """Mark a task as completed."""
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)
        if branch in self.active_branches:
            self.active_branches.remove(branch)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed."""
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
        self.failed_tasks[task_id] = error
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def block_task(self, task_id: str) -> None:
        """Mark a task as blocked (dependent on failed task)."""
        if task_id not in self.blocked_tasks:
            self.blocked_tasks.append(task_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_retries(self, count: int = 3) -> None:
        """Add additional retries (from 'Keep Trying' button)."""
        self.additional_retries += count
        self.updated_at = datetime.now(timezone.utc).isoformat()


class GenerationStateStore:
    """Redis-based storage for generation state."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400 * 7  # 7 days

    def _key(self, project_id: str) -> str:
        return f"generation:{project_id}"

    async def save(self, state: GenerationState) -> None:
        """Save state to Redis."""
        await self.redis.set(
            self._key(state.project_id),
            state.to_json(),
            expire=self.ttl
        )

    async def load(self, project_id: str) -> Optional[GenerationState]:
        """Load state from Redis."""
        data = await self.redis.get(self._key(project_id))
        if not data:
            return None
        # Handle both dict (RedisClient auto-parses) and string (raw redis)
        if isinstance(data, dict):
            return GenerationState.from_dict(data)
        return GenerationState.from_json(data)

    async def delete(self, project_id: str) -> None:
        """Delete state from Redis."""
        await self.redis.delete(self._key(project_id))

    async def exists(self, project_id: str) -> bool:
        """Check if state exists."""
        return await self.redis.exists(self._key(project_id))

"""Unit tests for FastAPI application."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.api import create_app
from app.api.dependencies import get_task_storage, get_analyzer
from app.models import Task, TaskStatus, TaskAnalysis, ApproachType
from app.storage import TaskStorage
from app.analyzer import UnifiedAnalyzer


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock task storage."""
        storage = MagicMock(spec=TaskStorage)
        storage.save_task = AsyncMock(return_value=True)
        storage.get_task = AsyncMock()
        storage.get_task_tree = AsyncMock()
        storage.get_children = AsyncMock(return_value=[])
        storage.count_tasks_by_status = AsyncMock(return_value={
            TaskStatus.SUBMITTED: 5,
            TaskStatus.PROCESSING: 3,
            TaskStatus.COMPLETED: 10,
            TaskStatus.ERROR: 1,
            TaskStatus.IN_PROGRESS: 2,
            TaskStatus.AWAITING_APPROVAL: 0,
            TaskStatus.REJECTED: 0
        })
        storage.search_tasks = AsyncMock(return_value=[])
        storage.get_tasks_by_status = AsyncMock(return_value=[])
        storage.get_user_tasks = AsyncMock(return_value=[])
        storage.update_task = AsyncMock(return_value=True)
        storage.delete_task = AsyncMock(return_value=True)
        storage.redis = MagicMock()
        storage.redis.keys = AsyncMock(return_value=[])
        storage.redis.redis = MagicMock()
        storage.redis.redis.ping = AsyncMock(return_value=True)
        storage.task_prefix = "task:"
        return storage

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock analyzer."""
        analyzer = MagicMock(spec=UnifiedAnalyzer)
        analyzer.analyze_task = AsyncMock(
            return_value=TaskAnalysis(
                complexity_score=0.5,
                is_atomic=False,
                is_specific=True,
                confidence=0.85,
                reasoning="Test analysis",
                suggested_approach=ApproachType.DECOMPOSE,
                estimated_story_points=5
            )
        )
        return analyzer

    @pytest.fixture
    def client(self, mock_storage, mock_analyzer):
        """Create a test client with mocked dependencies."""
        app = create_app()

        # Override dependencies
        app.dependency_overrides[get_task_storage] = lambda: mock_storage
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Cahoots Task Manager"
        assert "endpoints" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_readiness_check(self, client):
        """Test readiness check."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "checks" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert data["tasks"]["total"] == 21  # Sum of all statuses

    def test_create_task(self, client, mock_storage):
        """Test task creation."""
        # Configure mock
        created_task = Task(
            id="test-123",
            description="Test task",
            status=TaskStatus.PROCESSING,
            complexity_score=0.5,
            story_points=5
        )
        mock_storage.get_task.return_value = created_task

        # Create task
        response = client.post(
            "/api/tasks",
            json={
                "description": "Test task",
                "max_depth": 3,
                "max_subtasks": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Test task"
        assert data["status"] == "processing"
        assert data["story_points"] == 5

        # Verify storage was called
        assert mock_storage.save_task.called

    def test_get_task(self, client, mock_storage):
        """Test getting a task by ID."""
        # Configure mock
        task = Task(
            id="test-123",
            description="Test task",
            status=TaskStatus.COMPLETED
        )
        mock_storage.get_task.return_value = task

        # Get task
        response = client.get("/api/tasks/test-123")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-123"
        assert data["status"] == "completed"

    def test_get_task_not_found(self, client, mock_storage):
        """Test getting non-existent task."""
        mock_storage.get_task.return_value = None

        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_list_tasks(self, client, mock_storage):
        """Test listing tasks."""
        # Configure mock
        tasks = [
            Task(id="t1", description="Task 1"),
            Task(id="t2", description="Task 2")
        ]
        mock_storage.get_tasks.return_value = tasks
        mock_storage.redis.keys.return_value = ["task:t1", "task:t2"]

        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "stats" in data
        assert data["total"] == 21

    def test_update_task_status(self, client, mock_storage):
        """Test updating task status."""
        # Configure mock
        task = Task(id="test-123", description="Test task")
        mock_storage.get_task.side_effect = [
            task,  # First call - check existence
            Task(id="test-123", description="Test task", status=TaskStatus.COMPLETED)  # After update
        ]

        response = client.put(
            "/api/tasks/test-123/status",
            params={"status": "completed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

        # Verify update was called
        mock_storage.update_task.assert_called_once_with(
            "test-123",
            {"status": TaskStatus.COMPLETED}
        )

    def test_delete_task(self, client, mock_storage):
        """Test deleting a task."""
        # Configure mock
        task = Task(id="test-123", description="Test task")
        tree = MagicMock()
        tree.tasks = {"test-123": task}

        mock_storage.get_task.return_value = task
        mock_storage.get_task_tree.return_value = tree

        response = client.delete("/api/tasks/test-123")
        assert response.status_code == 200
        data = response.json()
        assert "Deleted task test-123" in data["message"]

        # Verify delete was called
        assert mock_storage.delete_task.called

    def test_search_tasks(self, client, mock_storage):
        """Test searching tasks."""
        # Configure mock
        tasks = [
            Task(id="t1", description="Build authentication"),
            Task(id="t2", description="Build database")
        ]
        mock_storage.search_tasks.return_value = tasks

        response = client.post(
            "/api/tasks/search",
            params={"query": "Build"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_children(self, client, mock_storage):
        """Test getting task children."""
        # Configure mock
        children = [
            Task(id="child1", description="Child 1", parent_id="parent"),
            Task(id="child2", description="Child 2", parent_id="parent")
        ]
        mock_storage.get_children.return_value = children

        response = client.get("/api/tasks/parent/children")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(task["parent_id"] == "parent" for task in data)
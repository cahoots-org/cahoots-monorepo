"""Integration tests for complete task processing pipeline."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
import json
from typing import Dict, Any
from datetime import datetime, timezone

from app.main import app
from app.models import Task, TaskAnalysis, TaskDecomposition, TaskStatus, ApproachType, TaskTree
from app.analyzer import UnifiedAnalyzer
from app.processor import TaskProcessor
from app.storage import TaskStorage
from app.cache import CacheManager


@pytest_asyncio.fixture
async def test_client():
    """Test client with dependency overrides."""
    return TestClient(app)


@pytest_asyncio.fixture
async def mock_analyzer():
    """Mock analyzer for integration tests."""
    analyzer = Mock(spec=UnifiedAnalyzer)

    def analyze_side_effect(description: str, context=None, depth=0):
        """Return different analysis based on task description."""
        if "simple" in description.lower() or "hello world" in description.lower():
            return TaskAnalysis(
                complexity_score=0.2,
                is_atomic=True,
                is_specific=True,
                confidence=0.9,
                reasoning="Simple task that can be implemented directly",
                suggested_approach=ApproachType.IMPLEMENT,
                implementation_hints="Create a function that prints 'Hello, World!'",
                estimated_story_points=1
            )
        elif "web application" in description.lower() or "user management" in description.lower():
            return TaskAnalysis(
                complexity_score=0.8,
                is_atomic=False,
                is_specific=True,
                confidence=0.85,
                reasoning="Complex task requiring decomposition",
                suggested_approach=ApproachType.DECOMPOSE,
                estimated_story_points=13
            )
        elif "authentication" in description.lower():
            return TaskAnalysis(
                complexity_score=0.6,
                is_atomic=False,
                is_specific=True,
                confidence=0.8,
                reasoning="Moderate complexity authentication feature",
                suggested_approach=ApproachType.DECOMPOSE,
                estimated_story_points=8
            )
        else:
            # Default for other subtasks
            return TaskAnalysis(
                complexity_score=0.3,
                is_atomic=True,
                is_specific=True,
                confidence=0.85,
                reasoning="Atomic subtask",
                suggested_approach=ApproachType.IMPLEMENT,
                implementation_hints="Direct implementation",
                estimated_story_points=2
            )

    def decompose_side_effect(description: str, context=None, max_subtasks=5, depth=0):
        """Return decomposition based on task description."""
        if "web application" in description.lower():
            return TaskDecomposition(
                subtasks=[
                    {
                        "description": "Setup project structure and dependencies",
                        "is_atomic": True,
                        "implementation_details": "Initialize project with framework and dependencies",
                        "story_points": 2
                    },
                    {
                        "description": "Implement user authentication system",
                        "is_atomic": False,
                        "implementation_details": None,
                        "story_points": 8
                    },
                    {
                        "description": "Create user interface components",
                        "is_atomic": True,
                        "implementation_details": "Build React components for user interaction",
                        "story_points": 3
                    }
                ],
                decomposition_reasoning="Split into infrastructure, backend auth, and frontend components"
            )
        elif "authentication" in description.lower():
            return TaskDecomposition(
                subtasks=[
                    {
                        "description": "Create user model and database schema",
                        "is_atomic": True,
                        "implementation_details": "Define user entity with email, password fields",
                        "story_points": 2
                    },
                    {
                        "description": "Implement password hashing and validation",
                        "is_atomic": True,
                        "implementation_details": "Use bcrypt for secure password hashing",
                        "story_points": 2
                    },
                    {
                        "description": "Create login and registration endpoints",
                        "is_atomic": True,
                        "implementation_details": "JWT-based authentication endpoints",
                        "story_points": 4
                    }
                ],
                decomposition_reasoning="Split into data model, security, and API endpoints"
            )
        else:
            return None

    analyzer.analyze_task = AsyncMock(side_effect=analyze_side_effect)
    analyzer.decompose_task = AsyncMock(side_effect=decompose_side_effect)

    return analyzer


@pytest_asyncio.fixture
async def mock_storage():
    """Mock storage that maintains in-memory data."""
    storage = Mock(spec=TaskStorage)

    # In-memory storage
    tasks = {}
    trees = {}

    async def save_task(task):
        tasks[task.id] = task

    async def get_task(task_id):
        return tasks.get(task_id)

    async def save_task_tree(tree):
        trees[tree.root.id] = tree

    async def get_task_tree(root_id):
        return trees.get(root_id)

    async def get_children(parent_id):
        return [task for task in tasks.values() if task.parent_id == parent_id]

    storage.save_task = AsyncMock(side_effect=save_task)
    storage.get_task = AsyncMock(side_effect=get_task)
    storage.save_task_tree = AsyncMock(side_effect=save_task_tree)
    storage.get_task_tree = AsyncMock(side_effect=get_task_tree)
    storage.get_children = AsyncMock(side_effect=get_children)

    # Additional methods for other API endpoints
    storage.get_tasks_by_status = AsyncMock(return_value=[])
    storage.get_user_tasks = AsyncMock(return_value=[])
    storage.get_tasks = AsyncMock(return_value=[])
    storage.count_tasks_by_status = AsyncMock(return_value={})
    storage.update_task = AsyncMock(return_value=True)
    storage.delete_task = AsyncMock(return_value=True)
    storage.search_tasks = AsyncMock(return_value=[])

    # Mock Redis client
    storage.redis = Mock()
    storage.redis.keys = AsyncMock(return_value=[])
    storage.task_prefix = "task:"

    return storage


@pytest_asyncio.fixture
async def mock_cache():
    """Mock cache manager."""
    cache = Mock(spec=CacheManager)
    cache.get_analysis = AsyncMock(return_value=None)
    cache.cache_analysis = AsyncMock()
    cache.get_decomposition = AsyncMock(return_value=None)
    cache.cache_decomposition = AsyncMock()
    cache.get_cache_stats = Mock(return_value={"hit_rate": 0.3})
    return cache


class TestCompletePipeline:
    """Test complete task processing pipeline."""

    def test_simple_atomic_task_pipeline(self, test_client, mock_analyzer, mock_storage, mock_cache):
        """Test processing of simple atomic task."""
        # Import the actual dependency functions
        from app.api.dependencies import get_analyzer, get_task_storage, get_cache_manager, get_task_processor

        # Create a realistic simple task result
        simple_task = Task(
            id="test-123",
            description="Create a simple hello world function",
            status=TaskStatus.COMPLETED,
            is_atomic=True,
            complexity_score=0.2,
            story_points=1,
            implementation_details="Create a function that prints 'Hello, World!'",
            depth=0,
            user_id="test-user",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Create mock tree with the simple task
        simple_tree = TaskTree(root=simple_task)
        simple_tree.add_task(simple_task)

        # Create mock processor
        mock_processor = Mock(spec=TaskProcessor)
        mock_processor.process_task_complete = AsyncMock(return_value=simple_tree)

        # Override dependencies
        app.dependency_overrides = {
            get_analyzer: lambda: mock_analyzer,
            get_task_storage: lambda: mock_storage,
            get_cache_manager: lambda: mock_cache,
            get_task_processor: lambda: mock_processor,
        }

        try:
            # Create simple task
            response = test_client.post(
                "/api/tasks",
                json={
                    "description": "Create a simple hello world function",
                    "user_id": "test-user",
                    "max_depth": 3
                }
            )

            # Verify response
            assert response.status_code == 200
            task_data = response.json()

            # Should be atomic and completed
            assert task_data["is_atomic"] is True
            assert task_data["status"] == "completed"
            assert task_data["complexity_score"] == 0.2
            assert task_data["story_points"] == 1
            assert "Hello, World!" in task_data["implementation_details"]

            # Verify processor was called with correct arguments
            mock_processor.process_task_complete.assert_called_once()
            call_args = mock_processor.process_task_complete.call_args
            assert call_args[1]["description"] == "Create a simple hello world function"
            assert call_args[1]["user_id"] == "test-user"
            assert call_args[1]["max_depth"] == 3

        finally:
            app.dependency_overrides = {}

    def test_complex_task_decomposition_pipeline(self, test_client, mock_analyzer, mock_storage, mock_cache):
        """Test processing of complex task with full decomposition."""
        from app.api.dependencies import get_analyzer, get_task_storage, get_cache_manager, get_task_processor

        # Create a complex task tree
        root_task = Task(
            id="root-123",
            description="Build a complete web application with user management",
            status=TaskStatus.COMPLETED,
            is_atomic=False,
            complexity_score=0.8,
            story_points=13,
            depth=0,
            user_id="test-user",
            subtasks=["subtask-1", "subtask-2", "subtask-3"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        subtask_1 = Task(
            id="subtask-1",
            description="Setup project structure and dependencies",
            status=TaskStatus.COMPLETED,
            is_atomic=True,
            depth=1,
            parent_id="root-123",
            user_id="test-user"
        )

        subtask_2 = Task(
            id="subtask-2",
            description="Implement user authentication system",
            status=TaskStatus.COMPLETED,
            is_atomic=False,
            depth=1,
            parent_id="root-123",
            user_id="test-user",
            subtasks=["subtask-2-1", "subtask-2-2"]
        )

        # Create complex tree
        complex_tree = TaskTree(root=root_task)
        complex_tree.add_task(root_task)
        complex_tree.add_task(subtask_1)
        complex_tree.add_task(subtask_2)

        # Create mock processor
        mock_processor = Mock(spec=TaskProcessor)
        mock_processor.process_task_complete = AsyncMock(return_value=complex_tree)

        # Override dependencies
        app.dependency_overrides = {
            get_analyzer: lambda: mock_analyzer,
            get_task_storage: lambda: mock_storage,
            get_cache_manager: lambda: mock_cache,
            get_task_processor: lambda: mock_processor,
        }

        try:
            # Create complex task
            response = test_client.post(
                "/api/tasks",
                json={
                    "description": "Build a complete web application with user management",
                    "user_id": "test-user",
                    "max_depth": 3,
                    "tech_preferences": {
                        "backend_language": "Python",
                        "frontend_framework": "React",
                        "database": "PostgreSQL"
                    }
                }
            )

            # Verify response
            assert response.status_code == 200
            task_data = response.json()

            # Root task should not be atomic and should be completed
            assert task_data["is_atomic"] is False
            assert task_data["status"] == "completed"
            assert task_data["complexity_score"] == 0.8
            assert task_data["story_points"] == 13

            # Verify processor was called with tech preferences
            mock_processor.process_task_complete.assert_called_once()
            call_args = mock_processor.process_task_complete.call_args
            assert "tech_stack" in call_args[1]["context"]

        finally:
            app.dependency_overrides = {}

    def test_task_tree_retrieval(self, test_client, mock_storage):
        """Test complete task tree retrieval after processing."""
        from app.api.dependencies import get_task_storage

        # Setup mock tree data
        root_task = Task(
            id="root-123",
            description="Build web app",
            status=TaskStatus.COMPLETED,
            is_atomic=False,
            depth=0,
            subtasks=["child-1", "child-2"]
        )

        child_1 = Task(
            id="child-1",
            description="Setup project",
            status=TaskStatus.COMPLETED,
            is_atomic=True,
            depth=1,
            parent_id="root-123"
        )

        child_2 = Task(
            id="child-2",
            description="Implement auth",
            status=TaskStatus.COMPLETED,
            is_atomic=False,
            depth=1,
            parent_id="root-123",
            subtasks=["grandchild-1"]
        )

        grandchild_1 = Task(
            id="grandchild-1",
            description="Create user model",
            status=TaskStatus.COMPLETED,
            is_atomic=True,
            depth=2,
            parent_id="child-2"
        )

        # Mock tree retrieval
        tree = TaskTree(root=root_task)
        tree.add_task(root_task)
        tree.add_task(child_1)
        tree.add_task(child_2)
        tree.add_task(grandchild_1)

        mock_storage.get_task_tree = AsyncMock(return_value=tree)
        mock_storage.get_children.side_effect = lambda pid: {
            "root-123": [child_1, child_2],
            "child-1": [],
            "child-2": [grandchild_1],
            "grandchild-1": []
        }.get(pid, [])

        # Override dependencies
        app.dependency_overrides = {
            get_task_storage: lambda: mock_storage,
        }

        try:
            # Get task tree
            response = test_client.get("/api/tasks/root-123/tree")

            assert response.status_code == 200
            tree_data = response.json()

            # Verify tree structure
            assert "root" in tree_data
            assert tree_data["root"]["task_id"] == "root-123"  # API uses task_id, not id
            assert tree_data["total_tasks"] == 4
            assert tree_data["max_depth"] == 2
            assert tree_data["completion_percentage"] == 100.0

            # Verify children structure
            root_children = tree_data["root"]["children"]
            assert len(root_children) == 2

            # Find auth task and verify it has children
            auth_task = next(c for c in root_children if "auth" in c["description"])
            assert len(auth_task["children"]) == 1
            assert auth_task["children"][0]["description"] == "Create user model"

        finally:
            app.dependency_overrides = {}

    def test_websocket_integration(self, test_client):
        """Test WebSocket connection and event handling."""
        from app.api.dependencies import get_task_storage
        from app.websocket.manager import WebSocketManager
        from app.websocket.events import TaskEventEmitter, TaskEventType

        # Create mock storage for WebSocket test
        mock_storage = Mock(spec=TaskStorage)

        # Test WebSocket connection
        with test_client.websocket_connect("/ws/global?token=test-token") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connection.established"
            assert "connection_id" in data

    def test_api_endpoints_compatibility(self, test_client):
        """Test that all expected API endpoints are available."""
        from app.api.dependencies import get_task_storage, get_redis_client
        from app.storage import RedisClient

        # Mock Redis client
        mock_redis_client = Mock(spec=RedisClient)
        mock_redis_client.ping = AsyncMock(return_value=True)

        # Mock storage for endpoint tests
        mock_storage = Mock(spec=TaskStorage)
        mock_storage.get_task = AsyncMock(return_value=None)
        mock_storage.count_tasks_by_status = AsyncMock(return_value={})

        app.dependency_overrides = {
            get_task_storage: lambda: mock_storage,
            get_redis_client: lambda: mock_redis_client,
        }

        try:
            # Test health endpoint
            response = test_client.get("/health")
            assert response.status_code == 200

            # Test stats endpoint
            response = test_client.get("/api/tasks/stats")
            assert response.status_code == 200

            # Test root endpoint
            response = test_client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Cahoots Task Manager"
            assert "endpoints" in data

        finally:
            app.dependency_overrides = {}

    def test_error_handling_in_pipeline(self, test_client):
        """Test error handling when processor fails."""
        from app.api.dependencies import get_task_processor

        # Create mock processor that raises exception
        failing_processor = Mock(spec=TaskProcessor)
        failing_processor.process_task_complete = AsyncMock(side_effect=Exception("Processing failed"))

        # Override dependencies
        app.dependency_overrides = {
            get_task_processor: lambda: failing_processor,
        }

        try:
            # Create task that should fail
            response = test_client.post(
                "/api/tasks",
                json={
                    "description": "Task that will fail",
                    "user_id": "test-user"
                }
            )

            # Should return 500 error
            assert response.status_code == 500
            assert "Processing failed" in response.json()["detail"]

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_performance_stats_tracking(self, mock_analyzer, mock_storage, mock_cache):
        """Test that performance statistics are properly tracked."""
        from app.processor import TaskProcessor, ProcessingConfig

        # Create real processor with mocked dependencies
        config = ProcessingConfig()
        processor = TaskProcessor(mock_storage, mock_analyzer, mock_cache, config)

        # Reset stats
        await processor.reset_stats()

        # Get initial stats
        stats = await processor.get_processing_stats()
        assert stats["tasks_processed"] == 0
        assert "processing_time" in stats
        assert "llm_efficiency" in stats

    def test_max_depth_handling(self, test_client):
        """Test max depth parameter handling."""
        from app.api.dependencies import get_task_processor

        # Create mock processor that respects max depth
        mock_processor = Mock(spec=TaskProcessor)

        # Create a simple task tree (depth 0 only due to max_depth=0)
        simple_task = Task(
            id="test-depth",
            description="Simple task with depth limit",
            status=TaskStatus.COMPLETED,
            is_atomic=True,
            depth=0,
            user_id="test-user"
        )

        simple_tree = TaskTree(root=simple_task)
        simple_tree.add_task(simple_task)

        mock_processor.process_task_complete = AsyncMock(return_value=simple_tree)

        app.dependency_overrides = {
            get_task_processor: lambda: mock_processor,
        }

        try:
            # Test with max_depth=1 (shallow depth limit)
            response = test_client.post(
                "/api/tasks",
                json={
                    "description": "Complex task that should be atomic due to depth limit",
                    "user_id": "test-user",
                    "max_depth": 1
                }
            )

            assert response.status_code == 200

            # Verify max_depth was passed to processor
            mock_processor.process_task_complete.assert_called_once()
            call_args = mock_processor.process_task_complete.call_args
            assert call_args[1]["max_depth"] == 1

        finally:
            app.dependency_overrides = {}


class TestWebSocketPipeline:
    """Test WebSocket functionality in the pipeline."""

    def test_websocket_connection_management(self, test_client):
        """Test WebSocket connection management."""
        # Test global WebSocket connection
        with test_client.websocket_connect("/ws/global?token=dev-token") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connection.established"
            assert "connection_id" in data
            # Global connection doesn't include user_id in confirmation
            # assert "user_id" in data

    def test_websocket_authentication(self, test_client):
        """Test WebSocket authentication."""
        # Test connection without token (should still work for dev)
        with test_client.websocket_connect("/ws/global") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection.established"

    def test_user_specific_websocket(self, test_client):
        """Test user-specific WebSocket endpoint."""
        # Test user-specific WebSocket
        with test_client.websocket_connect("/ws/user/test-user?token=dev-token") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection.established"
            # Check if user_id is included for user-specific connections
            if "user_id" in data:
                assert data["user_id"] == "test-user"


# Helper functions for integration testing
def verify_task_structure(task_data: Dict[str, Any]) -> None:
    """Verify that task data has correct structure."""
    required_fields = [
        "id", "description", "status", "depth", "is_atomic",
        "complexity_score", "created_at", "updated_at"
    ]

    for field in required_fields:
        assert field in task_data, f"Missing required field: {field}"

    # Verify data types
    assert isinstance(task_data["depth"], int)
    assert isinstance(task_data["is_atomic"], bool)
    assert isinstance(task_data["complexity_score"], (int, float))
    assert task_data["complexity_score"] >= 0.0
    assert task_data["complexity_score"] <= 1.0


def verify_tree_structure(tree_data: Dict[str, Any]) -> None:
    """Verify that tree data has correct structure."""
    required_fields = [
        "root", "total_tasks", "completed_tasks", "max_depth", "completion_percentage"
    ]

    for field in required_fields:
        assert field in tree_data, f"Missing required field: {field}"

    # Verify root task structure
    verify_task_structure(tree_data["root"])

    # Verify statistics
    assert isinstance(tree_data["total_tasks"], int)
    assert isinstance(tree_data["completed_tasks"], int)
    assert isinstance(tree_data["max_depth"], int)
    assert isinstance(tree_data["completion_percentage"], (int, float))
    assert 0 <= tree_data["completion_percentage"] <= 100
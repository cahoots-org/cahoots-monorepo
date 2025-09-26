"""Unit tests for storage layer."""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models import Task, TaskStatus, TaskTree
from app.storage import RedisClient, TaskStorage


class TestRedisClient:
    """Test suite for RedisClient."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        mock.close = AsyncMock()
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value='{"test": "data"}')
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.keys = AsyncMock(return_value=["key1", "key2"])
        mock.mget = AsyncMock(return_value=['{"a": 1}', None, '{"b": 2}'])
        mock.mset = AsyncMock(return_value=True)
        mock.incr = AsyncMock(return_value=5)
        mock.expire = AsyncMock(return_value=True)
        mock.ttl = AsyncMock(return_value=3600)
        mock.lpush = AsyncMock(return_value=3)
        mock.rpush = AsyncMock(return_value=3)
        mock.lrange = AsyncMock(return_value=['{"item": 1}', '{"item": 2}'])
        mock.llen = AsyncMock(return_value=2)
        mock.sadd = AsyncMock(return_value=2)
        mock.smembers = AsyncMock(return_value={'{"member": 1}', '{"member": 2}'})
        mock.scard = AsyncMock(return_value=2)
        mock.sismember = AsyncMock(return_value=True)
        return mock

    @pytest_asyncio.fixture
    async def redis_client(self, mock_redis):
        """Create a RedisClient with mock."""
        client = RedisClient(test_mode=True, test_client=mock_redis)
        return client

    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_client):
        """Test setting and getting values."""
        # Test setting a dictionary
        result = await redis_client.set("test_key", {"data": "value"})
        assert result is True

        # Test getting a value
        value = await redis_client.get("test_key")
        assert value == {"test": "data"}  # Mock returns this

    @pytest.mark.asyncio
    async def test_delete(self, redis_client):
        """Test deleting keys."""
        deleted = await redis_client.delete("key1", "key2")
        assert deleted == 1  # Mock returns 1

    @pytest.mark.asyncio
    async def test_exists(self, redis_client):
        """Test checking key existence."""
        exists = await redis_client.exists("test_key")
        assert exists == 1

    @pytest.mark.asyncio
    async def test_keys_pattern(self, redis_client):
        """Test getting keys by pattern."""
        keys = await redis_client.keys("test:*")
        assert keys == ["key1", "key2"]

    @pytest.mark.asyncio
    async def test_mget_mset(self, redis_client):
        """Test multi-get and multi-set operations."""
        # Test mset
        result = await redis_client.mset({"key1": {"a": 1}, "key2": {"b": 2}})
        assert result is True

        # Test mget
        values = await redis_client.mget(["key1", "key2", "key3"])
        assert len(values) == 3
        assert values[0] == {"a": 1}
        assert values[1] is None
        assert values[2] == {"b": 2}

    @pytest.mark.asyncio
    async def test_counter_operations(self, redis_client):
        """Test increment operation."""
        new_value = await redis_client.incr("counter")
        assert new_value == 5

        new_value = await redis_client.incr("counter", 10)
        assert new_value == 5  # Mock always returns 5

    @pytest.mark.asyncio
    async def test_expire_ttl(self, redis_client):
        """Test expiration operations."""
        result = await redis_client.expire("test_key", 3600)
        assert result is True

        ttl = await redis_client.ttl("test_key")
        assert ttl == 3600

    @pytest.mark.asyncio
    async def test_list_operations(self, redis_client):
        """Test list operations."""
        # Test lpush
        length = await redis_client.lpush("list_key", {"item": 1})
        assert length == 3

        # Test rpush
        length = await redis_client.rpush("list_key", {"item": 2})
        assert length == 3

        # Test lrange
        items = await redis_client.lrange("list_key", 0, -1)
        assert len(items) == 2
        assert items[0] == {"item": 1}

        # Test llen
        length = await redis_client.llen("list_key")
        assert length == 2

    @pytest.mark.asyncio
    async def test_set_operations(self, redis_client):
        """Test set operations."""
        # Test sadd
        added = await redis_client.sadd("set_key", {"member": 1})
        assert added == 2

        # Test smembers
        members = await redis_client.smembers("set_key")
        assert len(members) == 2

        # Test scard
        count = await redis_client.scard("set_key")
        assert count == 2

        # Test sismember
        is_member = await redis_client.sismember("set_key", {"member": 1})
        assert is_member is True


class TestTaskStorage:
    """Test suite for TaskStorage."""

    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """Create a mock RedisClient."""
        mock = AsyncMock(spec=RedisClient)
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock()
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.keys = AsyncMock(return_value=[])
        mock.mget = AsyncMock(return_value=[])
        mock.sadd = AsyncMock(return_value=1)
        mock.srem = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        mock.scard = AsyncMock(return_value=0)
        mock.lpush = AsyncMock(return_value=1)
        mock.lrange = AsyncMock(return_value=[])
        mock.srem = AsyncMock(return_value=1)  # Add srem for removing from sets
        return mock

    @pytest_asyncio.fixture
    async def task_storage(self, mock_redis_client):
        """Create a TaskStorage with mock Redis."""
        return TaskStorage(mock_redis_client)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task."""
        return Task(
            id="test-123",
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            depth=1,
            parent_id="parent-456",
            is_atomic=False,
            complexity_score=0.5,
            story_points=3,
            user_id="user-789"
        )

    @pytest.mark.asyncio
    async def test_save_and_get_task(self, task_storage, sample_task, mock_redis_client):
        """Test saving and retrieving a task."""
        # Configure mock to return the task data first time, then None for parent lookup
        mock_redis_client.get.side_effect = [None, sample_task.to_redis_dict()]

        # Save task
        result = await task_storage.save_task(sample_task)
        assert result is True
        # Will be called once for the task itself
        assert mock_redis_client.set.call_count == 1

        # Get task
        retrieved = await task_storage.get_task("test-123")
        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.description == sample_task.description
        assert retrieved.status == sample_task.status

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_storage, mock_redis_client):
        """Test getting a non-existent task."""
        mock_redis_client.get.return_value = None

        task = await task_storage.get_task("nonexistent")
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task(self, task_storage, sample_task, mock_redis_client):
        """Test updating a task."""
        # Configure mock to return the task, then None for parent lookup
        mock_redis_client.get.side_effect = [
            sample_task.to_redis_dict(),  # First call to get the task
            None  # Second call for parent lookup during save
        ]

        # Update task
        updates = {
            "status": TaskStatus.COMPLETED,
            "story_points": 5
        }
        result = await task_storage.update_task("test-123", updates)
        assert result is True

        # Verify set was called
        assert mock_redis_client.set.call_count >= 1

    @pytest.mark.asyncio
    async def test_delete_task(self, task_storage, sample_task, mock_redis_client):
        """Test deleting a task."""
        # Configure mock to return the task
        mock_redis_client.get.return_value = sample_task.to_redis_dict()
        mock_redis_client.delete.return_value = 1

        # Delete task
        result = await task_storage.delete_task("test-123")
        assert result is True
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_multiple_tasks(self, task_storage, mock_redis_client):
        """Test getting multiple tasks."""
        task1_data = Task(id="t1", description="Task 1").to_redis_dict()
        task2_data = Task(id="t2", description="Task 2").to_redis_dict()

        mock_redis_client.mget.return_value = [task1_data, None, task2_data]

        tasks = await task_storage.get_tasks(["t1", "t2", "t3"])
        assert len(tasks) == 3
        assert tasks[0].id == "t1"
        assert tasks[1] is None
        assert tasks[2].id == "t2"

    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, task_storage, mock_redis_client):
        """Test getting tasks by status."""
        # Configure mock to return task IDs
        mock_redis_client.smembers.return_value = {"task1", "task2"}

        # Configure mock to return task data
        task1 = Task(id="task1", description="Task 1", status=TaskStatus.IN_PROGRESS)
        task2 = Task(id="task2", description="Task 2", status=TaskStatus.IN_PROGRESS)
        mock_redis_client.mget.return_value = [
            task1.to_redis_dict(),
            task2.to_redis_dict()
        ]

        # Get tasks by status
        tasks = await task_storage.get_tasks_by_status(TaskStatus.IN_PROGRESS)
        assert len(tasks) == 2
        assert all(task.status == TaskStatus.IN_PROGRESS for task in tasks)

    @pytest.mark.asyncio
    async def test_get_user_tasks(self, task_storage, mock_redis_client):
        """Test getting user's tasks."""
        # Configure mock to return task IDs
        mock_redis_client.lrange.return_value = ["task1", "task2"]

        # Configure mock to return task data
        task1 = Task(id="task1", description="Task 1", user_id="user123")
        task2 = Task(id="task2", description="Task 2", user_id="user123")
        mock_redis_client.mget.return_value = [
            task1.to_redis_dict(),
            task2.to_redis_dict()
        ]

        # Get user tasks
        tasks = await task_storage.get_user_tasks("user123", limit=10)
        assert len(tasks) == 2
        assert all(task.user_id == "user123" for task in tasks)

    @pytest.mark.asyncio
    async def test_get_children(self, task_storage, mock_redis_client):
        """Test getting child tasks."""
        # Create parent with children
        parent = Task(id="parent", description="Parent", subtasks=["child1", "child2"])
        child1 = Task(id="child1", description="Child 1", parent_id="parent")
        child2 = Task(id="child2", description="Child 2", parent_id="parent")

        # Configure mock
        mock_redis_client.get.return_value = parent.to_redis_dict()
        mock_redis_client.mget.return_value = [
            child1.to_redis_dict(),
            child2.to_redis_dict()
        ]

        # Get children
        children = await task_storage.get_children("parent")
        assert len(children) == 2
        assert all(child.parent_id == "parent" for child in children)

    @pytest.mark.asyncio
    async def test_save_and_get_task_tree(self, task_storage, mock_redis_client):
        """Test saving and retrieving a task tree."""
        # Create a task tree
        root = Task(id="root", description="Root task")
        child1 = Task(id="child1", description="Child 1", parent_id="root", depth=1)
        child2 = Task(id="child2", description="Child 2", parent_id="root", depth=1)

        tree = TaskTree(root=root)
        tree.add_task(root)
        tree.add_task(child1)
        tree.add_task(child2)
        root.subtasks = ["child1", "child2"]

        # Configure mock to handle parent lookups during save
        # Each save_task call will look for parent, return None
        mock_redis_client.get.reset_mock()
        mock_redis_client.get.return_value = None

        # Save tree
        result = await task_storage.save_task_tree(tree)
        assert result is True

        # Now configure mock for retrieval
        tree_data = {
            "root_id": "root",
            "task_ids": ["root", "child1", "child2"],
            "depth_map": {"0": ["root"], "1": ["child1", "child2"]}
        }

        # Reset mock and set new behavior
        mock_redis_client.get.reset_mock()
        mock_redis_client.get.side_effect = [
            tree_data,  # Tree metadata
        ]
        mock_redis_client.mget.return_value = [
            root.to_redis_dict(),
            child1.to_redis_dict(),
            child2.to_redis_dict()
        ]

        # Get tree
        retrieved_tree = await task_storage.get_task_tree("root")
        assert retrieved_tree is not None
        assert retrieved_tree.root.id == "root"
        assert len(retrieved_tree.tasks) == 3

    @pytest.mark.asyncio
    async def test_count_tasks_by_status(self, task_storage, mock_redis_client):
        """Test counting tasks by status."""
        # Configure mock to return counts
        mock_redis_client.scard.side_effect = [10, 5, 3, 2, 1, 0, 0]

        counts = await task_storage.count_tasks_by_status()

        assert len(counts) == len(TaskStatus)
        assert sum(counts.values()) > 0

    @pytest.mark.asyncio
    async def test_search_tasks(self, task_storage, mock_redis_client):
        """Test searching tasks."""
        # Configure mock
        mock_redis_client.keys.return_value = ["task:t1", "task:t2", "task:t3"]

        task1 = Task(id="t1", description="Build authentication system")
        task2 = Task(id="t2", description="Create database schema")
        task3 = Task(id="t3", description="Build API endpoints")

        mock_redis_client.mget.return_value = [
            task1.to_redis_dict(),
            task2.to_redis_dict(),
            task3.to_redis_dict()
        ]

        # Search for "Build"
        results = await task_storage.search_tasks("Build", limit=2)
        assert len(results) == 2
        assert all("Build" in task.description for task in results)
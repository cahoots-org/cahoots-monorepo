"""Tests for WebSocket functionality."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

from app.websocket.manager import WebSocketManager
from app.websocket.events import TaskEventEmitter, TaskEventType
from app.models import Task, TaskStatus


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_text(self, message: str):
        self.messages.append(json.loads(message))

    async def close(self, code=1000, reason=""):
        self.closed = True

    async def ping(self):
        pass


@pytest_asyncio.fixture
async def ws_manager():
    """WebSocket manager for testing."""
    return WebSocketManager()


@pytest_asyncio.fixture
async def mock_websocket():
    """Mock WebSocket connection."""
    return MockWebSocket()


@pytest_asyncio.fixture
async def event_emitter(ws_manager):
    """Task event emitter for testing."""
    return TaskEventEmitter(ws_manager)


class TestWebSocketManager:
    """Test WebSocket manager functionality."""

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, ws_manager, mock_websocket):
        """Test WebSocket connection and disconnection."""
        connection_id = "test-conn-1"
        user_id = "test-user"

        # Connect
        await ws_manager.connect(mock_websocket, connection_id, user_id, is_global=True)

        # Verify connection is registered
        assert connection_id in ws_manager.connections
        assert user_id in ws_manager.user_connections
        assert connection_id in ws_manager.global_connections
        assert len(mock_websocket.messages) == 1  # Connection confirmation

        # Disconnect
        await ws_manager.disconnect(connection_id)

        # Verify connection is removed
        assert connection_id not in ws_manager.connections
        assert user_id not in ws_manager.user_connections
        assert connection_id not in ws_manager.global_connections

    @pytest.mark.asyncio
    async def test_send_to_connection(self, ws_manager, mock_websocket):
        """Test sending message to specific connection."""
        connection_id = "test-conn-1"
        await ws_manager.connect(mock_websocket, connection_id)

        message = {"type": "test", "data": "hello"}
        success = await ws_manager.send_to_connection(connection_id, message)

        assert success
        assert len(mock_websocket.messages) == 2  # Connection + test message
        assert mock_websocket.messages[1]["type"] == "test"

    @pytest.mark.asyncio
    async def test_send_to_user(self, ws_manager):
        """Test sending message to all user connections."""
        user_id = "test-user"

        # Connect multiple connections for same user
        ws1, ws2 = MockWebSocket(), MockWebSocket()
        await ws_manager.connect(ws1, "conn-1", user_id)
        await ws_manager.connect(ws2, "conn-2", user_id)

        message = {"type": "user_message", "data": "hello user"}
        await ws_manager.send_to_user(user_id, message)

        # Both connections should receive the message
        assert len(ws1.messages) == 2  # Connection + user message
        assert len(ws2.messages) == 2  # Connection + user message
        assert ws1.messages[1]["type"] == "user_message"
        assert ws2.messages[1]["type"] == "user_message"

    @pytest.mark.asyncio
    async def test_broadcast_global(self, ws_manager):
        """Test broadcasting to global connections."""
        # Connect global and user-specific connections
        global_ws = MockWebSocket()
        user_ws = MockWebSocket()

        await ws_manager.connect(global_ws, "global-1", is_global=True)
        await ws_manager.connect(user_ws, "user-1", "test-user", is_global=False)

        message = {"type": "broadcast", "data": "global message"}
        await ws_manager.broadcast_global(message)

        # Only global connection should receive broadcast
        assert len(global_ws.messages) == 2  # Connection + broadcast
        assert len(user_ws.messages) == 1   # Only connection message
        assert global_ws.messages[1]["type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_connection_stats(self, ws_manager):
        """Test connection statistics."""
        # Initially no connections
        stats = ws_manager.get_connection_count()
        assert stats["total_connections"] == 0
        assert stats["user_connections"] == 0
        assert stats["global_connections"] == 0

        # Add connections
        await ws_manager.connect(MockWebSocket(), "conn-1", "user-1", is_global=True)
        await ws_manager.connect(MockWebSocket(), "conn-2", "user-2", is_global=False)

        stats = ws_manager.get_connection_count()
        assert stats["total_connections"] == 2
        assert stats["user_connections"] == 2
        assert stats["global_connections"] == 1
        assert stats["users_connected"] == 2


class TestTaskEventEmitter:
    """Test task event emitter functionality."""

    @pytest.mark.asyncio
    async def test_emit_task_created(self, event_emitter, ws_manager):
        """Test task created event emission."""
        # Setup WebSocket connection
        mock_ws = MockWebSocket()
        await ws_manager.connect(mock_ws, "conn-1", is_global=True)

        # Create test task
        task = Task(
            id="task-123",
            description="Test task",
            status=TaskStatus.SUBMITTED,
            user_id="test-user"
        )

        # Emit event
        await event_emitter.emit_task_created(task, "test-user")

        # Verify event was sent
        assert len(mock_ws.messages) == 2  # Connection + task created
        task_event = mock_ws.messages[1]
        assert task_event["type"] == TaskEventType.CREATED.value
        assert task_event["task_id"] == "task-123"
        assert task_event["description"] == "Test task"
        assert task_event["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_emit_status_changed(self, event_emitter, ws_manager):
        """Test task status changed event emission."""
        # Setup WebSocket connection
        mock_ws = MockWebSocket()
        await ws_manager.connect(mock_ws, "conn-1", is_global=True)

        # Create test task
        task = Task(
            id="task-123",
            description="Test task",
            status=TaskStatus.COMPLETED,
            user_id="test-user"
        )

        # Emit status changed event
        await event_emitter.emit_task_status_changed(
            task,
            TaskStatus.IN_PROGRESS,
            "test-user"
        )

        # Should emit both status_changed AND completed events
        assert len(mock_ws.messages) == 3  # Connection + status_changed + completed

        status_event = mock_ws.messages[1]
        assert status_event["type"] == TaskEventType.STATUS_CHANGED.value
        assert status_event["old_status"] == "in_progress"
        assert status_event["new_status"] == "completed"

        completed_event = mock_ws.messages[2]
        assert completed_event["type"] == TaskEventType.COMPLETED.value

    @pytest.mark.asyncio
    async def test_emit_decomposition_events(self, event_emitter, ws_manager):
        """Test decomposition event emissions."""
        # Setup WebSocket connection
        mock_ws = MockWebSocket()
        await ws_manager.connect(mock_ws, "conn-1", is_global=True)

        # Create test task
        task = Task(
            id="task-123",
            description="Complex task",
            status=TaskStatus.PROCESSING,
            user_id="test-user"
        )

        # Emit decomposition events
        await event_emitter.emit_decomposition_started(task, "test-user")
        await event_emitter.emit_decomposition_completed(task, 3, "test-user")

        # Verify events
        assert len(mock_ws.messages) == 3  # Connection + started + completed

        started_event = mock_ws.messages[1]
        assert started_event["type"] == TaskEventType.DECOMPOSITION_STARTED.value
        assert "started" in started_event["message"]

        completed_event = mock_ws.messages[2]
        assert completed_event["type"] == TaskEventType.DECOMPOSITION_COMPLETED.value
        assert completed_event["subtask_count"] == 3

    @pytest.mark.asyncio
    async def test_bulk_event_emission(self, event_emitter, ws_manager):
        """Test bulk event emission."""
        # Setup WebSocket connection
        mock_ws = MockWebSocket()
        await ws_manager.connect(mock_ws, "conn-1", is_global=True)

        # Create test tasks
        task1 = Task(id="task-1", description="Task 1")
        task2 = Task(id="task-2", description="Task 2")

        # Emit bulk events
        events = [
            (TaskEventType.CREATED, task1, {"extra": "data1"}),
            (TaskEventType.CREATED, task2, {"extra": "data2"}),
        ]

        await event_emitter.emit_bulk_task_events(events, "test-user")

        # Verify all events were sent
        assert len(mock_ws.messages) == 3  # Connection + 2 task events
        assert mock_ws.messages[1]["task_id"] == "task-1"
        assert mock_ws.messages[2]["task_id"] == "task-2"


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_event_filtering_by_user(self, event_emitter, ws_manager):
        """Test that events are properly filtered by user."""
        # Setup connections for different users
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        global_ws = MockWebSocket()

        await ws_manager.connect(user1_ws, "user1-conn", "user-1", is_global=False)
        await ws_manager.connect(user2_ws, "user2-conn", "user-2", is_global=False)
        await ws_manager.connect(global_ws, "global-conn", is_global=True)

        # Create task for user-1
        task = Task(
            id="task-123",
            description="User 1 task",
            user_id="user-1"
        )

        # Emit task created event
        await event_emitter.emit_task_created(task, "user-1")

        # Global connection should receive event
        assert len(global_ws.messages) >= 2

        # User-1 connection should receive event
        assert len(user1_ws.messages) >= 2

        # Verify event content in global connection
        task_event = next(msg for msg in global_ws.messages if msg.get("type") == TaskEventType.CREATED.value)
        assert task_event["task_id"] == "task-123"
        assert task_event["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_error(self, ws_manager):
        """Test that connections are cleaned up on errors."""
        # Create a WebSocket that will fail
        failing_ws = Mock()
        failing_ws.accept = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Connection lost"))

        connection_id = "failing-conn"
        await ws_manager.connect(failing_ws, connection_id, is_global=True)

        # Verify connection was added
        assert connection_id in ws_manager.connections

        # Try to send message (should fail and cleanup connection)
        success = await ws_manager.send_to_connection(connection_id, {"test": "message"})

        # Verify cleanup
        assert not success
        assert connection_id not in ws_manager.connections
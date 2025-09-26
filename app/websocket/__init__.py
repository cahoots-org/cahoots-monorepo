"""WebSocket support for real-time task updates."""

from .manager import WebSocketManager, websocket_manager
from .events import TaskEventEmitter

__all__ = [
    "WebSocketManager",
    "websocket_manager",
    "TaskEventEmitter"
]
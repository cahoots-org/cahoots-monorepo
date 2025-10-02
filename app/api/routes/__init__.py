"""API route definitions."""

from .tasks import router as task_router
from .health import router as health_router
from .websocket import router as websocket_router
from .epics import router as epics_router
from .auth import router as auth_router
from .events import router as events_router

__all__ = [
    "task_router",
    "health_router",
    "websocket_router",
    "epics_router",
    "auth_router",
    "events_router",
]
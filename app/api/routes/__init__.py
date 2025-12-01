"""API route definitions."""

from .tasks import router as task_router
from .health import router as health_router
from .websocket import router as websocket_router
from .epics import router as epics_router
from .auth import router as auth_router
from .events import router as events_router
from .regenerate import router as regenerate_router
from .cascade import router as cascade_router
from .user_settings import router as user_settings_router
from .metrics import router as metrics_router
from .projects import router as projects_router

__all__ = [
    "task_router",
    "health_router",
    "websocket_router",
    "epics_router",
    "auth_router",
    "events_router",
    "regenerate_router",
    "cascade_router",
    "user_settings_router",
    "metrics_router",
    "projects_router",
]
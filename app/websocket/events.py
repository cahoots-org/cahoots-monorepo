"""Task event emitter for WebSocket notifications."""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from app.models import Task, TaskStatus
from .manager import websocket_manager


class TaskEventType(str, Enum):
    """Types of task events."""
    CREATED = "task.created"
    UPDATED = "task.updated"
    STATUS_CHANGED = "task.status_changed"
    COMPLETED = "task.completed"
    DELETED = "task.deleted"
    DECOMPOSITION_STARTED = "decomposition.started"
    DECOMPOSITION_COMPLETED = "decomposition.completed"
    DECOMPOSITION_ERROR = "decomposition.error"
    PROCESSING_UPDATE = "task.processing_update"
    EVENT_MODELING_STARTED = "event_modeling.started"
    EVENT_MODELING_PROGRESS = "event_modeling.progress"
    EVENT_MODELING_COMPLETED = "event_modeling.completed"


class TaskEventEmitter:
    """Emits task-related events via WebSocket."""

    def __init__(self, ws_manager=None):
        self.ws_manager = ws_manager or websocket_manager

    async def emit_task_created(
        self,
        task: Task,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Emit task created event."""
        await self._emit_task_event(
            TaskEventType.CREATED,
            task,
            user_id,
            additional_data
        )

    async def emit_task_updated(
        self,
        task: Task,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        """Emit task updated event."""
        additional_data = {"changes": changes} if changes else None
        await self._emit_task_event(
            TaskEventType.UPDATED,
            task,
            user_id,
            additional_data
        )

    async def emit_task_status_changed(
        self,
        task: Task,
        old_status: Optional[TaskStatus] = None,
        user_id: Optional[str] = None
    ):
        """Emit task status changed event."""
        additional_data = {
            "old_status": old_status.value if old_status else None,
            "new_status": task.status.value
        }

        # If task is completed, emit both status changed and completed events
        if task.status == TaskStatus.COMPLETED:
            await self._emit_task_event(
                TaskEventType.STATUS_CHANGED,
                task,
                user_id,
                additional_data
            )
            await self._emit_task_event(
                TaskEventType.COMPLETED,
                task,
                user_id,
                additional_data
            )
        else:
            await self._emit_task_event(
                TaskEventType.STATUS_CHANGED,
                task,
                user_id,
                additional_data
            )

    async def emit_task_deleted(
        self,
        task: Task,
        user_id: Optional[str] = None,
        deleted_count: int = 1
    ):
        """Emit task deleted event."""
        additional_data = {"deleted_count": deleted_count}
        await self._emit_task_event(
            TaskEventType.DELETED,
            task,
            user_id,
            additional_data
        )

    async def emit_decomposition_started(
        self,
        task: Task,
        user_id: Optional[str] = None
    ):
        """Emit decomposition started event."""
        await self._emit_task_event(
            TaskEventType.DECOMPOSITION_STARTED,
            task,
            user_id,
            {"message": "Task decomposition has started"}
        )

    async def emit_decomposition_completed(
        self,
        task: Task,
        subtask_count: int,
        user_id: Optional[str] = None
    ):
        """Emit decomposition completed event."""
        additional_data = {
            "subtask_count": subtask_count,
            "message": f"Decomposition completed with {subtask_count} subtasks"
        }
        await self._emit_task_event(
            TaskEventType.DECOMPOSITION_COMPLETED,
            task,
            user_id,
            additional_data
        )

    async def emit_decomposition_error(
        self,
        task: Task,
        error_message: str,
        user_id: Optional[str] = None
    ):
        """Emit decomposition error event."""
        additional_data = {
            "error": error_message,
            "message": "Task decomposition failed"
        }
        await self._emit_task_event(
            TaskEventType.DECOMPOSITION_ERROR,
            task,
            user_id,
            additional_data
        )

    async def emit_task_error(
        self,
        task: Task,
        error_message: str,
        user_id: Optional[str] = None
    ):
        """Emit general task error event."""
        additional_data = {
            "error": error_message,
            "message": "Task processing failed"
        }
        await self._emit_task_event(
            TaskEventType.DECOMPOSITION_ERROR,
            task,
            user_id,
            additional_data
        )

    async def emit_processing_update(
        self,
        task: Task,
        progress_info: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Emit processing update event."""
        await self._emit_task_event(
            TaskEventType.PROCESSING_UPDATE,
            task,
            user_id,
            progress_info
        )

    async def _emit_task_event(
        self,
        event_type: TaskEventType,
        task: Task,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Emit a task event to WebSocket connections."""
        # Build the event payload
        event_data = {
            "type": event_type.value,
            "task_id": task.id,
            "parent_id": task.parent_id,
            "root_task_id": self._get_root_task_id(task),
            "status": task.status.value,
            "description": task.description,
            "depth": task.depth,
            "is_atomic": task.is_atomic,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add additional data if provided
        if additional_data:
            event_data.update(additional_data)

        # Add user context
        if user_id:
            event_data["user_id"] = user_id
        elif task.user_id:
            event_data["user_id"] = task.user_id

        # Send to different audiences based on event type
        await self._broadcast_event(event_data, task.user_id)

    def _get_root_task_id(self, task: Task) -> str:
        """Get the root task ID for hierarchical event filtering."""
        # If this is already a root task, return its ID
        if task.parent_id is None:
            return task.id

        # For non-root tasks, we need to traverse up the tree
        # In a production system, you'd want to cache this or store it on the task
        # For now, we'll return the parent_id as a reasonable approximation
        # The frontend will need to handle multiple levels of hierarchy
        return task.parent_id if task.parent_id else task.id

    async def _broadcast_event(self, event_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast event to appropriate WebSocket connections."""
        print(f"[WebSocket] Broadcasting event: {event_data.get('type')} for task {event_data.get('task_id')}")
        try:
            # Send to global connections (like TaskBoard)
            await self.ws_manager.broadcast_global(event_data)

            # Send to specific user connections if user_id is available
            if user_id:
                await self.ws_manager.send_to_user(user_id, event_data)

        except Exception as e:
            # Log the error but don't fail the main operation
            print(f"Failed to broadcast WebSocket event: {e}")

    async def emit_bulk_task_events(
        self,
        events: list[tuple[TaskEventType, Task, Optional[Dict[str, Any]]]],
        user_id: Optional[str] = None
    ):
        """Emit multiple task events efficiently."""
        tasks = []
        for event_type, task, additional_data in events:
            tasks.append(self._emit_task_event(event_type, task, user_id, additional_data))

        # Execute all emissions concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def emit_event_modeling_started(
        self,
        task: Task,
        user_id: Optional[str] = None
    ):
        """Emit event modeling started event."""
        await self._emit_task_event(
            TaskEventType.EVENT_MODELING_STARTED,
            task,
            user_id,
            {"message": "Starting event modeling analysis..."}
        )

    async def emit_event_modeling_progress(
        self,
        task: Task,
        user_id: Optional[str] = None,
        events_count: int = 0,
        commands_count: int = 0,
        read_models_count: int = 0,
        interactions_count: int = 0,
        automations_count: int = 0
    ):
        """Emit event modeling progress event."""
        await self._emit_task_event(
            TaskEventType.EVENT_MODELING_PROGRESS,
            task,
            user_id,
            {
                "events": events_count,
                "commands": commands_count,
                "read_models": read_models_count,
                "user_interactions": interactions_count,
                "automations": automations_count
            }
        )

    async def emit_event_modeling_completed(
        self,
        task: Task,
        user_id: Optional[str] = None,
        events_count: int = 0,
        commands_count: int = 0,
        read_models_count: int = 0,
        interactions_count: int = 0,
        automations_count: int = 0
    ):
        """Emit event modeling completed event."""
        await self._emit_task_event(
            TaskEventType.EVENT_MODELING_COMPLETED,
            task,
            user_id,
            {
                "events": events_count,
                "commands": commands_count,
                "read_models": read_models_count,
                "user_interactions": interactions_count,
                "automations": automations_count,
                "message": f"Event modeling complete: {events_count} events, {commands_count} commands, {read_models_count} read models"
            }
        )


# Global task event emitter instance
task_event_emitter = TaskEventEmitter()
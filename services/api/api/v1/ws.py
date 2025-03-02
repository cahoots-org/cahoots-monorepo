"""WebSocket endpoints for real-time updates."""

from typing import Dict
from uuid import UUID

from api.dependencies import get_current_organization
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from cahoots_core.utils.infrastructure.redis.client import RedisClient, get_redis_client

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[UUID, Dict[str, WebSocket]] = {}

    async def connect(self, organization_id: UUID, client_id: str, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if organization_id not in self.active_connections:
            self.active_connections[organization_id] = {}
        self.active_connections[organization_id][client_id] = websocket

    async def disconnect(self, organization_id: UUID, client_id: str):
        """Disconnect a WebSocket client."""
        if organization_id in self.active_connections:
            self.active_connections[organization_id].pop(client_id, None)
            if not self.active_connections[organization_id]:
                self.active_connections.pop(organization_id)

    async def broadcast(self, organization_id: UUID, message: Dict):
        """Broadcast a message to all organization clients."""
        if organization_id in self.active_connections:
            for websocket in self.active_connections[organization_id].values():
                await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/projects/{client_id}")
async def project_updates(
    websocket: WebSocket,
    client_id: str,
    organization_id: UUID = Depends(get_current_organization),
    redis_client: RedisClient = Depends(get_redis_client),
):
    """WebSocket endpoint for project status updates.

    Subscribes to Redis channel for project updates and forwards
    them to connected WebSocket clients.
    """
    await manager.connect(organization_id, client_id, websocket)
    channel = f"org:{organization_id}:projects"

    try:
        # Subscribe to Redis channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Listen for messages
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message and message.get("type") == "message":
                    await websocket.send_json(message.get("data"))
            except WebSocketDisconnect:
                break

    finally:
        # Clean up
        await pubsub.unsubscribe(channel)
        await manager.disconnect(organization_id, client_id)

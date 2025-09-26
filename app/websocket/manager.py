"""WebSocket connection manager for real-time task updates."""

import json
import asyncio
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        # Active connections by connection ID
        self.connections: Dict[str, WebSocket] = {}
        # User connections mapping (user_id -> set of connection_ids)
        self.user_connections: Dict[str, Set[str]] = {}
        # Global connections (receive all events)
        self.global_connections: Set[str] = set()
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
        is_global: bool = False
    ):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        self.connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "is_global": is_global
        }

        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        # Track global connections
        if is_global:
            self.global_connections.add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id}, global: {is_global})")

        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            "type": "connection.established",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.connections:
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            is_global = metadata.get("is_global", False)

            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove from global connections
            if is_global:
                self.global_connections.discard(connection_id)

            # Clean up
            del self.connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]

            logger.info(f"WebSocket disconnected: {connection_id} (user: {user_id})")

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific connection."""
        if connection_id not in self.connections:
            return False

        try:
            websocket = self.connections[connection_id]
            await websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            # Connection is likely dead, remove it
            await self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return

        # Get a copy of connection IDs to avoid modification during iteration
        connection_ids = self.user_connections[user_id].copy()

        successful_sends = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                successful_sends += 1

        logger.debug(f"Sent message to user {user_id}: {successful_sends}/{len(connection_ids)} connections")

    async def broadcast_global(self, message: Dict[str, Any]):
        """Broadcast message to all global connections."""
        print(f"[WebSocket Manager] Broadcasting to {len(self.global_connections)} global connections")
        if not self.global_connections:
            print("[WebSocket Manager] No global connections to broadcast to")
            return

        # Get a copy to avoid modification during iteration
        connection_ids = self.global_connections.copy()

        successful_sends = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                successful_sends += 1

        print(f"[WebSocket Manager] Broadcast global message: {successful_sends}/{len(connection_ids)} connections")
        logger.debug(f"Broadcast global message: {successful_sends}/{len(connection_ids)} connections")

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all active connections."""
        if not self.connections:
            return

        # Get a copy of all connection IDs
        connection_ids = list(self.connections.keys())

        successful_sends = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                successful_sends += 1

        logger.debug(f"Broadcast to all: {successful_sends}/{len(connection_ids)} connections")

    def get_connection_count(self) -> Dict[str, int]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "user_connections": len(self.user_connections),
            "global_connections": len(self.global_connections),
            "users_connected": len([user for user, conns in self.user_connections.items() if conns])
        }

    async def broadcast_to_task(self, task_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections associated with a specific task/export."""
        sent_count = 0

        # Find connections with matching export_id in metadata
        for connection_id, metadata in self.connection_metadata.items():
            if metadata.get("export_id") == task_id:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1

        logger.debug(f"Broadcast to task {task_id}: {sent_count} connections")
        return sent_count

    async def handle_websocket_disconnect(self, websocket: WebSocket, connection_id: str):
        """Handle WebSocket disconnect with proper cleanup."""
        try:
            await websocket.close()
        except:
            pass  # Connection might already be closed
        finally:
            await self.disconnect(connection_id)

    async def ping_connections(self):
        """Send ping to all connections to check if they're alive."""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Get a copy to avoid modification during iteration
        connection_ids = list(self.connections.keys())

        for connection_id in connection_ids:
            try:
                websocket = self.connections[connection_id]
                await websocket.ping()
            except Exception as e:
                logger.warning(f"Ping failed for {connection_id}: {e}")
                await self.disconnect(connection_id)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
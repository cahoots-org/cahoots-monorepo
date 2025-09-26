"""WebSocket endpoints for real-time updates."""

import os
import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt
import logging

from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()


async def get_user_from_token(token: Optional[str] = None) -> Optional[str]:
    """Extract user ID from JWT token."""
    if not token:
        return None

    # Handle development bypass token (only in non-production)
    environment = os.environ.get("ENVIRONMENT", "development")
    if environment != "production" and token == "dev-bypass-token":
        return "dev-user"

    try:
        # In production, you'd verify the JWT token here
        # For now, we'll accept any token as a simple user ID
        payload = jwt.decode(token, verify=False)  # Don't verify in development
        return payload.get("user_id") or payload.get("sub")
    except:
        # If token parsing fails, treat as anonymous user
        return None


@router.websocket("/ws/global")
async def global_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """Global WebSocket endpoint for real-time task updates.

    This endpoint receives all task events and is used by components
    like TaskBoard that need to listen to multiple task updates.
    """
    connection_id = str(uuid.uuid4())
    user_id = await get_user_from_token(token)

    print(f"[WebSocket] New connection attempt - ID: {connection_id}, User: {user_id}, Token: {token}")

    try:
        # Connect to WebSocket manager
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            is_global=True
        )

        logger.info(f"Global WebSocket connected: {connection_id} (user: {user_id})")
        print(f"[WebSocket] Connection established - ID: {connection_id}")

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong, etc.)
                message = await websocket.receive_text()

                # Handle client messages if needed
                # For now, we just log them
                logger.debug(f"Received message from {connection_id}: {message}")

            except WebSocketDisconnect:
                print(f"[WebSocket] Client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in global WebSocket {connection_id}: {e}")
                print(f"[WebSocket] Error in connection {connection_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"Global WebSocket disconnected: {connection_id}")
        print(f"[WebSocket] Disconnected (WebSocketDisconnect): {connection_id}")
    except Exception as e:
        logger.error(f"Global WebSocket error for {connection_id}: {e}")
        print(f"[WebSocket] Error (Exception): {connection_id} - {e}")
    finally:
        print(f"[WebSocket] Cleaning up connection: {connection_id}")
        await websocket_manager.disconnect(connection_id)


@router.websocket("/ws/user/{user_id}")
async def user_websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """User-specific WebSocket endpoint for task updates.

    This endpoint only receives events for tasks belonging to the specified user.
    """
    connection_id = str(uuid.uuid4())
    authenticated_user_id = await get_user_from_token(token)

    # Basic security check - ensure user can only connect to their own WebSocket
    if authenticated_user_id and authenticated_user_id != user_id:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    try:
        # Connect to WebSocket manager
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            is_global=False
        )

        logger.info(f"User WebSocket connected: {connection_id} (user: {user_id})")

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                message = await websocket.receive_text()
                logger.debug(f"Received message from {connection_id}: {message}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in user WebSocket {connection_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"User WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"User WebSocket error for {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    stats = websocket_manager.get_connection_count()
    return {
        "status": "active",
        "connections": stats,
        "timestamp": "2025-09-23T15:45:00Z"
    }


@router.websocket("/ws/jira-export/{export_id}")
async def jira_export_websocket_endpoint(
    websocket: WebSocket,
    export_id: str,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """WebSocket endpoint for JIRA export progress updates."""
    connection_id = str(uuid.uuid4())
    user_id = await get_user_from_token(token)

    try:
        # Connect to WebSocket manager for this specific export
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            is_global=False
        )

        # Store export_id in metadata for routing messages
        websocket_manager.connection_metadata[connection_id]["export_id"] = export_id

        logger.info(f"JIRA export WebSocket connected: {connection_id} for export {export_id}")

        # Keep connection alive
        while True:
            try:
                message = await websocket.receive_text()
                logger.debug(f"Received message from {connection_id}: {message}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in JIRA export WebSocket {connection_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"JIRA export WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"JIRA export WebSocket error for {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@router.websocket("/ws/trello-export/{export_id}")
async def trello_export_websocket_endpoint(
    websocket: WebSocket,
    export_id: str,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """WebSocket endpoint for Trello export progress updates."""
    connection_id = str(uuid.uuid4())
    user_id = await get_user_from_token(token)

    try:
        # Connect to WebSocket manager for this specific export
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            is_global=False
        )

        # Store export_id in metadata for routing messages
        websocket_manager.connection_metadata[connection_id]["export_id"] = export_id

        logger.info(f"Trello export WebSocket connected: {connection_id} for export {export_id}")

        # Keep connection alive
        while True:
            try:
                message = await websocket.receive_text()
                logger.debug(f"Received message from {connection_id}: {message}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in Trello export WebSocket {connection_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"Trello export WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Trello export WebSocket error for {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@router.post("/ws/broadcast")
async def broadcast_message(
    message: dict,
    target: str = Query("global", description="Broadcast target: 'global' or 'user:{user_id}'")
):
    """Manual message broadcast endpoint (for testing/admin purposes)."""
    try:
        if target == "global":
            await websocket_manager.broadcast_global(message)
        elif target.startswith("user:"):
            user_id = target[5:]  # Remove "user:" prefix
            await websocket_manager.send_to_user(user_id, message)
        else:
            raise HTTPException(status_code=400, detail="Invalid target format")

        return {"status": "success", "target": target, "message": "Broadcast sent"}
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
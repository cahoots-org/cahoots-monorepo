"""Event bus for real-time context updates."""
from typing import Dict, List, Any, Callable, Optional, Set
import asyncio
import logging
from datetime import datetime
import json
from uuid import UUID

from cahoots_core.exceptions.base import ErrorCategory, ErrorSeverity
from cahoots_core.utils.errors.handling import RecoveryStrategy
from cahoots_core.utils.infrastructure.redis.client import get_redis_client
from redis import Redis
from sqlalchemy.orm import Session

class ContextEventBus:
    """Event bus for real-time context updates with Redis pub/sub."""
    
    def __init__(
        self,
        db: Session,
        redis: Optional[Redis] = None,
        channel_prefix: str = "context_events"
    ):
        """Initialize the context event bus.
        
        Args:
            db: Database session
            redis: Optional Redis client (will create if not provided)
            channel_prefix: Prefix for Redis pub/sub channels
        """
        self.db = db
        self.redis = redis or get_redis_client()
        self.channel_prefix = channel_prefix
        self.logger = logging.getLogger(__name__)
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.is_running = False
        self.listener_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the event bus listener."""
        if self.is_running:
            return
            
        self.is_running = True
        self.listener_task = asyncio.create_task(self.listen_for_events())
        self.logger.info("Context event bus started")
        
    async def stop(self) -> None:
        """Stop the event bus listener."""
        self.is_running = False
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None
        self.logger.info("Context event bus stopped")
        
    async def publish(
        self,
        project_id: UUID,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Publish a context event.
        
        Args:
            project_id: Project ID
            event_type: Type of event
            event_data: Event data
        """
        try:
            channel = f"{self.channel_prefix}:{project_id}"
            message = {
                "project_id": str(project_id),
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish to Redis
            await self.redis.publish(channel, json.dumps(message))
            self.logger.debug(f"Published event to {channel}: {event_type}")
            
        except Exception as e:
            raise SystemError(
                message=f"Failed to publish context event: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY,
                original_error=e,
                context={
                    "project_id": str(project_id),
                    "event_type": event_type
                }
            )
            
    async def subscribe(
        self,
        project_id: UUID,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to context events for a project.
        
        Args:
            project_id: Project ID
            callback: Callback function to handle events
        """
        channel = f"{self.channel_prefix}:{project_id}"
        if channel not in self.subscribers:
            self.subscribers[channel] = set()
        self.subscribers[channel].add(callback)
        self.logger.debug(f"Added subscriber to {channel}")
        
    async def unsubscribe(
        self,
        project_id: UUID,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Unsubscribe from context events for a project.
        
        Args:
            project_id: Project ID
            callback: Callback function to remove
        """
        channel = f"{self.channel_prefix}:{project_id}"
        if channel in self.subscribers:
            self.subscribers[channel].discard(callback)
            if not self.subscribers[channel]:
                del self.subscribers[channel]
        self.logger.debug(f"Removed subscriber from {channel}")
        
    async def listen_for_events(self) -> None:
        """Listen for events on Redis pub/sub channels."""
        try:
            # Subscribe to all project channels
            pubsub = self.redis.pubsub()
            pattern = f"{self.channel_prefix}:*"
            await pubsub.psubscribe(pattern)
            
            self.logger.info(f"Listening for events on pattern: {pattern}")
            
            while self.is_running:
                try:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )
                    
                    if not message:
                        continue
                        
                    channel = message.get("channel", "").decode("utf-8")
                    data = json.loads(message.get("data", {}).decode("utf-8"))
                    
                    # Notify subscribers
                    if channel in self.subscribers:
                        for callback in self.subscribers[channel]:
                            try:
                                await callback(data)
                            except Exception as e:
                                self.logger.error(
                                    f"Error in event subscriber callback: {str(e)}"
                                )
                                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    self.logger.error(f"Error processing context event: {str(e)}")
                    await asyncio.sleep(1)  # Prevent tight error loop
                    
        except asyncio.CancelledError:
            self.logger.info("Context event listener cancelled")
        finally:
            await pubsub.punsubscribe(pattern)
            await pubsub.close() 
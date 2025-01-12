"""Event system implementation."""
from typing import Dict, Any, Callable, List, Optional
import json
from datetime import datetime
from redis.asyncio import Redis

class EventSystem:
    """Event system for asynchronous communication."""
    
    def __init__(self, redis: Redis):
        """Initialize event system.
        
        Args:
            redis: Redis client instance
        """
        self.redis = redis
        self._connected = False
        self._handlers = {}
        self._pubsub = None
        
    @property
    def is_connected(self) -> bool:
        """Check if event system is connected."""
        return self._connected
    
    async def verify_connection(self) -> bool:
        """Verify connection to Redis is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            await self.redis.ping()
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False
    
    async def connect(self) -> None:
        """Connect to Redis and initialize pubsub."""
        if await self.verify_connection():
            if not self._pubsub:
                self._pubsub = await self.redis.pubsub()
                await self._pubsub.ping()
    
    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Coroutine function to handle the event
        """
        if not self._connected:
            await self.connect()
            
        if not self._pubsub:
            self._pubsub = await self.redis.pubsub()
            await self._pubsub.ping()
            
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            await self._pubsub.subscribe(event_type)
            
        self._handlers[event_type].append(handler)
    
    async def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                
            if not self._handlers[event_type]:
                await self._pubsub.unsubscribe(event_type)
                del self._handlers[event_type]
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event.
        
        Args:
            event_type: Type of event to publish
            data: Event data
        """
        if not self._connected:
            await self.connect()
            
        # Store event in Redis with timestamp
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        event_key = f"events:{event_type}:{datetime.utcnow().timestamp()}"
        
        # Store event in Redis hash
        await self.redis.hset(
            name="events",
            key=event_key,
            value=json.dumps(event)
        )

        # Publish event
        await self.redis.publish(event_type, json.dumps(event))
    
    async def get_processed_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get processed events, optionally filtered by type.
        
        Args:
            event_type: Optional event type to filter by
            
        Returns:
            List of processed events
        """
        if not self._connected:
            await self.connect()
            
        # Get all events from hash
        events = []
        all_events = await self.redis.hgetall("events")
        
        # Parse and filter events
        for event_key, event_json in all_events.items():
            try:
                event = json.loads(event_json)
                if event_type is None or event.get("type") == event_type:
                    events.append(event)
            except json.JSONDecodeError:
                continue
        
        # Sort by timestamp
        return sorted(events, key=lambda x: x.get("timestamp", 0))
    
    async def close(self) -> None:
        """Close all connections."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
            
        self._connected = False
        self._handlers.clear() 
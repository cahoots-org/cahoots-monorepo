import json
import os
import asyncio
import aioredis
from typing import Callable, Dict, Any, Optional
from ..utils.logger import Logger

class EventSystem:
    def __init__(self):
        self.logger = Logger("EventSystem")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.pubsub = self.redis.pubsub()
            self.logger.info("Connected to Redis")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to a channel with a handler function"""
        if not self.redis:
            await self.connect()
        
        self.handlers[channel] = handler
        await self.pubsub.subscribe(channel)
        self.logger.info(f"Subscribed to channel: {channel}")

    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish data to a channel"""
        if not self.redis:
            await self.connect()
            
        message = json.dumps(data)
        await self.redis.publish(channel, message)
        self.logger.info(f"Published to channel {channel}: {message}")

    async def start_listening(self):
        """Start listening for messages"""
        if not self.redis:
            await self.connect()
            
        self.running = True
        try:
            while self.running:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message and message["type"] == "message":
                    channel = message["channel"].decode()
                    data = json.loads(message["data"].decode())
                    
                    if channel in self.handlers:
                        try:
                            await self.handlers[channel](data)
                        except Exception as e:
                            self.logger.error(f"Error in handler for channel {channel}: {str(e)}")
                            
                await asyncio.sleep(0.1)  # Prevent busy waiting
        except Exception as e:
            self.logger.error(f"Error in event loop: {str(e)}")
            raise

    async def stop(self):
        """Stop listening and clean up"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis:
            await self.redis.close()
            await self.redis.connection_pool.disconnect()

# Event channels
CHANNELS = {
    "STORY_ASSIGNED": "story_assigned",
    "STORY_IMPLEMENTED": "story_implemented",
    "PR_CREATED": "pr_created",
    "PR_MERGED": "pr_merged",
    "CODE_REVIEWED": "code_reviewed"
} 
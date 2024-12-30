import json
import os
import asyncio
import redis.asyncio as redis
from typing import Callable, Dict, Any, Optional
from ..utils.logger import Logger

# Define available channels
CHANNELS = {
    "system": "system",
    "project_manager": "project_manager",
    "developer": "developer",
    "ux_designer": "ux_designer",
    "tester": "tester",
    "story_assigned": "story_assigned",
    "pr_created": "pr_created",
    "pr_merged": "pr_merged",
    "task_completed": "task_completed"
}

class EventSystem:
    def __init__(self):
        self.logger = Logger("EventSystem")
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection, creating it if needed"""
        if not self.redis:
            try:
                redis_url = f"redis://{self.redis_host}:{self.redis_port}"
                self.redis = redis.from_url(redis_url)
                self.logger.info("Connected to Redis")
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
        return self.redis

    async def get_pubsub(self) -> redis.client.PubSub:
        """Get Redis pubsub connection, creating it if needed"""
        if not self.pubsub:
            redis_client = await self.get_redis()
            self.pubsub = redis_client.pubsub()
        return self.pubsub

    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to a channel with a handler function"""
        self.handlers[channel] = handler
        pubsub = await self.get_pubsub()
        await pubsub.subscribe(channel)
        self.logger.info(f"Subscribed to channel: {channel}")

    async def publish(self, channel: str, message: Any):
        """Publish a message to a channel"""
        redis_client = await self.get_redis()
        message_str = json.dumps(message)
        await redis_client.publish(channel, message_str)
        self.logger.info(f"Published message to channel: {channel}")

    async def start_listening(self):
        """Start listening for messages"""
        self.logger.debug("Starting listening method")
        if self.running:
            self.logger.debug("Already running, returning early")
            return

        self.running = True
        self.logger.debug("Getting pubsub connection")
        pubsub = await self.get_pubsub()
        self.logger.debug("Got pubsub connection")
        
        while self.running:
            self.logger.debug("Start of message loop")
            try:
                self.logger.debug("Getting message from pubsub")
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                self.logger.debug(f"Raw message from pubsub: {message!r}")
                
                if message:
                    self.logger.debug(f"Message type: {type(message)}")
                    self.logger.debug(f"Message content: {message!r}")
                    
                if message and isinstance(message, dict):
                    self.logger.debug("Message is a dict")
                    if 'data' in message:
                        self.logger.debug("Message has data field")
                        try:
                            # Get the message data and decode it from bytes
                            message_data = message['data']
                            self.logger.debug(f"Message data type: {type(message_data)}")
                            self.logger.debug(f"Message data content: {message_data!r}")
                            
                            if isinstance(message_data, bytes):
                                self.logger.debug("Decoding message data from bytes")
                                message_data = message_data.decode('utf-8')
                                self.logger.debug(f"Decoded message data: {message_data!r}")
                            
                            # Parse the JSON string
                            self.logger.debug("Parsing JSON string")
                            message_dict = json.loads(message_data)
                            self.logger.debug(f"Parsed message dict: {message_dict!r}")
                            
                            # Get the channel and call its handler
                            self.logger.debug("Getting channel from message")
                            channel = message.get('channel', b'').decode('utf-8')
                            self.logger.debug(f"Channel: {channel!r}")
                            
                            if channel in self.handlers:
                                self.logger.debug(f"Found handler for channel {channel}")
                                try:
                                    self.logger.debug("Calling handler")
                                    await self.handlers[channel](message_dict)
                                    self.logger.debug("Handler call completed")
                                except Exception as e:
                                    self.logger.error(f"Handler error for channel {channel}: {str(e)}")
                                    self.logger.error("Handler error stack trace:", exc_info=True)
                                    import traceback
                                    self.logger.error(f"Full stack trace:\n{''.join(traceback.format_tb(e.__traceback__))}")
                            else:
                                self.logger.debug(f"No handler found for channel {channel}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to decode JSON message: {str(e)}")
                            self.logger.error(f"Raw message data: {message_data!r}")
                            self.logger.error("JSON decode error stack trace:", exc_info=True)
                            import traceback
                            self.logger.error(f"Full stack trace:\n{''.join(traceback.format_tb(e.__traceback__))}")
                        except Exception as e:
                            self.logger.error(f"Error processing message: {str(e)}")
                            self.logger.error(f"Message content: {message!r}")
                            self.logger.error("Message processing error stack trace:", exc_info=True)
                            import traceback
                            self.logger.error(f"Full stack trace:\n{''.join(traceback.format_tb(e.__traceback__))}")
                    else:
                        self.logger.debug("Message dict does not have data field")
                else:
                    self.logger.debug("Message is not a dict or is None")
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                self.logger.error("Main loop error stack trace:", exc_info=True)
                import traceback
                self.logger.error(f"Full stack trace:\n{''.join(traceback.format_tb(e.__traceback__))}")
                await asyncio.sleep(1)  # Avoid tight loop on persistent errors
            
            self.logger.debug("End of message loop iteration")
            await asyncio.sleep(0.1)  # Avoid tight loop when no messages

    async def stop_listening(self):
        """Stop listening for messages"""
        self.running = False
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None 

    async def connect(self):
        """Connect to Redis"""
        await self.get_redis() 
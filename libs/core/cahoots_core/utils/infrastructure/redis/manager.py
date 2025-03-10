"""Redis connection manager."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from cahoots_core.exceptions import InfrastructureError
from cahoots_core.utils.config import Config
from cahoots_core.utils.infrastructure.redis.client import get_redis_client


class RedisManager:
    """Manager for Redis connections."""

    def __init__(self, config: Config):
        """Initialize Redis manager.

        Args:
            config: Configuration containing Redis settings
        """
        self.config = config
        self._client: Optional[Redis] = None
        self._namespace_clients: Dict[str, Redis] = {}
        self._pubsub_clients: Dict[str, PubSub] = {}

    def _get_namespace_pattern(self, project_id: str) -> str:
        """Get Redis key pattern for project namespace.

        Args:
            project_id: Project ID

        Returns:
            Redis key pattern
        """
        return f"project:{project_id}:*"

    async def create_namespace(self, project_id: str) -> bool:
        """Create a new namespace for project.

        Args:
            project_id: Project ID

        Returns:
            True if created successfully, False otherwise
        """
        try:
            # Create namespace metadata
            namespace = f"project:{project_id}"
            metadata = {
                "created_at": int(datetime.now(timezone.UTC).timestamp()),
                "status": "active",
            }

            # Store namespace metadata
            await self._client.set(f"{namespace}:metadata", json.dumps(metadata))

            return True

        except Exception as e:
            print(f"Error creating namespace: {e}")
            return False

    async def initialize_namespace(self, project_id: str) -> bool:
        """Initialize namespace with required keys.

        Args:
            project_id: Project ID

        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            namespace = f"project:{project_id}"

            # Initialize required keys
            defaults = {
                f"{namespace}:config": json.dumps({}),
                f"{namespace}:metrics": json.dumps({}),
                f"{namespace}:events:sequence": "0",
            }

            # Use pipeline for atomic initialization
            async with self._client.pipeline(transaction=True) as pipe:
                for key, value in defaults.items():
                    pipe.set(key, value, nx=True)
                await pipe.execute()

            return True

        except Exception as e:
            print(f"Error initializing namespace: {e}")
            return False

    async def cleanup_namespace(self, project_id: str) -> bool:
        """Clean up project namespace.

        Args:
            project_id: Project ID

        Returns:
            True if cleaned up successfully, False otherwise
        """
        try:
            # Get all keys in namespace
            pattern = self._get_namespace_pattern(project_id)
            keys = await self._client.keys(pattern)

            if keys:
                # Delete all keys in namespace
                await self._client.delete(*keys)

            # Remove cached clients
            namespace = f"project:{project_id}"
            if namespace in self._namespace_clients:
                client = self._namespace_clients.pop(namespace)
                await client.close()
            if namespace in self._pubsub_clients:
                pubsub = self._pubsub_clients.pop(namespace)
                await pubsub.close()

            return True

        except Exception as e:
            print(f"Error cleaning up namespace: {e}")
            return False

    async def get_client(self) -> Redis:
        """Get Redis client.

        Returns:
            Redis: Configured Redis client

        Raises:
            InfrastructureError: If connection fails
        """
        if not self._client:
            try:
                self._client = get_redis_client()
                await self._client.ping()  # Verify connection
            except Exception as e:
                raise InfrastructureError(f"Failed to connect to Redis: {str(e)}")

        return self._client

    async def get_pubsub(self, project_id: str) -> PubSub:
        """Get PubSub client for project namespace.

        Args:
            project_id: Project ID

        Returns:
            PubSub client configured for project namespace
        """
        namespace = f"project:{project_id}"

        # Return cached client if exists
        if namespace in self._pubsub_clients:
            return self._pubsub_clients[namespace]

        # Create new PubSub client
        client = await self.get_client()
        pubsub = client.pubsub()

        self._pubsub_clients[namespace] = pubsub
        return pubsub

    async def get_keys(self, project_id: str) -> List[str]:
        """Get all keys in project namespace.

        Args:
            project_id: Project ID

        Returns:
            List of keys in namespace
        """
        pattern = self._get_namespace_pattern(project_id)
        return await self._client.keys(pattern)

    async def get_size(self, project_id: str) -> int:
        """Get size of project namespace in bytes.

        Args:
            project_id: Project ID

        Returns:
            Size in bytes
        """
        keys = await self.get_keys(project_id)
        if not keys:
            return 0

        # Get memory usage for all keys
        total = 0
        for key in keys:
            memory = await self._client.memory_usage(key)
            if memory:
                total += memory

        return total

    async def get_active_channels(self, project_id: str) -> Set[str]:
        """Get active channels in project namespace.

        Args:
            project_id: Project ID

        Returns:
            Set of active channel names
        """
        namespace = f"project:{project_id}"
        pubsub_channels = await self._client.pubsub_channels(f"{namespace}:*")
        return {channel.decode() for channel in pubsub_channels}

    async def cleanup(self):
        """Cleanup Redis manager resources."""
        # Close all namespace clients
        for client in self._namespace_clients.values():
            await client.close()
        self._namespace_clients.clear()

        # Close all pubsub clients
        for pubsub in self._pubsub_clients.values():
            await pubsub.close()
        self._pubsub_clients.clear()

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

"""User Settings storage operations using Redis."""

from typing import Optional
from datetime import datetime, timezone
import json

from app.models.user_settings import UserSettings
from .redis_client import RedisClient


class UserSettingsStorage:
    """Storage layer for user settings operations."""

    def __init__(self, redis_client: RedisClient):
        """Initialize user settings storage.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.settings_prefix = "user_settings:"

    def _settings_key(self, user_id: str) -> str:
        """Generate Redis key for user settings."""
        return f"{self.settings_prefix}{user_id}"

    async def save_settings(self, settings: UserSettings) -> bool:
        """Save user settings to Redis.

        Args:
            settings: UserSettings instance to save

        Returns:
            True if successful
        """
        settings.updated_at = datetime.now(timezone.utc)
        key = self._settings_key(settings.user_id)

        # Convert to dict for JSON serialization
        settings_dict = settings.to_dict()

        # Save to Redis (no expiration - persist indefinitely)
        success = await self.redis.set(key, settings_dict)

        return success

    async def get_settings(self, user_id: str) -> Optional[UserSettings]:
        """Get user settings by user ID.

        Args:
            user_id: User ID

        Returns:
            UserSettings or None if not found
        """
        key = self._settings_key(user_id)
        data = await self.redis.get(key)

        if data:
            # Redis client returns dict if decode_responses=True
            if isinstance(data, dict):
                return UserSettings.from_dict(data)
            # Fallback: parse JSON string
            elif isinstance(data, str):
                return UserSettings.from_dict(json.loads(data))

        return None

    async def delete_settings(self, user_id: str) -> bool:
        """Delete user settings.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        key = self._settings_key(user_id)
        result = await self.redis.delete(key)
        return result > 0

    async def update_partial(self, user_id: str, updates: dict) -> Optional[UserSettings]:
        """Partially update user settings.

        Args:
            user_id: User ID
            updates: Dictionary of fields to update

        Returns:
            Updated UserSettings or None if user settings not found
        """
        # Get existing settings
        existing = await self.get_settings(user_id)

        if not existing:
            # Create new settings if they don't exist
            existing = UserSettings(user_id=user_id)

        # Apply updates
        for field, value in updates.items():
            if hasattr(existing, field):
                setattr(existing, field, value)

        # Save updated settings
        await self.save_settings(existing)

        return existing

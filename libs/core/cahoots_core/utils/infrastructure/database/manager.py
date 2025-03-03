"""Database connection manager."""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.exceptions import InfrastructureError
from cahoots_core.utils.config import Config
from cahoots_core.utils.infrastructure.database.client import get_db_client


class DatabaseManager:
    """Manager for database connections."""

    def __init__(self, config: Config):
        """Initialize database manager.

        Args:
            config: Configuration containing database settings
        """
        self.config = config
        self._client = get_db_client()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session.

        Yields:
            Database session

        Raises:
            InfrastructureError: If connection fails
        """
        try:
            async with self._client.get_async_session() as session:
                yield session
        except Exception as e:
            raise InfrastructureError(f"Failed to get database session: {str(e)}")

    async def close(self) -> None:
        """Close database connection."""
        if self._client:
            await self._client.close()

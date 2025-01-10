"""Database session management."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from src.config import get_settings

# Create async engine
engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    future=True,
    pool_pre_ping=True
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.
    
    Yields:
        Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close() 
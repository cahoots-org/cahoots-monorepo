"""Database client for managing database connections and operations."""
from typing import Optional, Dict, Any, Generator, AsyncGenerator
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

class DatabaseClientError(Exception):
    """Base exception for database client errors."""
    pass

class ConnectionError(DatabaseClientError):
    """Exception raised for database connection errors."""
    pass

class OperationError(DatabaseClientError):
    """Exception raised for database operation errors."""
    pass

class DatabaseClient:
    """Client for managing database connections and operations."""
    
    def __init__(
        self,
        url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool = False
    ):
        """Initialize the database client.
        
        Args:
            url: Database URL (sync or async)
            pool_size: Connection pool size
            max_overflow: Maximum number of connections to allow above pool_size
            pool_timeout: Number of seconds to wait before giving up on getting a connection
            pool_recycle: Number of seconds after which to recycle connections
            echo: Whether to log SQL queries
        """
        self.url = url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        
        # Initialize engines and session factories
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_session_factory = None
        self._async_session_factory = None
        
    def _create_sync_engine(self) -> Engine:
        """Create synchronous SQLAlchemy engine."""
        if not self._sync_engine:
            try:
                self._sync_engine = create_engine(
                    self.url,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    echo=self.echo
                )
                self._sync_session_factory = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self._sync_engine
                )
            except Exception as e:
                logger.error(f"Failed to create sync engine: {str(e)}")
                raise ConnectionError(f"Failed to create sync engine: {str(e)}")
                
        return self._sync_engine
        
    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous SQLAlchemy engine."""
        if not self._async_engine:
            try:
                self._async_engine = create_async_engine(
                    self.url,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    echo=self.echo
                )
                self._async_session_factory = sessionmaker(
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False,
                    bind=self._async_engine
                )
            except Exception as e:
                logger.error(f"Failed to create async engine: {str(e)}")
                raise ConnectionError(f"Failed to create async engine: {str(e)}")
                
        return self._async_engine
        
    def get_sync_session(self) -> Generator[Session, None, None]:
        """Get synchronous database session.
        
        Yields:
            Database session
            
        Raises:
            ConnectionError: If session creation fails
        """
        if not self._sync_engine:
            self._create_sync_engine()
            
        session = self._sync_session_factory()
        try:
            yield session
        finally:
            session.close()
            
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get asynchronous database session.
        
        Yields:
            Database session
            
        Raises:
            ConnectionError: If session creation fails
        """
        if not self._async_engine:
            self._create_async_engine()
            
        async with self._async_session_factory() as session:
            yield session
            
    async def close(self):
        """Close database connections."""
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
            
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            
    async def verify_connection(self) -> bool:
        """Verify database connection is active.
        
        Returns:
            True if connected, False otherwise
            
        Raises:
            ConnectionError: If connection verification fails
        """
        try:
            if self._async_engine:
                async with self._async_engine.connect() as conn:
                    await conn.execute("SELECT 1")
            elif self._sync_engine:
                with self._sync_engine.connect() as conn:
                    conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection verification failed: {str(e)}")
            raise ConnectionError(f"Database connection verification failed: {str(e)}")

# Global client instance
_db_client: Optional[DatabaseClient] = None

def get_db_client(
    url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    echo: bool = False
) -> DatabaseClient:
    """Get or create the global database client instance.
    
    Args:
        url: Database URL (sync or async)
        pool_size: Connection pool size
        max_overflow: Maximum number of connections to allow above pool_size
        pool_timeout: Number of seconds to wait before giving up on getting a connection
        pool_recycle: Number of seconds after which to recycle connections
        echo: Whether to log SQL queries
        
    Returns:
        DatabaseClient instance
    """
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo
        )
    return _db_client 
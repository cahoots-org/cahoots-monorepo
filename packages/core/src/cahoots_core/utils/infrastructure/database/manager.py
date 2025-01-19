"""Database schema management."""
from typing import Optional, Dict
import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL

from src.config import get_settings
from src.utils.infrastructure import get_db_client

class DatabaseManager:
    """Manages project-specific database schemas."""

    def __init__(self):
        """Initialize database manager."""
        self.settings = get_settings()
        self.db = get_db_client()
        self._schema_engines: Dict[str, AsyncEngine] = {}

    async def create_schema(self, project_id: str) -> bool:
        """Create a new schema for project.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if created successfully, False otherwise
        """
        schema_name = f"project_{project_id}"
        
        try:
            # Connect directly with asyncpg for schema management
            conn = await asyncpg.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                database=self.settings.db_name
            )
            
            # Create schema if it doesn't exist
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            
            # Grant usage to application user
            await conn.execute(f'GRANT USAGE ON SCHEMA "{schema_name}" TO {self.settings.db_user}')
            await conn.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" TO {self.settings.db_user}')
            await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT ALL ON TABLES TO {self.settings.db_user}')
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"Error creating schema: {e}")
            return False

    async def initialize_schema(self, project_id: str) -> bool:
        """Initialize schema with required tables.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if initialized successfully, False otherwise
        """
        schema_name = f"project_{project_id}"
        
        try:
            # Create engine for schema
            engine = await self.get_engine(project_id)
            
            # Create all tables in schema
            async with engine.begin() as conn:
                await conn.run_sync(self.db.Base.metadata.create_all)
            
            return True
            
        except Exception as e:
            print(f"Error initializing schema: {e}")
            return False

    async def archive_schema(self, project_id: str) -> bool:
        """Archive project schema.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if archived successfully, False otherwise
        """
        schema_name = f"project_{project_id}"
        archive_name = f"archived_{schema_name}_{int(datetime.utcnow().timestamp())}"
        
        try:
            conn = await asyncpg.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                database=self.settings.db_name
            )
            
            # Rename schema to archived name
            await conn.execute(f'ALTER SCHEMA "{schema_name}" RENAME TO "{archive_name}"')
            
            # Revoke access to archived schema
            await conn.execute(f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{archive_name}" FROM {self.settings.db_user}')
            await conn.execute(f'REVOKE USAGE ON SCHEMA "{archive_name}" FROM {self.settings.db_user}')
            
            await conn.close()
            
            # Remove cached engine
            if schema_name in self._schema_engines:
                engine = self._schema_engines.pop(schema_name)
                await engine.dispose()
            
            return True
            
        except Exception as e:
            print(f"Error archiving schema: {e}")
            return False

    async def get_engine(self, project_id: str) -> AsyncEngine:
        """Get SQLAlchemy engine for project schema.
        
        Args:
            project_id: Project ID
            
        Returns:
            AsyncEngine configured for project schema
        """
        schema_name = f"project_{project_id}"
        
        # Return cached engine if exists
        if schema_name in self._schema_engines:
            return self._schema_engines[schema_name]
        
        # Create new engine with schema
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.settings.db_user,
            password=self.settings.db_password,
            host=self.settings.db_host,
            port=self.settings.db_port,
            database=self.settings.db_name,
            query={"options": f"-csearch_path={schema_name}"}
        )
        
        engine = create_async_engine(url, pool_size=5, max_overflow=10)
        self._schema_engines[schema_name] = engine
        return engine

    async def cleanup(self):
        """Cleanup database manager resources."""
        for engine in self._schema_engines.values():
            await engine.dispose()
        self._schema_engines.clear() 

    async def get_schema_size(self, project_id: str) -> int:
        """Get size of project schema in bytes.
        
        Args:
            project_id: Project ID
            
        Returns:
            Size in bytes
        """
        schema_name = f"project_{project_id}"
        
        try:
            conn = await asyncpg.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                database=self.settings.db_name
            )
            
            # Query schema size
            result = await conn.fetchval("""
                SELECT SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))
                FROM pg_tables
                WHERE schemaname = $1
            """, schema_name)
            
            await conn.close()
            return result or 0
            
        except Exception as e:
            print(f"Error getting schema size: {e}")
            return 0 
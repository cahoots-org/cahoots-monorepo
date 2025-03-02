"""Database migrations manager."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations programmatically."""

    def __init__(self, db_url: str, migrations_dir: str = "migrations"):
        """Initialize migration manager.

        Args:
            db_url: Database connection URL
            migrations_dir: Directory containing migrations
        """
        self.db_url = db_url
        self.migrations_dir = migrations_dir
        self.engine = create_engine(db_url)
        self.alembic_cfg = self._create_alembic_config()

    def _create_alembic_config(self) -> Config:
        """Create Alembic config object."""
        # Get the directory containing this file
        current_dir = Path(__file__).resolve().parent

        # Navigate to the API root directory
        api_dir = current_dir.parent.parent

        # Create Alembic config
        config = Config()
        config.set_main_option("script_location", str(api_dir / self.migrations_dir))
        config.set_main_option("sqlalchemy.url", self.db_url)

        return config

    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            with self.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    def get_available_migrations(self) -> List[Dict[str, Any]]:
        """Get list of available migrations."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            migrations = []

            for revision in script_dir.walk_revisions():
                migrations.append(
                    {
                        "revision": revision.revision,
                        "down_revision": revision.down_revision,
                        "description": revision.doc,
                        "created_date": datetime.fromtimestamp(revision.module.ts),
                        "module": revision.module.__name__,
                    }
                )

            return sorted(migrations, key=lambda x: x["created_date"])
        except Exception as e:
            logger.error(f"Failed to get available migrations: {e}")
            return []

    def create_migration(self, message: str, autogenerate: bool = True) -> Optional[str]:
        """Create a new migration.

        Args:
            message: Migration description
            autogenerate: Whether to autogenerate migration from models

        Returns:
            The revision ID if successful, None otherwise
        """
        try:
            # Ensure migrations directory exists
            migrations_path = Path(self.alembic_cfg.get_main_option("script_location"))
            versions_path = migrations_path / "versions"
            versions_path.mkdir(parents=True, exist_ok=True)

            # Create revision
            rev = command.revision(self.alembic_cfg, message, autogenerate=autogenerate)

            logger.info(f"Created migration {rev.revision}: {message}")
            return rev.revision
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            return None

    def upgrade(self, target: str = "head") -> bool:
        """Upgrade database to target revision.

        Args:
            target: Target revision (default: "head")

        Returns:
            True if successful, False otherwise
        """
        try:
            command.upgrade(self.alembic_cfg, target)
            current = self.get_current_revision()
            logger.info(f"Upgraded database to revision {current}")
            return True
        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            return False

    def downgrade(self, target: str) -> bool:
        """Downgrade database to target revision.

        Args:
            target: Target revision

        Returns:
            True if successful, False otherwise
        """
        try:
            command.downgrade(self.alembic_cfg, target)
            current = self.get_current_revision()
            logger.info(f"Downgraded database to revision {current}")
            return True
        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            return False

    def check_migration_status(self) -> Dict[str, Any]:
        """Check migration status.

        Returns:
            Dictionary containing migration status information
        """
        try:
            current = self.get_current_revision()
            available = self.get_available_migrations()

            # Find current migration in available list
            current_index = next(
                (i for i, m in enumerate(available) if m["revision"] == current), -1
            )

            return {
                "current_revision": current,
                "available_migrations": len(available),
                "pending_migrations": len(available) - (current_index + 1),
                "is_latest": current_index == len(available) - 1,
                "needs_upgrade": current_index < len(available) - 1,
            }
        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return {
                "error": str(e),
                "current_revision": None,
                "available_migrations": 0,
                "pending_migrations": 0,
                "is_latest": False,
                "needs_upgrade": False,
            }

    def verify_database(self) -> bool:
        """Verify database connection and migration table exists."""
        try:
            with self.engine.connect() as conn:
                # Check if we can connect
                conn.execute(text("SELECT 1"))

                # Check if alembic_version table exists
                result = conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version'"
                        ")"
                    )
                )
                has_version_table = result.scalar()

                if not has_version_table:
                    logger.warning("alembic_version table not found")
                    return False

                return True
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False

"""Project management service."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from schemas.projects import ProjectCreate, ProjectUpdate
from utils.config import ServiceConfig

from cahoots_core.models.db_models import Project
from cahoots_core.services.github_service import GitHubService
from cahoots_core.utils.infrastructure.database.manager import DatabaseManager
from cahoots_core.utils.infrastructure.k8s.client import KubernetesClient
from cahoots_core.utils.infrastructure.redis.manager import RedisManager

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing projects."""

    def __init__(
        self,
        settings: ServiceConfig,
        db_manager: DatabaseManager,
        redis_manager: RedisManager,
        k8s_client: KubernetesClient,
        github_service: GitHubService,
    ):
        """Initialize project service."""
        self.settings = settings
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.k8s_client = k8s_client
        self.github_service = github_service

    async def create_project(
        self, organization_id: UUID, project_data: ProjectCreate, user_id: UUID
    ) -> Project:
        """Create a new project."""
        try:
            # Validate resource limits
            await self._validate_resource_limits(project_data.resource_limits)

            # Initialize project resources
            project_id = UUID()
            namespace = f"project-{project_id}"
            redis_ns = f"project:{project_id}"
            db_schema = f"project_{project_id}"

            # Create Kubernetes namespace and resources
            await self.k8s_client.create_namespace(
                name=namespace,
                labels={
                    "resource-type": "project",
                    "organization-id": str(organization_id),
                    "project-id": str(project_id),
                },
            )
            await self.k8s_client.create_resource_quota(
                namespace=namespace,
                cpu=project_data.resource_limits["cpu"],
                memory=project_data.resource_limits["memory"],
            )

            # Initialize Redis namespace
            await self.redis_manager.create_namespace(redis_ns)
            await self.redis_manager.initialize_namespace(redis_ns)

            # Initialize database schema
            await self.db_manager.create_schema(db_schema)
            await self.db_manager.initialize_schema(db_schema)

            # Create GitHub repository if needed
            repo = None
            if project_data.agent_config:
                repo = await self.github_service.create_repository(
                    name=project_data.name, organization=str(organization_id), private=True
                )

            # Create project links
            links = {
                "self": f"{self.settings.api_base_url}/projects/{project_id}",
                "github_repo": repo.html_url if repo else "",
                "monitoring": f"{self.settings.api_base_url}/projects/{project_id}/monitoring",
                "logs": f"{self.settings.api_base_url}/projects/{project_id}/logs",
            }

            # Create project
            project = Project(
                id=project_id,
                organization_id=organization_id,
                name=project_data.name,
                description=project_data.description,
                agent_config=project_data.agent_config,
                resource_limits=project_data.resource_limits,
                status="ready",
                progress=100.0,
                links=links,
            )

            return project

        except Exception as e:
            logger.error(f"Failed to create project: {str(e)}")
            await self._cleanup_resources(project_id)
            raise

    async def update_project(
        self, project_id: UUID, update_data: ProjectUpdate, user_id: UUID
    ) -> Project:
        """Update a project."""
        try:
            # Get existing project
            project = await self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Update fields
            if update_data.name is not None:
                project.name = update_data.name
            if update_data.description is not None:
                project.description = update_data.description
            if update_data.agent_config is not None:
                project.agent_config = update_data.agent_config
            if update_data.resource_limits is not None:
                await self._validate_resource_limits(update_data.resource_limits)
                project.resource_limits = update_data.resource_limits

                # Update Kubernetes resources
                namespace = f"project-{project_id}"
                await self.k8s_client.update_resource_quota(
                    namespace=namespace,
                    cpu=update_data.resource_limits["cpu"],
                    memory=update_data.resource_limits["memory"],
                )

            return project

        except Exception as e:
            logger.error(f"Failed to update project: {str(e)}")
            raise

    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        """Delete a project."""
        try:
            # Get project
            project = await self.get_project(project_id)
            if not project:
                return True

            # Clean up resources
            await self._cleanup_resources(project_id)

            return True

        except Exception as e:
            logger.error(f"Failed to delete project: {str(e)}")
            raise

    async def get_project(self, project_id: UUID) -> Optional[Project]:
        """Get a project by ID."""
        try:
            # Get project from database
            # For now, return None as we haven't implemented persistence
            return None

        except Exception as e:
            logger.error(f"Failed to get project: {str(e)}")
            raise

    async def _validate_resource_limits(self, limits: dict) -> None:
        """Validate resource limits."""
        if not limits:
            return

        cpu = limits.get("cpu")
        memory = limits.get("memory")
        pods = limits.get("pods")

        if cpu and float(cpu.rstrip("m")) <= 0:
            raise ValueError("CPU limit must be positive")

        if memory and not any(memory.endswith(unit) for unit in ["Ki", "Mi", "Gi"]):
            raise ValueError("Memory limit must use Ki, Mi, or Gi units")

        if pods and int(pods) <= 0:
            raise ValueError("Pod limit must be positive")

    async def _cleanup_resources(self, project_id: UUID) -> None:
        """Clean up project resources."""
        try:
            namespace = f"project-{project_id}"
            redis_ns = f"project:{project_id}"
            db_schema = f"project_{project_id}"

            # Delete Kubernetes resources
            await self.k8s_client.delete_namespace(namespace)

            # Clean up Redis namespace
            await self.redis_manager.cleanup_namespace(redis_ns)

            # Clean up database schema
            await self.db_manager.archive_schema(db_schema)

        except Exception as e:
            logger.error(f"Failed to clean up resources: {str(e)}")
            raise

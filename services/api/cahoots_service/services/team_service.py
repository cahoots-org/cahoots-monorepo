"""Team management service."""
from typing import Optional, List
from uuid import UUID
import logging
from fastapi import HTTPException

from cahoots_core.models.db_models import Team, TeamMember
from cahoots_core.models.team_config import TeamConfig, ServiceRole, RoleConfig, ProjectLimits
from cahoots_core.utils.infrastructure.k8s.client import KubernetesClient
from cahoots_service.api.dependencies import ServiceDeps

logger = logging.getLogger(__name__)

class TeamService:
    """Service for managing teams."""
    
    def __init__(self, deps: ServiceDeps):
        """Initialize team service.
        
        Args:
            deps: Service dependencies
        """
        self.deps = deps
        
    async def create_team(
        self,
        name: str,
        description: Optional[str] = None,
        roles: Optional[dict] = None,
        limits: Optional[dict] = None
    ) -> TeamConfig:
        """Create a new team.
        
        Args:
            name: Team name
            description: Team description
            roles: Team roles configuration
            limits: Team resource limits
            
        Returns:
            Created team configuration
        """
        try:
            # Generate team ID
            team_id = str(UUID())
            
            # Set default roles if none provided
            if not roles:
                roles = {
                    "admin": RoleConfig(
                        role=ServiceRole.ADMIN,
                        permissions={
                            "manage_team": True,
                            "manage_projects": True,
                            "manage_members": True
                        }
                    ),
                    "member": RoleConfig(
                        role=ServiceRole.MEMBER,
                        permissions={
                            "manage_projects": True,
                            "manage_members": False
                        }
                    ),
                    "viewer": RoleConfig(
                        role=ServiceRole.VIEWER,
                        permissions={
                            "view_only": True
                        }
                    )
                }
            
            # Set default limits if none provided
            if not limits:
                limits = ProjectLimits()
            
            # Create team config
            team_config = TeamConfig(
                team_id=team_id,
                name=name,
                description=description,
                roles=roles,
                limits=limits,
                is_active=True
            )
            
            # Store in database
            await self.deps.db_manager.create_team(team_config)
            
            return team_config
            
        except Exception as e:
            logger.error(f"Failed to create team: {str(e)}")
            raise
            
    async def get_team(self, team_id: str) -> Optional[TeamConfig]:
        """Get team configuration.
        
        Args:
            team_id: Team ID
            
        Returns:
            Team configuration if found
        """
        try:
            # Try to get from cache first
            cached = await self.deps.redis.get(f"team:{team_id}")
            if cached:
                return TeamConfig.model_validate_json(cached)
            
            # Get from database
            team = await self.deps.db_manager.get_team(team_id)
            if team:
                # Cache the result
                await self.deps.redis.set(
                    f"team:{team_id}",
                    team.model_dump_json(),
                    expire=3600
                )
            return team
        except Exception as e:
            logger.error(f"Failed to get team: {e}")
            raise
            
    async def update_team(
        self,
        team_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        roles: Optional[dict] = None,
        limits: Optional[dict] = None
    ) -> Optional[TeamConfig]:
        """Update team configuration.
        
        Args:
            team_id: Team ID
            name: New team name
            description: New team description
            roles: New team roles
            limits: New resource limits
            
        Returns:
            Updated team configuration
        """
        try:
            team = await self.get_team(team_id)
            if not team:
                return None
                
            if name:
                team.name = name
            if description:
                team.description = description
            if roles:
                team.roles = roles
            if limits:
                team.limits = limits
                
            await self.deps.db_manager.update_team(team)
            return team
            
        except Exception as e:
            logger.error(f"Failed to update team: {str(e)}")
            raise
            
    async def delete_team(self, team_id: str) -> bool:
        """Delete a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            True if deleted successfully
        """
        try:
            return await self.deps.db_manager.delete_team(team_id)
        except Exception as e:
            logger.error(f"Failed to delete team: {str(e)}")
            raise

    async def update_team_config(self, config: TeamConfig) -> TeamConfig:
        """Update team configuration."""
        try:
            # Validate limits
            project_limits = await self._get_project_limits()
            if not self._validate_limits(config.limits, project_limits):
                raise HTTPException(
                    status_code=400,
                    detail="Team configuration exceeds project limits"
                )
            
            # Update in database
            updated = await self.deps.db_manager.update_team(config)
            
            # Update cache
            await self.deps.redis.set(
                f"team:{config.team_id}",
                updated.model_dump_json(),
                expire=3600
            )
            
            return updated
        except Exception as e:
            logger.error(f"Failed to update team config: {e}")
            raise

    async def update_role_config(
        self,
        role: ServiceRole,
        config: RoleConfig,
        team_id: str
    ) -> TeamConfig:
        """Update configuration for a specific role."""
        try:
            team = await self.get_team(team_id)
            if not team:
                raise HTTPException(
                    status_code=404,
                    detail="Team not found"
                )
            
            team.roles[role] = config
            return await self.update_team_config(team)
        except Exception as e:
            logger.error(f"Failed to update role config: {e}")
            raise

    async def scale_role_instances(
        self,
        role: ServiceRole,
        instances: int
    ) -> None:
        """Scale the number of instances for a role."""
        try:
            # Get current deployment
            deployment = await self.deps.k8s.get_deployment(role.value)
            
            # Update replicas
            await self.deps.k8s.scale_deployment(
                deployment.metadata.name,
                instances
            )
        except Exception as e:
            logger.error(f"Failed to scale role instances: {e}")
            raise

    def _validate_limits(
        self,
        team_limits: ProjectLimits,
        project_limits: ProjectLimits
    ) -> bool:
        """Validate team limits against project limits."""
        return (
            team_limits.max_projects <= project_limits.max_projects and
            team_limits.max_users <= project_limits.max_users and
            team_limits.max_storage_gb <= project_limits.max_storage_gb and
            team_limits.max_compute_units <= project_limits.max_compute_units
        )

    async def _get_project_limits(self) -> ProjectLimits:
        """Get project-wide limits."""
        # This would typically come from a configuration or database
        return ProjectLimits(
            max_projects=100,
            max_users=500,
            max_storage_gb=1000,
            max_compute_units=10000
        ) 
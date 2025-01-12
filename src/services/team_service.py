"""Team service for managing team configurations."""
from typing import Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import time

from src.models.team_config import TeamConfig, ServiceRole, RoleConfig, ProjectLimits
from src.utils.k8s import KubernetesClient
from src.core.dependencies import ServiceDeps

class TeamService:
    """Service for managing team configurations."""
    
    def __init__(self, deps: ServiceDeps, project_id: str):
        """Initialize team service.
        
        Args:
            deps: Service dependencies
            project_id: Project ID
        """
        self.db = deps.db
        self.redis = deps.redis
        self.k8s = deps.k8s
        self.project_id = project_id
        
    async def get_team_config(self) -> TeamConfig:
        """Retrieve the current team configuration."""
        config_key = f"team_config:{self.project_id}"
        cached_config = await self.redis.get(config_key)
        
        if cached_config:
            return TeamConfig.model_validate_json(cached_config)
            
        # If not in cache, load from database
        config = await self._load_config_from_db()
        if not config:
            # Create default configuration
            config = TeamConfig(project_id=self.project_id)
            
        await self.redis.set(config_key, config.model_dump_json())
        return config
    
    async def update_team_config(self, new_config: TeamConfig) -> TeamConfig:
        """Update the team configuration."""
        # Validate against project limits
        limits = await self._get_project_limits()
        self._validate_config_against_limits(new_config, limits)
        
        # Update configuration
        config_key = f"team_config:{self.project_id}"
        await self.redis.set(config_key, new_config.model_dump_json())
        await self._save_config_to_db(new_config)
        
        return new_config
    
    async def update_role_config(self, role: ServiceRole, config: RoleConfig) -> TeamConfig:
        """Update configuration for a specific role."""
        team_config = await self.get_team_config()
        team_config.roles[role] = config
        return await self.update_team_config(team_config)
    
    async def _get_project_limits(self) -> ProjectLimits:
        """Get the project's service limits based on subscription/tier."""
        # TODO: Implement actual limit retrieval based on subscription
        return ProjectLimits()
    
    def _validate_config_against_limits(self, config: TeamConfig, limits: ProjectLimits):
        """Validate configuration against project limits."""
        if len(config.roles) > limits.max_roles:
            raise HTTPException(status_code=400, detail=f"Exceeds maximum allowed roles ({limits.max_roles})")
            
        total_instances = sum(role.instances for role in config.roles.values())
        if total_instances > limits.max_total_instances:
            raise HTTPException(status_code=400, 
                              detail=f"Exceeds maximum total instances ({limits.max_total_instances})")
            
        for role, role_config in config.roles.items():
            if role not in limits.allowed_roles:
                raise HTTPException(status_code=400, detail=f"Role {role} not allowed for this project")
            if role_config.instances > limits.max_instances_per_role:
                raise HTTPException(status_code=400, 
                                  detail=f"Exceeds maximum instances for role {role}")
            if role_config.tier not in limits.allowed_tiers:
                raise HTTPException(status_code=400, 
                                  detail=f"Service tier {role_config.tier} not allowed for {role}")
    
    async def _load_config_from_db(self) -> Optional[TeamConfig]:
        """Load team configuration from database."""
        result = await self.db.execute(
            "SELECT config FROM team_configurations WHERE project_id = :project_id",
            {"project_id": self.project_id}
        )
        row = await result.first()
        if row:
            config_data = row[0]
            if isinstance(config_data, dict):
                config_data["project_id"] = self.project_id
            return TeamConfig.model_validate(config_data)
        return None

    async def _save_config_to_db(self, config: TeamConfig):
        """Save team configuration to database."""
        await self.db.execute(
            """
            INSERT INTO team_configurations (project_id, config, created_at, updated_at)
            VALUES (:project_id, :config, :timestamp, :timestamp)
            ON CONFLICT (project_id) 
            DO UPDATE SET config = :config, updated_at = :timestamp
            """,
            {
                "project_id": self.project_id,
                "config": config.model_dump(),
                "timestamp": int(time.time())
            }
        )
        await self.db.commit()
        
    async def _scale_role_instances(self, role: ServiceRole, instances: int):
        """Scale the number of instances for a role.
        
        Args:
            role: The service role to scale
            instances: The desired number of instances
        """
        deployment_name = f"{role}-{self.project_id}"
        await self.k8s.scale_deployment(deployment_name=deployment_name, replicas=instances) 
"""Master service implementation."""
from typing import Dict, List, Optional
from fastapi import HTTPException
import redis.asyncio as redis
import asyncio
from contextlib import asynccontextmanager

from src.models.team_config import ServiceRole, RoleConfig, TeamConfig
from src.utils.context_utils import ContextClient
from src.core.dependencies import ServiceDeps
from src.services.team_service import TeamService
from src.utils.logging import get_logger

logger = get_logger(__name__)

class MasterService:
    """Service for orchestrating requests across team roles."""
    
    # Memory protection constants
    MAX_CONTEXT_SIZE_MB = 100
    CLEANUP_INTERVAL_SECONDS = 300
    
    def __init__(self, deps: ServiceDeps, project_id: str):
        """Initialize master service."""
        self.redis = deps.redis
        self.context = deps.context
        self.team_service = TeamService(deps=deps, project_id=project_id)
        self.project_id = project_id
        self._cleanup_task = None
        self._start_cleanup_task()

    def __del__(self):
        """Ensure cleanup task is cancelled on service deletion."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

    def _start_cleanup_task(self):
        """Start background task for periodic cleanup."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """Periodically cleanup expired contexts and role instances."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_expired_contexts()
                await self._cleanup_role_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def _cleanup_expired_contexts(self):
        """Cleanup expired context data from Redis."""
        pattern = f"context:{self.project_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            if not await self.redis.exists(key):
                await self.redis.delete(key)

    async def _cleanup_role_instances(self):
        """Cleanup expired role instances."""
        pattern = f"scale:{self.project_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            if not await self.redis.exists(key):
                await self.redis.delete(key)

    @asynccontextmanager
    async def _context_cleanup(self, role: ServiceRole):
        """Context manager for cleaning up role-specific context data."""
        try:
            yield
        finally:
            cleanup_key = f"context:{self.project_id}:{role}"
            await self.redis.delete(cleanup_key)

    async def handle_request(self, request_type: str, payload: dict) -> dict:
        """Handle incoming requests with dynamic team configuration."""
        team_config = await self.team_service.get_team_config()
        
        # Determine required roles for this request type
        required_roles = self._get_required_roles(request_type)
        
        # Validate all required roles are enabled
        self._validate_required_roles(required_roles, team_config)
        
        # Enrich request context based on enabled roles
        enriched_context = await self._enrich_request_context(payload, team_config)
        
        # Route request to appropriate services based on configuration
        return await self._route_request(request_type, enriched_context, team_config)

    def _get_required_roles(self, request_type: str) -> List[ServiceRole]:
        """Determine which roles are required for a given request type."""
        # Example mapping of request types to required roles
        request_role_mapping = {
            "code_review": [ServiceRole.DEVELOPER],
            "test_generation": [ServiceRole.QA_TESTER],
            "ui_design": [ServiceRole.UX_DESIGNER],
            "project_planning": [ServiceRole.PROJECT_MANAGER],
            "feature_implementation": [
                ServiceRole.PROJECT_MANAGER,
                ServiceRole.DEVELOPER,
                ServiceRole.QA_TESTER
            ]
        }
        return request_role_mapping.get(request_type, [])

    def _validate_required_roles(self, required_roles: List[ServiceRole], config: TeamConfig):
        """Ensure all required roles are enabled in the configuration."""
        for role in required_roles:
            if role not in config.roles or not config.roles[role].enabled:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required role {role} is not enabled for this project"
                )

    async def _enrich_request_context(self, payload: dict, config: TeamConfig) -> dict:
        """Enrich request context based on enabled roles with memory protection."""
        context = payload.copy()
        total_size = 0
        
        for role, role_config in config.roles.items():
            if not role_config.enabled:
                continue
                
            # Calculate memory limit for this role
            role_limit_mb = role_config.context_priority * config.context_limit_mb
            if role_limit_mb + total_size > self.MAX_CONTEXT_SIZE_MB:
                logger.warning(f"Skipping context enrichment for {role} due to memory limits")
                continue

            async with self._context_cleanup(role):
                role_context = await self.context.get_role_context(
                    self.project_id,
                    role,
                    limit_mb=role_limit_mb
                )
                context_size = len(str(role_context)) / (1024 * 1024)  # Size in MB
                
                if context_size > role_limit_mb:
                    logger.warning(f"Context size {context_size}MB exceeds limit {role_limit_mb}MB for {role}")
                    continue
                    
                total_size += context_size
                context[f"{role}_context"] = role_context
        
        return context

    async def _route_request(
        self,
        request_type: str,
        context: dict,
        config: TeamConfig
    ) -> dict:
        """Route request to appropriate services based on configuration."""
        results = {}
        
        # Determine processing order based on role dependencies
        processing_order = self._get_processing_order(request_type)
        
        # Process request through each required role
        for role in processing_order:
            if role in config.roles and config.roles[role].enabled:
                # Get available instances for this role
                instances = await self._get_role_instances(role)
                
                # Distribute work across instances
                role_results = await self._process_role(
                    role,
                    instances,
                    context,
                    config.roles[role]
                )
                
                results[role] = role_results
                # Update context with results for next role
                context[f"{role}_results"] = role_results
        
        return results

    def _get_processing_order(self, request_type: str) -> List[ServiceRole]:
        """Determine the order in which roles should process the request."""
        # Example processing order for different request types
        order_mapping = {
            "feature_implementation": [
                ServiceRole.PROJECT_MANAGER,
                ServiceRole.DEVELOPER,
                ServiceRole.UX_DESIGNER,
                ServiceRole.QA_TESTER
            ],
            "code_review": [
                ServiceRole.DEVELOPER,
                ServiceRole.QA_TESTER
            ],
            "ui_design": [
                ServiceRole.UX_DESIGNER,
                ServiceRole.DEVELOPER
            ]
        }
        return order_mapping.get(request_type, [])

    async def _get_role_instances(self, role: ServiceRole) -> List[str]:
        """Get available instances for a role."""
        scaling_key = f"scale:{self.project_id}:{role}"
        instance_count = int(await self.redis.get(scaling_key) or 1)
        return [f"{role}-{i}" for i in range(instance_count)]

    async def _process_role(
        self,
        role: ServiceRole,
        instances: List[str],
        context: dict,
        role_config: RoleConfig
    ) -> dict:
        """Process request through instances of a specific role."""
        try:
            instance = instances[hash(str(context)) % len(instances)]
            return {
                "instance": instance,
                "tier": role_config.tier,
                "status": "completed",
                "results": {
                    "role": role,
                    "context_size": len(str(context))
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing request with {role} instance {role}-0: {str(e)}"
            ) 
"""Role-based access control module."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set

from cahoots_core.utils.infrastructure.redis.client import RedisClient

from ..security.base import AuthorizationProvider


class Action(str, Enum):
    """Standard CRUD actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class Permission:
    """Permission definition."""

    resource: str
    action: Action


@dataclass
class Role:
    """Role definition."""

    name: str
    permissions: Set[Permission]
    description: str = ""


class RedisRBACProvider(AuthorizationProvider):
    """Redis-backed RBAC implementation."""

    def __init__(self, redis_client: RedisClient):
        """Initialize RBAC provider.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission.

        Args:
            user_id: User ID to check
            resource: Resource to check access for
            action: Action to check

        Returns:
            True if user has permission, False otherwise
        """
        # Get user's roles
        roles = await self.get_user_roles(user_id)

        # Check each role's permissions
        for role_name in roles:
            role_perms = await self._get_role_permissions(role_name)
            if self._has_permission(role_perms, resource, action):
                return True

        return False

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get user's roles.

        Args:
            user_id: User ID to get roles for

        Returns:
            List of role names
        """
        roles = await self.redis.smembers(f"user_roles:{user_id}")
        return list(roles) if roles else []

    async def assign_role(self, user_id: str, role_name: str) -> None:
        """Assign role to user.

        Args:
            user_id: User ID to assign role to
            role_name: Role name to assign
        """
        await self.redis.sadd(f"user_roles:{user_id}", role_name)

    async def remove_role(self, user_id: str, role_name: str) -> None:
        """Remove role from user.

        Args:
            user_id: User ID to remove role from
            role_name: Role name to remove
        """
        await self.redis.srem(f"user_roles:{user_id}", role_name)

    async def create_role(self, role: Role) -> None:
        """Create or update a role.

        Args:
            role: Role to create/update
        """
        # Store role permissions
        perms = {f"{p.resource}:{p.action}" for p in role.permissions}
        await self.redis.delete(f"role_permissions:{role.name}")
        if perms:
            await self.redis.sadd(f"role_permissions:{role.name}", *perms)

    async def _get_role_permissions(self, role_name: str) -> Set[str]:
        """Get role's permissions.

        Args:
            role_name: Role name to get permissions for

        Returns:
            Set of permission strings in format "resource:action"
        """
        perms = await self.redis.smembers(f"role_permissions:{role_name}")
        return set(perms) if perms else set()

    def _has_permission(self, role_perms: Set[str], resource: str, action: str) -> bool:
        """Check if permission set includes specific permission.

        Args:
            role_perms: Set of role permissions
            resource: Resource to check
            action: Action to check

        Returns:
            True if permission exists in set
        """
        # Check for exact match
        if f"{resource}:{action}" in role_perms:
            return True

        # Check for wildcard resource
        if f"*:{action}" in role_perms:
            return True

        # Check for wildcard action
        if f"{resource}:*" in role_perms:
            return True

        # Check for admin permission
        if f"{resource}:{Action.ADMIN}" in role_perms:
            return True

        return False

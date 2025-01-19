import pytest
from src.utils.security import Role, Permission, ResourceType, PermissionLevel, RoleManager
from fastapi import HTTPException

@pytest.mark.integration
class TestRoleBasedAccess:
    """Integration tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_role_lifecycle(self, role_manager: RoleManager):
        """Test complete role lifecycle - creation, permission assignment, and verification."""
        # Given a role with specific permissions
        admin_permissions = [
            Permission(resource_type=ResourceType.PROJECT, level=PermissionLevel.ADMIN),
            Permission(resource_type=ResourceType.ORGANIZATION, level=PermissionLevel.WRITE)
        ]
        admin_role = Role("admin", admin_permissions, "Administrator role")

        # When we create the role
        await role_manager.create_role(admin_role)

        # Then we can retrieve its permissions
        permissions = await role_manager.get_role_permissions("admin")
        assert len(permissions) == 2
        assert any(p.resource_type == ResourceType.PROJECT and p.level == PermissionLevel.ADMIN 
                  for p in permissions)
        assert any(p.resource_type == ResourceType.ORGANIZATION and p.level == PermissionLevel.WRITE 
                  for p in permissions)

    @pytest.mark.asyncio
    async def test_permission_inheritance(self, role_manager: RoleManager):
        """Test permission level inheritance (e.g. ADMIN includes WRITE and READ)."""
        # Given a role with admin permission
        admin_permissions = [
            Permission(resource_type=ResourceType.PROJECT, level=PermissionLevel.ADMIN)
        ]
        admin_role = Role("project_admin", admin_permissions)
        await role_manager.create_role(admin_role)

        # When we check different permission levels
        permissions = await role_manager.get_role_permissions("project_admin")
        
        # Then admin should implicitly include lower levels
        assert permissions[0].level.value >= PermissionLevel.READ.value
        assert permissions[0].level.value >= PermissionLevel.WRITE.value

    @pytest.mark.asyncio
    async def test_resource_specific_permissions(self, role_manager: RoleManager):
        """Test permissions for specific resource instances."""
        # Given a role with resource-specific permission
        specific_permissions = [
            Permission(
                resource_type=ResourceType.PROJECT,
                level=PermissionLevel.WRITE,
                resource_id="project-123"
            )
        ]
        role = Role("project_writer", specific_permissions)
        await role_manager.create_role(role)

        # When we retrieve the permissions
        permissions = await role_manager.get_role_permissions("project_writer")

        # Then they should include the resource-specific details
        assert permissions[0].resource_id == "project-123"
        assert permissions[0].level == PermissionLevel.WRITE

    @pytest.mark.asyncio
    async def test_role_permission_validation(self, security_manager, role_manager: RoleManager):
        """Test validation of permissions against roles."""
        # Given a role with specific permissions
        viewer_permissions = [
            Permission(resource_type=ResourceType.PROJECT, level=PermissionLevel.READ)
        ]
        viewer_role = Role("viewer", viewer_permissions)
        await role_manager.create_role(viewer_role)

        # When we check permissions
        key_data = {"role": "viewer"}
        
        # Then appropriate permissions should be granted/denied
        read_permission = Permission(
            resource_type=ResourceType.PROJECT,
            level=PermissionLevel.READ
        )
        write_permission = Permission(
            resource_type=ResourceType.PROJECT,
            level=PermissionLevel.WRITE
        )
        
        assert await security_manager.check_permission(key_data, read_permission) is True
        assert await security_manager.check_permission(key_data, write_permission) is False 
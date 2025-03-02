"""Organization service implementation."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import EmailStr
from schemas.organizations import (
    MemberInvite,
    MemberResponse,
    MemberUpdate,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationWithMembers,
)
from services.email_service import EmailService
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.exceptions.domain import DomainError
from cahoots_core.exceptions.infrastructure import InfrastructureError
from cahoots_core.models.db_models import (
    Organization,
    OrganizationInvitation,
    Subscription,
)
from cahoots_core.models.user import User, UserRole


class OrganizationService:
    """Organization service."""

    def __init__(self, db: AsyncSession):
        """Initialize service.

        Args:
            db: Database session
        """
        self.db = db
        self.email_service = EmailService()

    async def create_organization(
        self, data: OrganizationCreate, owner_id: UUID
    ) -> OrganizationResponse:
        """Create a new organization.

        Args:
            data: Organization data
            owner_id: User ID of organization owner

        Returns:
            Created organization

        Raises:
            HTTPException: If organization creation fails
        """
        # Check if organization with name exists
        stmt = select(Organization).where(Organization.name == data.name)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists",
            )

        # Create organization
        organization = Organization(name=data.name, email=data.email, description=data.description)
        self.db.add(organization)

        # Add owner role
        role = UserRole(user_id=owner_id, organization_id=organization.id, role="owner")
        self.db.add(role)

        await self.db.commit()
        await self.db.refresh(organization)

        return await self._to_response(organization)

    async def get_organization(
        self, organization_id: UUID, include_members: bool = False
    ) -> Optional[OrganizationResponse]:
        """Get organization by ID.

        Args:
            organization_id: Organization ID
            include_members: Whether to include member details

        Returns:
            Organization if found, None otherwise
        """
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        organization = result.scalar_one_or_none()

        if not organization:
            return None

        if include_members:
            return await self._to_response_with_members(organization)
        return await self._to_response(organization)

    async def list_organizations(
        self, user_id: Optional[UUID] = None
    ) -> List[OrganizationResponse]:
        """List organizations.

        Args:
            user_id: Optional user ID to filter organizations

        Returns:
            List of organizations
        """
        if user_id:
            # Get organizations where user is a member
            stmt = (
                select(Organization)
                .join(UserRole, UserRole.organization_id == Organization.id)
                .where(UserRole.user_id == user_id)
            )
        else:
            stmt = select(Organization)

        result = await self.db.execute(stmt)
        organizations = result.scalars().all()

        return [await self._to_response(org) for org in organizations]

    async def update_organization(
        self, organization_id: UUID, data: OrganizationUpdate, user_id: UUID
    ) -> Optional[OrganizationResponse]:
        """Update organization.

        Args:
            organization_id: Organization ID
            data: Update data
            user_id: User ID performing update

        Returns:
            Updated organization if found, None otherwise

        Raises:
            HTTPException: If user doesn't have permission
        """
        # Check user has owner/admin role
        if not await self._has_permission(user_id, organization_id, ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        organization = result.scalar_one_or_none()

        if not organization:
            return None

        if data.name is not None:
            organization.name = data.name
        if data.email is not None:
            organization.email = data.email
        if data.description is not None:
            organization.description = data.description

        await self.db.commit()
        await self.db.refresh(organization)
        return await self._to_response(organization)

    async def delete_organization(self, organization_id: UUID, user_id: UUID) -> bool:
        """Delete organization.

        Args:
            organization_id: Organization ID
            user_id: User ID performing deletion

        Returns:
            True if organization was deleted, False if not found

        Raises:
            HTTPException: If user doesn't have permission
        """
        # Check user has owner role
        if not await self._has_permission(user_id, organization_id, ["owner"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owner can delete organization",
            )

        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        organization = result.scalar_one_or_none()

        if not organization:
            return False

        await self.db.delete(organization)
        await self.db.commit()
        return True

    async def invite_member(
        self, organization_id: UUID, invite: MemberInvite, inviter_id: UUID
    ) -> None:
        """Invite user to organization.

        Args:
            organization_id: Organization ID
            invite: Member invitation
            inviter_id: User ID sending invitation

        Raises:
            HTTPException: If invitation fails
        """
        # Check inviter has permission
        if not await self._has_permission(inviter_id, organization_id, ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite members",
            )

        # Check if user exists
        stmt = select(User).where(User.email == invite.email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Create pending user
            user = User(email=invite.email, is_verified=False)
            self.db.add(user)
            await self.db.commit()

        # Check if already a member
        stmt = select(UserRole).where(
            UserRole.user_id == user.id, UserRole.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

        # Create role
        role = UserRole(user_id=user.id, organization_id=organization_id, role=invite.role)
        self.db.add(role)
        await self.db.commit()

        # Send invitation email
        await self.email_service.send_organization_invite(
            email=invite.email, organization_id=organization_id, role=invite.role
        )

    async def update_member(
        self, organization_id: UUID, user_id: UUID, update: MemberUpdate, updater_id: UUID
    ) -> MemberResponse:
        """Update organization member.

        Args:
            organization_id: Organization ID
            user_id: User ID to update
            update: Member update
            updater_id: User ID performing update

        Returns:
            Updated member details

        Raises:
            HTTPException: If update fails
        """
        # Check updater has permission
        if not await self._has_permission(updater_id, organization_id, ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update members",
            )

        # Get role
        stmt = select(UserRole).where(
            UserRole.user_id == user_id, UserRole.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this organization",
            )

        # Prevent changing owner role
        if role.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify owner role"
            )

        # Update role
        role.role = update.role
        await self.db.commit()
        await self.db.refresh(role)

        return await self._to_member_response(role)

    async def remove_member(self, organization_id: UUID, user_id: UUID, remover_id: UUID) -> None:
        """Remove member from organization.

        Args:
            organization_id: Organization ID
            user_id: User ID to remove
            remover_id: User ID performing removal

        Raises:
            HTTPException: If removal fails
        """
        # Check remover has permission
        if not await self._has_permission(remover_id, organization_id, ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove members",
            )

        # Get role
        stmt = select(UserRole).where(
            UserRole.user_id == user_id, UserRole.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this organization",
            )

        # Prevent removing owner
        if role.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove organization owner"
            )

        await self.db.delete(role)
        await self.db.commit()

    async def list_members(self, organization_id: UUID) -> List[MemberResponse]:
        """List organization members.

        Args:
            organization_id: Organization ID

        Returns:
            List of members
        """
        stmt = select(UserRole).where(UserRole.organization_id == organization_id)
        result = await self.db.execute(stmt)
        roles = result.scalars().all()

        return [await self._to_member_response(role) for role in roles]

    async def _has_permission(
        self, user_id: UUID, organization_id: UUID, allowed_roles: List[str]
    ) -> bool:
        """Check if user has required role in organization.

        Args:
            user_id: User ID
            organization_id: Organization ID
            allowed_roles: List of roles that have permission

        Returns:
            True if user has permission, False otherwise
        """
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.organization_id == organization_id,
            UserRole.role.in_(allowed_roles),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _to_response(self, organization: Organization) -> OrganizationResponse:
        """Convert organization model to response schema.

        Args:
            organization: Organization model

        Returns:
            Organization response
        """
        # Get member count
        stmt = (
            select(func.count())
            .select_from(UserRole)
            .where(UserRole.organization_id == organization.id)
        )
        result = await self.db.execute(stmt)
        member_count = result.scalar_one()

        # Get subscription status
        stmt = (
            select(Subscription)
            .where(Subscription.organization_id == organization.id)
            .order_by(Subscription.created_at.desc())
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        subscription_status = subscription.status if subscription else "inactive"

        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            email=organization.email,
            description=organization.description,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            member_count=member_count,
            subscription_status=subscription_status,
        )

    async def _to_response_with_members(
        self, organization: Organization
    ) -> OrganizationWithMembers:
        """Convert organization model to response with members.

        Args:
            organization: Organization model

        Returns:
            Organization response with members
        """
        response = await self._to_response(organization)
        members = await self.list_members(organization.id)

        return OrganizationWithMembers(**response.dict(), members=members)

    async def _to_member_response(self, role: UserRole) -> MemberResponse:
        """Convert user role to member response.

        Args:
            role: User role model

        Returns:
            Member response
        """
        stmt = select(User).where(User.id == role.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one()

        return MemberResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role.role,
            joined_at=role.created_at,
            last_active=user.last_login,
            is_active=user.is_active,
        )

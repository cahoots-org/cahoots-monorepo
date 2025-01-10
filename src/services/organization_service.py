"""Organization service implementation."""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Organization
from src.schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)

class OrganizationService:
    """Organization service."""

    def __init__(self, db: AsyncSession):
        """Initialize service.
        
        Args:
            db: Database session
        """
        self.db = db

    async def create_organization(
        self,
        data: OrganizationCreate
    ) -> OrganizationResponse:
        """Create a new organization.
        
        Args:
            data: Organization data
            
        Returns:
            Created organization
        """
        organization = Organization(
            name=data.name,
            email=data.email,
            description=data.description
        )
        self.db.add(organization)
        await self.db.commit()
        await self.db.refresh(organization)
        return self._to_response(organization)

    async def get_organization(
        self,
        organization_id: str
    ) -> Optional[OrganizationResponse]:
        """Get organization by ID.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization if found, None otherwise
        """
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        organization = result.scalar_one_or_none()
        return self._to_response(organization) if organization else None

    async def list_organizations(self) -> List[OrganizationResponse]:
        """List all organizations.
        
        Returns:
            List of organizations
        """
        stmt = select(Organization)
        result = await self.db.execute(stmt)
        organizations = result.scalars().all()
        return [self._to_response(org) for org in organizations]

    async def update_organization(
        self,
        organization_id: str,
        data: OrganizationUpdate
    ) -> Optional[OrganizationResponse]:
        """Update organization.
        
        Args:
            organization_id: Organization ID
            data: Update data
            
        Returns:
            Updated organization if found, None otherwise
        """
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
        return self._to_response(organization)

    async def delete_organization(self, organization_id: str) -> bool:
        """Delete organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            True if organization was deleted, False if not found
        """
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        organization = result.scalar_one_or_none()
        
        if not organization:
            return False

        await self.db.delete(organization)
        await self.db.commit()
        return True

    def _to_response(self, organization: Organization) -> OrganizationResponse:
        """Convert organization model to response schema.
        
        Args:
            organization: Organization model
            
        Returns:
            Organization response
        """
        return OrganizationResponse(
            id=str(organization.id),
            name=organization.name,
            email=organization.email,
            description=organization.description,
            created_at=organization.created_at.isoformat(),
            updated_at=organization.updated_at.isoformat()
        ) 
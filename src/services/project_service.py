"""Project management service."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.project import Project
from src.database.models import Organization
from src.utils.event_system import EventSystem

class ProjectService:
    """Service for project management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_project(
        self,
        name: str,
        description: str,
        organization_id: str
    ) -> Project:
        """Create a new project.
        
        Args:
            name: Project name
            description: Project description
            organization_id: Organization ID
            
        Returns:
            Project: Created project
            
        Raises:
            ValueError: If project creation fails
        """
        project = Project(
            name=name,
            description=description,
            organization_id=organization_id,
            status="active"
        )
        
        self.db.add(project)
        await self.db.flush()
        
        return project
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_projects(
        self,
        organization_id: str,
        status: Optional[str] = None
    ) -> List[Project]:
        """List projects for an organization.
        
        Args:
            organization_id: Organization ID
            status: Optional status filter
            
        Returns:
            List[Project]: List of projects
        """
        stmt = select(Project).where(Project.organization_id == organization_id)
        if status:
            stmt = stmt.where(Project.status == status)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Project]:
        """Update project details.
        
        Args:
            project_id: Project ID
            updates: Dictionary of fields to update
            
        Returns:
            Optional[Project]: Updated project if found
        """
        project = await self.get_project(project_id)
        if not project:
            return None
            
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        await self.db.flush()
        return project
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        project = await self.get_project(project_id)
        if not project:
            return False
            
        await self.db.delete(project)
        await self.db.flush()
        return True 
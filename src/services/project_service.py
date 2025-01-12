"""Project service implementation."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Project
from src.core.dependencies import BaseDeps

class ProjectService:
    """Service for project management operations."""
    
    def __init__(self, deps: BaseDeps):
        """Initialize project service.
        
        Args:
            deps: Base dependencies including database
        """
        self.db = deps.db
        self.event_system = deps.event_system
    
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
        try:
            # Create project instance
            project = Project(
                name=name,
                description=description,
                organization_id=organization_id,
                status="active"
            )
            
            # Add to session
            self.db.add(project)
            
            # Emit event
            await self.event_system.publish(
                "project_manager",
                {
                    "type": "project_created",
                    "project_id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "organization_id": str(project.organization_id)
                }
            )
            
            return project
            
        except Exception as e:
            raise ValueError(f"Failed to create project: {str(e)}")
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        try:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            raise ValueError(f"Failed to get project: {str(e)}") 
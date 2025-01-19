"""Project Manager Agent package for Cahoots."""

from .core.project_manager import (
    ProjectManager,
    ProjectStatus,
    ProjectPriority,
    ProjectType,
)
from .master.master_service import (
    MasterService,
    MasterConfig,
    TaskAssignment,
    AgentRole,
)

__all__ = [
    # Core Project Management
    "ProjectManager",
    "ProjectStatus",
    "ProjectPriority",
    "ProjectType",
    
    # Master Service
    "MasterService",
    "MasterConfig",
    "TaskAssignment",
    "AgentRole",
]

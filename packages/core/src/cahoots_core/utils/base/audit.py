"""Audit logging utilities."""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

from ...models.db_models import Base

class AuditLog(Base):
    """Audit log model."""
    
    __tablename__ = "audit_logs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    organization_id = Column(PGUUID(as_uuid=True), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    changes = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    error = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)

class AuditLogger:
    """Audit logging service."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize audit logger.
        
        Args:
            db_session: Database session for storing logs
        """
        self.db = db_session
        
    async def log_action(
        self,
        organization_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        changes: Optional[Dict] = None,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an audited action.
        
        Args:
            organization_id: Organization ID
            action: Action being performed (create, update, delete)
            resource_type: Type of resource (project, agent, etc)
            resource_id: Optional ID of affected resource
            user_id: Optional ID of user performing action
            changes: Optional dict of changes made
            status: Status of action (success, failed)
            error: Optional error message if failed
            metadata: Optional additional metadata
        """
        try:
            # Create audit log entry
            log = AuditLog(
                id=UUID(),
                timestamp=datetime.utcnow(),
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes,
                status=status,
                error=error,
                metadata=metadata
            )
            
            # Add to database
            self.db.add(log)
            await self.db.commit()
            
        except Exception as e:
            # Log error but don't fail operation
            print(f"Failed to create audit log: {str(e)}")
            await self.db.rollback()
            
    async def get_audit_logs(
        self,
        organization_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs with filtering.
        
        Args:
            organization_id: Organization ID to get logs for
            resource_type: Optional resource type filter
            resource_id: Optional resource ID filter
            action: Optional action filter
            user_id: Optional user ID filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            
        Returns:
            List[AuditLog]: Matching audit logs
        """
        # Build query
        query = select(AuditLog).where(
            AuditLog.organization_id == organization_id
        )
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if action:
            query = query.where(AuditLog.action == action)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)
            
        # Add pagination
        query = query.order_by(AuditLog.timestamp.desc())
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.db.execute(query)
        return result.scalars().all() 
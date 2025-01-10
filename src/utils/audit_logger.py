"""Audit logger for tracking system events."""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request

# Configure logger
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)

class AuditLogger:
    """Audit logger for tracking system events."""
    
    async def log_data_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        organization_id: str,
        request: Optional[Request] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> None:
        """Log a data event.
        
        Args:
            action: Action performed (create, update, delete)
            resource_type: Type of resource (organization, user, etc.)
            resource_id: ID of the resource
            user_id: ID of the user performing the action
            organization_id: ID of the organization
            request: FastAPI request object
            details: Additional event details
            status: Event status (success, failure)
        """
        event_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "status": status,
            "details": details or {}
        }
        
        # Add request data if available
        if request:
            event_data["request"] = {
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
                "headers": dict(request.headers)
            }
            
        # Log event
        logger.info(
            f"{action.title()} {resource_type}",
            extra=event_data
        )

# Create singleton instance
audit_logger = AuditLogger() 
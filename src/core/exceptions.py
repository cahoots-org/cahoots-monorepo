"""Custom exceptions for the application."""
from typing import Optional, Any, Dict

class AIDTException(Exception):
    """Base exception class for all application exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception.
        
        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format.
        
        Returns:
            Dict[str, Any]: Exception details
        """
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "details": self.details
        }

class ValidationError(AIDTException):
    """Raised when data validation fails."""
    pass

class EventError(AIDTException):
    """Base class for event-related errors."""
    pass

class EventHandlingError(EventError):
    """Raised when event handling fails."""
    pass

class EventSubscriptionError(EventError):
    """Raised when event subscription fails."""
    pass

class ModelError(AIDTException):
    """Base class for model-related errors."""
    pass

class ModelGenerationError(ModelError):
    """Raised when model generation fails."""
    pass

class AgentError(AIDTException):
    """Base class for agent-related errors."""
    pass

class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""
    pass

class AgentCommunicationError(AgentError):
    """Raised when agent communication fails."""
    pass

class StoryError(AIDTException):
    """Base class for story-related errors."""
    pass

class StoryAssignmentError(StoryError):
    """Raised when story assignment fails."""
    pass

class StoryValidationError(StoryError):
    """Raised when story validation fails."""
    pass 
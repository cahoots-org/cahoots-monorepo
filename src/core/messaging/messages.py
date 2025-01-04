"""Message classes for agent communication."""
from dataclasses import dataclass, field, fields
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4, UUID

from ..exceptions import ValidationError

@dataclass
class BaseMessage:
    """Base class for all messages."""
    sender: str = field(default="system")
    recipient: Optional[str] = None
    message_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> None:
        """Validate message data.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.sender:
            raise ValidationError("Message sender is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format.
        
        Returns:
            Dict[str, Any]: Message details
        """
        return {
            "message_id": str(self.message_id),
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.__class__.__name__.lower()
        }

@dataclass
class SystemMessage:
    """System-level message."""
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    base: BaseMessage = field(default_factory=BaseMessage)
    
    def validate(self) -> None:
        """Validate system message data."""
        self.base.validate()
        if not self.command:
            raise ValidationError("System message command is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system message to dictionary format."""
        data = self.base.to_dict()
        data.update({
            "command": self.command,
            "payload": self.payload
        })
        return data

@dataclass
class StoryMessage:
    """Story-related message."""
    story_id: str
    action: str
    story_data: Dict[str, Any]
    base: BaseMessage = field(default_factory=BaseMessage)
    
    def validate(self) -> None:
        """Validate story message data."""
        self.base.validate()
        if not self.story_id:
            raise ValidationError("Story ID is required")
        if not self.action:
            raise ValidationError("Story action is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert story message to dictionary format."""
        data = self.base.to_dict()
        data.update({
            "story_id": self.story_id,
            "action": self.action,
            "story_data": self.story_data
        })
        return data

@dataclass
class TaskMessage:
    """Task-related message."""
    task_id: str
    task_type: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    task_data: Dict[str, Any] = field(default_factory=dict)
    base: BaseMessage = field(default_factory=BaseMessage)
    
    def validate(self) -> None:
        """Validate task message data."""
        self.base.validate()
        if not self.task_id:
            raise ValidationError("Task ID is required")
        if not self.task_type:
            raise ValidationError("Task type is required")
        if self.priority < 0:
            raise ValidationError("Priority must be non-negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task message to dictionary format."""
        data = self.base.to_dict()
        data.update({
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "task_data": self.task_data
        })
        return data

@dataclass
class ResponseMessage:
    """Response message."""
    request_id: UUID
    status: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    base: BaseMessage = field(default_factory=BaseMessage)
    
    def validate(self) -> None:
        """Validate response message data."""
        self.base.validate()
        if not self.request_id:
            raise ValidationError("Request ID is required")
        if not self.status:
            raise ValidationError("Response status is required")
        if self.status not in ["success", "error"]:
            raise ValidationError("Invalid response status")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response message to dictionary format."""
        data = self.base.to_dict()
        data.update({
            "request_id": str(self.request_id),
            "status": self.status,
            "data": self.data,
            "error": self.error
        })
        return data

def create_message(message_type: str, **kwargs) -> BaseMessage:
    """Create a message of the specified type.
    
    Args:
        message_type: Type of message to create
        **kwargs: Message data
        
    Returns:
        BaseMessage: Created message instance
        
    Raises:
        ValidationError: If message type is invalid
    """
    message_classes = {
        "system": SystemMessage,
        "story": StoryMessage,
        "task": TaskMessage,
        "response": ResponseMessage
    }
    
    if message_type not in message_classes:
        raise ValidationError(f"Invalid message type: {message_type}")
    
    # Extract base message fields
    base_fields = {f.name for f in fields(BaseMessage)}
    base_kwargs = {k: v for k, v in kwargs.items() if k in base_fields}
    other_kwargs = {k: v for k, v in kwargs.items() if k not in base_fields}
    
    # Create message with base
    message_class = message_classes[message_type]
    message = message_class(base=BaseMessage(**base_kwargs), **other_kwargs)
    message.validate()
    return message 
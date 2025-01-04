"""Tests for message classes."""
import pytest
from uuid import UUID
from datetime import datetime

from src.core.messaging.messages import (
    BaseMessage,
    SystemMessage,
    StoryMessage,
    TaskMessage,
    ResponseMessage,
    create_message,
    ValidationError
)

def test_base_message_validation():
    """Test base message validation."""
    # Valid case
    msg = BaseMessage(sender="test")
    msg.validate()  # Should not raise
    
    # Invalid case
    msg = BaseMessage(sender="")
    with pytest.raises(ValidationError, match="sender is required"):
        msg.validate()

def test_base_message_to_dict():
    """Test base message serialization."""
    msg = BaseMessage(sender="test", recipient="recipient")
    data = msg.to_dict()
    
    assert isinstance(data["message_id"], str)
    assert UUID(data["message_id"])  # Should be valid UUID
    assert isinstance(data["timestamp"], str)
    assert datetime.fromisoformat(data["timestamp"])  # Should be valid ISO format
    assert data["sender"] == "test"
    assert data["recipient"] == "recipient"
    assert data["type"] == "basemessage"

def test_system_message():
    """Test system message."""
    # Valid case
    base = BaseMessage(sender="system")
    msg = SystemMessage(
        command="test_command",
        payload={"key": "value"},
        base=base
    )
    msg.validate()  # Should not raise
    
    data = msg.to_dict()
    assert data["command"] == "test_command"
    assert data["payload"] == {"key": "value"}
    assert data["sender"] == "system"
    
    # Invalid case
    msg = SystemMessage(command="", base=base)
    with pytest.raises(ValidationError, match="command is required"):
        msg.validate()

def test_story_message():
    """Test story message."""
    # Valid case
    base = BaseMessage(sender="pm")
    msg = StoryMessage(
        story_id="story123",
        action="create",
        story_data={"title": "Test Story"},
        base=base
    )
    msg.validate()  # Should not raise
    
    data = msg.to_dict()
    assert data["story_id"] == "story123"
    assert data["action"] == "create"
    assert data["story_data"] == {"title": "Test Story"}
    assert data["sender"] == "pm"
    
    # Invalid cases
    with pytest.raises(ValidationError, match="Story ID is required"):
        StoryMessage(story_id="", action="create", story_data={}, base=base).validate()
        
    with pytest.raises(ValidationError, match="Story action is required"):
        StoryMessage(story_id="story123", action="", story_data={}, base=base).validate()

def test_task_message():
    """Test task message."""
    # Valid case
    base = BaseMessage(sender="dev")
    msg = TaskMessage(
        task_id="task123",
        task_type="implementation",
        priority=1,
        dependencies=["task1", "task2"],
        task_data={"description": "Test Task"},
        base=base
    )
    msg.validate()  # Should not raise
    
    data = msg.to_dict()
    assert data["task_id"] == "task123"
    assert data["task_type"] == "implementation"
    assert data["priority"] == 1
    assert data["dependencies"] == ["task1", "task2"]
    assert data["task_data"] == {"description": "Test Task"}
    assert data["sender"] == "dev"
    
    # Invalid cases
    with pytest.raises(ValidationError, match="Task ID is required"):
        TaskMessage(task_id="", task_type="test", base=base).validate()
        
    with pytest.raises(ValidationError, match="Task type is required"):
        TaskMessage(task_id="task123", task_type="", base=base).validate()
        
    with pytest.raises(ValidationError, match="Priority must be non-negative"):
        TaskMessage(task_id="task123", task_type="test", priority=-1, base=base).validate()

def test_response_message():
    """Test response message."""
    request_id = UUID('12345678-1234-5678-1234-567812345678')
    base = BaseMessage(sender="agent")
    
    # Valid case
    msg = ResponseMessage(
        request_id=request_id,
        status="success",
        data={"result": "ok"},
        base=base
    )
    msg.validate()  # Should not raise
    
    data = msg.to_dict()
    assert data["request_id"] == str(request_id)
    assert data["status"] == "success"
    assert data["data"] == {"result": "ok"}
    assert data["error"] is None
    assert data["sender"] == "agent"
    
    # Error case
    msg = ResponseMessage(
        request_id=request_id,
        status="error",
        error={"message": "Failed"},
        base=base
    )
    msg.validate()  # Should not raise
    
    data = msg.to_dict()
    assert data["status"] == "error"
    assert data["error"] == {"message": "Failed"}
    
    # Invalid cases
    with pytest.raises(ValidationError, match="Request ID is required"):
        ResponseMessage(request_id=None, status="success", base=base).validate()
        
    with pytest.raises(ValidationError, match="Response status is required"):
        ResponseMessage(request_id=request_id, status="", base=base).validate()
        
    with pytest.raises(ValidationError, match="Invalid response status"):
        ResponseMessage(request_id=request_id, status="invalid", base=base).validate()

def test_create_message():
    """Test message factory function."""
    # Test creating different message types
    system_msg = create_message(
        "system",
        sender="system",
        command="test",
        payload={}
    )
    assert isinstance(system_msg, SystemMessage)
    assert system_msg.base.sender == "system"
    assert system_msg.command == "test"
    
    story_msg = create_message(
        "story",
        sender="pm",
        story_id="story123",
        action="create",
        story_data={}
    )
    assert isinstance(story_msg, StoryMessage)
    assert story_msg.base.sender == "pm"
    assert story_msg.story_id == "story123"
    
    # Test invalid message type
    with pytest.raises(ValidationError, match="Invalid message type"):
        create_message("invalid_type")
        
    # Test validation during creation
    with pytest.raises(ValidationError):
        create_message("system", sender="system", command="") 
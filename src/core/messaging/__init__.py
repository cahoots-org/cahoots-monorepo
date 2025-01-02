"""Core messaging utilities for agent communication."""
from typing import Dict, Any, List, Optional, TypedDict
from ...utils.base_logger import BaseLogger

class MessageResponse(TypedDict):
    """Standard message response format."""
    status: str
    message: Optional[str]

def create_success_response(**kwargs) -> Dict[str, Any]:
    """Create a standardized success response.
    
    Args:
        **kwargs: Additional fields to include in response
        
    Returns:
        Dict[str, Any]: Success response with status and additional fields
    """
    response = {"status": "success"}
    response.update(kwargs)
    return response

def create_error_response(message: str) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        message: Error message
        
    Returns:
        Dict[str, Any]: Error response with status and message
    """
    return {
        "status": "error",
        "message": message
    }

def validate_story_assignment(
    data: Dict[str, Any],
    agent_id: str,
    logger: BaseLogger
) -> Optional[Dict[str, str]]:
    """Validate story assignment data.
    
    Args:
        data: Story assignment data
        agent_id: ID of the agent to validate against
        logger: Logger instance
        
    Returns:
        Optional[Dict[str, str]]: Error response if validation fails, None if successful
    """
    # Ensure we have all required fields
    required_fields = ["story_id", "title", "description", "assigned_to"]
    if not all(field in data for field in required_fields):
        error_msg = f"Missing required fields in story assignment. Required: {required_fields}, Got: {list(data.keys())}"
        logger.error(error_msg)
        return create_error_response(error_msg)
            
    if data.get("assigned_to") != agent_id:
        logger.info(f"Story assigned to {data.get('assigned_to')}, but I am {agent_id}. Ignoring.")
        return create_error_response(f"Story not assigned to {agent_id}")
            
    return None

def validate_message_type(
    message: Dict[str, Any],
    valid_types: List[str],
    logger: BaseLogger
) -> Optional[Dict[str, str]]:
    """Validate message type.
    
    Args:
        message: Message to validate
        valid_types: List of valid message types
        logger: Logger instance
        
    Returns:
        Optional[Dict[str, str]]: Error response if validation fails, None if successful
    """
    message_type = message.get("type")
    if not message_type or message_type not in valid_types:
        error_msg = f"Unknown message type: {message_type}"
        logger.error(error_msg)
        return create_error_response(error_msg)
    return None 
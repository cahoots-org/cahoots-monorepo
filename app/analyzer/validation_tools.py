"""Validation Tools for LLM Tool Calling

This module defines validation functions that can be called by LLMs
during event model generation. This allows the LLM to self-validate
during generation rather than requiring separate retry loops.
"""

from typing import Dict, Any, List
from app.analyzer.event_extractor import EventType, EVENT_TYPE_MAPPING


# Tool definitions for Ollama tool calling
VALIDATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "validate_event_type",
            "description": "Validates that an event type is one of the allowed values: user_action, system_event, integration, state_change",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "The event type to validate"
                    }
                },
                "required": ["event_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_command_event_pair",
            "description": "Validates that a command triggers at least one event. Commands MUST trigger events in Event Modeling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command_name": {
                        "type": "string",
                        "description": "The command name to validate"
                    },
                    "triggered_events": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of event names that this command triggers"
                    }
                },
                "required": ["command_name", "triggered_events"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_event_name",
            "description": "Validates that an event name is in past tense (e.g., 'UserRegistered', not 'RegisterUser')",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": "The event name to validate"
                    }
                },
                "required": ["event_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_command_name",
            "description": "Validates that a command name is imperative (e.g., 'RegisterUser', not 'UserRegistered')",
            "parameters": {
                "type": "object",
                "properties": {
                    "command_name": {
                        "type": "string",
                        "description": "The command name to validate"
                    }
                },
                "required": ["command_name"]
            }
        }
    }
]


def validate_event_type(event_type: str) -> Dict[str, Any]:
    """Validate that an event type is one of the allowed values."""
    # Try mapping first
    mapped_type = EVENT_TYPE_MAPPING.get(event_type, event_type)

    try:
        EventType(mapped_type)
        return {
            "valid": True,
            "mapped_type": mapped_type,
            "message": f"Event type '{event_type}' is valid (mapped to '{mapped_type}')"
        }
    except ValueError:
        valid_types = [e.value for e in EventType]
        return {
            "valid": False,
            "error": f"Invalid event type '{event_type}'. Must be one of: {', '.join(valid_types)}",
            "valid_types": valid_types
        }


def validate_command_event_pair(command_name: str, triggered_events: List[str]) -> Dict[str, Any]:
    """Validate that a command triggers at least one event."""
    if not triggered_events or len(triggered_events) == 0:
        return {
            "valid": False,
            "error": f"Command '{command_name}' must trigger at least one event. Commands in Event Modeling always produce events."
        }

    return {
        "valid": True,
        "message": f"Command '{command_name}' triggers {len(triggered_events)} event(s)"
    }


def validate_event_name(event_name: str) -> Dict[str, Any]:
    """Validate that an event name is in past tense."""
    # Simple heuristic: past tense events typically end with 'ed', 'en', or are past tense verbs
    # Event Modeling convention: past tense (e.g., "UserRegistered", "OrderPlaced", "EmailSent")

    past_tense_endings = ['ed', 'en', 'ied', 'led', 'red', 'ted', 'ded', 'ned']
    past_tense_words = ['Sent', 'Built', 'Bought', 'Sold', 'Paid', 'Made', 'Took', 'Gave', 'Got', 'Found', 'Lost', 'Won', 'Wrote']

    # Check if ends with past tense suffix
    for ending in past_tense_endings:
        if event_name.endswith(ending):
            return {
                "valid": True,
                "message": f"Event name '{event_name}' appears to be in past tense"
            }

    # Check if contains known past tense word
    for word in past_tense_words:
        if word in event_name:
            return {
                "valid": True,
                "message": f"Event name '{event_name}' appears to be in past tense"
            }

    return {
        "valid": False,
        "warning": f"Event name '{event_name}' may not be in past tense. Event names should describe what happened (e.g., 'UserRegistered', 'OrderPlaced')"
    }


def validate_command_name(command_name: str) -> Dict[str, Any]:
    """Validate that a command name is imperative."""
    # Command names should be imperative (e.g., "RegisterUser", "PlaceOrder", "SendEmail")
    # Not past tense (e.g., "UserRegistered", "OrderPlaced")

    past_tense_endings = ['ed', 'en', 'ied', 'led', 'red', 'ted', 'ded', 'ned']

    # Check if it looks like past tense (which would be wrong for a command)
    for ending in past_tense_endings:
        if command_name.endswith(ending):
            return {
                "valid": False,
                "error": f"Command name '{command_name}' appears to be in past tense. Commands should be imperative (e.g., 'RegisterUser', not 'UserRegistered')"
            }

    return {
        "valid": True,
        "message": f"Command name '{command_name}' appears to be imperative"
    }


# Map tool names to functions
TOOL_FUNCTIONS = {
    "validate_event_type": validate_event_type,
    "validate_command_event_pair": validate_command_event_pair,
    "validate_event_name": validate_event_name,
    "validate_command_name": validate_command_name,
}


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call and return the result."""
    if tool_name not in TOOL_FUNCTIONS:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(TOOL_FUNCTIONS.keys())
        }

    func = TOOL_FUNCTIONS[tool_name]
    try:
        return func(**arguments)
    except Exception as e:
        return {
            "error": f"Error executing {tool_name}: {str(e)}"
        }

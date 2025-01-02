"""Code validation functionality for the developer agent."""
from typing import Dict, Any
import logging
import json

from src.models.task import Task

class CodeValidator:
    """Handles code validation."""
    
    def __init__(self, agent):
        """Initialize the code validator.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
    async def validate_implementation(self, code: str, task: Task) -> Dict[str, Any]:
        """Validate implementation against quality standards.
        
        Args:
            code: The implementation code to validate
            task: The task being implemented
            
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_prompt = f"""Validate this implementation against these criteria:
        Code:
        {code}
        
        Task:
        {task.title}
        {task.description}
        
        Validation criteria:
        1. Proper type hints
        2. Comprehensive docstrings
        3. Error handling
        4. Input validation
        5. Edge case handling
        6. SOLID principles
        7. Testability
        8. Logging
        
        Respond with:
        {{
            "valid": true/false,
            "errors": []  // List of validation failures if any
        }}
        """
        
        validation_response = await self.agent.generate_response(validation_prompt)
        
        try:
            result = json.loads(validation_response)
            return {
                "valid": result.get("valid", False),
                "errors": result.get("errors", [])
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse validation response: {str(e)}")
            return {
                "valid": False,
                "errors": ["Failed to parse validation response"]
            } 
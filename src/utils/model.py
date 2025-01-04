from typing import Optional
import os
import requests
import json
import aiohttp
from .config import config

class Model:
    """Model class for interacting with Together.xyz API."""

    def __init__(self, model_name: str) -> None:
        """Initialize model.
        
        Args:
            model_name: Name of model to use
            
        Raises:
            RuntimeError: If Together API key is not configured
        """
        self.model_name = model_name
        
        # Get Together service config
        together_service = config.services.get("together")
        if not together_service or not together_service.api_key:
            raise RuntimeError("Together API key not configured")
            
        self.api_key = together_service.api_key
        self.api_base = together_service.url + "/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # For test environments, use mock responses
        self.is_test = os.getenv("ENV", "development") == "test"

    async def generate_response(self, prompt: str) -> str:
        """Generate response from model.
        
        Args:
            prompt: Prompt to send to model
            
        Returns:
            str: Generated response
            
        Raises:
            HTTPError: If API request fails
        """
        # In test environment, return mock response
        if self.is_test:
            if "roadmap" in prompt.lower():
                return json.dumps({
                    "milestones": [
                        {"id": "m1", "name": "Planning", "description": "Initial project planning phase"},
                        {"id": "m2", "name": "Development", "description": "Core development phase"}
                    ],
                    "tasks": [
                        {"id": "t1", "milestone": "m1", "name": "Requirements gathering", "description": "Collect and document requirements"},
                        {"id": "t2", "milestone": "m1", "name": "Architecture design", "description": "Design system architecture"},
                        {"id": "t3", "milestone": "m2", "name": "Core implementation", "description": "Implement core features"}
                    ],
                    "dependencies": [
                        {"from": "t1", "to": "t2"},
                        {"from": "t2", "to": "t3"}
                    ],
                    "estimates": {
                        "t1": "3d",
                        "t2": "5d",
                        "t3": "10d"
                    }
                })
            elif "test suite" in prompt.lower():
                return """Title: Test Login Flow
Description: Verify user can log in successfully
Steps:
1. Navigate to login page
2. Enter valid credentials
3. Click submit
Expected Result: User is logged in and redirected to dashboard
---
Title: Test Invalid Login
Description: Verify error handling for invalid credentials
Steps:
1. Navigate to login page
2. Enter invalid credentials
3. Click submit
Expected Result: Error message is displayed
---"""
            return "Test response"

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.api_base,
                headers=self.headers,
                json=data
            )
            await response.raise_for_status()
            result = await response.json()
            return result["choices"][0]["message"]["content"] 
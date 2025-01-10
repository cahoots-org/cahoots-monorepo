"""Model utility for interacting with Together.xyz API."""
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
        
        # Get config
        if "together" not in config.services:
            raise RuntimeError("Together service not configured")
            
        service_config = config.services["together"]
        
        # Set up API configuration
        self.api_key = service_config.api_key
        if not self.api_key:
            raise RuntimeError("Together API key not configured")
            
        self.api_base = f"{service_config.url}/chat/completions"
        
        # Set up headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_response(self, prompt: str) -> str:
        """Generate response from model.
        
        Args:
            prompt: Prompt to send to model
            
        Returns:
            Model response
            
        Raises:
            RuntimeError: If API request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
                
                async with session.post(
                    self.api_base,
                    headers=self.headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"API request failed: {error_text}")
                        
                    response_data = await response.json()
                    try:
                        return response_data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError) as e:
                        raise RuntimeError(f"Invalid API response: {str(e)}")
                        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to connect to API: {str(e)}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid API response: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {str(e)}") 
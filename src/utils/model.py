from typing import Optional
import os
import requests
import json

class Model:
    """A class that provides AI model functionality using Together AI's API."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize the Model with an optional model name.
        
        Args:
            model_name: The name of the model to use. If None, uses a default model.
        """
        self.model_name = model_name or "togethercomputer/CodeLlama-7b-Instruct"
        self.api_url = "https://api.together.xyz/inference"
        
    def generate_response(self, prompt: str) -> str:
        """Generate a response based on the given prompt.
        
        Args:
            prompt: The input prompt to generate a response for.
            
        Returns:
            str: The generated response.
            
        Raises:
            ValueError: If TOGETHER_API_KEY environment variable is not set.
            Exception: If there is an error generating the response.
        """
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY environment variable must be set")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "repetition_penalty": 1.0
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result["output"]["choices"][0]["text"] 
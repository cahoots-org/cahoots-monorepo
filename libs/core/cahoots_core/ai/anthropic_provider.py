import os
from typing import Any, AsyncGenerator, List, Optional

import anthropic
from anthropic import AsyncAnthropic

from .base import AIProvider


class AnthropicProvider(AIProvider):
    """Provider for Anthropic's Claude AI model."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Anthropic provider.
        
        Args:
            api_key: Optional API key. If not provided, will try to get from env.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-opus-20240229"

    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the model.
        
        Args:
            prompt: The prompt to send to the model.
            **kwargs: Additional arguments to pass to the model.
            
        Returns:
            The generated response.
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {str(e)}") from e

    async def stream_response(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Stream a response from the model.
        
        Args:
            prompt: The prompt to send to the model.
            **kwargs: Additional arguments to pass to the model.
            
        Yields:
            Chunks of the generated response.
        """
        try:
            stream = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            async for chunk in stream:
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            raise RuntimeError(f"Failed to stream response: {str(e)}") from e

    async def generate_embeddings(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to generate embeddings for.
            **kwargs: Additional arguments to pass to the model.
            
        Returns:
            List of embeddings, one for each input text.
        """
        try:
            embeddings = []
            for text in texts:
                response = await self.client.embeddings.create(
                    model="claude-3-opus-20240229",
                    input=text
                )
                embeddings.append(response.embeddings)
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}") from e 
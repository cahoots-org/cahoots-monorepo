"""OpenAI provider implementation."""

import os
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import openai
import tiktoken
from openai import AsyncOpenAI

from .base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI implementation of AIProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gpt-4-turbo-preview",
        organization: Optional[str] = None,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            default_model: Default model to use
            organization: Optional organization ID
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.default_model = default_model
        self.client = AsyncOpenAI(api_key=self.api_key, organization=organization)

    async def generate_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response using OpenAI."""
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            **kwargs,
        )
        return response.choices[0].message.content

    async def generate_embeddings(
        self, texts: List[str], *, model: Optional[str] = "text-embedding-3-small", **kwargs: Any
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        response = await self.client.embeddings.create(model=model, input=texts, **kwargs)
        return [data.embedding for data in response.data]

    async def stream_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a response using OpenAI."""
        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            stream=True,
            **kwargs,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_token_count(self, text: str) -> int:
        """Get token count using tiktoken."""
        try:
            encoding = tiktoken.encoding_for_model(self.default_model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

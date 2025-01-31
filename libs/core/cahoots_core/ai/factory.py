"""Factory for creating AI providers."""
from typing import Dict, Optional, Type, Any, AsyncGenerator, List
import os

from .base import AIProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .test_provider import TestProvider

class AIProviderFactory:
    """Factory for creating AI providers."""
    
    _providers: Dict[str, Type[AIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "test": TestProvider,
        # Add more providers here as they're implemented
        # "local": LocalProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AIProvider:
        """Create an AI provider instance.
        
        Args:
            provider: Provider type ("openai", etc)
            api_key: Optional API key
            model: Optional default model
            **kwargs: Additional provider-specific args
            
        Returns:
            AIProvider: Configured provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )
            
        provider_cls = cls._providers[provider]
        
        # Handle provider-specific initialization
        if provider == "openai":
            return provider_cls(
                api_key=api_key,
                default_model=model,
                **kwargs
            )
            
        # Add other provider initialization here
        
        return provider_cls(**kwargs)
        
    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[AIProvider]):
        """Register a new provider type.
        
        Args:
            name: Provider name
            provider_cls: Provider class
        """
        cls._providers[name] = provider_cls 

    @staticmethod
    def create_provider(provider_type: str = "openai", api_key: Optional[str] = None) -> AIProvider:
        """Create an AI provider instance.

        Args:
            provider_type: Type of AI provider to create
            api_key: Optional API key for the provider

        Returns:
            AIProvider instance

        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type == "openai":
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAIProvider(api_key)
        elif provider_type == "anthropic":
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key is required")
            return AnthropicProvider(api_key)
        elif provider_type == "test":
            return TestProvider()
        else:
            raise ValueError(f"Unsupported provider: {provider_type}. Supported providers: ['openai', 'anthropic', 'test']")

class TestProvider(AIProvider):
    """Test AI provider for use in tests."""

    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """Generate a mock response.

        Args:
            prompt: Input prompt
            **kwargs: Additional arguments

        Returns:
            Mock response
        """
        return '{"status": "success", "message": "Test response"}'

    async def stream_response(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Stream a mock response.

        Args:
            prompt: Input prompt
            **kwargs: Additional arguments

        Yields:
            Mock response chunks
        """
        yield '{"status": "success", "message": "Test response"}'

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate mock embeddings.

        Args:
            text: Input text

        Returns:
            Mock embeddings
        """
        return [0.1, 0.2, 0.3] 
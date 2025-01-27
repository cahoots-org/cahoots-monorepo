"""Base interface for AI providers."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

class AIProvider(ABC):
    """Base interface for AI model providers."""
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> str:
        """Generate a response from the AI model.
        
        Args:
            prompt: The input prompt
            model: Optional model identifier to use
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Generated response
        """
        pass
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> List[List[float]]:
        """Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to embed
            model: Optional model identifier to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream a response from the AI model.
        
        Args:
            prompt: The input prompt
            model: Optional model identifier to use
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
            **kwargs: Additional provider-specific parameters
            
        Yields:
            str: Generated response chunks
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Get the number of tokens in the text.
        
        Args:
            text: Input text
            
        Returns:
            int: Number of tokens
        """
        pass 
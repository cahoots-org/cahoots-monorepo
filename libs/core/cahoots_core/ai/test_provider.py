from typing import Any, AsyncGenerator, List

from .base import AIProvider


class TestProvider(AIProvider):
    """Test provider for AI operations."""

    def __init__(self, responses: dict[str, str] | None = None):
        """Initialize the test provider.

        Args:
            responses: Optional dictionary mapping prompts to responses.
        """
        self.responses = responses or {}
        self.default_response = "Test response"
        self.default_embedding = [0.1] * 1536  # Standard OpenAI embedding size

    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """Generate a mock response.

        Args:
            prompt: The prompt to send to the model.
            **kwargs: Additional arguments to pass to the model.

        Returns:
            The mock response.
        """
        return self.responses.get(prompt, self.default_response)

    async def stream_response(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Stream a mock response.

        Args:
            prompt: The prompt to send to the model.
            **kwargs: Additional arguments to pass to the model.

        Yields:
            Chunks of the mock response.
        """
        response = self.responses.get(prompt, self.default_response)
        words = response.split()
        for word in words:
            yield word + " "

    async def generate_embeddings(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """Generate mock embeddings.

        Args:
            texts: List of texts to generate embeddings for.
            **kwargs: Additional arguments to pass to the model.

        Returns:
            List of mock embeddings.
        """
        return [self.default_embedding for _ in texts]

import pytest
from unittest.mock import MagicMock, AsyncMock
import json

@pytest.fixture
def mock_agent():
    """Create mock agent for testing."""
    agent = AsyncMock()
    agent.ai = AsyncMock()
    agent.ai.generate_response = AsyncMock(return_value=json.dumps({
        "status": "success",
        "changes": ["test change"],
        "suggestions": ["test suggestion"]
    }))
    agent.ai.stream_response = AsyncMock(return_value=AsyncMockStream(["chunk1", "chunk2"]))
    agent.config = {
        "provider": "test",
        "api_key": "test-key",
        "models": {
            "default": "test-model",
            "fallback": "test-model-fallback"
        }
    }
    return agent

class AsyncMockStream:
    """Mock async stream for testing."""
    def __init__(self, chunks):
        self.chunks = chunks
        self.index = 0
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self.index]
        self.index += 1
        return chunk 
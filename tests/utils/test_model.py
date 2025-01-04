"""Tests for the Model class."""
import pytest
from typing import TYPE_CHECKING, Dict, Any
from unittest.mock import AsyncMock, patch

from src.utils.model import Model
from src.utils.config import Config, ServiceConfig

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

@pytest.fixture
def mock_together_service() -> ServiceConfig:
    """Create a mock Together service config."""
    return ServiceConfig(
        name="together",
        url="https://api.together.xyz",
        timeout=30,
        retry_attempts=3,
        retry_delay=1,
        api_key="test_api_key"
    )

@pytest.fixture
def mock_config(monkeypatch: pytest.MonkeyPatch, mock_together_service: ServiceConfig) -> None:
    """Mock the config module."""
    services = {"together": mock_together_service}
    monkeypatch.setattr("src.utils.config.config.services", services)

@pytest.mark.asyncio
async def test_model_initialization(mock_config: None) -> None:
    """Test model initialization."""
    model = Model("test-model")
    assert model.model_name == "test-model"
    assert model.api_key == "test_api_key"
    assert model.api_base == "https://api.together.xyz/chat/completions"
    assert model.headers == {
        "Authorization": "Bearer test_api_key",
        "Content-Type": "application/json"
    }

@pytest.mark.asyncio
async def test_model_initialization_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test model initialization with no API key."""
    services: Dict[str, Any] = {}
    monkeypatch.setattr("src.utils.config.config.services", services)
    
    with pytest.raises(RuntimeError, match="Together API key not configured"):
        Model("test-model")

@pytest.mark.asyncio
async def test_generate_response(mock_config: None, mocker: "MockerFixture") -> None:
    """Test generate_response method."""
    # Mock Together API configuration
    mock_config = Config()
    mock_config.services = {
        "together": ServiceConfig(
            name="together",
            url="https://api.together.xyz",
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            api_key="test_api_key"
        )
    }
    mocker.patch("src.utils.config.config", mock_config)

    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "choices": [{"message": {"content": "Test response"}}]
    })

    # Create mock session
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    # Patch aiohttp.ClientSession
    with patch("aiohttp.ClientSession", return_value=mock_session):
        model = Model("test-model")
        response = await model.generate_response("Test prompt")
    
    assert response == "Test response"
    mock_session.post.assert_called_once_with(
        "https://api.together.xyz/chat/completions",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json"
        },
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Test prompt"}],
            "temperature": 0.7,
            "max_tokens": 1024
        }
    ) 
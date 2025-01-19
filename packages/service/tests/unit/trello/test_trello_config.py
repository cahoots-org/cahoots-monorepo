"""Tests for TrelloConfig."""
import pytest
from src.services.trello.config import TrelloConfig
from src.utils.exceptions import ConfigurationError

def test_trello_config_init() -> None:
    """Test TrelloConfig initialization."""
    config = TrelloConfig(
        api_key="test_key",
        api_token="test_token",
        base_url="https://test.trello.com"
    )
    assert config.api_key == "test_key"
    assert config.api_token == "test_token"
    assert config.base_url == "https://test.trello.com"

def test_trello_config_defaults() -> None:
    """Test TrelloConfig default values."""
    config = TrelloConfig(
        api_key="test_key",
        api_token="test_token"
    )
    assert config.base_url == "https://api.trello.com/1"
    assert config.timeout == 30

def test_trello_config_validation() -> None:
    """Test TrelloConfig validation."""
    # Test missing required fields
    with pytest.raises(ConfigurationError, match="Invalid service configuration: 1 validation error for TrelloConfig"):
        TrelloConfig(api_token="test_token")
        
    with pytest.raises(ConfigurationError, match="Invalid service configuration: 1 validation error for TrelloConfig"):
        TrelloConfig(api_key="test_key")

def test_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful config loading from environment."""
    monkeypatch.setenv("TRELLO_API_KEY", "test_key")
    monkeypatch.setenv("TRELLO_API_TOKEN", "test_token")
    monkeypatch.setenv("TRELLO_BASE_URL", "https://test.trello.com")
    
    config = TrelloConfig.from_env()
    assert config.api_key == "test_key"
    assert config.api_token == "test_token"
    assert config.base_url == "https://test.trello.com"

def test_from_env_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config loading with missing required environment variables."""
    # Clear any existing env vars
    monkeypatch.delenv("TRELLO_API_KEY", raising=False)
    monkeypatch.delenv("TRELLO_API_TOKEN", raising=False)
    
    with pytest.raises(ConfigurationError, match="Invalid service configuration: 2 validation errors for TrelloConfig"):
        TrelloConfig.from_env() 
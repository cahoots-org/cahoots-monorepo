"""Tests for TrelloConfig."""
import pytest
from src.services.trello.config import TrelloConfig
from src.utils.config import Config, ServiceConfig

def test_trello_config_init() -> None:
    """Test TrelloConfig initialization."""
    config = TrelloConfig(
        api_key="test_key",
        api_token="test_token"
    )
    assert config.api_key == "test_key"
    assert config.api_token == "test_token"
    assert config.base_url == "https://api.trello.com/1"
    assert config.timeout == 30

def test_from_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful config loading from global config."""
    mock_config = Config()
    mock_config.services = {
        "trello": ServiceConfig(
            name="trello",
            url="https://test.trello.com",
            api_key="test_key",
            api_secret="test_token",
            timeout=5,
            retry_attempts=3,
            retry_delay=1
        )
    }
    monkeypatch.setattr("src.services.trello.config.config", mock_config)
    
    config = TrelloConfig.from_config()
    assert config.api_key == "test_key"
    assert config.api_token == "test_token"
    assert config.base_url == "https://test.trello.com"
    assert config.timeout == 5

def test_from_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config loading with missing Trello config."""
    mock_config = Config()
    mock_config.services = {}
    monkeypatch.setattr("src.services.trello.config.config", mock_config)
    
    with pytest.raises(RuntimeError, match="Trello configuration missing"):
        TrelloConfig.from_config() 
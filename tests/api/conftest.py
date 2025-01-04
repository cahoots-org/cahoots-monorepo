"""API test fixtures."""
import pytest
from fastapi.testclient import TestClient
from typing import Dict, Generator

from src.api.main import app


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_key_header() -> Dict[str, str]:
    """Create API key header for authentication."""
    return {"X-API-Key": "test-api-key"} 
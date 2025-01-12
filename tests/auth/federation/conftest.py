"""Test fixtures for federation tests."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.database.models import User, IdentityProvider

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    mock.add = AsyncMock()
    mock.commit = AsyncMock()
    
    # Configure execute to return a Result object
    result = MagicMock()
    result.scalars = MagicMock(return_value=result)
    result.scalar_one_or_none = MagicMock()  # Will be configured per test
    result.all = MagicMock(return_value=[])
    
    mock.execute = AsyncMock(return_value=result)
    
    # Configure query builder methods
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None
    query.all.return_value = []
    mock.query = MagicMock(return_value=query)
    
    return mock

@pytest.fixture
def mock_k8s():
    """Create a mock Kubernetes client."""
    mock = MagicMock()
    mock.namespace = "test"
    return mock

@pytest.fixture
def mock_deps(mock_db, mock_k8s, mock_redis):
    """Create mock dependencies."""
    deps = MagicMock()
    deps.db = mock_db
    deps.k8s = mock_k8s
    deps.model = MagicMock()
    deps.github = MagicMock()
    deps.stripe = MagicMock()
    deps.redis = mock_redis
    return deps

@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=str(uuid4()),
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed",
        is_active=True,
        is_verified=True
    )

@pytest.fixture
def test_provider():
    """Create a test identity provider."""
    return IdentityProvider(
        id=str(uuid4()),
        name="Test Provider",
        type="saml",
        description="Test Provider Description",
        provider_metadata={}
    )

@pytest.fixture
def test_app(mock_deps):
    """Create a test FastAPI application."""
    from fastapi import FastAPI
    from src.auth.federation.routes import router as federation_router
    from src.core.dependencies import get_github

    app = FastAPI()
    app.include_router(federation_router)

    # Override dependencies
    app.dependency_overrides = {
        "get_deps": lambda: mock_deps,
        "get_session": lambda: mock_deps.db,
        "get_redis": lambda: mock_deps.redis,
        get_github: lambda: mock_deps.github
    }

    return app

@pytest.fixture
async def test_client(test_app):
    """Create async test client."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client
"""Context selection tests."""
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from cahoots_context.manager import ContextSelectionService
from cahoots_core.utils.dependencies import ServiceDeps

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock()
    deps.db = AsyncMock()
    deps.event_system = AsyncMock()
    deps.context_service = AsyncMock()
    return deps

@pytest.fixture
def context_service(mock_deps):
    """Create context service with mock dependencies."""
    return ContextSelectionService(deps=mock_deps)

@pytest.fixture
def sample_context():
    now = datetime.utcnow()
    return {
        "code_changes": [
            {
                "files": ["src/api/main.py"],
                "change": "Updated API endpoints",
                "timestamp": now.isoformat()
            },
            {
                "files": ["src/services/auth.py"],
                "change": "Added authentication",
                "timestamp": (now - timedelta(days=5)).isoformat()
            }
        ],
        "architectural_decisions": [
            {
                "title": "Use FastAPI",
                "description": "Chose FastAPI for better async support"
            }
        ],
        "standards": {
            "global": {
                "code_style": "PEP 8"
            },
            "python": {
                "typing": "Use type hints"
            },
            "security": {
                "auth": "Use JWT tokens"
            }
        },
        "discussions": [
            {
                "type": "code_review",
                "related_files": ["src/api/main.py"],
                "content": "Consider adding rate limiting",
                "timestamp": now.isoformat()
            }
        ],
        "patterns": [
            {
                "name": "Repository Pattern",
                "applicable_to": ["code_generation", "code_review"]
            }
        ],
        "requirements": {
            "performance": {
                "api_latency": "< 100ms"
            },
            "security": {
                "authentication": "Required for all endpoints"
            }
        }
    }

[... rest of the file remains unchanged ...] 
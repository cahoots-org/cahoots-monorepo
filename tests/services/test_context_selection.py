"""Tests for context selection service."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from src.services.context_selection import ContextSelectionService
from src.core.dependencies import ServiceDeps

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

async def test_get_llm_context_basic(context_service, mock_deps, sample_context):
    # Setup
    project_id = uuid4()
    mock_deps.context_service.get_context.return_value = sample_context
    
    # Test
    context = await context_service.get_llm_context(
        project_id=project_id,
        request_type="code_review",
        relevant_files=["src/api/main.py"]
    )
    
    # Assert
    assert all(key in context for key in ["code_changes", "architectural_decisions", "standards", "discussions", "patterns", "requirements"])
    assert all(change["files"] == ["src/api/main.py"] for change in context["code_changes"])

def test_filter_code_changes(context_service):
    # Setup
    now = datetime.utcnow()
    changes = [
        {
            "files": ["file1.py"],
            "timestamp": now.isoformat()
        },
        {
            "files": ["file2.py"],
            "timestamp": (now - timedelta(days=40)).isoformat()
        }
    ]
    
    # Test with file filtering
    filtered = context_service._filter_code_changes(
        changes,
        relevant_files=["file1.py"]
    )
    
    # Assert
    assert len(filtered) == 1
    assert filtered[0]["files"] == ["file1.py"]

def test_filter_standards(context_service):
    # Setup
    standards = {
        "global": {"style": "PEP 8"},
        "python": {"typing": "required"},
        "code_generation": {"patterns": "use factory"}
    }
    
    # Test
    filtered = context_service._filter_standards(
        standards,
        request_type="code_generation"
    )
    
    # Assert
    assert "global" in filtered
    assert "python" in filtered
    assert "code_generation" in filtered

def test_filter_discussions_scoring(context_service):
    # Setup
    now = datetime.utcnow()
    discussions = [
        {
            "type": "code_review",
            "related_files": ["file1.py"],
            "timestamp": now.isoformat()
        },
        {
            "type": "other",
            "related_files": ["file2.py"],
            "timestamp": (now - timedelta(days=5)).isoformat()
        }
    ]
    
    # Test
    filtered = context_service._filter_discussions(
        discussions,
        request_type="code_review",
        relevant_files=["file1.py"]
    )
    
    # Assert
    assert len(filtered) == 2
    assert filtered[0]["type"] == "code_review"  # Should be first due to higher score

def test_filter_patterns(context_service):
    # Setup
    patterns = [
        {
            "name": "Repository",
            "applicable_to": ["code_generation"]
        },
        {
            "name": "Factory",
            "applicable_to": ["other"]
        }
    ]
    
    # Test
    filtered = context_service._filter_patterns(
        patterns,
        request_type="code_generation"
    )
    
    # Assert
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Repository"

def test_filter_requirements(context_service):
    # Setup
    requirements = {
        "performance": {"latency": "100ms"},
        "security": {"auth": "required"},
        "functional": [
            {
                "related_files": ["file1.py"],
                "tags": ["security"]
            }
        ]
    }
    
    # Test
    filtered = context_service._filter_requirements(
        requirements,
        request_type="security_review",
        relevant_files=["file1.py"]
    )
    
    # Assert
    assert "performance" in filtered
    assert "security" in filtered
    assert len(filtered["functional"]) == 1 
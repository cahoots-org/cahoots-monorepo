"""Unit tests for context selection functionality."""
import pytest
from unittest.mock import Mock, patch
from core.utils.context_selector import ContextSelector
from core.models import Task, CodeContext

@pytest.fixture
def context_selector():
    """Create a context selector instance."""
    return ContextSelector()

@pytest.fixture
def sample_contexts():
    """Create sample code contexts for testing."""
    return [
        CodeContext(
            file_path="src/models/user.py",
            content="class User:\n    pass",
            relevance_score=0.8,
            metadata={"type": "model"}
        ),
        CodeContext(
            file_path="src/api/routes.py",
            content="@app.get('/users')\ndef get_users():\n    pass",
            relevance_score=0.9,
            metadata={"type": "api"}
        ),
        CodeContext(
            file_path="src/ui/components.py",
            content="class UserList:\n    pass",
            relevance_score=0.7,
            metadata={"type": "ui"}
        )
    ]

def test_select_contexts_by_relevance(context_selector, sample_contexts):
    """Test context selection by relevance score."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="relevance"
    )
    
    assert len(selected) == 2
    assert selected[0].file_path == "src/api/routes.py"
    assert selected[1].file_path == "src/models/user.py"

def test_select_contexts_by_type(context_selector, sample_contexts):
    """Test context selection by type."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="type",
        type_filter="model"
    )
    
    assert len(selected) == 1
    assert selected[0].file_path == "src/models/user.py"

def test_select_contexts_by_path(context_selector, sample_contexts):
    """Test context selection by file path."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="path",
        path_filter="src/api"
    )
    
    assert len(selected) == 1
    assert selected[0].file_path == "src/api/routes.py"

def test_select_contexts_empty(context_selector):
    """Test context selection with empty input."""
    selected = context_selector.select_contexts(
        [],
        max_contexts=2,
        strategy="relevance"
    )
    
    assert len(selected) == 0

def test_select_contexts_max_limit(context_selector, sample_contexts):
    """Test context selection with max limit."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=1,
        strategy="relevance"
    )
    
    assert len(selected) == 1
    assert selected[0].file_path == "src/api/routes.py"

def test_select_contexts_invalid_strategy(context_selector, sample_contexts):
    """Test context selection with invalid strategy."""
    with pytest.raises(ValueError):
        context_selector.select_contexts(
            sample_contexts,
            max_contexts=2,
            strategy="invalid"
        )

def test_select_contexts_no_matches(context_selector, sample_contexts):
    """Test context selection with no matching contexts."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="type",
        type_filter="nonexistent"
    )
    
    assert len(selected) == 0

def test_select_contexts_combine_strategies(context_selector, sample_contexts):
    """Test context selection with combined strategies."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="combined",
        type_filter="model",
        path_filter="src/models"
    )
    
    assert len(selected) == 1
    assert selected[0].file_path == "src/models/user.py"

def test_select_contexts_metadata_filter(context_selector, sample_contexts):
    """Test context selection with metadata filter."""
    selected = context_selector.select_contexts(
        sample_contexts,
        max_contexts=2,
        strategy="metadata",
        metadata_filter={"type": "api"}
    )
    
    assert len(selected) == 1
    assert selected[0].file_path == "src/api/routes.py" 
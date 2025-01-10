"""Tests for the feedback manager module."""
import pytest
from unittest.mock import Mock, AsyncMock
import time
import logging

from src.agents.developer.feedback_manager import FeedbackManager

# Set logging level to debug to capture similarity scores
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = Mock()
    agent.generate_embedding = Mock()
    return agent

@pytest.fixture
def feedback_manager(mock_agent):
    """Create a feedback manager instance."""
    return FeedbackManager(mock_agent)

@pytest.fixture
def sample_feedback():
    """Create sample feedback entries."""
    current_time = time.time()
    return [
        {
            "type": "review",
            "content": "Add error handling for edge cases",
            "context": "function process_data(data)",
            "outcome": "failure",
            "timestamp": current_time  # Most recent
        },
        {
            "type": "implementation",
            "content": "Good use of type hints and docstrings",
            "context": "class DataProcessor",
            "code": "def process(self, data: List[Dict]): ...",
            "outcome": "success",
            "timestamp": current_time - 3600  # 1 hour ago
        }
    ]

def test_init(feedback_manager):
    """Test feedback manager initialization."""
    # Test behavior: New manager should return no relevant feedback
    context = "any context"
    assert len(feedback_manager.get_relevant_feedback(context)) == 0

def test_integrate_and_retrieve_feedback(feedback_manager, mock_agent):
    """Test the full feedback lifecycle - integration and retrieval."""
    # Setup realistic embeddings for similarity
    mock_agent.generate_embedding.side_effect = [
        [1.0, 0.0, 0.0],  # Query context for first search
        [0.9, 0.1, 0.0],  # Similar feedback (similarity = 0.9)
        [0.1, 0.9, 0.0],  # Different feedback (similarity = 0.1)
        [0.0, 0.0, 1.0],  # Query context for second search
        [0.1, 0.1, 0.1],  # Similar feedback (similarity = 0.1)
        [0.1, 0.1, 0.1],  # Different feedback (similarity = 0.1)
    ]
    
    # Test behavior: Feedback should be retrievable when context is similar
    similar_feedback = {
        "type": "review",
        "content": "Add error handling",
        "context": "error handling in process_data",
        "outcome": "failure"
    }
    different_feedback = {
        "type": "review",
        "content": "Improve UI layout",
        "context": "dashboard component",
        "outcome": "success"
    }
    
    feedback_manager.integrate_feedback(similar_feedback)
    feedback_manager.integrate_feedback(different_feedback)
    
    # When querying with similar context
    relevant = feedback_manager.get_relevant_feedback("error handling function")
    assert len(relevant) == 1
    assert relevant[0]["content"] == "Add error handling"
    
    # When querying with different context
    irrelevant = feedback_manager.get_relevant_feedback("database schema")
    assert len(irrelevant) == 0

def test_feedback_relevance_ordering(feedback_manager, mock_agent):
    """Test that feedback is ordered by relevance and recency."""
    # Setup embeddings with different similarity scores
    mock_agent.generate_embedding.side_effect = [
        [1.0, 0.0, 0.0],      # Query context
        [0.95, 0.05, 0.0],    # Most similar
        [0.90, 0.10, 0.0],    # Similar but less so
        [0.85, 0.15, 0.0],    # Least similar but still relevant
    ]
    
    # Create feedback entries with different timestamps
    feedbacks = [
        {
            "content": "Most similar feedback",
            "context": "very similar context",
            "outcome": "success",
            "timestamp": 1000
        },
        {
            "content": "Similar feedback",
            "context": "somewhat similar context",
            "outcome": "failure",
            "timestamp": 2000
        },
        {
            "content": "Less similar feedback",
            "context": "less similar context",
            "outcome": "success",
            "timestamp": 3000
        }
    ]
    
    # Add feedback in arbitrary order
    for feedback in feedbacks:
        feedback_manager.integrate_feedback(feedback)
    
    # Test behavior: Results should be ordered by similarity
    results = feedback_manager.get_relevant_feedback("test context")
    assert len(results) == 3
    
    # Verify ordering by checking similarity scores
    similarities = []
    for result in results:
        idx = feedbacks.index(result)
        similarity = 0.95 - (idx * 0.05)  # Based on our mock embeddings
        similarities.append(similarity)
    
    # Verify results are ordered by decreasing similarity
    assert similarities == sorted(similarities, reverse=True)

def test_feedback_formatting(feedback_manager):
    """Test that feedback is formatted appropriately for different types."""
    # Success feedback
    success_feedback = [{
        "type": "implementation",
        "content": "Good implementation",
        "code": "def example(): pass",
        "outcome": "success"
    }]
    success_format = feedback_manager.format_feedback_for_prompt(success_feedback)
    assert "Success Pattern" in success_format
    assert "def example(): pass" in success_format
    
    # Failure feedback
    failure_feedback = [{
        "type": "review",
        "content": "Missing error handling",
        "outcome": "failure"
    }]
    failure_format = feedback_manager.format_feedback_for_prompt(failure_feedback)
    assert "Issues to Avoid" in failure_format
    assert "Missing error handling" in failure_format
    
    # Empty feedback
    empty_format = feedback_manager.format_feedback_for_prompt([])
    assert "No relevant" in empty_format
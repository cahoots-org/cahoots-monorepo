"""Unit tests for the unified analyzer."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import json

from app.analyzer import UnifiedAnalyzer, MockLLMClient
from app.models import TaskAnalysis, TaskDecomposition, ApproachType


class TestUnifiedAnalyzer:
    """Test suite for UnifiedAnalyzer."""

    @pytest_asyncio.fixture
    async def mock_llm_client(self):
        """Create a mock LLM client."""
        return MockLLMClient()

    @pytest_asyncio.fixture
    async def analyzer(self, mock_llm_client):
        """Create an analyzer with mock LLM."""
        return UnifiedAnalyzer(mock_llm_client)

    @pytest.mark.asyncio
    async def test_analyze_simple_task(self, analyzer, mock_llm_client):
        """Test analyzing a simple atomic task."""
        # Configure mock response
        mock_llm_client.responses = [{
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "complexity_score": 0.2,
                        "is_atomic": True,
                        "is_specific": True,
                        "confidence": 0.95,
                        "reasoning": "Simple CRUD operation",
                        "suggested_approach": "implement",
                        "implementation_hints": "Use standard REST endpoints",
                        "estimated_story_points": 2,
                        "requires_human_review": False,
                        "similar_patterns": ["CRUD"],
                        "missing_details": [],
                        "dependencies": [],
                        "risk_factors": []
                    })
                }
            }]
        }]

        # Analyze task
        result = await analyzer.analyze_task("Create a user registration endpoint")

        # Verify result
        assert isinstance(result, TaskAnalysis)
        assert result.complexity_score == 0.2
        assert result.is_atomic is True
        assert result.is_specific is True
        assert result.confidence == 0.95
        assert result.suggested_approach == ApproachType.IMPLEMENT
        assert result.implementation_hints == "Use standard REST endpoints"
        assert result.estimated_story_points == 2
        assert "CRUD" in result.similar_patterns

    @pytest.mark.asyncio
    async def test_analyze_complex_task(self, analyzer, mock_llm_client):
        """Test analyzing a complex task that needs decomposition."""
        # Configure mock response
        mock_llm_client.responses = [{
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "complexity_score": 0.8,
                        "is_atomic": False,
                        "is_specific": True,
                        "confidence": 0.85,
                        "reasoning": "Complex system requiring multiple components",
                        "suggested_approach": "decompose",
                        "implementation_hints": None,
                        "estimated_story_points": 21,
                        "requires_human_review": False,
                        "similar_patterns": ["microservices", "distributed-system"],
                        "missing_details": ["scaling requirements"],
                        "dependencies": ["infrastructure", "authentication"],
                        "risk_factors": ["performance", "data consistency"]
                    })
                }
            }]
        }]

        # Analyze task
        result = await analyzer.analyze_task(
            "Build a distributed task processing system",
            depth=0
        )

        # Verify result
        assert result.complexity_score == 0.8
        assert result.is_atomic is False
        assert result.suggested_approach == ApproachType.DECOMPOSE
        assert result.implementation_hints is None
        assert result.estimated_story_points == 21
        assert "scaling requirements" in result.missing_details
        assert "performance" in result.risk_factors

    @pytest.mark.asyncio
    async def test_analyze_with_context(self, analyzer, mock_llm_client):
        """Test analyzing with context (tech stack, best practices)."""
        context = {
            "tech_stack": "Python, FastAPI, Redis",
            "best_practices": "Use async/await, follow PEP8"
        }

        result = await analyzer.analyze_task(
            "Implement caching layer",
            context=context,
            depth=1
        )

        # Verify context was used in the prompt
        assert len(mock_llm_client.call_history) == 1
        system_prompt = mock_llm_client.call_history[0]["messages"][0]["content"]
        assert "Python, FastAPI, Redis" in system_prompt
        assert "PEP8" in system_prompt

    @pytest.mark.asyncio
    async def test_analyze_error_handling(self, analyzer):
        """Test error handling in analysis."""
        # Create a client that will raise an error
        error_client = MockLLMClient()
        error_client.chat_completion = AsyncMock(side_effect=Exception("API error"))
        analyzer = UnifiedAnalyzer(error_client)

        result = await analyzer.analyze_task("Test task")

        # Should return conservative defaults
        assert result.complexity_score == 0.7
        assert result.is_atomic is False
        assert result.suggested_approach == ApproachType.HUMAN_REVIEW
        assert result.requires_human_review is True
        assert "Analysis failed" in result.reasoning

    @pytest.mark.asyncio
    async def test_decompose_task(self, analyzer, mock_llm_client):
        """Test task decomposition with inline analysis."""
        # Configure mock response
        mock_llm_client.responses = [{
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "subtasks": [
                            {
                                "description": "Set up database schema",
                                "is_atomic": True,
                                "implementation_details": "Create users and posts tables",
                                "story_points": 3,
                                "dependencies": [],
                                "parallel_group": 0
                            },
                            {
                                "description": "Create API endpoints",
                                "is_atomic": False,
                                "implementation_details": None,
                                "story_points": 8,
                                "dependencies": [0],
                                "parallel_group": 1
                            },
                            {
                                "description": "Add authentication",
                                "is_atomic": True,
                                "implementation_details": "Use JWT tokens",
                                "story_points": 5,
                                "dependencies": [0],
                                "parallel_group": 1
                            }
                        ],
                        "decomposition_reasoning": "Split into data, API, and auth layers",
                        "estimated_total_points": 16,
                        "suggested_order": [0, 1, 2],
                        "parallel_groups": [[0], [1, 2]]
                    })
                }
            }]
        }]

        # Decompose task
        result = await analyzer.decompose_task(
            "Build a blog application",
            max_subtasks=5,
            depth=0
        )

        # Verify result
        assert isinstance(result, TaskDecomposition)
        assert len(result.subtasks) == 3

        # Check first subtask
        first = result.subtasks[0]
        assert first["description"] == "Set up database schema"
        assert first["is_atomic"] is True
        assert first["implementation_details"] == "Create users and posts tables"
        assert first["story_points"] == 3

        # Check decomposition metadata
        assert result.decomposition_reasoning == "Split into data, API, and auth layers"
        assert result.estimated_total_points == 16
        assert result.suggested_order == [0, 1, 2]
        assert result.parallel_groups == [[0], [1, 2]]

        # Check helper methods
        atomic_tasks = result.get_atomic_tasks()
        assert len(atomic_tasks) == 2
        complex_tasks = result.get_complex_tasks()
        assert len(complex_tasks) == 1

    @pytest.mark.asyncio
    async def test_decompose_with_max_subtasks(self, analyzer, mock_llm_client):
        """Test that decomposition respects max_subtasks limit."""
        # Configure mock with too many subtasks
        mock_llm_client.responses = [{
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "subtasks": [
                            {"description": f"Task {i}", "is_atomic": True, "story_points": 2}
                            for i in range(10)
                        ],
                        "decomposition_reasoning": "Many subtasks"
                    })
                }
            }]
        }]

        result = await analyzer.decompose_task(
            "Complex task",
            max_subtasks=3
        )

        # Should be limited to 3 subtasks
        assert len(result.subtasks) == 3

    @pytest.mark.asyncio
    async def test_decompose_error_handling(self, analyzer):
        """Test error handling in decomposition."""
        # Create a client that will raise an error
        error_client = MockLLMClient()
        error_client.chat_completion = AsyncMock(side_effect=Exception("API error"))
        analyzer = UnifiedAnalyzer(error_client)

        result = await analyzer.decompose_task("Test task")

        # Should return fallback decomposition
        assert len(result.subtasks) == 1
        assert result.subtasks[0]["description"] == "Test task"
        assert result.subtasks[0]["is_atomic"] is True
        assert "Decomposition failed" in result.decomposition_reasoning

    @pytest.mark.asyncio
    async def test_decompose_malformed_response(self, analyzer, mock_llm_client):
        """Test handling of malformed LLM responses."""
        # Configure mock with malformed response
        mock_llm_client.responses = [{
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "subtasks": "not a list",  # Wrong type
                        "decomposition_reasoning": "Bad response"
                    })
                }
            }]
        }]

        result = await analyzer.decompose_task("Test task")

        # Should handle gracefully
        assert isinstance(result.subtasks, list)
        assert len(result.subtasks) == 0
        assert result.decomposition_reasoning == "Bad response"

    @pytest.mark.asyncio
    async def test_mock_llm_client(self):
        """Test the mock LLM client itself."""
        mock = MockLLMClient()

        # Test default response
        response = await mock.chat_completion(
            [{"role": "user", "content": "Test"}],
            temperature=0.5
        )

        assert "choices" in response
        assert len(mock.call_history) == 1
        assert mock.call_history[0]["temperature"] == 0.5

        # Test generate_json method
        result = await mock.generate_json(
            "System prompt",
            "User prompt"
        )

        assert isinstance(result, dict)
        assert "complexity_score" in result
        assert result["is_atomic"] is False
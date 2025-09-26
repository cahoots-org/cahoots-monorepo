"""Unit tests for the cache system."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from app.cache import CacheManager, SemanticCache, TemplateCache
from app.models import TaskAnalysis, TaskDecomposition, ApproachType
from app.storage import RedisClient


class TestTemplateCache:
    """Test suite for TemplateCache."""

    @pytest.fixture
    def template_cache(self):
        """Create a template cache instance."""
        return TemplateCache()

    def test_crud_pattern_matching(self, template_cache):
        """Test CRUD pattern recognition."""
        crud_descriptions = [
            "Create CRUD operations for users",
            "Build REST API for products",
            "Implement user management system",
            "Add API endpoints for items"
        ]

        for desc in crud_descriptions:
            analysis = template_cache.get_analysis_template(desc)
            assert analysis is not None
            assert "CRUD" in analysis.similar_patterns
            assert analysis.suggested_approach == ApproachType.DECOMPOSE

    def test_authentication_pattern_matching(self, template_cache):
        """Test authentication pattern recognition."""
        auth_descriptions = [
            "Implement user authentication",
            "Add signin and signup functionality",
            "Create JWT token system",
            "Build user authentication"
        ]

        for desc in auth_descriptions:
            analysis = template_cache.get_analysis_template(desc)
            assert analysis is not None
            assert "auth" in analysis.similar_patterns
            assert analysis.complexity_score >= 0.3

    def test_api_endpoint_pattern_matching(self, template_cache):
        """Test API endpoint pattern recognition."""
        api_descriptions = [
            "Create user registration endpoint",
            "Add GET route for products",
            "Implement POST endpoint for orders"
        ]

        for desc in api_descriptions:
            analysis = template_cache.get_analysis_template(desc)
            assert analysis is not None
            assert analysis.is_atomic is True
            assert analysis.suggested_approach == ApproachType.IMPLEMENT

    def test_depth_complexity_adjustment(self, template_cache):
        """Test that complexity is adjusted based on depth."""
        desc = "Create CRUD operations for users"

        # Analysis at different depths
        depth_0 = template_cache.get_analysis_template(desc, depth=0)
        depth_2 = template_cache.get_analysis_template(desc, depth=2)

        assert depth_0 is not None
        assert depth_2 is not None
        assert depth_2.complexity_score < depth_0.complexity_score

    def test_crud_decomposition_template(self, template_cache):
        """Test CRUD decomposition template."""
        decomp = template_cache.get_decomposition_template("Create CRUD API for users")
        assert decomp is not None
        assert len(decomp.subtasks) == 6
        assert decomp.estimated_total_points == 11

        # Check first subtask
        first_task = decomp.subtasks[0]
        assert "data model" in first_task["description"].lower()
        assert first_task["is_atomic"] is True

    def test_authentication_decomposition_template(self, template_cache):
        """Test authentication decomposition template."""
        decomp = template_cache.get_decomposition_template("Implement user authentication")
        assert decomp is not None
        assert len(decomp.subtasks) == 6
        assert "jwt" in decomp.decomposition_reasoning.lower()

    def test_no_pattern_match(self, template_cache):
        """Test that non-matching descriptions return None."""
        non_matching = [
            "Solve world hunger",
            "Build a time machine",
            "Calculate pi to infinite precision"
        ]

        for desc in non_matching:
            analysis = template_cache.get_analysis_template(desc)
            decomp = template_cache.get_decomposition_template(desc)
            assert analysis is None
            assert decomp is None

    def test_available_patterns(self, template_cache):
        """Test getting available patterns."""
        patterns = template_cache.get_available_patterns()
        expected_patterns = ["crud", "authentication", "api_endpoint", "database_setup", "unit_test", "ui_component", "deployment"]

        for pattern in expected_patterns:
            assert pattern in patterns


class TestSemanticCache:
    """Test suite for SemanticCache."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock(spec=RedisClient)
        redis.keys = AsyncMock(return_value=[])
        redis.mget = AsyncMock(return_value=[])
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        return redis

    @pytest_asyncio.fixture
    async def semantic_cache(self, mock_redis):
        """Create a semantic cache instance."""
        return SemanticCache(mock_redis)

    @pytest.mark.asyncio
    async def test_simple_embedding_generation(self, semantic_cache):
        """Test simple embedding generation."""
        embedding = semantic_cache._simple_embedding("create user authentication")
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_store_and_find_analysis(self, semantic_cache, mock_redis):
        """Test storing and finding similar analysis."""
        # Create test analysis
        analysis = TaskAnalysis(
            complexity_score=0.5,
            is_atomic=False,
            is_specific=True,
            confidence=0.85,
            reasoning="Test analysis",
            suggested_approach=ApproachType.DECOMPOSE
        )

        # Store analysis
        await semantic_cache.store_analysis("create user authentication", analysis)

        # Verify storage was called
        assert mock_redis.set.called

        # Mock finding similar analysis
        stored_data = {
            "description": "create user authentication",
            "embedding": semantic_cache._simple_embedding("create user authentication"),
            "result": analysis.model_dump()
        }
        mock_redis.keys.return_value = ["cache:semantic:analysis:123"]
        mock_redis.mget.return_value = [stored_data]

        # Find similar analysis
        found = await semantic_cache.find_similar_analysis("implement user auth", threshold=0.5)
        assert found is not None
        assert found.complexity_score == 0.5

    @pytest.mark.asyncio
    async def test_no_similar_analysis_found(self, semantic_cache, mock_redis):
        """Test when no similar analysis is found."""
        mock_redis.keys.return_value = []

        found = await semantic_cache.find_similar_analysis("completely different task")
        assert found is None

    @pytest.mark.asyncio
    async def test_store_and_find_decomposition(self, semantic_cache, mock_redis):
        """Test storing and finding similar decomposition."""
        decomp = TaskDecomposition(
            subtasks=[
                {
                    "description": "Create user model",
                    "is_atomic": True,
                    "story_points": 3
                }
            ],
            decomposition_reasoning="Test decomposition"
        )

        # Store decomposition
        await semantic_cache.store_decomposition("build user system", decomp)
        assert mock_redis.set.called

        # Mock finding similar decomposition
        stored_data = {
            "description": "build user system",
            "embedding": semantic_cache._simple_embedding("build user system"),
            "result": decomp.model_dump()
        }
        mock_redis.keys.return_value = ["cache:semantic:decomp:456"]
        mock_redis.mget.return_value = [stored_data]

        # Find similar decomposition
        found = await semantic_cache.find_similar_decomposition("create user management", threshold=0.5)
        assert found is not None
        assert len(found.subtasks) == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, semantic_cache, mock_redis):
        """Test clearing the cache."""
        mock_redis.keys.side_effect = [
            ["cache:semantic:analysis:1", "cache:semantic:analysis:2"],
            ["cache:semantic:decomp:1"]
        ]

        await semantic_cache.clear()

        # Should call keys twice and delete once
        assert mock_redis.keys.call_count == 2
        assert mock_redis.delete.called


class TestCacheManager:
    """Test suite for CacheManager."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock(spec=RedisClient)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.keys = AsyncMock(return_value=[])
        redis.delete = AsyncMock(return_value=1)
        return redis

    @pytest_asyncio.fixture
    async def cache_manager(self, mock_redis):
        """Create a cache manager instance."""
        return CacheManager(mock_redis, use_semantic_cache=True)

    @pytest.mark.asyncio
    async def test_cache_miss_all_levels(self, cache_manager, mock_redis):
        """Test cache miss at all levels."""
        # Configure mocks for misses
        mock_redis.get.return_value = None  # Exact cache miss
        cache_manager.semantic_cache.find_similar_analysis = AsyncMock(return_value=None)

        # Try to get analysis
        result = await cache_manager.get_analysis("unique task description")
        assert result is None

        # Check stats
        stats = cache_manager.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["total_requests"] == 1

    @pytest.mark.asyncio
    async def test_exact_cache_hit(self, cache_manager, mock_redis):
        """Test exact cache hit."""
        # Mock exact cache hit
        cached_analysis = {
            "complexity_score": 0.5,
            "is_atomic": False,
            "is_specific": True,
            "confidence": 0.85,
            "reasoning": "Cached analysis",
            "suggested_approach": "decompose"
        }
        mock_redis.get.return_value = cached_analysis

        result = await cache_manager.get_analysis("test task")
        assert result is not None
        assert result.complexity_score == 0.5

        # Check stats
        stats = cache_manager.get_cache_stats()
        assert stats["exact_hits"] == 1
        assert stats["hit_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_semantic_cache_hit(self, cache_manager, mock_redis):
        """Test semantic cache hit."""
        # Configure exact cache miss
        mock_redis.get.return_value = None

        # Configure semantic cache hit
        semantic_analysis = TaskAnalysis(
            complexity_score=0.6,
            is_atomic=True,
            is_specific=True,
            confidence=0.8,
            reasoning="Semantic match",
            suggested_approach=ApproachType.IMPLEMENT
        )
        cache_manager.semantic_cache.find_similar_analysis = AsyncMock(return_value=semantic_analysis)

        result = await cache_manager.get_analysis("similar task")
        assert result is not None
        assert result.complexity_score == 0.6

        # Check stats
        stats = cache_manager.get_cache_stats()
        assert stats["semantic_hits"] == 1

    @pytest.mark.asyncio
    async def test_template_cache_hit(self, cache_manager, mock_redis):
        """Test template cache hit."""
        # Configure exact and semantic cache misses
        mock_redis.get.return_value = None
        cache_manager.semantic_cache.find_similar_analysis = AsyncMock(return_value=None)

        # Use a description that should match template
        result = await cache_manager.get_analysis("create CRUD operations for users")
        assert result is not None
        assert "CRUD" in result.similar_patterns

        # Check stats
        stats = cache_manager.get_cache_stats()
        assert stats["template_hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_analysis(self, cache_manager, mock_redis):
        """Test caching an analysis."""
        analysis = TaskAnalysis(
            complexity_score=0.7,
            is_atomic=False,
            is_specific=True,
            confidence=0.9,
            reasoning="Test caching",
            suggested_approach=ApproachType.DECOMPOSE
        )

        await cache_manager.cache_analysis("test task", analysis)

        # Should cache in exact cache
        assert mock_redis.set.called

        # Should cache in semantic cache (mock the method call)
        cache_manager.semantic_cache.store_analysis = AsyncMock()
        await cache_manager.cache_analysis("test task", analysis)
        assert cache_manager.semantic_cache.store_analysis.called

    @pytest.mark.asyncio
    async def test_decomposition_caching(self, cache_manager, mock_redis):
        """Test decomposition caching."""
        decomp = TaskDecomposition(
            subtasks=[{"description": "subtask 1", "is_atomic": True}],
            decomposition_reasoning="test"
        )

        # Cache decomposition
        await cache_manager.cache_decomposition("test task", decomp)
        assert mock_redis.set.called

        # Test retrieval (mock cache hit)
        mock_redis.get.return_value = decomp.model_dump()

        result = await cache_manager.get_decomposition("test task")
        assert result is not None
        assert len(result.subtasks) == 1

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager, mock_redis):
        """Test cache invalidation."""
        mock_redis.keys.return_value = ["cache:exact:pattern1", "cache:exact:pattern2"]

        deleted = await cache_manager.invalidate_pattern("pattern")
        assert deleted == 1
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_manager, mock_redis):
        """Test clearing all cache."""
        mock_redis.keys.side_effect = [
            ["cache:analysis:1", "cache:analysis:2"],  # Analysis keys
            ["cache:decomp:1"],  # Decomposition keys
            [],  # Semantic analysis keys (empty)
            []   # Semantic decomp keys (empty)
        ]

        await cache_manager.clear_cache()

        assert mock_redis.keys.call_count >= 2
        assert mock_redis.delete.called

        # Stats should be reset
        stats = cache_manager.get_cache_stats()
        assert stats["total_requests"] == 0

    def test_cache_stats_calculation(self, cache_manager):
        """Test cache statistics calculation."""
        # Simulate some cache activity
        cache_manager.stats = {
            "exact_hits": 10,
            "semantic_hits": 5,
            "template_hits": 3,
            "misses": 2,
            "total_requests": 20
        }

        stats = cache_manager.get_cache_stats()
        assert stats["hit_rate"] == 0.9  # 18/20
        assert stats["exact_hit_rate"] == 0.5  # 10/20
        assert stats["semantic_hit_rate"] == 0.25  # 5/20
        assert stats["template_hit_rate"] == 0.15  # 3/20
        assert stats["miss_rate"] == 0.1  # 2/20

    def test_cache_stats_no_requests(self, cache_manager):
        """Test cache stats when no requests made."""
        stats = cache_manager.get_cache_stats()
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 0
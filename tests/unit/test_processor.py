"""Tests for task processor components."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional

from app.processor import TaskProcessor, ProcessingRules, ProcessingConfig
from app.models import Task, TaskStatus, TaskAnalysis, TaskDecomposition, ApproachType
from app.storage import TaskStorage
from app.analyzer import UnifiedAnalyzer
from app.cache import CacheManager


@pytest_asyncio.fixture
async def mock_storage():
    """Mock task storage."""
    storage = Mock(spec=TaskStorage)
    storage.save_task = AsyncMock()
    storage.get_task = AsyncMock()
    storage.save_task_tree = AsyncMock()
    storage.get_children = AsyncMock(return_value=[])
    return storage


@pytest_asyncio.fixture
async def mock_analyzer():
    """Mock unified analyzer."""
    analyzer = Mock(spec=UnifiedAnalyzer)
    analyzer.analyze_task = AsyncMock()
    analyzer.decompose_task = AsyncMock()
    return analyzer


@pytest_asyncio.fixture
async def mock_cache():
    """Mock cache manager."""
    cache = Mock(spec=CacheManager)
    cache.get_analysis = AsyncMock(return_value=None)
    cache.cache_analysis = AsyncMock()
    cache.get_decomposition = AsyncMock(return_value=None)
    cache.cache_decomposition = AsyncMock()
    cache.get_cache_stats = Mock(return_value={"hit_rate": 0.5})
    return cache


@pytest_asyncio.fixture
async def processing_config():
    """Processing configuration."""
    return ProcessingConfig(
        max_depth=3,
        complexity_threshold=0.5,
        batch_sibling_threshold=3
    )


@pytest_asyncio.fixture
async def processor(mock_storage, mock_analyzer, mock_cache, processing_config):
    """Task processor instance."""
    return TaskProcessor(mock_storage, mock_analyzer, mock_cache, processing_config)


class TestProcessingRules:
    """Test processing rules engine."""

    def test_should_decompose_atomic_task(self):
        """Test that atomic tasks are not decomposed."""
        rules = ProcessingRules()
        task = Task(description="Test", depth=1)
        analysis = TaskAnalysis(
            complexity_score=0.8,
            is_atomic=True,
            is_specific=True,
            confidence=0.9,
            reasoning="Already atomic",
            suggested_approach=ApproachType.IMPLEMENT
        )

        assert not rules.should_decompose(task, analysis)

    def test_should_decompose_complex_task(self):
        """Test that complex non-atomic tasks are decomposed."""
        rules = ProcessingRules()
        task = Task(description="Build a web application", depth=1)
        analysis = TaskAnalysis(
            complexity_score=0.8,
            is_atomic=False,
            is_specific=True,
            confidence=0.9,
            reasoning="Complex task",
            suggested_approach=ApproachType.DECOMPOSE
        )

        assert rules.should_decompose(task, analysis)

    def test_should_not_decompose_at_max_depth(self):
        """Test that tasks at max depth are not decomposed."""
        config = ProcessingConfig(force_atomic_depth=2)
        rules = ProcessingRules(config)
        task = Task(description="Test", depth=2)
        analysis = TaskAnalysis(
            complexity_score=0.8,
            is_atomic=False,
            is_specific=True,
            confidence=0.9,
            reasoning="At max depth",
            suggested_approach=ApproachType.DECOMPOSE
        )

        assert not rules.should_decompose(task, analysis)

    def test_should_batch_process_multiple_siblings(self):
        """Test batching with multiple siblings."""
        config = ProcessingConfig(batch_sibling_threshold=3)
        rules = ProcessingRules(config)

        # Should batch with 3+ siblings at depth 2+
        assert rules.should_batch_process(sibling_count=4, depth=2)

        # Should not batch at shallow depth
        assert not rules.should_batch_process(sibling_count=4, depth=1)

        # Should not batch with few siblings
        assert not rules.should_batch_process(sibling_count=2, depth=2)

    def test_should_require_human_review(self):
        """Test human review requirements."""
        rules = ProcessingRules()
        task = Task(description="Critical security task", depth=0)

        # Low confidence should require review
        analysis = TaskAnalysis(
            complexity_score=0.5,
            is_atomic=False,
            is_specific=True,
            confidence=0.4,  # Low confidence
            reasoning="Uncertain",
            suggested_approach=ApproachType.DECOMPOSE
        )
        assert rules.should_require_human_review(task, analysis)

        # Explicit requirement should require review
        analysis.confidence = 0.8
        analysis.requires_human_review = True
        assert rules.should_require_human_review(task, analysis)

    def test_get_processing_priority(self):
        """Test processing priority calculation."""
        rules = ProcessingRules()

        # Shallow atomic task should have high priority
        task = Task(description="Simple task", depth=1)
        analysis = TaskAnalysis(
            complexity_score=0.3,
            is_atomic=True,
            is_specific=True,
            confidence=0.9,
            reasoning="Simple and atomic",
            suggested_approach=ApproachType.IMPLEMENT
        )

        priority = rules.get_processing_priority(task, analysis)
        assert priority > 100  # Should be high priority

    def test_get_max_subtasks(self):
        """Test max subtasks calculation."""
        rules = ProcessingRules()
        task = Task(description="Complex task", depth=1)

        # High complexity should allow more subtasks
        analysis = TaskAnalysis(
            complexity_score=0.9,
            is_atomic=False,
            is_specific=True,
            confidence=0.8,
            reasoning="Very complex",
            suggested_approach=ApproachType.DECOMPOSE
        )

        max_subtasks = rules.get_max_subtasks(task, analysis)
        assert max_subtasks >= 7  # Should allow more for complex tasks


class TestTaskProcessor:
    """Test task processor."""

    @pytest.mark.asyncio
    async def test_process_atomic_task(self, processor, mock_analyzer):
        """Test processing of atomic task."""
        # Mock atomic analysis
        mock_analyzer.analyze_task.return_value = TaskAnalysis(
            complexity_score=0.3,
            is_atomic=True,
            is_specific=True,
            confidence=0.9,
            reasoning="Simple task",
            suggested_approach=ApproachType.IMPLEMENT,
            implementation_hints="Just implement directly",
            estimated_story_points=2
        )

        # Process task
        tree = await processor.process_task_complete(
            "Create a hello world function",
            user_id="test-user"
        )

        # Verify results
        assert tree.root.is_atomic
        assert tree.root.status == TaskStatus.COMPLETED
        assert tree.root.story_points == 2
        assert tree.root.implementation_details == "Just implement directly"
        assert len(tree.tasks) == 1  # Only root task

    @pytest.mark.asyncio
    async def test_process_complex_task(self, processor, mock_analyzer):
        """Test processing of complex task that needs decomposition."""
        # Configure analyzer to return different results based on task description
        def analyze_side_effect(description, context=None, depth=0):
            if "Build a user management system" in description:
                # Root task - complex
                return TaskAnalysis(
                    complexity_score=0.8,
                    is_atomic=False,
                    is_specific=True,
                    confidence=0.9,
                    reasoning="Complex task",
                    suggested_approach=ApproachType.DECOMPOSE,
                    estimated_story_points=8
                )
            else:
                # Subtasks - atomic
                return TaskAnalysis(
                    complexity_score=0.3,
                    is_atomic=True,
                    is_specific=True,
                    confidence=0.9,
                    reasoning="Simple subtask",
                    suggested_approach=ApproachType.IMPLEMENT,
                    implementation_hints="Direct implementation",
                    estimated_story_points=3
                )

        mock_analyzer.analyze_task.side_effect = analyze_side_effect

        # Mock decomposition
        mock_analyzer.decompose_task.return_value = TaskDecomposition(
            subtasks=[
                {
                    "description": "Setup authentication",
                    "is_atomic": True,
                    "implementation_details": "Use JWT tokens",
                    "story_points": 3
                },
                {
                    "description": "Create user interface",
                    "is_atomic": True,
                    "implementation_details": "Build React components",
                    "story_points": 5
                }
            ],
            decomposition_reasoning="Split into auth and UI"
        )

        # Process task
        tree = await processor.process_task_complete(
            "Build a user management system",
            user_id="test-user",
            max_depth=2
        )

        # Verify results
        assert not tree.root.is_atomic
        assert tree.root.status == TaskStatus.COMPLETED
        assert len(tree.root.subtasks) == 2
        assert len(tree.tasks) == 3  # Root + 2 subtasks

    @pytest.mark.asyncio
    async def test_max_depth_handling(self, processor, mock_analyzer):
        """Test that max depth is respected."""
        # Mock analysis that would normally decompose
        mock_analyzer.analyze_task.return_value = TaskAnalysis(
            complexity_score=0.8,
            is_atomic=False,
            is_specific=True,
            confidence=0.9,
            reasoning="Complex task",
            suggested_approach=ApproachType.DECOMPOSE
        )

        # Process with max depth 0
        tree = await processor.process_task_complete(
            "Complex task",
            user_id="test-user",
            max_depth=0  # Force atomic at root
        )

        # Should be treated as atomic due to depth limit
        assert tree.root.is_atomic
        assert tree.root.status == TaskStatus.COMPLETED
        assert len(tree.tasks) == 1

    @pytest.mark.asyncio
    async def test_caching_behavior(self, processor, mock_cache, mock_analyzer):
        """Test that caching is used appropriately."""
        # Setup cache hit
        cached_analysis = TaskAnalysis(
            complexity_score=0.3,
            is_atomic=True,
            is_specific=True,
            confidence=0.9,
            reasoning="Cached result",
            suggested_approach=ApproachType.IMPLEMENT
        )
        mock_cache.get_analysis.return_value = cached_analysis

        # Process task
        await processor.process_task_complete(
            "Cached task",
            user_id="test-user"
        )

        # Verify cache was checked
        mock_cache.get_analysis.assert_called_once()
        # Analyzer should not be called due to cache hit
        mock_analyzer.analyze_task.assert_not_called()

        # Verify stats were updated
        assert processor.stats["cache_hits"] == 1
        assert processor.stats["llm_calls_saved"] == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, processor, mock_analyzer):
        """Test error handling during processing."""
        # Mock analyzer to raise exception
        mock_analyzer.analyze_task.side_effect = Exception("LLM API error")

        # Process should handle gracefully
        with pytest.raises(Exception):
            await processor.process_task_complete(
                "Failing task",
                user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_get_processing_stats(self, processor):
        """Test processing statistics."""
        # Update some stats
        processor.stats["tasks_processed"] = 10
        processor.stats["cache_hits"] = 5
        processor.stats["llm_calls_saved"] = 5

        stats = await processor.get_processing_stats()

        assert stats["tasks_processed"] == 10
        assert stats["cache_hits"] == 5
        assert stats["llm_calls_saved"] == 5
        assert "cache_hit_rate" in stats
        assert "llm_efficiency" in stats

    @pytest.mark.asyncio
    async def test_reset_stats(self, processor):
        """Test statistics reset."""
        # Set some stats
        processor.stats["tasks_processed"] = 10
        processor.stats["cache_hits"] = 5

        # Reset
        await processor.reset_stats()

        # Verify reset
        assert processor.stats["tasks_processed"] == 0
        assert processor.stats["cache_hits"] == 0


class TestBatchProcessor:
    """Test batch processor functionality."""

    @pytest.mark.asyncio
    async def test_batch_analyze_tasks(self, processor, mock_analyzer, mock_cache):
        """Test batch task analysis."""
        from app.processor.batch_processor import BatchProcessor

        batch_processor = BatchProcessor(
            processor.storage,
            processor.analyzer,
            processor.cache,
            processor.rules
        )

        # Create test tasks
        tasks = [
            Task(description="Task 1", depth=1),
            Task(description="Task 2", depth=1),
            Task(description="Task 3", depth=1)
        ]

        # Mock analysis results
        mock_analyzer.analyze_task.return_value = TaskAnalysis(
            complexity_score=0.5,
            is_atomic=True,
            is_specific=True,
            confidence=0.8,
            reasoning="Batch analysis",
            suggested_approach=ApproachType.IMPLEMENT
        )

        # Batch analyze
        results = await batch_processor.batch_analyze_tasks(tasks)

        # Verify results
        assert len(results) == 3
        assert all(isinstance(r, TaskAnalysis) for r in results)

    @pytest.mark.asyncio
    async def test_batch_processing_stats(self, processor):
        """Test batch processing statistics."""
        from app.processor.batch_processor import BatchProcessor

        batch_processor = BatchProcessor(
            processor.storage,
            processor.analyzer,
            processor.cache,
            processor.rules
        )

        # Create tasks at different depths
        tasks = [
            Task(description="Root task", depth=0),
            Task(description="Child 1", depth=1),
            Task(description="Child 2", depth=1),
            Task(description="Child 3", depth=1),
            Task(description="Grandchild", depth=2)
        ]

        stats = await batch_processor.get_batch_processing_stats(tasks)

        assert stats["total_tasks"] == 5
        assert "depth_distribution" in stats
        assert "batchable_tasks" in stats
        assert "batch_efficiency" in stats
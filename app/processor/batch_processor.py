"""Batch processor for handling multiple tasks efficiently."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from app.models import Task, TaskStatus, TaskAnalysis, TaskDecomposition
from app.storage import TaskStorage
from app.analyzer import UnifiedAnalyzer
from .processing_rules import ProcessingRules


class BatchProcessor:
    """Processor that handles multiple related tasks in batches."""

    def __init__(
        self,
        storage: TaskStorage,
        analyzer: UnifiedAnalyzer,
        rules: ProcessingRules
    ):
        """Initialize batch processor.

        Args:
            storage: Task storage instance
            analyzer: Unified analyzer instance
            rules: Processing rules instance
        """
        self.storage = storage
        self.analyzer = analyzer
        self.rules = rules

    async def batch_analyze_tasks(
        self,
        tasks: List[Task],
        context: Optional[Dict[str, Any]] = None
    ) -> List[TaskAnalysis]:
        """Analyze multiple tasks in batch.

        Args:
            tasks: List of tasks to analyze
            context: Shared context for analysis

        Returns:
            List of analysis results
        """
        # Process in smaller batches to avoid overwhelming the LLM
        batch_size = 3
        all_results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await self._analyze_batch_parallel(batch, context)
            all_results.extend(batch_results)

        return all_results

    async def _analyze_batch_parallel(
        self,
        tasks: List[Task],
        context: Optional[Dict[str, Any]]
    ) -> List[TaskAnalysis]:
        """Analyze a batch of tasks in parallel.

        Args:
            tasks: Tasks to analyze
            context: Analysis context

        Returns:
            List of analysis results
        """
        # Create analysis tasks
        analysis_tasks = [
            self.analyzer.analyze_task(task.description, context, task.depth)
            for task in tasks
        ]

        # Execute in parallel
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create fallback analysis for failed tasks
                print(f"Analysis failed for task {tasks[i].id}: {result}")
                fallback = TaskAnalysis(
                    complexity_score=0.5,
                    is_atomic=False,
                    is_specific=False,
                    confidence=0.3,
                    reasoning=f"Analysis failed: {str(result)}",
                    suggested_approach="human_review",
                    requires_human_review=True
                )
                final_results.append(fallback)
            else:
                final_results.append(result)

        return final_results

    async def batch_decompose_tasks(
        self,
        tasks: List[Tuple[Task, TaskAnalysis]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Optional[TaskDecomposition]]:
        """Decompose multiple tasks in batch.

        Args:
            tasks: List of (task, analysis) tuples
            context: Shared context

        Returns:
            List of decomposition results (None for atomic tasks)
        """
        results = []
        decomp_tasks = []

        # Filter tasks that need decomposition
        for task, analysis in tasks:
            if not self.rules.should_decompose(task, analysis):
                results.append(None)
            else:
                max_subtasks = self.rules.get_max_subtasks(task, analysis)
                decomp_tasks.append((task, analysis, max_subtasks))
                results.append("placeholder")  # Will be replaced

        # Process decompositions
        if decomp_tasks:
            batch_size = 2  # Smaller batches for decomposition
            decomp_results = []

            for i in range(0, len(decomp_tasks), batch_size):
                batch = decomp_tasks[i:i + batch_size]
                batch_results = await self._decompose_batch_parallel(batch, context)
                decomp_results.extend(batch_results)

            # Replace placeholders with actual results
            decomp_idx = 0
            for i in range(len(results)):
                if results[i] == "placeholder":
                    results[i] = decomp_results[decomp_idx]
                    decomp_idx += 1

        return results

    async def _decompose_batch_parallel(
        self,
        tasks: List[Tuple[Task, TaskAnalysis, int]],
        context: Optional[Dict[str, Any]]
    ) -> List[Optional[TaskDecomposition]]:
        """Decompose a batch of tasks in parallel.

        Args:
            tasks: List of (task, analysis, max_subtasks) tuples
            context: Processing context

        Returns:
            List of decomposition results
        """
        # Create decomposition tasks
        decomp_tasks = [
            self.analyzer.decompose_task(
                task.description,
                context,
                max_subtasks,
                task.depth
            )
            for task, analysis, max_subtasks in tasks
        ]

        # Execute in parallel
        results = await asyncio.gather(*decomp_tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Decomposition failed for task {tasks[i][0].id}: {result}")
                final_results.append(None)
            else:
                final_results.append(result)

        return final_results

    async def process_sibling_batch(
        self,
        sibling_tasks: List[Task],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a batch of sibling tasks efficiently.

        This method optimizes processing of tasks at the same level
        by batching LLM calls and leveraging shared context.

        Args:
            sibling_tasks: List of sibling tasks to process
            context: Shared processing context

        Returns:
            Processing results summary
        """
        start_time = datetime.now(timezone.utc)

        # Step 1: Batch analyze all siblings
        analyses = await self.batch_analyze_tasks(sibling_tasks, context)

        # Step 2: Update tasks with analysis results
        for task, analysis in zip(sibling_tasks, analyses):
            task.complexity_score = analysis.complexity_score
            task.is_atomic = analysis.is_atomic
            task.story_points = analysis.estimated_story_points
            task.implementation_details = analysis.implementation_hints

            # Save updated task
            await self.storage.save_task(task)

        # Step 3: Batch decompose non-atomic tasks
        task_analysis_pairs = list(zip(sibling_tasks, analyses))
        decompositions = await self.batch_decompose_tasks(task_analysis_pairs, context)

        # Step 4: Process results
        atomic_count = 0
        decomposed_count = 0
        review_count = 0

        for task, analysis, decomposition in zip(sibling_tasks, analyses, decompositions):
            strategy = self.rules.get_processing_strategy(task, analysis)

            if strategy["should_require_review"]:
                task.status = TaskStatus.AWAITING_APPROVAL
                review_count += 1
            elif analysis.is_atomic or not decomposition:
                task.status = TaskStatus.COMPLETED
                atomic_count += 1
            else:
                task.status = TaskStatus.IN_PROGRESS
                decomposed_count += 1

            await self.storage.save_task(task)

        # Calculate processing statistics
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return {
            "processed_count": len(sibling_tasks),
            "atomic_count": atomic_count,
            "decomposed_count": decomposed_count,
            "review_count": review_count,
            "processing_time": processing_time,
            "average_time_per_task": processing_time / len(sibling_tasks)
        }

    async def optimize_task_order(
        self,
        tasks: List[Task],
        analyses: List[TaskAnalysis]
    ) -> List[Tuple[Task, TaskAnalysis]]:
        """Optimize the processing order of tasks based on dependencies and priorities.

        Args:
            tasks: List of tasks
            analyses: Corresponding analyses

        Returns:
            Optimized list of (task, analysis) pairs
        """
        task_analysis_pairs = list(zip(tasks, analyses))

        # Sort by processing priority (higher first)
        task_analysis_pairs.sort(
            key=lambda pair: self.rules.get_processing_priority(pair[0], pair[1]),
            reverse=True
        )

        # Further optimize by dependency order
        # For now, use simple priority sorting
        # In the future, this could implement topological sorting
        # based on task dependencies

        return task_analysis_pairs

    async def get_batch_processing_stats(
        self,
        tasks: List[Task]
    ) -> Dict[str, Any]:
        """Get statistics about batch processing efficiency.

        Args:
            tasks: Tasks to analyze

        Returns:
            Batch processing statistics
        """
        if not tasks:
            return {"message": "No tasks to analyze"}

        total_tasks = len(tasks)
        depths = [task.depth for task in tasks]

        # Group by depth
        depth_groups = {}
        for task in tasks:
            if task.depth not in depth_groups:
                depth_groups[task.depth] = []
            depth_groups[task.depth].append(task)

        # Calculate potential batching opportunities
        batchable_groups = [
            group for group in depth_groups.values()
            if len(group) >= self.rules.config.batch_sibling_threshold
        ]

        batchable_tasks = sum(len(group) for group in batchable_groups)

        return {
            "total_tasks": total_tasks,
            "depth_distribution": {str(k): len(v) for k, v in depth_groups.items()},
            "batchable_groups": len(batchable_groups),
            "batchable_tasks": batchable_tasks,
            "batch_efficiency": batchable_tasks / total_tasks if total_tasks > 0 else 0,
            "average_depth": sum(depths) / len(depths) if depths else 0,
            "max_depth": max(depths) if depths else 0
        }
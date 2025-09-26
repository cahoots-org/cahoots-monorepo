"""Single-pass task processor that combines analysis and decomposition."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.models import Task, TaskStatus, TaskAnalysis, TaskDecomposition, TaskTree, ApproachType
from app.storage import TaskStorage
from app.analyzer import UnifiedAnalyzer, EpicAnalyzer, StoryAnalyzer, CoverageValidator
from app.analyzer.agentic_analyzer import AgenticAnalyzer
from app.websocket.events import task_event_emitter
from .processing_rules import ProcessingRules, ProcessingConfig
from .epic_story_processor import EpicStoryProcessor


class TaskProcessor:
    """Single-pass processor that handles complete task lifecycle."""

    def __init__(
        self,
        storage: TaskStorage,
        analyzer: UnifiedAnalyzer,
        config: Optional[ProcessingConfig] = None,
        agentic_analyzer: Optional[AgenticAnalyzer] = None,
        epic_story_processor: Optional[EpicStoryProcessor] = None,
        story_driven_analyzer: Optional[Any] = None
    ):
        """Initialize task processor.

        Args:
            storage: Task storage instance
            analyzer: Unified analyzer instance
            config: Processing configuration
            agentic_analyzer: Optional agentic analyzer for root tasks
            epic_story_processor: Optional epic/story processor for story-driven decomposition
            story_driven_analyzer: Optional story-driven analyzer for decomposing stories to tasks
        """
        self.storage = storage
        self.analyzer = analyzer
        self.agentic_analyzer = agentic_analyzer
        self.story_driven_analyzer = story_driven_analyzer
        self.rules = ProcessingRules(config or ProcessingConfig())

        # Initialize Epic/Story processor if not provided
        if epic_story_processor:
            self.epic_story_processor = epic_story_processor
        else:
            self.epic_story_processor = None

        # Processing statistics
        self.stats = {
            "tasks_processed": 0,
            "decompositions": 0,
            "atomic_tasks": 0,
            "processing_time": 0.0,
            "epics_created": 0,
            "stories_created": 0,
            "gap_stories": 0
        }

    async def process_task_complete(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> TaskTree:
        """Process a task completely from description to full decomposition.

        This is the main entry point that handles the entire task lifecycle:
        1. Create root task
        2. Generate Epics and Stories
        3. Decompose each Story into tasks
        4. Process tasks recursively if needed
        5. Return complete task tree

        Args:
            description: Task description
            context: Optional context (tech stack, etc.)
            user_id: User ID for the task
            max_depth: Maximum decomposition depth

        Returns:
            Complete task tree
        """
        start_time = datetime.now(timezone.utc)

        # Create root task
        root_task = Task(
            id=str(uuid.uuid4()),
            description=description,
            status=TaskStatus.PROCESSING,
            depth=0,
            user_id=user_id,
            context=context
        )

        # Initialize task tree
        tree = TaskTree(root=root_task)
        tree.add_task(root_task)

        # Emit task created event
        await task_event_emitter.emit_task_created(root_task, user_id)

        # Step 1: Generate Epics and Stories (if processor available)
        epics = []
        stories_by_epic = {}
        if self.epic_story_processor:
            print(f"[TaskProcessor] Generating Epics and Stories for root task")
            epics, stories_by_epic = await self.epic_story_processor.initialize_epics_and_stories(
                root_task, context
            )
            self.stats["epics_created"] = len(epics)
            self.stats["stories_created"] = sum(len(stories) for stories in stories_by_epic.values())

        # Store epics and stories in context for frontend
        if epics or stories_by_epic:
            if not root_task.context:
                root_task.context = {}
            root_task.context["epics"] = [epic.to_dict() for epic in epics]
            root_task.context["user_stories"] = []
            for epic_stories in stories_by_epic.values():
                root_task.context["user_stories"].extend([story.to_dict() for story in epic_stories])
            await self.storage.save_task(root_task)

        # Step 2: Process stories into tasks (story-driven decomposition)
        if self.story_driven_analyzer and stories_by_epic:
            print(f"[TaskProcessor] Decomposing stories into implementation tasks")
            await self._process_stories_to_tasks(root_task, tree, epics, stories_by_epic, context, max_depth)
        else:
            # Fallback to old recursive processing if no story-driven analyzer
            effective_max_depth = max_depth if max_depth is not None else 5
            await self._process_task_recursive(root_task, tree, context, effective_max_depth, parent_epic=None)

        # Update statistics
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        self.stats["processing_time"] += processing_time
        self.stats["tasks_processed"] += len(tree.tasks)

        # Generate and log coverage report (if processor available)
        if self.epic_story_processor:
            coverage_report = await self.epic_story_processor.validate_coverage(root_task, tree)
            print(f"[TaskProcessor] Final Coverage Score: {coverage_report.coverage_score:.2%}")

            # Add processing statistics from Epic/Story processor
            epic_stats = self.epic_story_processor.get_processing_statistics()
            self.stats.update(epic_stats)

        # Save complete tree
        await self.storage.save_task_tree(tree)

        return tree

    async def process_task_async(
        self,
        root_task: Task,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> None:
        """Process a task asynchronously in the background.

        This method is designed to be run in a background task.
        It processes the task decomposition and sends WebSocket updates.

        Args:
            root_task: The root task to process
            context: Optional context
            user_id: User ID
            max_depth: Maximum decomposition depth
        """
        print(f"[TaskProcessor] Starting async processing for task {root_task.id}")
        try:
            # Initialize task tree with the existing root task
            tree = TaskTree(root=root_task)
            tree.add_task(root_task)

            # Initialize Epics and Stories for root task (if processor available)
            epics = []
            stories_by_epic = {}
            if self.epic_story_processor:
                print(f"[TaskProcessor] Initializing Epics and Stories for root task in async processing")
                epics, stories_by_epic = await self.epic_story_processor.initialize_epics_and_stories(
                    root_task, context
                )
                self.stats["epics_created"] = len(epics)
                self.stats["stories_created"] = sum(len(stories) for stories in stories_by_epic.values())

            # Store epics and stories in context for frontend
            if epics or stories_by_epic:
                if not root_task.context:
                    root_task.context = {}
                root_task.context["epics"] = [epic.to_dict() for epic in epics]
                root_task.context["user_stories"] = []
                for epic_stories in stories_by_epic.values():
                    root_task.context["user_stories"].extend([story.to_dict() for story in epic_stories])
                await self.storage.save_task(root_task)

            # Process stories into tasks (story-driven decomposition)
            if self.story_driven_analyzer and stories_by_epic:
                print(f"[TaskProcessor] Using story-driven decomposition in async processing")
                await self._process_stories_to_tasks(root_task, tree, epics, stories_by_epic, context, max_depth)
            else:
                # Fallback to old recursive processing if no story-driven analyzer
                effective_max_depth = max_depth if max_depth is not None else 5
                await self._process_task_recursive(root_task, tree, context, effective_max_depth, parent_epic=None)

            # Generate and log coverage report (if processor available)
            if self.epic_story_processor:
                coverage_report = await self.epic_story_processor.validate_coverage(root_task, tree)
                print(f"[TaskProcessor] Final Coverage Score: {coverage_report.coverage_score:.2%}")

                # Add processing statistics from Epic/Story processor
                epic_stats = self.epic_story_processor.get_processing_statistics()
                self.stats.update(epic_stats)

            # Save complete tree
            await self.storage.save_task_tree(tree)

            # Update statistics
            processing_time = (datetime.now(timezone.utc) - root_task.created_at).total_seconds()
            self.stats["processing_time"] += processing_time
            self.stats["tasks_processed"] += len(tree.tasks)

        except Exception as e:
            print(f"Error in async task processing: {e}")
            # Update task status to error
            root_task.status = TaskStatus.ERROR
            await self.storage.save_task(root_task)
            # Emit error event
            await task_event_emitter.emit_task_error(root_task, str(e), user_id)

    async def _process_task_recursive(
        self,
        task: Task,
        tree: TaskTree,
        context: Optional[Dict[str, Any]],
        max_depth: int,
        parent_epic: Optional[Any] = None
    ) -> None:
        """Process a task and all its subtasks recursively.

        Args:
            task: Task to process
            tree: Task tree to update
            context: Processing context
            max_depth: Maximum depth to process
            parent_epic: Parent task's epic (if any)
        """
        # Skip if already at max depth
        if task.depth >= max_depth:
            task.status = TaskStatus.COMPLETED
            task.is_atomic = True
            await self.storage.save_task(task)
            return

        # Step 1: Analyze task
        analysis = await self._analyze_task(task, context)

        # Update task with analysis results
        task.complexity_score = analysis.complexity_score
        task.is_atomic = analysis.is_atomic
        task.story_points = analysis.estimated_story_points
        task.implementation_details = analysis.implementation_hints

        # Step 1.5: Process with Epic/Story awareness (skip for root task as it's already done)
        assigned_epic = parent_epic
        matched_stories = []
        has_story_gap = False

        if task.depth > 0 and self.epic_story_processor:  # Not root task and processor available
            assigned_epic, matched_stories, has_story_gap = await self.epic_story_processor.process_task_with_stories(
                task, parent_epic, context
            )
            if has_story_gap:
                self.stats["gap_stories"] += 1

        # Step 2: Determine processing strategy considering stories
        strategy = self.rules.get_processing_strategy(task, analysis)

        # Step 3: Handle based on strategy
        if strategy["should_require_review"]:
            old_status = task.status
            task.status = TaskStatus.AWAITING_APPROVAL
            await self.storage.save_task(task)
            await task_event_emitter.emit_task_status_changed(task, old_status, task.user_id)
            return

        # Check if stories suggest decomposition
        should_decompose_for_stories = False
        if matched_stories and self.epic_story_processor:
            should_decompose_for_stories = await self.epic_story_processor.should_decompose_based_on_stories(
                task, matched_stories
            )

        if (not strategy["should_decompose"] and not should_decompose_for_stories) or analysis.is_atomic:
            # Task is atomic - mark as ready for implementation
            old_status = task.status
            task.status = TaskStatus.COMPLETED
            task.is_atomic = True
            await self.storage.save_task(task)
            await task_event_emitter.emit_task_status_changed(task, old_status, task.user_id)
            self.stats["atomic_tasks"] += 1

            # Update story completion if task is completed
            if task.status == TaskStatus.COMPLETED and self.epic_story_processor:
                await self.epic_story_processor.update_story_completion(task)
            return

        # Step 4: Decompose task
        await task_event_emitter.emit_decomposition_started(task, task.user_id)
        decomposition = await self._decompose_task(task, context, analysis)
        if not decomposition or not decomposition.subtasks:
            # Decomposition failed - set error status
            old_status = task.status
            task.status = TaskStatus.ERROR
            task.error_message = "Failed to decompose task - LLM API error or invalid response"
            await self.storage.save_task(task)
            await task_event_emitter.emit_decomposition_error(task, "Failed to generate subtasks", task.user_id)
            await task_event_emitter.emit_task_status_changed(task, old_status, task.user_id)
            return

        # Step 5: Create subtasks
        subtask_ids = await self._create_subtasks(task, decomposition, tree, context)
        task.subtasks = subtask_ids
        old_status = task.status
        task.status = TaskStatus.IN_PROGRESS
        await self.storage.save_task(task)
        await task_event_emitter.emit_task_status_changed(task, old_status, task.user_id)
        await task_event_emitter.emit_decomposition_completed(task, len(subtask_ids), task.user_id)

        # Step 6: Process all subtasks
        subtasks = [tree.get_task(tid) for tid in subtask_ids if tree.get_task(tid)]

        # Determine if we should batch process
        if self.rules.should_batch_process(len(subtasks), task.depth):
            await self._process_subtasks_batch(subtasks, tree, context, max_depth, assigned_epic)
        else:
            await self._process_subtasks_sequential(subtasks, tree, context, max_depth, assigned_epic)

        # Step 7: Check if all children are complete
        await self._check_task_completion(task, tree)

    async def _analyze_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> TaskAnalysis:
        """Analyze task.

        Args:
            task: Task to analyze
            context: Analysis context

        Returns:
            Task analysis result
        """
        # Use agentic analyzer for root tasks if available
        if task.depth == 0 and self.agentic_analyzer:
            print(f"Using agentic analyzer for root task: {task.description[:100]}")
            analysis = await self.agentic_analyzer.analyze_task_with_tools(
                task.description,
                context,
                task.depth
            )
        else:
            # Perform regular analysis for subtasks
            analysis = await self.analyzer.analyze_task(
                task.description,
                context,
                task.depth
            )

        return analysis

    async def _decompose_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]],
        analysis: TaskAnalysis
    ) -> Optional[TaskDecomposition]:
        """Decompose task.

        Args:
            task: Task to decompose
            context: Processing context
            analysis: Task analysis

        Returns:
            Decomposition result or None
        """
        try:
            max_subtasks = self.rules.get_max_subtasks(task, analysis)

            # Use agentic analyzer for root task decomposition if available
            if task.depth == 0 and self.agentic_analyzer:
                print(f"Using agentic decomposition for root task: {task.description[:100]}")
                decomposition = await self.agentic_analyzer.decompose_task_with_context(
                    task.description,
                    context,
                    max_subtasks,
                    task.depth
                )
            else:
                # Perform regular decomposition for subtasks
                decomposition = await self.analyzer.decompose_task(
                    task.description,
                    context,
                    max_subtasks,
                    task.depth
                )

            self.stats["decompositions"] += 1
            return decomposition

        except Exception as e:
            print(f"Error in decomposition for task {task.id}: {e}")
            # Return None to trigger error handling in the caller
            return None

    async def _create_subtasks(
        self,
        parent: Task,
        decomposition: TaskDecomposition,
        tree: TaskTree,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Create subtasks from decomposition.

        Args:
            parent: Parent task
            decomposition: Decomposition result
            tree: Task tree to update
            context: Processing context

        Returns:
            List of created subtask IDs
        """
        subtask_ids = []

        for i, subtask_data in enumerate(decomposition.subtasks):
            subtask = Task(
                id=str(uuid.uuid4()),
                description=subtask_data["description"],
                status=TaskStatus.SUBMITTED,
                depth=parent.depth + 1,
                parent_id=parent.id,
                is_atomic=subtask_data.get("is_atomic", False),
                implementation_details=subtask_data.get("implementation_details"),
                story_points=subtask_data.get("story_points"),
                context=context,
                user_id=parent.user_id
            )

            # Add to tree and storage
            tree.add_task(subtask)
            await self.storage.save_task(subtask)
            subtask_ids.append(subtask.id)

            # Emit task created event for each subtask
            print(f"[TaskProcessor] Emitting task.created event for subtask {subtask.id} (parent: {parent.id})")
            await task_event_emitter.emit_task_created(subtask, subtask.user_id)

        return subtask_ids

    async def _process_subtasks_sequential(
        self,
        subtasks: List[Task],
        tree: TaskTree,
        context: Optional[Dict[str, Any]],
        max_depth: int,
        parent_epic: Optional[Any] = None
    ) -> None:
        """Process subtasks sequentially.

        Args:
            subtasks: List of subtasks to process
            tree: Task tree
            context: Processing context
            max_depth: Maximum depth
            parent_epic: Parent task's epic
        """
        for subtask in subtasks:
            await self._process_task_recursive(subtask, tree, context, max_depth, parent_epic)

    async def _process_subtasks_batch(
        self,
        subtasks: List[Task],
        tree: TaskTree,
        context: Optional[Dict[str, Any]],
        max_depth: int,
        parent_epic: Optional[Any] = None
    ) -> None:
        """Process all sibling subtasks in a single batch to reduce LLM calls.

        Args:
            subtasks: List of subtasks to process
            tree: Task tree
            context: Processing context
            max_depth: Maximum depth
            parent_epic: Parent task's epic
        """
        # Batch analyze all siblings in one call
        if self.analyzer and subtasks:
            print(f"[TaskProcessor] Batch processing {len(subtasks)} sibling tasks")

            # TODO: Add batch analysis method to UnifiedAnalyzer
            # For now, process individually but could be optimized
            for subtask in subtasks:
                await self._process_task_recursive(subtask, tree, context, max_depth, parent_epic)

    async def _process_stories_to_tasks(
        self,
        root_task: Task,
        tree: TaskTree,
        epics: List[Any],
        stories_by_epic: Dict[str, List[Any]],
        context: Optional[Dict[str, Any]],
        max_depth: Optional[int]
    ) -> None:
        """Process all stories into implementation tasks using batch processing.

        Args:
            root_task: Root task
            tree: Task tree to populate
            epics: List of epics
            stories_by_epic: Stories grouped by epic
            context: Processing context
            max_depth: Maximum depth for further decomposition
        """
        total_stories = sum(len(stories) for stories in stories_by_epic.values())
        print(f"[TaskProcessor] Batch processing {total_stories} stories into tasks")

        for epic in epics:
            epic_stories = stories_by_epic.get(epic.id, [])

            if not epic_stories:
                continue

            print(f"[TaskProcessor] Batch decomposing {len(epic_stories)} stories for epic: {epic.title}")

            # Batch decompose all stories for this epic in a single call
            story_decompositions = await self.story_driven_analyzer.decompose_stories_to_tasks(
                epic_stories, epic, context
            )

            # Process the decompositions
            for story in epic_stories:
                decomposition = story_decompositions.get(story.id)
                if not decomposition:
                    raise ValueError(f"No decomposition generated for story {story.id}")

                # Create tasks from decomposition
                for subtask_data in decomposition.subtasks:
                    is_atomic = subtask_data.get("is_atomic", False)

                    # Atomic tasks with implementation details are completed
                    status = TaskStatus.COMPLETED if (is_atomic and subtask_data.get("implementation_details")) else TaskStatus.SUBMITTED

                    task = Task(
                        id=str(uuid.uuid4()),
                        description=subtask_data["description"],
                        status=status,
                        depth=1,  # All story tasks start at depth 1
                        parent_id=root_task.id,
                        is_atomic=is_atomic,
                        implementation_details=subtask_data.get("implementation_details"),
                        story_points=subtask_data.get("story_points"),
                        story_ids=[subtask_data.get("story_id")] if subtask_data.get("story_id") else [],
                        epic_ids=[subtask_data.get("epic_id")] if subtask_data.get("epic_id") else [],
                        context=context,
                        user_id=root_task.user_id
                    )

                    # Add to tree
                    tree.add_task(task)
                    await self.storage.save_task(task)

                    # Add to root task's children
                    if not root_task.subtasks:
                        root_task.subtasks = []
                    root_task.subtasks.append(task.id)

                    # Emit event
                    await task_event_emitter.emit_task_created(task, task.user_id)

                    # Story-generated tasks should be atomic enough
                    # Only decompose if explicitly marked as needing it and depth < 2
                    if not task.is_atomic and task.depth < 2:
                        print(f"[TaskProcessor] WARNING: Non-atomic task from story at depth {task.depth}, marking as atomic")
                        task.is_atomic = True
                        await self.storage.save_task(task)

        # Update root task status and check for completion
        await self._check_task_completion(root_task, tree)

        # If still not complete but all processing is done, mark as complete
        if root_task.status != TaskStatus.COMPLETED:
            print(f"[TaskProcessor] All stories processed, marking root task as complete")
            root_task.status = TaskStatus.COMPLETED
            await self.storage.save_task(root_task)

    async def _check_task_completion(self, task: Task, tree: TaskTree) -> None:
        """Check if a task is complete based on its children.

        Args:
            task: Task to check
            tree: Task tree
        """
        if not task.subtasks:
            return

        # Get all children
        children = [tree.get_task(tid) for tid in task.subtasks]
        children = [child for child in children if child is not None]

        if not children:
            return

        # Check if all children are complete
        all_complete = all(
            child.status in [TaskStatus.COMPLETED, TaskStatus.REJECTED]
            for child in children
        )

        if all_complete:
            task.status = TaskStatus.COMPLETED
            await self.storage.save_task(task)

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        cache_stats = self.cache.get_cache_stats()

        return {
            **self.stats,
            "cache_hit_rate": cache_stats.get("hit_rate", 0.0),
            "llm_efficiency": (
                self.stats["llm_calls_saved"] /
                max(1, self.stats["tasks_processed"])
            )
        }

    async def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.stats = {
            "tasks_processed": 0,
            "cache_hits": 0,
            "decompositions": 0,
            "atomic_tasks": 0,
            "llm_calls_saved": 0,
            "processing_time": 0.0
        }
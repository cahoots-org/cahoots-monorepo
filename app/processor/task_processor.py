"""Single-pass task processor that combines analysis and decomposition."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.models import Task, TaskStatus, TaskAnalysis, TaskDecomposition, TaskTree, ApproachType
from app.storage import TaskStorage
from app.analyzer import UnifiedAnalyzer, EpicAnalyzer, StoryAnalyzer, CoverageValidator
from app.analyzer.agentic_analyzer import AgenticAnalyzer
from app.analyzer.context_aware_domain_analyzer import ContextAwareDomainAnalyzer
from app.analyzer.requirements_generator import generate_requirements
from app.analyzer.state_machine_detector import StateMachineDetector
from app.analyzer.cqrs_detector import CQRSDetector
from app.analyzer.schema_generator import SchemaGenerator
from app.websocket.events import task_event_emitter
from .processing_rules import ProcessingRules, ProcessingConfig
from .epic_story_processor import EpicStoryProcessor
from app.config import PromptTuningConfig
from app.metrics import (
    epic_story_generation_duration,
    story_decomposition_duration,
    event_modeling_duration,
    context_engine_publish_duration,
    epics_generated_total,
    stories_generated_total,
    projects_created_total,
    tasks_generated_total,
    atomic_tasks_total,
    commands_generated_total,
    read_models_generated_total,
    automations_generated_total,
    chapters_generated_total,
    events_generated_total,
    event_model_validations_total,
    get_task_count_bucket
)


class TaskProcessor:
    """Single-pass processor that handles complete task lifecycle."""

    def __init__(
        self,
        storage: TaskStorage,
        analyzer: UnifiedAnalyzer,
        config: Optional[ProcessingConfig] = None,
        agentic_analyzer: Optional[AgenticAnalyzer] = None,
        epic_story_processor: Optional[EpicStoryProcessor] = None,
        story_driven_analyzer: Optional[Any] = None,
        context_engine_client: Optional[Any] = None
    ):
        """Initialize task processor.

        Args:
            storage: Task storage instance
            analyzer: Unified analyzer instance
            config: Processing configuration
            agentic_analyzer: Optional agentic analyzer for root tasks
            epic_story_processor: Optional epic/story processor for story-driven decomposition
            story_driven_analyzer: Optional story-driven analyzer for decomposing stories to tasks
            context_engine_client: Optional Context Engine Redis client for event publishing
        """
        self.storage = storage
        self.analyzer = analyzer
        self.agentic_analyzer = agentic_analyzer
        self.story_driven_analyzer = story_driven_analyzer
        self.context_engine_client = context_engine_client
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
        max_depth: Optional[int] = None,
        prompt_config: Optional[PromptTuningConfig] = None
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
            prompt_config: Optional prompt tuning configuration

        Returns:
            Complete task tree
        """
        # Store prompt config in context for use throughout processing
        if context is None:
            context = {}
        if prompt_config is not None:
            context['prompt_config'] = prompt_config
        start_time = datetime.now(timezone.utc)

        # Initialize timing dictionary
        timing_metrics = {
            "start_time": start_time.isoformat(),
            "phases": {}
        }

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

        # Record project creation metric
        projects_created_total.labels(source="api").inc()

        # Emit task created event
        await task_event_emitter.emit_task_created(root_task, user_id)

        # Step 1: Generate Epics and Stories (if processor available)
        epics = []
        stories_by_epic = {}
        if self.epic_story_processor:
            phase_start = datetime.now(timezone.utc)
            print(f"[TaskProcessor] Generating Epics and Stories for root task")
            epics, stories_by_epic = await self.epic_story_processor.initialize_epics_and_stories(
                root_task, context
            )
            phase_duration = (datetime.now(timezone.utc) - phase_start).total_seconds()

            # Record Prometheus metrics
            # Use story count as proxy for complexity
            story_count = sum(len(stories) for stories in stories_by_epic.values())
            task_bucket = get_task_count_bucket(story_count)
            epic_story_generation_duration.labels(task_count_bucket=task_bucket).observe(phase_duration)
            epics_generated_total.inc(len(epics))
            stories_generated_total.inc(story_count)

            timing_metrics["phases"]["epic_story_generation"] = phase_duration
            print(f"[TaskProcessor] ⏱️  Epic/Story generation took {phase_duration:.2f}s")
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
            phase_start = datetime.now(timezone.utc)
            print(f"[TaskProcessor] Decomposing stories into implementation tasks")
            await self._process_stories_to_tasks(root_task, tree, epics, stories_by_epic, context, max_depth)
            phase_duration = (datetime.now(timezone.utc) - phase_start).total_seconds()

            # Record Prometheus metrics
            # Use total task count as proxy for complexity
            total_tasks = len(tree.tasks) - 1  # Exclude root task
            task_bucket = get_task_count_bucket(total_tasks)
            story_decomposition_duration.labels(task_count_bucket=task_bucket).observe(phase_duration)

            # Record tasks generated
            tasks_generated_total.labels(source="story").inc(total_tasks)
            atomic_count = len([t for t in tree.tasks.values() if t.is_atomic and t.depth > 0])
            atomic_tasks_total.inc(atomic_count)

            timing_metrics["phases"]["story_decomposition"] = phase_duration
            print(f"[TaskProcessor] ⏱️  Story decomposition took {phase_duration:.2f}s")
        else:
            # Fallback to old recursive processing if no story-driven analyzer
            phase_start = datetime.now(timezone.utc)
            effective_max_depth = max_depth if max_depth is not None else 5
            await self._process_task_recursive(root_task, tree, context, effective_max_depth, parent_epic=None)
            phase_duration = (datetime.now(timezone.utc) - phase_start).total_seconds()

            # Record Prometheus metrics
            # Use total task count as proxy for complexity
            total_tasks = len(tree.tasks) - 1  # Exclude root task
            task_bucket = get_task_count_bucket(total_tasks)
            story_decomposition_duration.labels(task_count_bucket=task_bucket).observe(phase_duration)

            timing_metrics["phases"]["recursive_processing"] = phase_duration
            print(f"[TaskProcessor] ⏱️  Recursive processing took {phase_duration:.2f}s")

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

        # Event modeling analysis - Single LLM call
        print(f"[TaskProcessor] Performing event modeling analysis")
        try:
            # Emit event modeling started
            await task_event_emitter.emit_event_modeling_started(root_task, user_id)

            # Publish context data to Context Engine before domain analysis
            if self.context_engine_client:
                project_id = root_task.id

                # Publish tech stack from root task context
                if context and any(k in context for k in ['tech_stack', 'database', 'framework']):
                    await self.context_engine_client.publish_data(
                        project_id=project_id,
                        data_key="tech_stack",
                        data=context
                    )
                    print(f"[TaskProcessor] ✓ Published tech_stack to Context Engine")
                    await task_event_emitter.emit_context_updated(root_task, "tech_stack", user_id)

                # Publish epics and stories
                if epics or stories_by_epic:
                    epics_data = [
                        {
                            "id": epic.id,
                            "title": epic.title,
                            "description": epic.description,
                            "scope_keywords": epic.scope_keywords,
                            "priority": epic.priority
                        }
                        for epic in epics
                    ]

                    stories_data = []
                    for epic_stories in stories_by_epic.values():
                        for story in epic_stories:
                            stories_data.append({
                                "id": story.id,
                                "actor": story.actor,
                                "action": story.action,
                                "benefit": story.benefit,
                                "acceptance_criteria": story.acceptance_criteria,
                                "epic_id": story.epic_id
                            })

                    await self.context_engine_client.publish_data(
                        project_id=project_id,
                        data_key="epics_and_stories",
                        data={
                            "epics": epics_data,
                            "stories": stories_data,
                            "total_epics": len(epics),
                            "total_stories": len(stories_data)
                        }
                    )
                    print(f"[TaskProcessor] ✓ Published {len(epics)} epics and {len(stories_data)} stories to Context Engine")
                    await task_event_emitter.emit_context_updated(root_task, "epics_and_stories", user_id)

                # Publish decomposed tasks
                task_summary = []
                for task in tree.tasks.values():
                    if task.depth > 0:  # Skip root task
                        task_summary.append({
                            "id": task.id,
                            "description": task.description,
                            "depth": task.depth,
                            "complexity": task.metadata.get("complexity_score") if hasattr(task, "metadata") else None,
                            "parent_id": task.parent_id
                        })

                if task_summary:
                    await self.context_engine_client.publish_data(
                        project_id=project_id,
                        data_key="decomposed_tasks",
                        data={
                            "tasks": task_summary,
                            "total_tasks": len(task_summary),
                            "max_depth": max(t["depth"] for t in task_summary) if task_summary else 0
                        }
                    )
                    print(f"[TaskProcessor] ✓ Published {len(task_summary)} decomposed tasks to Context Engine")
                    await task_event_emitter.emit_context_updated(root_task, "decomposed_tasks", user_id)

            # Track event modeling timing
            event_modeling_start = datetime.now(timezone.utc)

            unified_analyzer = ContextAwareDomainAnalyzer(
                self.analyzer.llm,
                self.context_engine_client,
                task_event_emitter
            )

            # Prepare data for requirements generation
            epics_data = [
                {"title": e.title, "name": e.title, "description": e.description}
                for e in epics
            ] if epics else []

            stories_data = []
            for epic_stories in stories_by_epic.values():
                for story in epic_stories:
                    stories_data.append({
                        "actor": story.actor,
                        "action": story.action,
                        "benefit": story.benefit
                    })

            tech_stack = context.get("tech_stack", {}) if context else {}

            # Run event modeling AND requirements generation in parallel
            print(f"[TaskProcessor] Running event modeling and requirements generation in parallel")
            analysis_task = unified_analyzer.analyze_domain(
                list(tree.tasks.values()),
                root_task,
                user_id,
                project_id=root_task.id
            )
            requirements_task = generate_requirements(
                self.analyzer.llm,
                root_task.description,
                epics_data,
                stories_data,
                tech_stack
            )

            analysis, requirements = await asyncio.gather(analysis_task, requirements_task)

            # Store requirements in metadata
            if requirements:
                root_task.metadata["requirements"] = requirements
                fr_count = len(requirements.get("functional_requirements", []))
                nfr_count = len(requirements.get("non_functional_requirements", []))
                print(f"[TaskProcessor] Generated {fr_count} functional, {nfr_count} non-functional requirements")

            # Record event modeling metrics
            event_modeling_time = (datetime.now(timezone.utc) - event_modeling_start).total_seconds()
            total_tasks = len(tree.tasks) - 1  # Exclude root task
            task_bucket = get_task_count_bucket(total_tasks)
            event_modeling_duration.labels(task_count_bucket=task_bucket).observe(event_modeling_time)
            timing_metrics["phases"]["event_modeling"] = event_modeling_time
            print(f"[TaskProcessor] ⏱️  Event modeling took {event_modeling_time:.2f}s")

            # Ensure metadata is a dict
            if not isinstance(root_task.metadata, dict):
                root_task.metadata = {}

            # Store events
            if analysis["events"]:
                root_task.metadata["extracted_events"] = [
                    {
                        "name": e.name,
                        "event_type": e.event_type.value,
                        "description": e.description,
                        "actor": e.actor,
                        "affected_entity": e.affected_entity,
                        "triggers": e.triggers,
                        "source_task_id": e.source_task_id,
                        "metadata": e.metadata,
                        # Flatten payload from metadata for frontend convenience
                        "payload": e.metadata.get("payload", []) if isinstance(e.metadata, dict) else []
                    }
                    for e in analysis["events"]
                ]
                print(f"[TaskProcessor] Extracted {len(analysis['events'])} events")

            # Store commands, read models, user interactions, automations
            if analysis["commands"]:
                root_task.metadata["commands"] = analysis["commands"]
                print(f"[TaskProcessor] Identified {len(analysis['commands'])} commands")

            if analysis["read_models"]:
                root_task.metadata["read_models"] = analysis["read_models"]
                print(f"[TaskProcessor] Identified {len(analysis['read_models'])} read models")

            if analysis["user_interactions"]:
                root_task.metadata["user_interactions"] = analysis["user_interactions"]
                print(f"[TaskProcessor] Identified {len(analysis['user_interactions'])} user interactions")

            if analysis["automations"]:
                root_task.metadata["automations"] = analysis["automations"]
                print(f"[TaskProcessor] Identified {len(analysis['automations'])} automations")

            # Store swimlanes and chapters
            if analysis.get("swimlanes"):
                root_task.metadata["swimlanes"] = analysis["swimlanes"]
                print(f"[TaskProcessor] Identified {len(analysis['swimlanes'])} swimlanes")

            if analysis.get("chapters"):
                root_task.metadata["chapters"] = analysis["chapters"]
                print(f"[TaskProcessor] Identified {len(analysis['chapters'])} chapters")

            # Validate event model
            from app.analyzer.event_model_validator import EventModelValidator
            validator = EventModelValidator()
            is_valid, validation_issues = validator.validate(analysis)
            validation_summary = validator.get_validation_summary()

            print(f"[TaskProcessor] Event model validation: {'PASSED' if is_valid else 'FAILED'}")
            print(f"  - Errors: {validation_summary['errors']}")
            print(f"  - Warnings: {validation_summary['warnings']}")

            # Store validation results
            root_task.metadata["event_model_validation"] = {
                "valid": is_valid,
                "summary": validation_summary,
                "issues": [
                    {
                        "severity": issue.severity,
                        "category": issue.category,
                        "message": issue.message,
                        "details": issue.details
                    }
                    for issue in validation_issues
                ]
            }

            # Generate event model markdown
            from app.analyzer.event_model_markdown_generator import EventModelMarkdownGenerator
            markdown_generator = EventModelMarkdownGenerator()
            event_model_markdown = markdown_generator.generate(analysis, root_task.description)

            # Append validation results to markdown
            if not is_valid or validation_summary['warnings'] > 0:
                event_model_markdown += self._generate_validation_section(validation_summary, validation_issues)

            root_task.metadata["event_model_markdown"] = event_model_markdown
            print(f"[TaskProcessor] Generated event model markdown ({len(event_model_markdown)} chars)")

            await self.storage.save_task(root_task)

            # Emit event modeling completed with counts
            await task_event_emitter.emit_event_modeling_completed(
                root_task,
                user_id,
                events_count=len(analysis.get("events", [])),
                commands_count=len(analysis.get("events", [])),
                read_models_count=len(analysis.get("read_models", [])),
                interactions_count=len(analysis.get("user_interactions", [])),
                automations_count=len(analysis.get("automations", []))
            )

            # PASS 3: Task Enrichment with Complete Event Model
            if self.story_driven_analyzer and stories_by_epic and analysis:
                print(f"[TaskProcessor] PASS 3: Enriching tasks with complete event model context")
                enriched_tasks = await self._enrich_tasks_with_event_model(
                    root_task, tree, epics, stories_by_epic, analysis, context, max_depth, user_id
                )
                print(f"[TaskProcessor] Task enrichment complete: {len(enriched_tasks)} new tasks added")

            # Mark task as completed after event modeling
            old_status = root_task.status
            root_task.status = TaskStatus.COMPLETED
            await self.storage.save_task(root_task)
            await task_event_emitter.emit_task_status_changed(root_task, old_status, user_id)

        except Exception as e:
            print(f"[TaskProcessor] Error in event modeling analysis: {e}")
            # Mark as completed even if event modeling fails
            old_status = root_task.status
            root_task.status = TaskStatus.COMPLETED
            await self.storage.save_task(root_task)
            await task_event_emitter.emit_task_status_changed(root_task, old_status, user_id)

        # Save complete tree
        await self.storage.save_task_tree(tree)

        return tree

    async def process_task_async(
        self,
        root_task: Task,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        max_depth: Optional[int] = None,
        prompt_config: Optional[PromptTuningConfig] = None
    ) -> None:
        """Process a task asynchronously in the background.

        This method is designed to be run in a background task.
        It processes the task decomposition and sends WebSocket updates.

        Args:
            root_task: The root task to process
            context: Optional context
            user_id: User ID
            max_depth: Maximum decomposition depth
            prompt_config: Optional prompt tuning configuration
        """
        # Store prompt config in context for use throughout processing
        if context is None:
            context = {}
        if prompt_config is not None:
            context['prompt_config'] = prompt_config
        print(f"[TaskProcessor] Starting async processing for task {root_task.id}")
        try:
            # Check if repository analysis is pending
            if context and context.get("repository_analysis_pending"):
                repo_info = context["repository_analysis_pending"]
                owner = repo_info["owner"]
                repo = repo_info["repo"]

                print(f"[TaskProcessor] Starting repository analysis for {owner}/{repo}")

                # Download and analyze repository in background
                try:
                    import os
                    from app.services.github_zip_analyzer import GitHubZipAnalyzer

                    analyzer = GitHubZipAnalyzer(github_token=os.getenv("GITHUB_TOKEN"))
                    analysis = await analyzer.analyze_repository(owner, repo)

                    if not analysis.get("error"):
                        # Add analysis to context
                        architectural_context = analyzer.format_analysis_for_llm(analysis)

                        # Merge with existing context
                        if context.get("repository_context"):
                            context["repository_context"] = f"{context['repository_context']}\n\n{architectural_context}"
                        else:
                            context["repository_context"] = architectural_context

                        context["repository_architecture"] = architectural_context
                        context["repository_analysis"] = analysis

                        # Update the pending status
                        context["repository_analysis_pending"]["status"] = "completed"

                        # Update root task context
                        root_task.context = context
                        await self.storage.save_task(root_task)

                        print(f"[TaskProcessor] Repository analysis completed for {owner}/{repo}")
                    else:
                        print(f"[TaskProcessor] Repository analysis failed: {analysis.get('error')}")
                        context["repository_analysis_pending"]["status"] = "failed"
                        context["repository_analysis_pending"]["error"] = analysis.get('error')

                except Exception as e:
                    print(f"[TaskProcessor] Repository analysis exception: {e}")
                    context["repository_analysis_pending"]["status"] = "failed"
                    context["repository_analysis_pending"]["error"] = str(e)

            # Initialize task tree with the existing root task
            tree = TaskTree(root=root_task)
            tree.add_task(root_task)

            # Record project creation metric
            projects_created_total.labels(source="api").inc()

            # STEP 1: Initialize Epics and Stories
            epics = []
            stories_by_epic = {}
            if self.epic_story_processor:
                phase_start = datetime.now(timezone.utc)
                print(f"[TaskProcessor] STEP 1: Initializing Epics and Stories")
                epics, stories_by_epic = await self.epic_story_processor.initialize_epics_and_stories(
                    root_task, context
                )
                phase_duration = (datetime.now(timezone.utc) - phase_start).total_seconds()

                # Record Prometheus metrics
                story_count = sum(len(stories) for stories in stories_by_epic.values())
                task_bucket = get_task_count_bucket(story_count)
                epic_story_generation_duration.labels(task_count_bucket=task_bucket).observe(phase_duration)
                epics_generated_total.inc(len(epics))
                stories_generated_total.inc(story_count)

                print(f"[TaskProcessor] ⏱️  Epic/Story generation took {phase_duration:.2f}s (bucket: {task_bucket})")

                self.stats["epics_created"] = len(epics)
                self.stats["stories_created"] = story_count

            # Store epics and stories in context for frontend
            if epics or stories_by_epic:
                if not root_task.context:
                    root_task.context = {}
                root_task.context["epics"] = [epic.to_dict() for epic in epics]
                root_task.context["user_stories"] = []
                for epic_stories in stories_by_epic.values():
                    root_task.context["user_stories"].extend([story.to_dict() for story in epic_stories])
                await self.storage.save_task(root_task)

                # Publish user stories to Context Engine
                if self.context_engine_client:
                    try:
                        stories_data = {
                            "epics": root_task.context["epics"],
                            "stories": root_task.context["user_stories"]
                        }
                        await self.context_engine_client.redis.publish(
                            "project:stories_updated",
                            __import__('json').dumps({
                                "project_id": root_task.id,
                                "user_id": root_task.user_id,
                                "stories": stories_data
                            })
                        )
                        print(f"[TaskProcessor] ✓ Published {len(root_task.context['user_stories'])} user stories to Context Engine")
                    except Exception as e:
                        print(f"[TaskProcessor] ⚠ Failed to publish stories to Context Engine: {e}")

            # STEP 2: Process stories into preliminary tasks
            phase_start = datetime.now(timezone.utc)
            print(f"[TaskProcessor] STEP 2: Decomposing stories into preliminary tasks")
            if self.story_driven_analyzer and stories_by_epic:
                await self._process_stories_to_tasks(root_task, tree, epics, stories_by_epic, context, max_depth)
            else:
                # Fallback to old recursive processing if no story-driven analyzer
                effective_max_depth = max_depth if max_depth is not None else 5
                await self._process_task_recursive(root_task, tree, context, effective_max_depth, parent_epic=None)

            phase_duration = (datetime.now(timezone.utc) - phase_start).total_seconds()

            # Record Prometheus metrics
            total_tasks = len(tree.tasks) - 1  # Exclude root task
            task_bucket = get_task_count_bucket(total_tasks)
            story_decomposition_duration.labels(task_count_bucket=task_bucket).observe(phase_duration)

            # Record tasks generated
            tasks_generated_total.labels(source="story").inc(total_tasks)
            atomic_count = len([t for t in tree.tasks.values() if t.is_atomic and t.depth > 0])
            atomic_tasks_total.inc(atomic_count)

            print(f"[TaskProcessor] ⏱️  Story decomposition took {phase_duration:.2f}s (bucket: {task_bucket}, tasks: {total_tasks})")

            # Generate and log coverage report (if processor available)
            if self.epic_story_processor:
                coverage_report = await self.epic_story_processor.validate_coverage(root_task, tree)
                print(f"[TaskProcessor] Final Coverage Score: {coverage_report.coverage_score:.2%}")

                # Add processing statistics from Epic/Story processor
                epic_stats = self.epic_story_processor.get_processing_statistics()
                self.stats.update(epic_stats)

            # PASS 2: Event Modeling from ALL preliminary tasks
            print(f"[TaskProcessor] PASS 2: Analyzing ALL {len(tree.tasks) - 1} tasks to create complete event model")
            event_model_analysis = None
            try:
                # Emit event modeling started
                await task_event_emitter.emit_event_modeling_started(root_task, user_id)

                # Publish context data to Context Engine before domain analysis (PASS 2)
                # These are optional - don't let them break event modeling
                if self.context_engine_client:
                    try:
                        project_id = root_task.id

                        # Publish tech stack from root task context
                        if context and any(k in context for k in ['tech_stack', 'database', 'framework']):
                            await self.context_engine_client.publish_data(
                                project_id=project_id,
                                data_key="tech_stack",
                                data=context
                            )
                            print(f"[TaskProcessor] ✓ Published tech_stack to Context Engine")

                        # Publish epics and stories (already stored in root_task.context)
                        if root_task.context and ('epics' in root_task.context or 'user_stories' in root_task.context):
                            epics_data = root_task.context.get('epics', [])
                            stories_data = root_task.context.get('user_stories', [])

                            if epics_data or stories_data:
                                await self.context_engine_client.publish_data(
                                    project_id=project_id,
                                    data_key="epics_and_stories",
                                    data={
                                        "epics": epics_data,
                                        "stories": stories_data,
                                        "total_epics": len(epics_data),
                                        "total_stories": len(stories_data)
                                    }
                                )
                                print(f"[TaskProcessor] ✓ Published {len(epics_data)} epics and {len(stories_data)} stories to Context Engine")

                        # Publish decomposed tasks
                        all_tasks_summary = []
                        for task in tree.tasks.values():
                            if task.depth > 0:  # Skip root task
                                all_tasks_summary.append({
                                    "id": task.id,
                                    "description": task.description,
                                    "depth": task.depth,
                                    "complexity": task.metadata.get("complexity_score") if hasattr(task, "metadata") else None,
                                    "parent_id": task.parent_id
                                })

                        if all_tasks_summary:
                            await self.context_engine_client.publish_data(
                                project_id=project_id,
                                data_key="decomposed_tasks",
                                data={
                                    "tasks": all_tasks_summary,
                                    "total_tasks": len(all_tasks_summary),
                                    "max_depth": max(t["depth"] for t in all_tasks_summary) if all_tasks_summary else 0
                                }
                            )
                            print(f"[TaskProcessor] ✓ Published {len(all_tasks_summary)} decomposed tasks to Context Engine")
                    except Exception as ce_error:
                        print(f"[TaskProcessor] ⚠ Context Engine publish failed (non-blocking): {ce_error}")

                # Analyze domain from ALL tasks (excluding root)
                event_modeling_start = datetime.now(timezone.utc)
                unified_analyzer = ContextAwareDomainAnalyzer(
                    self.analyzer.llm,
                    self.context_engine_client,
                    task_event_emitter
                )
                all_tasks = [task for task in tree.tasks.values() if task.depth > 0]

                # Prepare data for requirements generation
                epics_for_req = root_task.context.get('epics', []) if root_task.context else []
                stories_for_req = root_task.context.get('user_stories', []) if root_task.context else []
                tech_stack_for_req = context.get('tech_stack', {}) if context else {}

                # Run event modeling AND requirements generation in parallel
                print(f"[TaskProcessor] Running event modeling and requirements generation in parallel")
                event_model_task = unified_analyzer.analyze_domain(
                    all_tasks,
                    root_task,
                    user_id,
                    project_id=root_task.id
                )
                requirements_task = generate_requirements(
                    self.analyzer.llm,
                    root_task.description,
                    epics_for_req,
                    stories_for_req,
                    tech_stack_for_req
                )

                event_model_analysis, requirements_result = await asyncio.gather(
                    event_model_task, requirements_task
                )

                # Store requirements in metadata
                if requirements_result:
                    if not isinstance(root_task.metadata, dict):
                        root_task.metadata = {}
                    root_task.metadata["requirements"] = requirements_result
                    fr_count = len(requirements_result.get("functional_requirements", []))
                    nfr_count = len(requirements_result.get("non_functional_requirements", []))
                    print(f"[TaskProcessor] Generated {fr_count} functional, {nfr_count} non-functional requirements")

                # Record event modeling metrics
                event_modeling_time = (datetime.now(timezone.utc) - event_modeling_start).total_seconds()
                total_tasks = len(tree.tasks) - 1  # Exclude root task
                task_bucket = get_task_count_bucket(total_tasks)
                event_modeling_duration.labels(task_count_bucket=task_bucket).observe(event_modeling_time)
                print(f"[TaskProcessor] ⏱️  Event modeling took {event_modeling_time:.2f}s (bucket: {task_bucket}, tasks: {total_tasks})")

                # Ensure metadata is a dict
                if not isinstance(root_task.metadata, dict):
                    root_task.metadata = {}

                # Store complete event model
                self._store_event_model(root_task, event_model_analysis)

                await self.storage.save_task(root_task)

                # Emit event modeling completed with counts
                await task_event_emitter.emit_event_modeling_completed(
                    root_task,
                    user_id,
                    len(event_model_analysis.get("events", [])),
                    len(event_model_analysis.get("commands", [])),
                    len(event_model_analysis.get("read_models", []))
                )

                print(f"[TaskProcessor] Complete event model: {len(event_model_analysis.get('commands', []))} commands, {len(event_model_analysis.get('events', []))} events")

                # Publish event model to Context Engine
                if self.context_engine_client:
                    try:
                        # Serialize event model for JSON (convert DomainEvent objects to dicts)
                        serializable_event_model = {}

                        # Serialize events (DomainEvent objects)
                        if event_model_analysis.get("events"):
                            serializable_event_model["events"] = [
                                {
                                    "name": e.name,
                                    "event_type": e.event_type.value,
                                    "description": e.description,
                                    "actor": e.actor,
                                    "affected_entity": e.affected_entity,
                                    "triggers": e.triggers,
                                    "source_task_id": e.source_task_id,
                                    "metadata": e.metadata
                                }
                                for e in event_model_analysis["events"]
                            ]

                        # Copy other fields directly (they're already serializable)
                        for key in ["commands", "read_models", "user_interactions", "automations", "swimlanes", "chapters", "wireframes"]:
                            if event_model_analysis.get(key):
                                serializable_event_model[key] = event_model_analysis[key]

                        await self.context_engine_client.redis.publish(
                            "project:event_model_updated",
                            __import__('json').dumps({
                                "project_id": root_task.id,
                                "user_id": root_task.user_id,
                                "event_model": serializable_event_model
                            })
                        )
                        print(f"[TaskProcessor] ✓ Published event model to Context Engine")
                    except Exception as e:
                        print(f"[TaskProcessor] ⚠ Failed to publish event model to Context Engine: {e}")

            except Exception as e:
                print(f"[TaskProcessor] Error in event modeling analysis: {e}")
                import traceback
                traceback.print_exc()
                # Continue even if event modeling fails

            # PASS 3: Task Enrichment with Complete Event Model (if event model exists)
            if self.story_driven_analyzer and stories_by_epic and event_model_analysis:
                print(f"[TaskProcessor] PASS 3: Enriching tasks with complete event model context")
                enriched_tasks = await self._enrich_tasks_with_event_model(
                    root_task, tree, epics, stories_by_epic, event_model_analysis, context, max_depth, user_id
                )
                print(f"[TaskProcessor] Task enrichment complete: {len(enriched_tasks)} new tasks added")

            # PASS 4: Associate tasks with slices
            if event_model_analysis and event_model_analysis.get("chapters"):
                print(f"[TaskProcessor] PASS 4: Associating tasks with slices for code generation")
                from app.services.slice_associator import SliceAssociator
                slice_associator = SliceAssociator(self.analyzer.llm)

                # Get all atomic tasks
                all_tasks = [task for task in tree.tasks.values() if task.is_atomic]

                # Associate and update tasks
                task_slice_map = await slice_associator.associate_and_update_tasks(
                    all_tasks, event_model_analysis, self.storage
                )

                # Store slice mapping in root task metadata for easy access
                if not isinstance(root_task.metadata, dict):
                    root_task.metadata = {}
                root_task.metadata["task_slice_map"] = task_slice_map
                await self.storage.save_task(root_task)

                print(f"[TaskProcessor] Associated tasks with {len(task_slice_map)} slices")

            # Mark root task as complete
            if root_task.status != TaskStatus.COMPLETED:
                print(f"[TaskProcessor] All processing complete, marking root task as complete")
                old_status = root_task.status
                root_task.status = TaskStatus.COMPLETED
                await self.storage.save_task(root_task)
                # Emit status change event so frontend updates
                await task_event_emitter.emit_task_status_changed(root_task, old_status, root_task.user_id)

            # Save complete tree
            await self.storage.save_task_tree(tree)

            # Publish task tree to Context Engine
            if self.context_engine_client:
                try:
                    # Build task tree summary for Context Engine
                    task_tree_data = {
                        "root_task_id": root_task.id,
                        "total_tasks": len(tree.tasks),
                        "atomic_tasks": len([t for t in tree.tasks.values() if t.is_atomic]),
                        "max_depth": max([t.depth for t in tree.tasks.values()]),
                        "tasks": [
                            {
                                "id": task.id,
                                "description": task.description,
                                "depth": task.depth,
                                "is_atomic": task.is_atomic,
                                "parent_id": task.parent_id
                            }
                            for task in tree.tasks.values()
                        ]
                    }
                    await self.context_engine_client.redis.publish(
                        "project:task_tree_updated",
                        __import__('json').dumps({
                            "project_id": root_task.id,
                            "user_id": root_task.user_id,
                            "task_tree": task_tree_data
                        })
                    )
                    print(f"[TaskProcessor] ✓ Published task tree ({len(tree.tasks)} tasks) to Context Engine")
                except Exception as e:
                    print(f"[TaskProcessor] ⚠ Failed to publish task tree to Context Engine: {e}")

            # Update statistics
            processing_time = (datetime.now(timezone.utc) - root_task.created_at).total_seconds()
            self.stats["processing_time"] += processing_time
            self.stats["tasks_processed"] += len(tree.tasks)

        except Exception as e:
            import traceback
            print(f"Error in async task processing: {e}")
            print(f"Full traceback:")
            traceback.print_exc()

            # Check if this is a retryable error
            retry_count = root_task.metadata.get("retry_count", 0)
            max_retries = 3

            # Errors that should be retried
            is_retryable = (
                "validation error" in str(e).lower() or
                "timeout" in str(e).lower() or
                "connection" in str(e).lower() or
                "rate limit" in str(e).lower()
            )

            if is_retryable and retry_count < max_retries:
                retry_count += 1
                root_task.metadata["retry_count"] = retry_count
                root_task.metadata["last_error"] = str(e)
                root_task.status = TaskStatus.PENDING
                await self.storage.save_task(root_task)

                print(f"[TaskProcessor] Retrying task (attempt {retry_count}/{max_retries})...")

                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** retry_count)

                # Retry the processing
                await self.process_task_async(root_task, context, user_id, max_depth)
            else:
                # Update task status to error
                root_task.status = TaskStatus.ERROR
                root_task.metadata["error"] = str(e)
                root_task.metadata["retry_count"] = retry_count
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
            # Use the pre-assigned ID if available (from dependency resolution)
            subtask_id = subtask_data.get("id") or str(uuid.uuid4())
            # Don't store full context - it's published to Context Engine
            # Only store tech_stack reference for quick access
            minimal_context = {"tech_stack": context.get("tech_stack")} if context and context.get("tech_stack") else None
            subtask = Task(
                id=subtask_id,
                description=subtask_data["description"],
                status=TaskStatus.SUBMITTED,
                depth=parent.depth + 1,
                parent_id=parent.id,
                is_atomic=subtask_data.get("is_atomic", False),
                implementation_details=subtask_data.get("implementation_details"),
                story_points=subtask_data.get("story_points"),
                depends_on=subtask_data.get("depends_on", []),  # Include dependencies!
                context=minimal_context,
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
            try:
                # Extract prompt config from context if present
                prompt_config = context.get('prompt_config') if context else None
                story_decompositions = await self.story_driven_analyzer.decompose_stories_to_tasks(
                    epic_stories, epic, context, config=prompt_config
                )
            except Exception as e:
                print(f"[TaskProcessor] ERROR: Story decomposition failed for epic {epic.title}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with next epic instead of failing entirely
                continue

            # Process the decompositions
            for story in epic_stories:
                decomposition = story_decompositions.get(story.id)
                if not decomposition:
                    print(f"[TaskProcessor] WARNING: No decomposition generated for story {story.id}, skipping")
                    continue

                # Create tasks from decomposition
                for subtask_data in decomposition.subtasks:
                    is_atomic = subtask_data.get("is_atomic", False)

                    # Atomic tasks with implementation details are completed
                    status = TaskStatus.COMPLETED if (is_atomic and subtask_data.get("implementation_details")) else TaskStatus.SUBMITTED

                    # Use pre-assigned ID if available (from dependency resolution)
                    task_id = subtask_data.get("id") or str(uuid.uuid4())
                    # Don't store full context - it's published to Context Engine
                    minimal_context = {"tech_stack": context.get("tech_stack")} if context and context.get("tech_stack") else None
                    task = Task(
                        id=task_id,
                        description=subtask_data["description"],
                        status=status,
                        depth=1,  # All story tasks start at depth 1
                        parent_id=root_task.id,
                        is_atomic=is_atomic,
                        implementation_details=subtask_data.get("implementation_details"),
                        story_points=subtask_data.get("story_points"),
                        depends_on=subtask_data.get("depends_on", []),  # Include dependencies!
                        story_ids=[subtask_data.get("story_id")] if subtask_data.get("story_id") else [],
                        epic_ids=[subtask_data.get("epic_id")] if subtask_data.get("epic_id") else [],
                        context=minimal_context,
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

        # NOTE: Do NOT mark as complete here - event modeling happens after this method returns
        # Completion is handled in process_task_async after event modeling completes

    async def _enrich_tasks_with_event_model(
        self,
        root_task: Task,
        tree: TaskTree,
        epics: List[Any],
        stories_by_epic: Dict[str, List[Any]],
        event_model: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        max_depth: Optional[int],
        user_id: Optional[str]
    ) -> List[Task]:
        """Re-decompose stories with full event model context, replacing Pass 1 tasks.

        Pass 2 has the complete event model context, so we clear Pass 1 tasks
        and regenerate from scratch to avoid duplication and get better quality.

        Args:
            root_task: Root task
            tree: Current task tree (with preliminary tasks from Pass 1)
            epics: List of epics
            stories_by_epic: Stories grouped by epic
            event_model: Complete event model from Pass 2
            context: Processing context
            max_depth: Maximum depth
            user_id: User ID for events

        Returns:
            List of newly created enriched tasks
        """
        # Create enriched context with full event model
        enriched_context = {**(context or {}), "event_model": event_model}

        # Keep track of Pass 1 tasks - only delete after we successfully generate Pass 3 tasks
        pass1_task_ids = [
            task_id for task_id, task in tree.tasks.items()
            if task.depth > 0 and task.id != root_task.id
        ]
        pass1_task_count = len(pass1_task_ids)

        new_tasks = []
        existing_descriptions = set()  # Start fresh
        pass3_successful_epics = 0
        pass3_failed_epics = 0

        total_stories = sum(len(stories) for stories in stories_by_epic.values())
        print(f"[TaskProcessor] Re-decomposing {total_stories} stories with {len(event_model.get('commands', []))} commands in event model context")

        for epic in epics:
            epic_stories = stories_by_epic.get(epic.id, [])
            if not epic_stories:
                continue

            print(f"[TaskProcessor] Re-decomposing {len(epic_stories)} stories for epic: {epic.title} (with event model)")

            # Re-decompose with full event model context
            try:
                # Extract prompt config from enriched context if present
                prompt_config = enriched_context.get('prompt_config')
                story_decompositions = await self.story_driven_analyzer.decompose_stories_to_tasks(
                    epic_stories, epic, enriched_context,  # ← Now has complete event model!
                    config=prompt_config
                )
                pass3_successful_epics += 1
            except Exception as e:
                print(f"[TaskProcessor] Error in enriched decomposition for epic {epic.title}: {e}")
                import traceback
                traceback.print_exc()
                pass3_failed_epics += 1
                continue

            # Process decompositions
            for story in epic_stories:
                decomposition = story_decompositions.get(story.id)
                if not decomposition:
                    continue

                for subtask_data in decomposition.subtasks:
                    description = subtask_data["description"]
                    description_normalized = description.lower().strip()

                    # Skip if we already have this task (avoid duplicates)
                    if description_normalized in existing_descriptions:
                        continue

                    # Create new enriched task - use pre-assigned ID if available
                    task_id = subtask_data.get("id") or str(uuid.uuid4())
                    # Don't store full enriched_context - it's published to Context Engine
                    minimal_context = {"tech_stack": enriched_context.get("tech_stack")} if enriched_context and enriched_context.get("tech_stack") else None
                    task = Task(
                        id=task_id,
                        description=description,
                        status=TaskStatus.COMPLETED,
                        depth=1,
                        parent_id=root_task.id,
                        is_atomic=True,
                        implementation_details=subtask_data.get("implementation_details"),
                        story_points=subtask_data.get("story_points"),
                        depends_on=subtask_data.get("depends_on", []),  # Include dependencies!
                        story_ids=[story.id],
                        epic_ids=[epic.id],
                        context=minimal_context,
                        user_id=root_task.user_id,
                        metadata={"source": "event_model_enrichment"}  # Mark as enriched
                    )

                    # Add to tree
                    tree.add_task(task)
                    await self.storage.save_task(task)

                    # Add to root task's children
                    if not root_task.subtasks:
                        root_task.subtasks = []
                    root_task.subtasks.append(task.id)

                    # Track
                    new_tasks.append(task)
                    existing_descriptions.add(description_normalized)

                    # Emit event
                    await task_event_emitter.emit_task_created(task, user_id)

        # Only clear Pass 1 tasks if Pass 3 successfully generated replacement tasks
        if new_tasks and pass3_successful_epics > 0:
            print(f"[TaskProcessor] Pass 3 succeeded ({pass3_successful_epics} epics, {len(new_tasks)} tasks). Clearing {pass1_task_count} Pass 1 tasks.")
            for task_id in pass1_task_ids:
                # Remove from tree
                if task_id in tree.tasks:
                    del tree.tasks[task_id]
                # Remove from root's subtasks (but keep Pass 3 tasks we just added)
                if root_task.subtasks and task_id in root_task.subtasks:
                    root_task.subtasks.remove(task_id)
                # Delete from storage
                await self.storage.delete_task(task_id)
        elif pass3_failed_epics > 0 and not new_tasks:
            print(f"[TaskProcessor] ⚠ Pass 3 FAILED for all {pass3_failed_epics} epics. KEEPING {pass1_task_count} Pass 1 tasks to avoid zero-task state.")
        elif not new_tasks and pass1_task_count > 0:
            print(f"[TaskProcessor] ⚠ Pass 3 produced no new tasks. KEEPING {pass1_task_count} Pass 1 tasks.")

        return new_tasks

    async def _check_task_completion(self, task: Task, tree: TaskTree) -> None:
        """Check if a task is complete based on its children.

        Args:
            task: Task to check
            tree: Task tree
        """
        # Don't auto-complete root tasks - they need event modeling first
        if task.depth == 0:
            return

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

    def _store_event_model(self, root_task: Task, analysis: Dict[str, Any]) -> None:
        """Store event model analysis in task metadata.

        Args:
            root_task: Root task to store metadata in
            analysis: Event model analysis from UnifiedDomainAnalyzer
        """
        # Store events
        if analysis.get("events"):
            root_task.metadata["extracted_events"] = [
                {
                    "name": e.name,
                    "event_type": e.event_type.value,
                    "description": e.description,
                    "actor": e.actor,
                    "affected_entity": e.affected_entity,
                    "triggers": e.triggers,
                    "source_task_id": e.source_task_id,
                    "metadata": e.metadata,
                    # Flatten payload from metadata for frontend convenience
                    "payload": e.metadata.get("payload", []) if isinstance(e.metadata, dict) else []
                }
                for e in analysis["events"]
            ]
            # Record events by type
            for event in analysis["events"]:
                events_generated_total.labels(event_type=event.event_type.value).inc()
            print(f"[TaskProcessor] Extracted {len(analysis['events'])} events")

        # Store commands, read models, user interactions, automations
        if analysis.get("commands"):
            root_task.metadata["commands"] = analysis["commands"]
            commands_generated_total.inc(len(analysis["commands"]))
            print(f"[TaskProcessor] Identified {len(analysis['commands'])} commands")

        if analysis.get("read_models"):
            root_task.metadata["read_models"] = analysis["read_models"]
            read_models_generated_total.inc(len(analysis["read_models"]))
            print(f"[TaskProcessor] Identified {len(analysis['read_models'])} read models")

        if analysis.get("user_interactions"):
            root_task.metadata["user_interactions"] = analysis["user_interactions"]
            print(f"[TaskProcessor] Identified {len(analysis['user_interactions'])} user interactions")

        if analysis.get("automations"):
            root_task.metadata["automations"] = analysis["automations"]
            automations_generated_total.inc(len(analysis["automations"]))
            print(f"[TaskProcessor] Identified {len(analysis['automations'])} automations")

        # Store swimlanes and chapters
        if analysis.get("swimlanes"):
            root_task.metadata["swimlanes"] = analysis["swimlanes"]
            print(f"[TaskProcessor] Identified {len(analysis['swimlanes'])} swimlanes")

        if analysis.get("chapters"):
            root_task.metadata["chapters"] = analysis["chapters"]
            chapters_generated_total.inc(len(analysis["chapters"]))
            print(f"[TaskProcessor] Identified {len(analysis['chapters'])} chapters")

        # Store wireframes if present
        if analysis.get("wireframes"):
            root_task.metadata["wireframes"] = analysis["wireframes"]
            print(f"[TaskProcessor] Generated {len(analysis['wireframes'])} wireframes")

        # Validate event model
        from app.analyzer.event_model_validator import EventModelValidator
        validator = EventModelValidator()
        is_valid, validation_issues = validator.validate(analysis)
        validation_summary = validator.get_validation_summary()

        print(f"[TaskProcessor] Event model validation: {'PASSED' if is_valid else 'FAILED'}")
        print(f"  - Errors: {validation_summary['errors']}")
        print(f"  - Warnings: {validation_summary['warnings']}")

        # Record validation metrics
        event_model_validations_total.labels(result="passed" if is_valid else "failed").inc()

        # Store validation results
        root_task.metadata["event_model_validation"] = {
            "valid": is_valid,
            "summary": validation_summary,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "details": issue.details
                }
                for issue in validation_issues
            ]
        }

        # Store data flow validation if present
        if analysis.get("data_flow_validation"):
            root_task.metadata["data_flow_validation"] = analysis["data_flow_validation"]

        # Generate event model markdown
        from app.analyzer.event_model_markdown_generator import EventModelMarkdownGenerator
        markdown_generator = EventModelMarkdownGenerator()
        event_model_markdown = markdown_generator.generate(analysis, root_task.description)

        # Append validation results to markdown
        if not is_valid or validation_summary['warnings'] > 0:
            event_model_markdown += self._generate_validation_section(validation_summary, validation_issues)

        root_task.metadata["event_model_markdown"] = event_model_markdown
        print(f"[TaskProcessor] Generated event model markdown ({len(event_model_markdown)} chars)")

    def _generate_validation_section(self, summary: Dict[str, Any], issues: List) -> str:
        """Generate markdown section for validation results"""

        md = "\n\n---\n\n## ⚠️ Event Model Validation\n\n"

        # Summary
        if summary['valid']:
            md += "**Status**: ✅ PASSED (with warnings)\n\n"
        else:
            md += "**Status**: ❌ FAILED\n\n"

        md += f"- **Errors**: {summary['errors']}\n"
        md += f"- **Warnings**: {summary['warnings']}\n"
        md += f"- **Total Issues**: {summary['total_issues']}\n\n"

        # Critical issues
        if summary.get('critical_issues'):
            md += "### Critical Issues\n\n"
            for issue in summary['critical_issues']:
                md += f"- **{issue['message']}**\n"
                if issue.get('details'):
                    for key, value in issue['details'].items():
                        md += f"  - {key}: {value}\n"
                md += "\n"

        # Issues by category
        if summary.get('issues_by_category'):
            md += "### Issues by Category\n\n"
            md += "| Category | Count |\n"
            md += "|----------|-------|\n"
            for category, count in sorted(summary['issues_by_category'].items()):
                md += f"| {category} | {count} |\n"
            md += "\n"

        # All issues
        errors = [i for i in issues if i.severity == 'error']
        warnings = [i for i in issues if i.severity == 'warning']

        if errors:
            md += "### Errors\n\n"
            for issue in errors:
                md += f"**{issue.category}**: {issue.message}\n\n"

        if warnings:
            md += "### Warnings\n\n"
            for issue in warnings:
                md += f"**{issue.category}**: {issue.message}\n\n"

        return md
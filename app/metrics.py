"""
Comprehensive metrics for the Idea Compiler pipeline.

This module provides Prometheus metrics for all stages of the pipeline:
- Stage 0: Input & Context Enrichment
- Stage 1: Epic & Story Generation
- Stage 2: Event Model Generation
- Stage 3: Event Model Validation
- Stage 4: Task Decomposition
- Stage 5: Slice Association
- Stage 6: Code Generation - Scaffolding
- Stage 7: Code Generation - Slice Processing
- Stage 8: Test Execution
- Stage 9: Merge & Conflict Resolution
- Stage 10: Integration
- Stage 11: Project Completion

Plus cross-cutting LLM cost & efficiency metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time
from typing import Callable, Any, Optional
from contextlib import contextmanager


# =============================================================================
# STAGE 0: Input & Context Enrichment
# =============================================================================

projects_created_total = Counter(
    'projects_created_total',
    'Total projects initiated',
    ['source']  # api, ui
)

context_enrichment_duration_seconds = Histogram(
    'context_enrichment_duration_seconds',
    'Time spent enriching context via web search',
    ['enrichment_type'],  # domain, technical, competitive
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

web_searches_total = Counter(
    'web_searches_total',
    'Number of web searches performed',
    ['search_type', 'status']  # status: success, error
)

web_search_results_count = Histogram(
    'web_search_results_count',
    'Number of results returned per search',
    ['search_type'],
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

context_tokens_total = Counter(
    'context_tokens_total',
    'Tokens in enriched context',
    ['context_type']  # user_input, web_enrichment, repository
)


# =============================================================================
# STAGE 1: Epic & Story Generation
# =============================================================================

epic_generation_duration_seconds = Histogram(
    'epic_generation_duration_seconds',
    'Time to generate epics',
    ['project_complexity'],  # simple, medium, complex
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

epics_generated_total = Counter(
    'epics_generated_total',
    'Total epics created'
)

epics_per_project = Histogram(
    'epics_per_project',
    'Distribution of epic count per project',
    buckets=[1, 2, 3, 5, 7, 10, 15, 20]
)

story_generation_duration_seconds = Histogram(
    'story_generation_duration_seconds',
    'Time to generate stories',
    ['project_complexity'],
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

stories_generated_total = Counter(
    'stories_generated_total',
    'Total stories created'
)

stories_per_epic = Histogram(
    'stories_per_epic',
    'Distribution of stories per epic',
    buckets=[1, 2, 3, 5, 7, 10, 15, 20]
)

# Combined metric for backward compatibility
epic_story_generation_duration = Histogram(
    'epic_story_generation_duration_seconds',
    'Duration of epic and story generation phase',
    ['task_count_bucket'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)


# =============================================================================
# STAGE 2: Event Model Generation
# =============================================================================

event_model_generation_duration_seconds = Histogram(
    'event_model_generation_duration_seconds',
    'Time to generate complete event model',
    ['task_count_bucket'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

events_generated_total = Counter(
    'events_generated_total',
    'Total events created',
    ['event_type']  # user_action, system, integration
)

commands_generated_total = Counter(
    'commands_generated_total',
    'Total commands created'
)

read_models_generated_total = Counter(
    'read_models_generated_total',
    'Total read models created'
)

automations_generated_total = Counter(
    'automations_generated_total',
    'Total automations created'
)

chapters_generated_total = Counter(
    'chapters_generated_total',
    'Total chapters created'
)

slices_generated_total = Counter(
    'slices_generated_total',
    'Total slices created',
    ['slice_type']  # state_change, state_view, automation
)

swimlanes_generated_total = Counter(
    'swimlanes_generated_total',
    'Total swimlanes created'
)

events_per_project = Histogram(
    'events_per_project',
    'Events per project distribution',
    buckets=[5, 10, 20, 50, 100, 200, 500]
)

slices_per_chapter = Histogram(
    'slices_per_chapter',
    'Slices per chapter distribution',
    buckets=[1, 2, 3, 5, 7, 10, 15, 20]
)

# Backward compatibility alias
event_modeling_duration = Histogram(
    'event_modeling_duration_seconds',
    'Duration of event modeling analysis phase',
    ['task_count_bucket'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

# =============================================================================
# STAGE 2B: Event Modeling Sub-Phase Breakdown
# =============================================================================

event_modeling_subphase_duration = Histogram(
    'event_modeling_subphase_duration_seconds',
    'Duration of each event modeling sub-phase',
    ['subphase'],  # analyze_description, swimlanes_chapters, wireframes_dataflow, validation, fix_errors
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 90.0, 120.0]
)

event_modeling_llm_calls_per_subphase = Counter(
    'event_modeling_llm_calls_per_subphase',
    'LLM calls made during each event modeling sub-phase',
    ['subphase']
)

event_modeling_validation_retries = Histogram(
    'event_modeling_validation_retries',
    'Number of validation fix retries',
    buckets=[0, 1, 2, 3]
)

# Pre-initialize labels so metrics appear in /metrics endpoint even before first use
_SUBPHASE_LABELS = ['context_fetch', 'analyze_description', 'consolidation', 'deduplication', 'swimlanes_chapters', 'wireframes_dataflow', 'validation', 'fix_errors', 'context_publish']
for _subphase in _SUBPHASE_LABELS:
    event_modeling_subphase_duration.labels(subphase=_subphase)
    event_modeling_llm_calls_per_subphase.labels(subphase=_subphase)


# =============================================================================
# STAGE 3: Event Model Validation
# =============================================================================

event_model_validation_duration_seconds = Histogram(
    'event_model_validation_duration_seconds',
    'Time to validate event model',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

event_model_validations_total = Counter(
    'event_model_validations_total',
    'Total validations run',
    ['result']  # passed, failed
)

validation_errors_total = Counter(
    'validation_errors_total',
    'Total validation errors',
    ['category']  # command_without_event, orphan_event, etc.
)

validation_warnings_total = Counter(
    'validation_warnings_total',
    'Total validation warnings',
    ['category']
)

commands_without_events_total = Counter(
    'commands_without_events_total',
    'Commands with no resulting events'
)

orphan_events_total = Counter(
    'orphan_events_total',
    'Events with no trigger'
)

validation_score = Gauge(
    'validation_score',
    'Current validation score (0-100)',
    ['project_id']
)


# =============================================================================
# STAGE 4: Task Decomposition
# =============================================================================

task_decomposition_duration_seconds = Histogram(
    'task_decomposition_duration_seconds',
    'Time to decompose stories into tasks',
    ['task_count_bucket'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

tasks_generated_total = Counter(
    'tasks_generated_total',
    'Total tasks created',
    ['source']  # story, enrichment
)

tasks_per_story = Histogram(
    'tasks_per_story',
    'Tasks per story distribution',
    buckets=[1, 2, 3, 5, 7, 10, 15, 20]
)

atomic_tasks_total = Counter(
    'atomic_tasks_total',
    'Tasks marked as atomic'
)

task_dependency_edges_total = Counter(
    'task_dependency_edges_total',
    'Dependency relationships created'
)

dependency_graph_depth = Histogram(
    'dependency_graph_depth',
    'Max depth of task dependency graph',
    buckets=[1, 2, 3, 4, 5, 7, 10]
)

parallel_task_groups = Histogram(
    'parallel_task_groups',
    'Number of tasks that can run in parallel',
    buckets=[1, 2, 3, 5, 10, 20, 50]
)

# Backward compatibility
story_decomposition_duration = Histogram(
    'story_decomposition_duration_seconds',
    'Duration of story-to-tasks decomposition phase',
    ['task_count_bucket'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)


# =============================================================================
# STAGE 5: Slice Association
# =============================================================================

slice_association_duration_seconds = Histogram(
    'slice_association_duration_seconds',
    'Time to associate tasks with slices',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

tasks_per_slice = Histogram(
    'tasks_per_slice',
    'Tasks mapped to each slice',
    buckets=[0, 1, 2, 3, 5, 10, 20]
)

unassociated_tasks_total = Counter(
    'unassociated_tasks_total',
    'Tasks not mapped to any slice'
)

slices_without_tasks_total = Counter(
    'slices_without_tasks_total',
    'Slices with no implementing tasks'
)


# =============================================================================
# STAGE 6: Code Generation - Scaffolding
# =============================================================================

scaffold_duration_seconds = Histogram(
    'scaffold_duration_seconds',
    'Time to scaffold project',
    ['tech_stack'],
    buckets=[5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

scaffold_attempts_total = Counter(
    'scaffold_attempts_total',
    'Scaffold attempts',
    ['status', 'tech_stack']  # status: success, failure
)

scaffold_files_created = Histogram(
    'scaffold_files_created',
    'Files created during scaffold',
    ['tech_stack'],
    buckets=[5, 10, 20, 50, 100, 200]
)

scaffold_lines_of_code = Histogram(
    'scaffold_lines_of_code',
    'Lines of code in scaffold',
    ['tech_stack'],
    buckets=[100, 500, 1000, 2000, 5000, 10000]
)


# =============================================================================
# STAGE 7: Code Generation - Slice Processing
# =============================================================================

slice_processing_duration_seconds = Histogram(
    'slice_processing_duration_seconds',
    'Total time per slice (test+code+fix+merge)',
    ['slice_type', 'tech_stack'],
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

slices_processed_total = Counter(
    'slices_processed_total',
    'Slices processed',
    ['status', 'slice_type']  # status: success, failure, blocked
)

slices_in_progress = Gauge(
    'slices_in_progress',
    'Currently processing slices'
)

slice_test_generation_duration_seconds = Histogram(
    'slice_test_generation_duration_seconds',
    'Time to generate tests',
    ['slice_type'],
    buckets=[5.0, 10.0, 30.0, 60.0, 120.0]
)

slice_code_generation_duration_seconds = Histogram(
    'slice_code_generation_duration_seconds',
    'Time to generate implementation',
    ['slice_type'],
    buckets=[5.0, 10.0, 30.0, 60.0, 120.0]
)

slice_fix_iterations = Histogram(
    'slice_fix_iterations',
    'Fix attempts before success',
    ['slice_type'],
    buckets=[0, 1, 2, 3, 4, 5, 7, 10]
)

slice_fix_attempts_total = Counter(
    'slice_fix_attempts_total',
    'Total fix attempts',
    ['status', 'reason']  # reason: test_failure, lint_error, type_error
)

tests_generated_per_slice = Histogram(
    'tests_generated_per_slice',
    'Tests created per slice',
    ['slice_type'],
    buckets=[1, 2, 3, 5, 10, 20]
)

lines_of_code_per_slice = Histogram(
    'lines_of_code_per_slice',
    'Lines of code generated per slice',
    ['slice_type'],
    buckets=[10, 50, 100, 200, 500, 1000]
)

files_created_per_slice = Histogram(
    'files_created_per_slice',
    'Files created per slice',
    ['slice_type'],
    buckets=[1, 2, 3, 5, 10, 20]
)

slice_blocked_total = Counter(
    'slice_blocked_total',
    'Slices blocked (max retries)',
    ['reason']  # dependency_failed, max_retries, conflict
)

slice_queue_wait_seconds = Histogram(
    'slice_queue_wait_seconds',
    'Time slice waited before processing',
    buckets=[0, 1, 5, 10, 30, 60, 120]
)


# =============================================================================
# STAGE 8: Test Execution
# =============================================================================

test_run_duration_seconds = Histogram(
    'test_run_duration_seconds',
    'Time to run tests',
    ['tech_stack'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

test_runs_total = Counter(
    'test_runs_total',
    'Total test runs',
    ['status']  # passed, failed
)

tests_passed_total = Counter(
    'tests_passed_total',
    'Tests that passed'
)

tests_failed_total = Counter(
    'tests_failed_total',
    'Tests that failed',
    ['failure_type']  # assertion, timeout, error
)

test_pass_rate = Gauge(
    'test_pass_rate',
    'Current test pass rate',
    ['project_id']
)

first_run_pass_rate = Histogram(
    'first_run_pass_rate',
    'Percentage of tests passing on first run',
    buckets=[0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
)


# =============================================================================
# STAGE 9: Merge & Conflict Resolution
# =============================================================================

merge_attempts_total = Counter(
    'merge_attempts_total',
    'Total merge attempts',
    ['status']  # success, conflict, failure
)

merge_duration_seconds = Histogram(
    'merge_duration_seconds',
    'Time to complete merge',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
)

merge_conflicts_total = Counter(
    'merge_conflicts_total',
    'Merges with conflicts',
    ['conflict_type']  # textual, semantic
)

conflict_resolution_duration_seconds = Histogram(
    'conflict_resolution_duration_seconds',
    'Time to resolve conflicts',
    ['conflict_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
)

conflict_resolution_success_rate = Gauge(
    'conflict_resolution_success_rate',
    'Percentage of conflicts auto-resolved'
)

lines_conflicted_per_merge = Histogram(
    'lines_conflicted_per_merge',
    'Lines in conflict',
    buckets=[1, 5, 10, 20, 50, 100]
)

rebase_required_total = Counter(
    'rebase_required_total',
    'Merges requiring rebase'
)


# =============================================================================
# STAGE 10: Integration
# =============================================================================

integration_duration_seconds = Histogram(
    'integration_duration_seconds',
    'Time for integration pass',
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0]
)

integration_attempts_total = Counter(
    'integration_attempts_total',
    'Integration attempts',
    ['status']  # success, failure
)

integration_issues_found = Counter(
    'integration_issues_found',
    'Issues found during integration',
    ['issue_type']  # import_error, type_mismatch, missing_dependency
)

integration_fixes_applied = Counter(
    'integration_fixes_applied',
    'Auto-fixes applied',
    ['fix_type']
)


# =============================================================================
# STAGE 11: Project Completion - THE HEADLINE METRICS
# =============================================================================

project_completion_total = Counter(
    'project_completion_total',
    'Projects completed',
    ['status']  # success, partial, failed
)

project_duration_seconds = Histogram(
    'project_duration_seconds',
    'Total time from input to completion',
    ['complexity_bucket'],  # simple, medium, complex
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]  # 1min to 4hrs
)

idea_to_code_duration_seconds = Histogram(
    'idea_to_code_duration_seconds',
    'THE HEADLINE METRIC: Time from idea to deployable code',
    ['tech_stack'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]
)

total_lines_of_code_generated = Histogram(
    'total_lines_of_code_generated',
    'Total lines of code per project',
    ['tech_stack'],
    buckets=[100, 500, 1000, 2000, 5000, 10000, 50000]
)

total_files_generated = Histogram(
    'total_files_generated',
    'Total files per project',
    ['tech_stack'],
    buckets=[5, 10, 20, 50, 100, 200, 500]
)

total_tests_generated = Histogram(
    'total_tests_generated',
    'Total tests per project',
    ['tech_stack'],
    buckets=[5, 10, 20, 50, 100, 200]
)

human_interventions_total = Counter(
    'human_interventions_total',
    'Times humans had to intervene',
    ['intervention_type']  # approval, conflict, error
)

fully_autonomous_projects_total = Counter(
    'fully_autonomous_projects_total',
    'Projects completed without intervention'
)


# =============================================================================
# LLM COST & EFFICIENCY (Cross-cutting)
# =============================================================================

llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['operation', 'model', 'status']
)

llm_call_duration_seconds = Histogram(
    'llm_call_duration_seconds',
    'LLM call latency',
    ['operation', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_input_total = Counter(
    'llm_tokens_input_total',
    'Input tokens consumed',
    ['operation', 'model']
)

llm_tokens_output_total = Counter(
    'llm_tokens_output_total',
    'Output tokens generated',
    ['operation', 'model']
)

llm_cost_dollars = Counter(
    'llm_cost_dollars',
    'Estimated LLM cost in dollars',
    ['operation', 'model']
)

llm_retries_total = Counter(
    'llm_retries_total',
    'LLM calls that required retry',
    ['reason']  # rate_limit, timeout, error
)

llm_cache_hits_total = Counter(
    'llm_cache_hits_total',
    'Cached LLM responses used',
    ['operation']
)


# =============================================================================
# USER STATISTICS
# =============================================================================

user_projects_created_total = Counter(
    'user_projects_created_total',
    'Projects created per user',
    ['user_id']
)

user_llm_tokens_consumed_total = Counter(
    'user_llm_tokens_consumed_total',
    'Total LLM tokens consumed per user',
    ['user_id', 'token_type']  # token_type: input, output
)

user_codegen_runs_total = Counter(
    'user_codegen_runs_total',
    'Code generation runs per user',
    ['user_id', 'status']  # status: started, completed, failed
)

user_active_sessions = Gauge(
    'user_active_sessions',
    'Current active sessions per user',
    ['user_id']
)

unique_users_total = Counter(
    'unique_users_total',
    'Total unique users (increment on first activity)',
    ['source']  # source: auth0, local, anonymous
)

user_request_total = Counter(
    'user_request_total',
    'Total API requests per user',
    ['user_id', 'endpoint_category']  # endpoint_category: tasks, codegen, export, etc.
)

user_api_latency = Histogram(
    'user_api_latency_seconds',
    'API request latency per user',
    ['user_id', 'endpoint_category'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

daily_active_users = Gauge(
    'daily_active_users',
    'Number of users active in the last 24 hours'
)

weekly_active_users = Gauge(
    'weekly_active_users',
    'Number of users active in the last 7 days'
)

monthly_active_users = Gauge(
    'monthly_active_users',
    'Number of users active in the last 30 days'
)


# =============================================================================
# BACKWARD COMPATIBILITY - Legacy metrics
# =============================================================================

# Keep these for backward compatibility with existing code
llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total tokens used in LLM calls (legacy)',
    ['operation', 'model', 'type']
)

task_processing_duration = Histogram(
    'task_processing_duration_seconds',
    'Duration of task processing pipeline (legacy)',
    ['complexity'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

tasks_processed_total = Counter(
    'tasks_processed_total',
    'Total tasks processed (legacy)',
    ['status', 'complexity']
)

impl_tasks_generated_total = Counter(
    'impl_tasks_generated_total',
    'Total implementation tasks generated (legacy)'
)

active_tasks = Gauge(
    'active_tasks',
    'Number of tasks currently being processed (legacy)'
)

context_engine_publish_duration = Histogram(
    'context_engine_publish_duration_seconds',
    'Duration of context engine data publishing',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_task_count_bucket(task_count: int) -> str:
    """Convert task count to a bucket label for metrics."""
    if task_count <= 5:
        return "1-5"
    elif task_count <= 10:
        return "6-10"
    elif task_count <= 20:
        return "11-20"
    elif task_count <= 50:
        return "21-50"
    else:
        return "51+"


def get_complexity_bucket(complexity_score: float) -> str:
    """Convert complexity score (0-1) to bucket label."""
    if complexity_score < 0.3:
        return "simple"
    elif complexity_score < 0.7:
        return "medium"
    else:
        return "complex"


# =============================================================================
# DECORATORS FOR EASY INSTRUMENTATION
# =============================================================================

def track_llm_call(operation: str, model: str = "unknown"):
    """Decorator to track LLM call metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                llm_call_duration_seconds.labels(operation=operation, model=model).observe(duration)
                llm_calls_total.labels(operation=operation, model=model, status=status).inc()
        return wrapper
    return decorator


def track_task_processing(complexity: str = "unknown"):
    """Decorator to track task processing metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            active_tasks.inc()
            start = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                active_tasks.dec()
                task_processing_duration.labels(complexity=complexity).observe(duration)
                tasks_processed_total.labels(status=status, complexity=complexity).inc()
        return wrapper
    return decorator


def track_stage_duration(stage_histogram: Histogram, **labels):
    """Generic decorator to track stage duration."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                stage_histogram.labels(**labels).observe(duration)
        return wrapper
    return decorator


@contextmanager
def track_duration(histogram: Histogram, **labels):
    """Context manager to track duration of a code block."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        histogram.labels(**labels).observe(duration)


class MetricsCollector:
    """
    Centralized metrics collector for a project/generation run.

    Tracks all metrics for a single project and provides summary methods.
    """

    def __init__(self, project_id: str, tech_stack: str = "unknown"):
        self.project_id = project_id
        self.tech_stack = tech_stack
        self.start_time = time.time()

        # Internal counters for this project
        self._epics = 0
        self._stories = 0
        self._tasks = 0
        self._slices_completed = 0
        self._slices_failed = 0
        self._tests_passed = 0
        self._tests_failed = 0
        self._llm_calls = 0
        self._llm_tokens_in = 0
        self._llm_tokens_out = 0
        self._lines_of_code = 0
        self._files_created = 0
        self._human_interventions = 0

    def record_project_start(self, source: str = "api"):
        """Record project creation."""
        projects_created_total.labels(source=source).inc()

    def record_epics(self, count: int, duration: float, complexity: str = "medium"):
        """Record epic generation."""
        self._epics = count
        epics_generated_total.inc(count)
        epics_per_project.observe(count)
        epic_generation_duration_seconds.labels(project_complexity=complexity).observe(duration)

    def record_stories(self, count: int, epic_count: int, duration: float, complexity: str = "medium"):
        """Record story generation."""
        self._stories = count
        stories_generated_total.inc(count)
        if epic_count > 0:
            stories_per_epic.observe(count / epic_count)
        story_generation_duration_seconds.labels(project_complexity=complexity).observe(duration)

    def record_event_model(
        self,
        events: int,
        commands: int,
        read_models: int,
        automations: int,
        chapters: int,
        slices: int,
        duration: float
    ):
        """Record event model generation."""
        commands_generated_total.inc(commands)
        read_models_generated_total.inc(read_models)
        automations_generated_total.inc(automations)
        chapters_generated_total.inc(chapters)
        events_per_project.observe(events)

        task_bucket = get_task_count_bucket(self._tasks or slices)
        event_model_generation_duration_seconds.labels(task_count_bucket=task_bucket).observe(duration)

    def record_validation(self, passed: bool, errors: int, warnings: int, score: float):
        """Record event model validation."""
        result = "passed" if passed else "failed"
        event_model_validations_total.labels(result=result).inc()
        validation_score.labels(project_id=self.project_id).set(score)

    def record_tasks(self, count: int, atomic_count: int, source: str = "story"):
        """Record task decomposition."""
        self._tasks = count
        tasks_generated_total.labels(source=source).inc(count)
        atomic_tasks_total.inc(atomic_count)

    def record_slice_start(self):
        """Record slice processing start."""
        slices_in_progress.inc()

    def record_slice_complete(
        self,
        slice_type: str,
        duration: float,
        fix_iterations: int,
        tests: int,
        loc: int,
        files: int
    ):
        """Record successful slice completion."""
        slices_in_progress.dec()
        self._slices_completed += 1
        self._lines_of_code += loc
        self._files_created += files

        slices_processed_total.labels(status="success", slice_type=slice_type).inc()
        slice_processing_duration_seconds.labels(
            slice_type=slice_type, tech_stack=self.tech_stack
        ).observe(duration)
        slice_fix_iterations.labels(slice_type=slice_type).observe(fix_iterations)
        tests_generated_per_slice.labels(slice_type=slice_type).observe(tests)
        lines_of_code_per_slice.labels(slice_type=slice_type).observe(loc)
        files_created_per_slice.labels(slice_type=slice_type).observe(files)

    def record_slice_failure(self, slice_type: str, reason: str):
        """Record slice failure."""
        slices_in_progress.dec()
        self._slices_failed += 1
        slices_processed_total.labels(status="failure", slice_type=slice_type).inc()
        slice_blocked_total.labels(reason=reason).inc()

    def record_llm_call(
        self,
        operation: str,
        model: str,
        duration: float,
        tokens_in: int,
        tokens_out: int,
        status: str = "success"
    ):
        """Record LLM API call."""
        self._llm_calls += 1
        self._llm_tokens_in += tokens_in
        self._llm_tokens_out += tokens_out

        llm_calls_total.labels(operation=operation, model=model, status=status).inc()
        llm_call_duration_seconds.labels(operation=operation, model=model).observe(duration)
        llm_tokens_input_total.labels(operation=operation, model=model).inc(tokens_in)
        llm_tokens_output_total.labels(operation=operation, model=model).inc(tokens_out)

    def record_test_run(self, passed: int, failed: int, duration: float):
        """Record test execution."""
        self._tests_passed += passed
        self._tests_failed += failed

        status = "passed" if failed == 0 else "failed"
        test_runs_total.labels(status=status).inc()
        tests_passed_total.inc(passed)
        test_run_duration_seconds.labels(tech_stack=self.tech_stack).observe(duration)

        if passed + failed > 0:
            pass_rate = passed / (passed + failed)
            test_pass_rate.labels(project_id=self.project_id).set(pass_rate)

    def record_merge(self, success: bool, conflicts: int = 0, duration: float = 0):
        """Record merge operation."""
        status = "success" if success else ("conflict" if conflicts > 0 else "failure")
        merge_attempts_total.labels(status=status).inc()
        merge_duration_seconds.observe(duration)
        if conflicts > 0:
            merge_conflicts_total.labels(conflict_type="textual").inc(conflicts)

    def record_human_intervention(self, intervention_type: str):
        """Record human intervention."""
        self._human_interventions += 1
        human_interventions_total.labels(intervention_type=intervention_type).inc()

    def record_completion(self, status: str = "success"):
        """Record project completion and emit summary metrics."""
        total_duration = time.time() - self.start_time

        project_completion_total.labels(status=status).inc()
        project_duration_seconds.labels(
            complexity_bucket=get_complexity_bucket(self._tasks / 100 if self._tasks else 0)
        ).observe(total_duration)

        # THE HEADLINE METRIC
        idea_to_code_duration_seconds.labels(tech_stack=self.tech_stack).observe(total_duration)

        total_lines_of_code_generated.labels(tech_stack=self.tech_stack).observe(self._lines_of_code)
        total_files_generated.labels(tech_stack=self.tech_stack).observe(self._files_created)
        total_tests_generated.labels(tech_stack=self.tech_stack).observe(self._tests_passed)

        if self._human_interventions == 0:
            fully_autonomous_projects_total.inc()

    def get_summary(self) -> dict:
        """Get summary of all metrics for this project."""
        total_duration = time.time() - self.start_time
        return {
            "project_id": self.project_id,
            "tech_stack": self.tech_stack,
            "duration_seconds": total_duration,
            "epics": self._epics,
            "stories": self._stories,
            "tasks": self._tasks,
            "slices_completed": self._slices_completed,
            "slices_failed": self._slices_failed,
            "tests_passed": self._tests_passed,
            "tests_failed": self._tests_failed,
            "llm_calls": self._llm_calls,
            "llm_tokens_in": self._llm_tokens_in,
            "llm_tokens_out": self._llm_tokens_out,
            "lines_of_code": self._lines_of_code,
            "files_created": self._files_created,
            "human_interventions": self._human_interventions,
            "fully_autonomous": self._human_interventions == 0,
        }


def get_metrics():
    """Get current metrics in Prometheus format."""
    return generate_latest()

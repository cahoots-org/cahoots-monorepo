"""Context-Aware wrapper for UnifiedDomainAnalyzer

This wraps the existing UnifiedDomainAnalyzer to provide automatic context injection
via the Context Engine while preserving its efficient single-LLM-call architecture.
"""

import types
from typing import List, Dict, Any, Optional
from app.models import Task
from app.analyzer.llm_client import LLMClient
from app.analyzer.context_aware_agent import ContextAwareAgent
from app.analyzer.unified_domain_analyzer import UnifiedDomainAnalyzer
from app.services.context_engine_client import ContextEngineClient


class ContextAwareDomainAnalyzer(ContextAwareAgent):
    """Domain analyzer with automatic context injection from Context Engine

    This agent wraps UnifiedDomainAnalyzer to provide:
    - Automatic registration with Context Engine
    - Context injection into all LLM calls
    - Publishing of analysis results back to Context Engine
    - Preservation of efficient single-LLM-call architecture
    """

    AGENT_ID = "domain-analyzer"

    DATA_NEEDS = [
        "tech stack and programming languages used in the project",
        "existing event models and domain patterns from previous analysis",
        "completed tasks with implementation details and patterns",
        "user stories and epics with acceptance criteria",
        "architectural context from repository analysis",
        "database schema and data models",
        "API endpoints and integration patterns"
    ]

    def __init__(
        self,
        llm_client: LLMClient,
        context_engine: Optional[ContextEngineClient] = None,
        task_event_emitter=None
    ):
        """Initialize context-aware domain analyzer

        Args:
            llm_client: LLM client for making model calls
            context_engine: Optional Context Engine client for automatic context
            task_event_emitter: Optional event emitter for progress updates
        """
        super().__init__(llm_client, context_engine)

        # Create wrapped analyzer instance - but override its llm to use our context-aware one
        self.domain_analyzer = UnifiedDomainAnalyzer(llm_client, task_event_emitter)
        self.task_event_emitter = task_event_emitter

        # Intercept the LLM client to inject context
        self._wrap_llm_client()

    def _wrap_llm_client(self):
        """Wrap the LLM client's chat_completion method to automatically inject context"""
        # IMPORTANT: Wrap the domain_analyzer's LLM, not self.llm, since that's what UnifiedDomainAnalyzer uses
        llm_instance = self.domain_analyzer.llm
        original_chat_completion = llm_instance.chat_completion

        # Store reference to self for closure
        wrapper_self = self

        async def context_aware_chat_completion(llm_self, *args, **kwargs):
            """Wrapper that injects context before calling LLM

            Args:
                llm_self: The LLM client instance (bound method first parameter)
                *args: Positional arguments (first is messages)
                **kwargs: Keyword arguments
            """
            # Extract messages from args or kwargs
            if args:
                messages = args[0]
                remaining_args = args[1:]
            else:
                messages = kwargs.get('messages', [])
                remaining_args = ()

            # Check if we have cached context from batch processing
            cached_context = getattr(wrapper_self, '_cached_context', None)

            if cached_context is not None:
                # Use cached context (batch processing mode)
                context = cached_context
                print(f"[ContextAwareDomainAnalyzer] ✓ Using cached context (batch mode)")
            else:
                # Fetch context on demand (fallback for non-batch calls)
                project_id = getattr(wrapper_self, '_current_project_id', None)

                if project_id and wrapper_self.context_engine:
                    # Ensure we're registered
                    await wrapper_self._ensure_registered(project_id)

                    # Get context
                    context = await wrapper_self._get_context(project_id)
                    print(f"[ContextAwareDomainAnalyzer] DEBUG: Retrieved context on-demand")
                else:
                    context = None

            if context:
                # Format and prepend context
                context_section = wrapper_self._format_context_section(context)

                # Inject context into first user message
                if messages and len(messages) > 0:
                    for msg in messages:
                        if msg["role"] == "user":
                            msg["content"] = context_section + "\n\n" + msg["content"]
                            print(f"[ContextAwareDomainAnalyzer] ✓ Injected context into LLM prompt")
                            break

            # Call original LLM with context-injected messages
            if args:
                return await original_chat_completion(messages, *remaining_args, **kwargs)
            else:
                return await original_chat_completion(**kwargs)

        # Bind the wrapper function as a method on the LLM instance
        llm_instance.chat_completion = types.MethodType(context_aware_chat_completion, llm_instance)

    async def analyze_domain(
        self,
        tasks: List[Task],
        root_task: Task,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze domain with automatic context injection

        This calls the wrapped UnifiedDomainAnalyzer.analyze_domain() but with
        automatic context injection from the Context Engine.

        Args:
            tasks: List of tasks to analyze
            root_task: Root task for the analysis
            user_id: User ID for event emission
            project_id: Project ID for context retrieval (defaults to root_task.id)

        Returns:
            Dictionary with events, commands, read_models, user_interactions, automations,
            swimlanes, chapters, wireframes, and validation results
        """
        # Store project_id for LLM wrapper to use
        if project_id is None:
            project_id = root_task.id
        self._current_project_id = project_id

        # OPTIMIZATION: Fetch context ONCE at the start of batch processing
        # This avoids redundant context retrievals for each task
        if self.context_engine and project_id:
            await self._ensure_registered(project_id)
            self._cached_context = await self._get_context(project_id)
            print(f"[ContextAwareDomainAnalyzer] ✓ Fetched context once for batch processing ({len(tasks)} tasks)")
        else:
            self._cached_context = None

        try:
            # Call the wrapped analyzer - all its LLM calls will use cached context
            analysis = await self.domain_analyzer.analyze_domain(tasks, root_task, user_id)

            # Publish analysis results to Context Engine for other agents
            if self.context_engine and project_id:
                await self.publish_data(
                    project_id=project_id,
                    data_key="event_model_analysis",
                    data={
                        "events": [
                            {
                                "name": e.name,
                                "event_type": e.event_type.value,
                                "description": e.description,
                                "actor": e.actor,
                                "affected_entity": e.affected_entity,
                                "triggers": e.triggers
                            }
                            for e in analysis.get("events", [])
                        ],
                        "commands": analysis.get("commands", []),
                        "read_models": analysis.get("read_models", []),
                        "user_interactions": analysis.get("user_interactions", []),
                        "automations": analysis.get("automations", []),
                        "swimlanes": analysis.get("swimlanes", []),
                        "chapters": analysis.get("chapters", [])
                    }
                )
                print(f"[ContextAwareDomainAnalyzer] ✓ Published event model analysis to Context Engine")

            return analysis

        finally:
            # Clean up cached context and project context
            if hasattr(self, '_cached_context'):
                delattr(self, '_cached_context')
            if hasattr(self, '_current_project_id'):
                delattr(self, '_current_project_id')

    async def analyze_domain_from_description(
        self,
        root_task: Task,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze domain from description only (pre-decomposition) with context

        Args:
            root_task: Root task with description
            user_id: User ID for event emission
            project_id: Project ID for context (defaults to root_task.id)

        Returns:
            Dictionary with events, commands, read_models, etc.
        """
        # Store project_id for LLM wrapper
        if project_id is None:
            project_id = root_task.id
        self._current_project_id = project_id

        # OPTIMIZATION: Fetch context once at start
        if self.context_engine and project_id:
            await self._ensure_registered(project_id)
            self._cached_context = await self._get_context(project_id)
            print(f"[ContextAwareDomainAnalyzer] ✓ Fetched context once for pre-decomposition analysis")
        else:
            self._cached_context = None

        try:
            # Call wrapped analyzer with automatic context injection
            analysis = await self.domain_analyzer.analyze_domain_from_description(
                root_task, user_id
            )

            # Publish results
            if self.context_engine and project_id:
                await self.publish_data(
                    project_id=project_id,
                    data_key="event_model_analysis_pre_decomposition",
                    data={
                        "events": [
                            {
                                "name": e.name,
                                "event_type": e.event_type.value,
                                "description": e.description
                            }
                            for e in analysis.get("events", [])
                        ],
                        "commands": analysis.get("commands", []),
                        "read_models": analysis.get("read_models", [])
                    }
                )
                print(f"[ContextAwareDomainAnalyzer] ✓ Published pre-decomposition analysis to Context Engine")

            return analysis

        finally:
            # Clean up cached context and project context
            if hasattr(self, '_cached_context'):
                delattr(self, '_cached_context')
            if hasattr(self, '_current_project_id'):
                delattr(self, '_current_project_id')

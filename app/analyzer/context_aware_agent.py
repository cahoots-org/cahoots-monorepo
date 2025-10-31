"""Base class for context-aware agents

This provides automatic context injection for agents. Agents declare their
semantic needs in natural language, and the Context Engine automatically
provides relevant context via embedding-based matching.

Key Features:
- Context is DECOUPLED from prompts
- Context is AUTOMATICALLY injected before each LLM call
- Context is SEMANTIC - no hardcoded schema mappings
- Context is REAL-TIME - agents get updates as data changes
"""

from typing import List, Dict, Any, Optional
from app.analyzer.llm_client import LLMClient
from app.services.context_engine_client import ContextEngineClient


class ContextAwareAgent:
    """
    Base class for agents that automatically receive context.
    
    Usage:
        class MyAnalyzer(ContextAwareAgent):
            AGENT_ID = "my-analyzer"
            
            DATA_NEEDS = [
                "programming languages and frameworks used",
                "event model with events and commands",
                "completed tasks and patterns"
            ]
            
            def __init__(self, llm_client, context_engine):
                super().__init__(llm_client, context_engine)
            
            async def analyze(self, task, project_id):
                # Context is automatically injected!
                response = await self.llm_call(
                    prompt="Analyze this task...",
                    project_id=project_id
                )
    """
    
    # Subclasses MUST override these
    AGENT_ID: str = None
    DATA_NEEDS: List[str] = []
    
    def __init__(
        self,
        llm_client: LLMClient,
        context_engine: Optional[ContextEngineClient] = None
    ):
        """
        Initialize context-aware agent.
        
        Args:
            llm_client: LLM client for making calls
            context_engine: Context Engine client (optional)
        """
        if not self.AGENT_ID:
            raise ValueError(f"{self.__class__.__name__} must define AGENT_ID")
        
        self.llm = llm_client
        self.context_engine = context_engine
        self._registered_projects: Dict[str, bool] = {}
    
    async def _ensure_registered(self, project_id: str):
        """Ensure agent is registered for this project"""
        if not self.context_engine:
            return
        
        cache_key = f"{self.AGENT_ID}:{project_id}"
        if cache_key in self._registered_projects:
            return
        
        try:
            await self.context_engine.register_agent(
                agent_id=self.AGENT_ID,
                project_id=project_id,
                data_needs=self.DATA_NEEDS,
                last_seen_sequence="0"
            )
            self._registered_projects[cache_key] = True
            
        except Exception as e:
            print(f"[{self.AGENT_ID}] ⚠ Failed to register with Context Engine: {e}")
    
    async def _get_context(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get current context for this agent"""
        if not self.context_engine:
            return None
        
        try:
            return await self.context_engine.get_agent_context(
                agent_id=self.AGENT_ID,
                project_id=project_id
            )
        except Exception as e:
            print(f"[{self.AGENT_ID}] ⚠ Failed to get context: {e}")
            return None
    
    def _format_context_section(self, context: Dict[str, Any]) -> str:
        """Format context as a readable section"""
        if not context:
            return ""
        
        lines = [
            "",
            "=" * 80,
            "CONTEXT (Automatically provided by Context Engine)",
            "=" * 80,
            ""
        ]
        
        # Format each data source
        data_keys = context.get("data_keys", [])
        if data_keys:
            lines.append("Available Data:")
            for key in data_keys:
                lines.append(f"  - {key}")
            lines.append("")
        
        # Add semantic needs that were matched
        needs = context.get("needs", [])
        if needs:
            lines.append("Your Semantic Needs (matched):")
            for need in needs:
                lines.append(f"  - {need}")
            lines.append("")
        
        lines.extend([
            "Note: This context is automatically updated as project data changes.",
            "=" * 80,
            ""
        ])
        
        return "\n".join(lines)
    
    async def llm_call(
        self,
        prompt: str,
        project_id: str,
        max_tokens: int = 32000,
        messages: Optional[List[Dict[str, str]]] = None,
        cached_context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make an LLM call with automatic context injection.

        This method:
        1. Ensures agent is registered with Context Engine
        2. Fetches current context (or uses cached_context if provided)
        3. Injects context into the prompt
        4. Makes the LLM call

        Args:
            prompt: The main prompt (context will be prepended)
            project_id: Project identifier for context lookup
            max_tokens: Maximum tokens for response
            messages: Optional pre-built messages (context will be prepended to first user message)
            cached_context: Optional pre-fetched context to avoid redundant lookups (for batch processing)

        Returns:
            LLM response
        """
        # Ensure registered
        await self._ensure_registered(project_id)

        # Get context (use cached if provided, otherwise fetch)
        if cached_context is not None:
            context = cached_context
        else:
            context = await self._get_context(project_id)
        context_section = self._format_context_section(context) if context else ""
        
        # Build messages
        if messages is None:
            # Simple case: single prompt
            full_prompt = context_section + prompt if context_section else prompt
            messages = [{"role": "user", "content": full_prompt}]
        else:
            # Complex case: inject context into first user message
            if context_section:
                for msg in messages:
                    if msg["role"] == "user":
                        msg["content"] = context_section + msg["content"]
                        break
        
        # Make LLM call
        return await self.llm.chat_completion(
            messages=messages,
            max_tokens=max_tokens
        )
    
    async def publish_data(
        self,
        project_id: str,
        data_key: str,
        data: Dict[str, Any]
    ):
        """
        Publish data to Context Engine.
        
        This makes the data available to all agents with relevant semantic needs.
        
        Args:
            project_id: Project identifier
            data_key: Data identifier (e.g., 'event_model', 'tech_stack')
            data: The data to publish
        """
        if not self.context_engine:
            return
        
        try:
            await self.context_engine.publish_data(
                project_id=project_id,
                data_key=data_key,
                data=data
            )
        except Exception as e:
            print(f"[{self.AGENT_ID}] ⚠ Failed to publish data: {e}")

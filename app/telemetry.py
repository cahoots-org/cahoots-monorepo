"""
Traceloop/OpenLLMetry integration for LLM observability.

This module provides:
- Automatic LLM call tracing via OpenTelemetry
- Workflow and task decorators for pipeline stages
- Token usage and cost tracking
- Integration with external observability platforms (Datadog, Honeycomb, etc.)

Setup:
    Set the following environment variables:
    - TRACELOOP_API_KEY: Your Traceloop API key (optional, for Traceloop cloud)
    - TRACELOOP_BASE_URL: Custom exporter URL (optional)
    - OTEL_EXPORTER_OTLP_ENDPOINT: For self-hosted OpenTelemetry collector
    - CAHOOTS_TELEMETRY_ENABLED: Set to "false" to disable (default: true)

Usage:
    from app.telemetry import init_telemetry, workflow, task, agent

    # Initialize at app startup
    init_telemetry(service_name="cahoots-api")

    # Decorate pipeline stages
    @workflow(name="decomposition")
    async def decompose_project(description: str):
        ...

    @task(name="generate_epics")
    async def generate_epics(context: dict):
        ...

    @agent(name="code_agent")
    async def run_code_agent(task: AgentTask):
        ...
"""

import os
import logging
from typing import Optional, Callable, Any, Dict
from functools import wraps
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)

# Global state
_initialized = False
_traceloop_available = False

# Try to import Traceloop SDK
try:
    from traceloop.sdk import Traceloop
    from traceloop.sdk.decorators import workflow as tl_workflow, task as tl_task, agent as tl_agent
    from traceloop.sdk.tracing import set_association_properties
    _traceloop_available = True
except ImportError:
    logger.warning("Traceloop SDK not installed. LLM telemetry will be disabled.")
    _traceloop_available = False

# Try to import OpenTelemetry for custom spans
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    _otel_available = True
except ImportError:
    _otel_available = False


def init_telemetry(
    service_name: str = "cahoots",
    environment: Optional[str] = None,
    disable_batch: bool = False,
) -> bool:
    """
    Initialize Traceloop/OpenLLMetry telemetry.

    Args:
        service_name: Name of the service for tracing
        environment: Environment name (dev, staging, prod)
        disable_batch: If True, send traces immediately (useful for debugging)

    Returns:
        True if initialization succeeded, False otherwise
    """
    global _initialized

    # Check if telemetry is disabled
    if os.getenv("CAHOOTS_TELEMETRY_ENABLED", "true").lower() == "false":
        logger.info("Telemetry disabled via CAHOOTS_TELEMETRY_ENABLED")
        return False

    if not _traceloop_available:
        logger.warning("Traceloop SDK not available, telemetry disabled")
        return False

    if _initialized:
        logger.debug("Telemetry already initialized")
        return True

    try:
        # Get configuration from environment
        api_key = os.getenv("TRACELOOP_API_KEY")
        base_url = os.getenv("TRACELOOP_BASE_URL")
        env = environment or os.getenv("ENVIRONMENT", "development")

        # Initialize Traceloop
        Traceloop.init(
            app_name=service_name,
            api_key=api_key,
            api_endpoint=base_url,
            disable_batch=disable_batch,
            resource_attributes={
                "service.name": service_name,
                "deployment.environment": env,
                "service.version": os.getenv("APP_VERSION", "dev"),
            },
        )

        _initialized = True
        logger.info(f"Traceloop telemetry initialized for {service_name} ({env})")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Traceloop: {e}")
        return False


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled and initialized."""
    return _initialized and _traceloop_available


# =============================================================================
# DECORATORS
# =============================================================================

def workflow(name: str, version: int = 1):
    """
    Decorator for pipeline workflows (e.g., decomposition, generation).

    Creates a trace span for the entire workflow and captures:
    - Duration
    - Input/output (if serializable)
    - Any LLM calls made within

    Example:
        @workflow(name="project_decomposition")
        async def decompose_project(description: str) -> TaskTree:
            ...
    """
    def decorator(func: Callable) -> Callable:
        if _traceloop_available and _initialized:
            # Use Traceloop's workflow decorator
            return tl_workflow(name=name)(func)

        # Fallback: just run the function
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper

    return decorator


def task(name: str):
    """
    Decorator for individual tasks within a workflow.

    Example:
        @task(name="generate_epics")
        async def generate_epics(context: dict) -> List[Epic]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        if _traceloop_available and _initialized:
            return tl_task(name=name)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper

    return decorator


def agent(name: str):
    """
    Decorator for agent executions (code agent, test agent, etc.).

    Example:
        @agent(name="code_agent")
        async def run_code_agent(task: AgentTask) -> AgentResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        if _traceloop_available and _initialized:
            return tl_agent(name=name)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper

    return decorator


def set_project_context(
    project_id: str,
    user_id: Optional[str] = None,
    tech_stack: Optional[str] = None,
    **extra_properties: Any
) -> None:
    """
    Set association properties for the current trace.

    This allows filtering and grouping traces by project, user, etc.

    Example:
        set_project_context(
            project_id="proj_123",
            user_id="user_456",
            tech_stack="nodejs-api"
        )
    """
    if not _traceloop_available or not _initialized:
        return

    try:
        properties = {
            "project_id": project_id,
        }
        if user_id:
            properties["user_id"] = user_id
        if tech_stack:
            properties["tech_stack"] = tech_stack
        properties.update(extra_properties)

        set_association_properties(properties)
    except Exception as e:
        logger.debug(f"Failed to set association properties: {e}")


# =============================================================================
# LLM INSTRUMENTATION WRAPPER
# =============================================================================

class InstrumentedLLMClient:
    """
    Wrapper that adds telemetry to any LLM client.

    Usage:
        from app.analyzer.llm_client import CerebrasLLMClient
        from app.telemetry import InstrumentedLLMClient

        raw_client = CerebrasLLMClient(api_key="...")
        client = InstrumentedLLMClient(raw_client, model_name="llama3.1-70b")
    """

    def __init__(
        self,
        client: Any,
        model_name: str = "unknown",
        provider: str = "unknown",
    ):
        self._client = client
        self._model_name = model_name
        self._provider = provider

        # Get model from client if available
        if hasattr(client, "model"):
            self._model_name = client.model
        if hasattr(client, "__class__"):
            class_name = client.__class__.__name__
            if "Cerebras" in class_name:
                self._provider = "cerebras"
            elif "OpenAI" in class_name:
                self._provider = "openai"
            elif "Groq" in class_name:
                self._provider = "groq"
            elif "Local" in class_name:
                self._provider = "local"
            elif "Lambda" in class_name:
                self._provider = "lambda"
            elif "Bedrock" in class_name:
                self._provider = "bedrock"
            elif "Featherless" in class_name:
                self._provider = "featherless"

    async def chat_completion(
        self,
        messages: list,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
        **kwargs
    ) -> dict:
        """
        Instrumented chat completion that tracks:
        - Duration
        - Token usage (if available in response)
        - Success/failure status
        """
        from app.metrics import (
            llm_calls_total,
            llm_call_duration_seconds,
            llm_tokens_input_total,
            llm_tokens_output_total,
            llm_retries_total,
        )

        start_time = time.time()
        status = "success"
        operation = kwargs.pop("operation", "chat_completion")

        try:
            result = await self._client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                **kwargs
            )

            # Extract token usage if available
            usage = result.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)

            # Record metrics
            if tokens_in > 0:
                llm_tokens_input_total.labels(
                    operation=operation, model=self._model_name
                ).inc(tokens_in)
            if tokens_out > 0:
                llm_tokens_output_total.labels(
                    operation=operation, model=self._model_name
                ).inc(tokens_out)

            return result

        except Exception as e:
            status = "error"
            # Check for retryable errors
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                llm_retries_total.labels(reason="rate_limit").inc()
            elif "timeout" in error_str:
                llm_retries_total.labels(reason="timeout").inc()
            else:
                llm_retries_total.labels(reason="error").inc()
            raise

        finally:
            duration = time.time() - start_time
            llm_calls_total.labels(
                operation=operation,
                model=self._model_name,
                status=status
            ).inc()
            llm_call_duration_seconds.labels(
                operation=operation,
                model=self._model_name
            ).observe(duration)

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        operation: str = "generate_json"
    ) -> dict:
        """Instrumented JSON generation."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            operation=operation
        )

        content = response["choices"][0]["message"]["content"]
        return self._client._parse_json(content)

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to the underlying client."""
        return getattr(self._client, name)


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@contextmanager
def trace_stage(
    stage_name: str,
    project_id: Optional[str] = None,
    **attributes
):
    """
    Context manager for tracing a pipeline stage.

    Example:
        with trace_stage("event_model_generation", project_id="123"):
            analysis = await analyzer.analyze_domain(tasks)
    """
    if not _otel_available or not _initialized:
        yield
        return

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(stage_name) as span:
        try:
            if project_id:
                span.set_attribute("project.id", project_id)
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


# =============================================================================
# COST ESTIMATION
# =============================================================================

# Pricing per 1M tokens (as of late 2024, update as needed)
MODEL_PRICING = {
    # Cerebras
    "llama3.1-70b": {"input": 0.60, "output": 0.60},
    "llama3.1-8b": {"input": 0.10, "output": 0.10},

    # OpenAI
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},

    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},

    # Default for unknown models
    "default": {"input": 1.00, "output": 2.00},
}


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate the cost of an LLM call in dollars.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in dollars
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def record_llm_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    operation: str = "unknown"
) -> float:
    """
    Record LLM cost to Prometheus metrics.

    Returns the estimated cost.
    """
    from app.metrics import llm_cost_dollars

    cost = estimate_cost(model, input_tokens, output_tokens)
    llm_cost_dollars.labels(operation=operation, model=model).inc(cost)

    return cost


# =============================================================================
# INITIALIZATION HELPER
# =============================================================================

def setup_telemetry_for_fastapi(app) -> None:
    """
    Set up telemetry for a FastAPI application.

    Call this in your app startup:
        from app.telemetry import setup_telemetry_for_fastapi

        app = FastAPI()
        setup_telemetry_for_fastapi(app)
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        # Startup
        init_telemetry(
            service_name="cahoots-api",
            environment=os.getenv("ENVIRONMENT", "development"),
        )
        yield
        # Shutdown (nothing needed)

    # Note: This doesn't modify the app directly since lifespan
    # needs to be set at FastAPI creation time. Instead, call
    # init_telemetry() in your existing lifespan handler.
    init_telemetry(
        service_name="cahoots-api",
        environment=os.getenv("ENVIRONMENT", "development"),
    )

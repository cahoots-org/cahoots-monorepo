"""Dependency injection for FastAPI."""

import os
from typing import Optional
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.storage import RedisClient, TaskStorage
from app.analyzer import UnifiedAnalyzer, LLMClient, MockLLMClient
from app.analyzer.llm_client import OpenAILLMClient, GroqLLMClient, LambdaLLMClient, CerebrasLLMClient, LocalLLMClient
from app.analyzer.agentic_analyzer import AgenticAnalyzer
from app.analyzer.story_driven_analyzer import StoryDrivenAnalyzer
from app.processor import TaskProcessor
from app.processor.processing_rules import ProcessingConfig
from app.services.context_engine_client import ContextEngineClient, initialize_context_engine


security = HTTPBearer(auto_error=False)


# Global instances (initialized once)
_redis_client: Optional[RedisClient] = None
_task_storage: Optional[TaskStorage] = None
_llm_client: Optional[LLMClient] = None
_analyzer: Optional[UnifiedAnalyzer] = None
_task_processor: Optional[TaskProcessor] = None
_context_engine_client: Optional[ContextEngineClient] = None


async def get_redis_client() -> RedisClient:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        # Try to use REDIS_URL first (for Fly.io)
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            # Parse the Redis URL
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            _redis_client = RedisClient(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=int(parsed.path.lstrip('/') or 0) if parsed.path and parsed.path != '/' else 0,
                password=parsed.password
            )
        else:
            # Fall back to individual settings
            _redis_client = RedisClient(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                password=os.getenv("REDIS_PASSWORD")
            )
        await _redis_client.connect()
    return _redis_client


async def get_task_storage() -> TaskStorage:
    """Get task storage instance."""
    global _task_storage
    if _task_storage is None:
        redis_client = await get_redis_client()
        _task_storage = TaskStorage(redis_client)
    return _task_storage


async def get_llm_client() -> LLMClient:
    """Get LLM client instance based on configuration."""
    global _llm_client
    if _llm_client is None:
        provider = os.getenv("LLM_PROVIDER", "mock").lower()

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            _llm_client = OpenAILLMClient(
                api_key=api_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4")
            )
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            _llm_client = GroqLLMClient(
                api_key=api_key,
                model=os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
            )
        elif provider == "lambda":
            api_key = os.getenv("LAMBDA_API_KEY")
            if not api_key:
                raise ValueError("LAMBDA_API_KEY not set")
            _llm_client = LambdaLLMClient(
                api_key=api_key,
                model=os.getenv("LAMBDA_MODEL", "hermes-3-llama-3.1-405b-fp8")
            )
        elif provider == "cerebras":
            api_key = os.getenv("CEREBRAS_API_KEY")
            if not api_key:
                raise ValueError("CEREBRAS_API_KEY not set")
            model = os.getenv("CEREBRAS_MODEL", "llama3.1-70b")
            print(f"DEBUG: Using Cerebras model: {model} (env var: {os.getenv('CEREBRAS_MODEL')})")
            _llm_client = CerebrasLLMClient(
                api_key=api_key,
                model=model
            )
        elif provider == "local":
            base_url = os.getenv("LOCAL_LLM_URL", "http://localhost:8001/v1")
            model = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
            print(f"DEBUG: Using Local LLM: {model} at {base_url}")
            _llm_client = LocalLLMClient(
                base_url=base_url,
                model=model
            )
        else:  # mock or any other value
            _llm_client = MockLLMClient()

    return _llm_client


async def get_analyzer() -> UnifiedAnalyzer:
    """Get unified analyzer instance."""
    global _analyzer
    if _analyzer is None:
        llm_client = await get_llm_client()
        _analyzer = UnifiedAnalyzer(llm_client)
    return _analyzer


async def get_task_processor() -> TaskProcessor:
    """Get task processor instance."""
    global _task_processor
    if _task_processor is None:
        storage = await get_task_storage()
        analyzer = await get_analyzer()

        # Create agentic analyzer for root tasks
        llm_client = await get_llm_client()
        agentic_analyzer = AgenticAnalyzer(llm_client)

        # Create Story-driven analyzer
        story_driven_analyzer = StoryDrivenAnalyzer(llm_client)

        # Create Epic/Story processor if we have an LLM client
        epic_story_processor = None
        if not isinstance(llm_client, MockLLMClient):
            from app.analyzer import EpicAnalyzer, StoryAnalyzer, CoverageValidator
            from app.processor import EpicStoryProcessor

            epic_story_processor = EpicStoryProcessor(
                storage=storage,
                epic_analyzer=EpicAnalyzer(llm_client),
                story_analyzer=StoryAnalyzer(llm_client),
                coverage_validator=CoverageValidator()
            )

        # Create processing config from environment
        config = ProcessingConfig(
            max_depth=int(os.getenv("MAX_DEPTH", "5")),
            complexity_threshold=float(os.getenv("COMPLEXITY_THRESHOLD", "0.45")),
            batch_sibling_threshold=int(os.getenv("BATCH_SIZE", "3"))
        )

        # Get Context Engine client for event publishing
        context_engine_client = await get_context_engine_client()

        _task_processor = TaskProcessor(
            storage, analyzer, config, agentic_analyzer, epic_story_processor, story_driven_analyzer, context_engine_client
        )
    return _task_processor


async def get_context_engine_client() -> Optional[ContextEngineClient]:
    """Get Context Engine client instance."""
    global _context_engine_client
    if _context_engine_client is None:
        # Create async Redis client for pub/sub subscriptions
        from redis.asyncio import Redis
        redis_url = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
        async_redis = Redis.from_url(redis_url, decode_responses=True)

        # Initialize HTTP-based Context Engine client
        _context_engine_client = await initialize_context_engine(redis_client=async_redis)
        print("[Dependencies] ✓ Context Engine client initialized")
    return _context_engine_client


async def cleanup_dependencies():
    """Clean up all dependencies on shutdown."""
    global _redis_client, _task_storage, _llm_client, _analyzer, _cache_manager, _task_processor

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if hasattr(_llm_client, 'close'):
        await _llm_client.close()

    _task_storage = None
    _llm_client = None
    _analyzer = None
    _cache_manager = None
    _task_processor = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: RedisClient = Depends(get_redis_client)
) -> dict:
    """Get current authenticated user from JWT token."""
    print(f"[AUTH DEBUG] Credentials: {credentials}")
    if not credentials:
        print("[AUTH DEBUG] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required"
        )

    token = credentials.credentials
    print(f"[AUTH DEBUG] Token: {token[:20]}...")

    # Check for development bypass token
    if token == "dev-bypass-token" and os.getenv("ENVIRONMENT", "development") == "development":
        print("[AUTH DEBUG] Using dev bypass token")
        return {
            "id": "dev-user-123",
            "email": "dev@localhost"
        }

    try:
        # Import here to avoid circular dependency
        from app.api.routes.auth import OAuthConfig

        payload = jwt.decode(token, OAuthConfig.get_jwt_secret(), algorithms=["HS256"])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # For integrations, we just need a basic user object
        return {
            "id": user_id,
            "email": payload.get("email")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
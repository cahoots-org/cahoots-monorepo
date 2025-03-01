"""Hybrid provider implementation combining multiple AI providers for cost optimization."""
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Union
import logging
import json
from datetime import datetime, timedelta

from mistralai.client import MistralClient
from mistralai.async_client import MistralAsyncClient
from anthropic import AsyncAnthropic
import aioredis
from prometheus_client import Counter, Histogram

from .base import AIProvider

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    'ai_requests_total',
    'Total AI requests',
    ['provider', 'model', 'task_type']
)
TOKENS_TOTAL = Counter(
    'ai_tokens_total',
    'Total tokens processed',
    ['provider', 'model', 'direction']  # direction: input/output
)
REQUEST_DURATION = Histogram(
    'ai_request_duration_seconds',
    'AI request duration in seconds',
    ['provider', 'model']
)
ERROR_TOTAL = Counter(
    'ai_errors_total',
    'Total AI errors',
    ['provider', 'model', 'error_type']
)

class ResponseCache:
    """Cache for AI responses."""
    
    def __init__(self, redis_url: str, ttl: int = 3600):
        """Initialize cache.
        
        Args:
            redis_url: Redis connection URL
            ttl: Cache TTL in seconds
        """
        self.redis = aioredis.from_url(redis_url)
        self.ttl = ttl
        
    async def get(self, key: str) -> Optional[str]:
        """Get cached response."""
        return await self.redis.get(f"ai_cache:{key}")
        
    async def set(self, key: str, value: str):
        """Cache response."""
        await self.redis.set(f"ai_cache:{key}", value, ex=self.ttl)
        
    def get_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key."""
        # Only cache deterministic responses
        if temperature > 0:
            return None
        return f"{model}:{hash(prompt)}"

class HybridProvider(AIProvider):
    """Hybrid implementation combining multiple AI providers for cost optimization."""
    
    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        mistral_api_key: Optional[str] = None,
        default_model: str = "mistral-large-latest",
        task_routing: Optional[Dict[str, str]] = None,
        redis_url: Optional[str] = None
    ):
        """Initialize hybrid provider.
        
        Args:
            anthropic_api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            mistral_api_key: Mistral API key (defaults to MISTRAL_API_KEY env var)
            default_model: Default model to use
            task_routing: Optional mapping of task types to specific models
            redis_url: Optional Redis URL for caching
        """
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        if not self.mistral_api_key:
            raise ValueError("Mistral API key is required")
            
        self.default_model = default_model
        self.task_routing = task_routing or {
            "complex_reasoning": "claude-instant-1.2",
            "code": "mistral-large-latest",
            "embeddings": "mistral-embed",
            "default": "mistral-medium"
        }
        
        # Initialize clients
        self.mistral_client = MistralAsyncClient(api_key=self.mistral_api_key)
        
        if self.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None
            logger.warning("Anthropic API key not provided. Complex reasoning tasks will fall back to Mistral.")
            
        # Initialize cache
        self.cache = ResponseCache(self.redis_url)
        
    def _get_model_for_task(self, task_type: str = "default") -> str:
        """Get the appropriate model for the given task type."""
        model = self.task_routing.get(task_type, self.task_routing["default"])
        
        # Fall back to Mistral if Anthropic isn't configured but task needs it
        if "claude" in model and not self.anthropic_client:
            logger.info(f"Falling back to Mistral for task type {task_type}")
            return self.default_model
            
        return model
        
    def _is_anthropic_model(self, model: str) -> bool:
        """Check if the model is an Anthropic model."""
        return "claude" in model.lower()
        
    async def generate_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        task_type: str = "default",
        **kwargs: Any
    ) -> str:
        """Generate a response using the appropriate provider.
        
        Args:
            prompt: The input prompt
            model: Optional specific model to use
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
            task_type: Type of task (default, code, complex_reasoning, etc.)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Generated response
        """
        model = model or self._get_model_for_task(task_type)
        
        # Check cache for deterministic queries
        cache_key = self.cache.get_cache_key(prompt, model, temperature)
        if cache_key:
            if cached := await self.cache.get(cache_key):
                logger.info(f"Cache hit for model {model}")
                return cached
                
        start_time = datetime.now()
        provider = "anthropic" if self._is_anthropic_model(model) else "mistral"
        
        try:
            if self._is_anthropic_model(model):
                if not self.anthropic_client:
                    raise ValueError("Anthropic client not configured")
                    
                response = await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens or 4096,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                    stop_sequences=stop if isinstance(stop, list) else [stop] if stop else None
                )
                result = response.content[0].text
                
            else:  # Mistral model
                response = await self.mistral_client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    **kwargs
                )
                result = response.choices[0].message.content
                
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            REQUESTS_TOTAL.labels(provider=provider, model=model, task_type=task_type).inc()
            REQUEST_DURATION.labels(provider=provider, model=model).observe(duration)
            
            # Approximate token counting
            input_tokens = self.get_token_count(prompt)
            output_tokens = self.get_token_count(result)
            TOKENS_TOTAL.labels(provider=provider, model=model, direction="input").inc(input_tokens)
            TOKENS_TOTAL.labels(provider=provider, model=model, direction="output").inc(output_tokens)
            
            # Cache result if appropriate
            if cache_key:
                await self.cache.set(cache_key, result)
                
            return result
                
        except Exception as e:
            logger.error(f"Error generating response with {model}: {str(e)}")
            ERROR_TOTAL.labels(provider=provider, model=model, error_type=type(e).__name__).inc()
            
            # Fall back to default model if primary fails
            if model != self.default_model:
                logger.info(f"Falling back to default model {self.default_model}")
                return await self.generate_response(
                    prompt,
                    model=self.default_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    task_type=task_type,  # Preserve task type in fallback
                    **kwargs
                )
            raise
            
    async def generate_embeddings(
        self,
        texts: List[str],
        *,
        model: Optional[str] = "mistral-embed",
        **kwargs: Any
    ) -> List[List[float]]:
        """Generate embeddings using Mistral's embedding model."""
        start_time = datetime.now()
        
        try:
            embeddings = []
            for text in texts:
                response = await self.mistral_client.embeddings(
                    model=model,
                    input=text
                )
                embeddings.append(response.data[0].embedding)
                
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            REQUESTS_TOTAL.labels(provider="mistral", model=model, task_type="embeddings").inc()
            REQUEST_DURATION.labels(provider="mistral", model=model).observe(duration)
            
            total_tokens = sum(self.get_token_count(text) for text in texts)
            TOKENS_TOTAL.labels(provider="mistral", model=model, direction="input").inc(total_tokens)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            ERROR_TOTAL.labels(provider="mistral", model=model, error_type=type(e).__name__).inc()
            raise
            
    async def stream_response(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        task_type: str = "default",
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream a response using the appropriate provider."""
        model = model or self._get_model_for_task(task_type)
        start_time = datetime.now()
        provider = "anthropic" if self._is_anthropic_model(model) else "mistral"
        
        try:
            if self._is_anthropic_model(model):
                if not self.anthropic_client:
                    raise ValueError("Anthropic client not configured")
                    
                stream = await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens or 4096,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                    stop_sequences=stop if isinstance(stop, list) else [stop] if stop else None,
                    stream=True
                )
                
                response_text = ""
                async for chunk in stream:
                    if chunk.content:
                        response_text += chunk.content[0].text
                        yield chunk.content[0].text
                        
            else:  # Mistral model
                stream = await self.mistral_client.chat_stream(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    **kwargs
                )
                
                response_text = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        response_text += text
                        yield text
                        
            # Update metrics after streaming completes
            duration = (datetime.now() - start_time).total_seconds()
            REQUESTS_TOTAL.labels(provider=provider, model=model, task_type=task_type).inc()
            REQUEST_DURATION.labels(provider=provider, model=model).observe(duration)
            
            input_tokens = self.get_token_count(prompt)
            output_tokens = self.get_token_count(response_text)
            TOKENS_TOTAL.labels(provider=provider, model=model, direction="input").inc(input_tokens)
            TOKENS_TOTAL.labels(provider=provider, model=model, direction="output").inc(output_tokens)
                        
        except Exception as e:
            logger.error(f"Error streaming response with {model}: {str(e)}")
            ERROR_TOTAL.labels(provider=provider, model=model, error_type=type(e).__name__).inc()
            
            # Fall back to default model if primary fails
            if model != self.default_model:
                logger.info(f"Falling back to default model {self.default_model}")
                async for chunk in self.stream_response(
                    prompt,
                    model=self.default_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    task_type=task_type,  # Preserve task type in fallback
                    **kwargs
                ):
                    yield chunk
            else:
                raise
                
    def get_token_count(self, text: str) -> int:
        """Get approximate token count.
        
        Note: This is a rough approximation. For precise counts,
        you should use model-specific tokenizers.
        """
        # Rough approximation: 4 characters per token
        return len(text) // 4 
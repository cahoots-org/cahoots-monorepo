"""LLM client abstraction for the analyzer."""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.metrics import llm_calls_total, llm_call_duration_seconds, llm_tokens_input_total, llm_tokens_output_total


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    # Override in subclass to specify model name for metrics
    model_name: str = "unknown"

    def _record_llm_metrics(
        self,
        operation: str,
        duration: float,
        status: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ):
        """Record LLM call metrics."""
        llm_calls_total.labels(operation=operation, model=self.model_name, status=status).inc()
        llm_call_duration_seconds.labels(operation=operation, model=self.model_name).observe(duration)
        if tokens_in > 0:
            llm_tokens_input_total.labels(operation=operation, model=self.model_name).inc(tokens_in)
        if tokens_out > 0:
            llm_tokens_output_total.labels(operation=operation, model=self.model_name).inc(tokens_out)

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Generate a chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Response dictionary with 'choices' containing the completion
        """
        pass

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        operation: str = "generate_json"
    ) -> Dict[str, Any]:
        """Generate a JSON response from the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            operation: Operation name for metrics

        Returns:
            Parsed JSON response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        start_time = time.time()
        status = "success"
        try:
            response = await self.chat_completion(
                messages,
                temperature,
                max_tokens,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            status = "error"
            self._record_llm_metrics(operation, time.time() - start_time, status)
            raise

        duration = time.time() - start_time

        # Extract token usage if available
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        self._record_llm_metrics(operation, duration, status, tokens_in, tokens_out)

        content = response["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response text.

        Args:
            text: Response text that should contain JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json.loads(json_match.group(1).strip())

        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group(0))

        # Try to find JSON array
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            return json.loads(json_match.group(0))

        raise json.JSONDecodeError(f"No valid JSON found in response", text, 0)


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        """Initialize mock client with predefined responses.

        Args:
            responses: List of response dictionaries to return in order
        """
        self.responses = responses or []
        self.call_count = 0
        self.call_history = []

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Return a mock response."""
        self.call_history.append({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format
        })

        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response

        # Default mock response
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "complexity_score": 0.5,
                        "is_atomic": False,
                        "is_specific": True,
                        "confidence": 0.85,
                        "reasoning": "Mock analysis",
                        "suggested_approach": "decompose",
                        "implementation_hints": None,
                        "estimated_story_points": 5,
                        "requires_human_review": False,
                        "similar_patterns": [],
                        "missing_details": [],
                        "dependencies": [],
                        "risk_factors": []
                    })
                }
            }]
        }


class OpenAILLMClient(LLMClient):
    """OpenAI API client implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4", base_url: Optional[str] = None):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
            base_url: Optional custom API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call OpenAI API for chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format:
            payload["response_format"] = response_format

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class GroqLLMClient(LLMClient):
    """Groq API client implementation."""

    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        """Initialize Groq client.

        Args:
            api_key: Groq API key
            model: Model to use (default: mixtral-8x7b-32768)
        """
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call Groq API for chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format:
            payload["response_format"] = response_format

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class LambdaLLMClient(LLMClient):
    """Lambda Labs API client implementation."""

    def __init__(self, api_key: str, model: str = "hermes-3-llama-3.1-405b-fp8"):
        """Initialize Lambda client.

        Args:
            api_key: Lambda API key
            model: Model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(
            base_url="https://api.lambdalabs.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call Lambda API for chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class BedrockLLMClient(LLMClient):
    """AWS Bedrock API client implementation using bearer token auth."""

    def __init__(self, api_key: str, model: str, region: str = "us-east-1"):
        """Initialize Bedrock client.

        Args:
            api_key: AWS Bedrock bearer token
            model: Model ID (e.g., qwen.qwen3-235b-a22b-2507-v1:0)
            region: AWS region (default: us-east-1)
        """
        self.api_key = api_key
        self.model = model
        self.region = region
        self.base_url = f"https://bedrock-runtime.{region}.amazonaws.com"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )

    @property
    def model_name(self) -> str:
        """Get model name for metrics."""
        return f"bedrock:{self.model}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call Bedrock Converse API for chat completion."""
        # Convert OpenAI message format to Bedrock format
        bedrock_messages = []
        system_prompts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                # Bedrock handles system prompts separately
                system_prompts.append({"text": content})
            else:
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": content}]
                })

        payload = {
            "messages": bedrock_messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "performanceConfig": {
                "latency": "optimized"
            }
        }

        # Add system prompts if any
        if system_prompts:
            payload["system"] = system_prompts

        # URL-encode the model ID (contains colon which must be encoded)
        from urllib.parse import quote
        encoded_model = quote(self.model, safe='')
        url = f"{self.base_url}/model/{encoded_model}/converse"
        response = await self.client.post(url, json=payload)

        if response.status_code != 200:
            print(f"[Bedrock] API Error: {response.status_code} - {response.text[:500]}")

        response.raise_for_status()
        result = response.json()

        # Convert Bedrock response to OpenAI format for compatibility
        output = result.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        # Extract text from content blocks (skip reasoningContent blocks)
        text_content = ""
        for block in content_blocks:
            if "text" in block:
                text_content += block["text"]
            # Skip reasoningContent blocks - they contain internal reasoning

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": text_content
                }
            }]
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class FeatherlessLLMClient(LLMClient):
    """Featherless AI API client implementation (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"):
        """Initialize Featherless client.

        Args:
            api_key: Featherless API key
            model: Model to use (default: meta-llama/Meta-Llama-3.1-8B-Instruct)
        """
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(
            base_url="https://api.featherless.ai/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0  # Longer timeout for larger models
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call Featherless API for chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Featherless supports JSON mode via response_format
        if response_format:
            payload["response_format"] = response_format

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class CerebrasLLMClient(LLMClient):
    """Cerebras API client implementation with model rotation for rate limits."""

    def __init__(self, api_key: str, model: str = "llama3.1-70b"):
        """Initialize Cerebras client.

        Args:
            api_key: Cerebras API key
            model: Model or comma-separated list of models for rotation
                   (e.g., "gpt-oss-120b,llama3.1-70b,llama3.1-8b")
        """
        self.api_key = api_key
        # Parse comma-separated models into a list
        self.models = [m.strip() for m in model.split(",")]
        self.current_model_index = 0
        self.client = httpx.AsyncClient(
            base_url="https://api.cerebras.ai/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
        # Rate limit retry configuration
        self.max_rate_limit_retries = 5
        self.rate_limit_backoff_seconds = 10

    @property
    def model(self) -> str:
        """Get the current model."""
        return self.models[self.current_model_index]

    @property
    def model_name(self) -> str:
        """Get model name for metrics."""
        return f"cerebras:{self.model}"

    def _rotate_model(self) -> bool:
        """Rotate to the next model. Returns True if rotated, False if exhausted."""
        if self.current_model_index < len(self.models) - 1:
            self.current_model_index += 1
            print(f"[Cerebras] Rotating to model: {self.model}")
            return True
        return False

    def _reset_model_index(self):
        """Reset to the first model."""
        self.current_model_index = 0

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call Cerebras API for chat completion with automatic model rotation on 429 or invalid model.

        When all models are rate limited, waits with exponential backoff and retries.
        """
        import asyncio

        last_error = None

        for retry_attempt in range(self.max_rate_limit_retries):
            # Reset to first model at the start of each retry cycle
            self._reset_model_index()

            while True:
                try:
                    return await self._make_request(messages, temperature, max_tokens, response_format, tools)
                except httpx.HTTPStatusError as e:
                    last_error = e
                    # 429 = rate limited, 400/404 = possibly invalid model
                    if e.response.status_code in (429, 400, 404):
                        print(f"[Cerebras] Error {e.response.status_code} on {self.model}, rotating...")
                        if not self._rotate_model():
                            # All models exhausted - wait and retry
                            break
                        continue
                    else:
                        raise

            # All models exhausted in this cycle - wait with backoff
            backoff = self.rate_limit_backoff_seconds * (2 ** retry_attempt)
            print(f"[Cerebras] All models rate limited. Waiting {backoff}s before retry {retry_attempt + 1}/{self.max_rate_limit_retries}...")
            await asyncio.sleep(backoff)

        # All retries exhausted
        print(f"[Cerebras] All retries exhausted after {self.max_rate_limit_retries} attempts")
        raise last_error

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Make a single request to Cerebras API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Cerebras supports JSON mode
        if response_format and response_format.get("type") == "json_object":
            payload["response_format"] = response_format

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        response = await self.client.post("/chat/completions", json=payload)

        # Log error details if request fails
        if response.status_code != 200:
            print(f"[Cerebras] API Error: Status {response.status_code} on model {self.model}")
            if response.status_code != 429:
                print(f"[Cerebras] Response: {response.text[:500]}")

        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class LocalLLMClient(LLMClient):
    """Local LLM via vLLM OpenAI-compatible API."""

    def __init__(self, base_url: str, model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
        """Initialize Local LLM client.

        Args:
            base_url: Base URL for vLLM server (e.g., http://vllm:8000/v1)
            model: Model name (default: Qwen/Qwen3-32B-Instruct)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=600.0  # 10 minutes for local inference
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call Ollama native API for chat completion."""
        # Ollama's native API uses different format than OpenAI
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }

        # Add tools if provided (for tool calling support)
        if tools:
            payload["tools"] = tools

        # Note: We don't use Ollama's "format": "json" parameter
        # Some models (e.g., DeepSeek-R1) return empty responses with this constraint
        # Instead, we rely on prompt engineering to request JSON output
        # The _parse_json() method handles extraction from various response formats

        # Use Ollama's native /api/chat endpoint
        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        result = response.json()

        # Get message and check for tool calls
        message = result["message"]
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")

        if response_format and response_format.get("type") == "json_object":
            # Remove <think>...</think> tags that Qwen3 adds
            import re
            original_content = content
            content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
            content = content.strip()

            # If stripping think tags left us with nothing, log the issue
            if not content or not content.strip():
                print(f"[LocalLLM] WARNING: Model returned ONLY thinking tags, no JSON content")
                print(f"[LocalLLM] Original response (first 1000 chars): {original_content[:1000]}")
                # Raise error so caller knows the LLM failed to produce JSON
                raise ValueError(f"LLM returned only thinking tags with no JSON content")

            # Log what we're about to parse
            print(f"[LocalLLM] Content after stripping think tags (first 200 chars): {content[:200]}")

        # Convert Ollama response format to OpenAI format for compatibility
        response_msg = {
            "content": content,
            "role": "assistant"
        }

        # Include tool calls if present
        if tool_calls:
            response_msg["tool_calls"] = tool_calls

        return {
            "choices": [{
                "message": response_msg
            }],
            "tool_calls": tool_calls  # Also at top level for easy access
        }

    async def chat_completion_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_executor: Any,  # Function to execute tools: tool_executor(tool_name, args) -> dict
        temperature: float = 0.0,
        max_tokens: int = 2048,
        max_rounds: int = 5,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with tool support, implementing agentic loop.

        This method:
        1. Calls LLM with tools available
        2. If LLM makes tool calls, executes them
        3. Feeds tool results back to LLM
        4. Repeats until LLM returns final answer (no more tool calls)

        Args:
            messages: Initial conversation messages
            tools: List of tool definitions in Ollama format
            tool_executor: Callable that executes tool calls
            temperature: LLM temperature
            max_tokens: Max tokens in response
            max_rounds: Maximum number of LLM calls (prevents infinite loops)
            response_format: Optional response format specification

        Returns:
            Final LLM response with all tool interactions complete
        """
        import json

        conversation = list(messages)  # Copy messages

        for round_num in range(max_rounds):
            print(f"[LocalLLM Tool Loop] Round {round_num + 1}/{max_rounds}")

            # Call LLM with tools
            response = await self.chat_completion(
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                tools=tools
            )

            # Extract message and tool calls
            message = response["choices"][0]["message"]
            content = message.get("content", "")
            tool_calls = response.get("tool_calls") or message.get("tool_calls")

            # Add assistant message to conversation
            conversation.append({
                "role": "assistant",
                "content": content
            })

            # If no tool calls, we're done
            if not tool_calls:
                print(f"[LocalLLM Tool Loop] Complete - no tool calls")
                return response

            # Execute tool calls
            print(f"[LocalLLM Tool Loop] Executing {len(tool_calls)} tool call(s)")
            for i, tool_call in enumerate(tool_calls):
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"]["arguments"]

                print(f"[LocalLLM Tool Loop]   Tool {i+1}: {func_name}({list(func_args.keys())})")

                # Execute the tool
                try:
                    tool_result = tool_executor(func_name, func_args)
                    result_str = json.dumps(tool_result)
                except Exception as e:
                    tool_result = {"error": f"Tool execution failed: {str(e)}"}
                    result_str = json.dumps(tool_result)
                    print(f"[LocalLLM Tool Loop]   Error: {e}")

                # Add tool result to conversation
                conversation.append({
                    "role": "tool",
                    "content": result_str
                })

        print(f"[LocalLLM Tool Loop] Max rounds ({max_rounds}) reached")
        # Return last response even if max rounds reached
        return response

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
"""LLM client abstraction for the analyzer."""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

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
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Generate a JSON response from the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Parsed JSON response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.chat_completion(
            messages,
            temperature,
            max_tokens,
            response_format={"type": "json_object"}
        )

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


class CerebrasLLMClient(LLMClient):
    """Cerebras API client implementation."""

    def __init__(self, api_key: str, model: str = "llama3.1-70b"):
        """Initialize Cerebras client.

        Args:
            api_key: Cerebras API key
            model: Model to use (default: llama3.1-70b)
        """
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(
            base_url="https://api.cerebras.ai/v1",
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
        """Call Cerebras API for chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Cerebras supports JSON mode
        if response_format and response_format.get("type") == "json_object":
            payload["response_format"] = response_format

        # Debug: Print the user message being sent
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        print(f"DEBUG CEREBRAS REQUEST: {user_msg[:200]}...")

        response = await self.client.post("/chat/completions", json=payload)

        # Log error details if request fails
        if response.status_code != 200:
            print(f"CEREBRAS API ERROR: Status {response.status_code}")
            print(f"Response: {response.text[:500]}")

        response.raise_for_status()
        result = response.json()

        # Debug: Print what we got back
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"DEBUG CEREBRAS RESPONSE: {content[:200]}...")

        return result

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
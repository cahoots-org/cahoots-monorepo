"""Client for Context Engine service using official SDK

This client communicates with the standalone Context Engine service.
The Context Engine uses embedding-based semantic matching to automatically provide
relevant context to agents based on their semantic needs.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from redis.asyncio import Redis

try:
    from contex import ContexAsyncClient
    CONTEX_SDK_AVAILABLE = True
except ImportError:
    CONTEX_SDK_AVAILABLE = False
    ContexAsyncClient = None


class ContextEngineClient:
    """
    Client for Context Engine using the official contex-python SDK.

    Features:
    - Agent registration with semantic needs (natural language)
    - Data publishing (any schema)
    - Automatic semantic matching via embeddings
    - Real-time updates via Redis pub/sub
    - Agent catch-up for missed events
    """

    def __init__(self, base_url: str = None, redis_client: Redis = None, api_key: str = None):
        """
        Initialize Context Engine client.

        Args:
            base_url: Context Engine API URL (default: http://context-engine:8001)
            redis_client: Redis client for pub/sub subscriptions (optional)
            api_key: API key for Context Engine (optional)
        """
        self.base_url = base_url or os.getenv("CONTEXT_ENGINE_URL", "http://context-engine:8001")
        self.api_key = api_key or os.getenv("CONTEXT_ENGINE_API_KEY", "")
        self.redis = redis_client
        self.registered_agents: Dict[str, str] = {}  # agent_id -> notification_channel
        self._client: Optional[ContexAsyncClient] = None
        self._is_available = False

    async def _get_client(self) -> Optional[ContexAsyncClient]:
        """Get or create the SDK client"""
        if not CONTEX_SDK_AVAILABLE:
            print("[ContextEngine] ⚠ contex-python SDK not installed")
            return None

        if self._client is None:
            self._client = ContexAsyncClient(
                url=self.base_url,
                api_key=self.api_key if self.api_key else None
            )
        return self._client

    async def close(self):
        """Close the client"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def health_check(self) -> bool:
        """Check if Context Engine is available and functional"""
        import httpx

        try:
            # Use the simple /health endpoint which just checks if service is running
            # The /api/v1/health is too strict about optional components like RediSearch
            url = f"{self.base_url}/health"
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(url)
                response.raise_for_status()
                data = response.json()

            is_healthy = data.get('status') == 'healthy'
            self._is_available = is_healthy
            return is_healthy
        except Exception as e:
            print(f"[ContextEngine] Health check failed: {e}")
            self._is_available = False
            return False

    async def publish_data(
        self,
        project_id: str,
        data_key: str,
        data: Dict[str, Any],
        event_type: Optional[str] = None
    ) -> str:
        """
        Publish data to Context Engine.

        The Context Engine will:
        1. Auto-generate a description of the data
        2. Create embeddings for semantic matching
        3. Store in event log with sequence number
        4. Notify subscribed agents via pub/sub

        Args:
            project_id: Project identifier
            data_key: Data identifier (e.g., 'tech_stack', 'event_model')
            data: The actual data (any schema)
            event_type: Optional event type (auto-generated if not provided)

        Returns:
            Event sequence number
        """
        client = await self._get_client()
        if not client:
            raise RuntimeError("Context Engine SDK not available")

        try:
            response = await client.publish(
                project_id=project_id,
                data_key=data_key,
                data=data
            )

            sequence = getattr(response, 'sequence', '0')
            print(f"[ContextEngine] ✓ Published {data_key} for project {project_id} (seq: {sequence})")
            return str(sequence)

        except Exception as e:
            print(f"[ContextEngine] ✗ Failed to publish data: {e}")
            raise

    async def register_agent(
        self,
        agent_id: str,
        project_id: str,
        data_needs: List[str],
        last_seen_sequence: str = "0",
        notification_channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register an agent with semantic data needs.

        The Context Engine will:
        1. Match agent needs to available data via semantic similarity
        2. Send initial context for all matches
        3. Catch up agent with missed events
        4. Subscribe agent to real-time updates

        Args:
            agent_id: Unique agent identifier
            project_id: Project this agent works on
            data_needs: List of semantic needs (natural language)
                Examples:
                - "programming languages and frameworks used"
                - "event model with events and commands"
                - "completed tasks and patterns"
            last_seen_sequence: Last event sequence processed (for catch-up)
            notification_channel: Redis channel for updates (optional)

        Returns:
            Registration response with matched data and catch-up info
        """
        import httpx

        # Use direct HTTP to avoid SDK response parsing issues
        try:
            url = f"{self.base_url}/api/v1/agents/register"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            payload = {
                "agent_id": agent_id,
                "project_id": project_id,
                "data_needs": data_needs
            }

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Extract response data
            notification_ch = data.get('notification_channel', f"agent:{agent_id}")
            caught_up = data.get('caught_up_events', 0)
            matched_needs = data.get('matched_needs', {})
            matched_data = data.get('matched_data', [])

            # Calculate total matches
            if matched_needs and isinstance(matched_needs, dict):
                matched_count = sum(matched_needs.values())
            else:
                matched_count = len(matched_data) if matched_data else 0

            # Store registration
            self.registered_agents[agent_id] = notification_ch

            print(f"[ContextEngine] ✓ Registered agent {agent_id}")
            print(f"[ContextEngine]   Matched needs: {matched_count}")
            print(f"[ContextEngine]   Caught up events: {caught_up}")

            return {
                "matched_data": matched_data,
                "matched_needs": matched_needs,
                "notification_channel": notification_ch,
                "total_matches": matched_count,
                "caught_up_events": caught_up
            }

        except httpx.HTTPStatusError as e:
            print(f"[ContextEngine] ✗ Failed to register agent: HTTP {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            print(f"[ContextEngine] ✗ Failed to register agent: {type(e).__name__}: {e}")
            raise

    async def query(
        self,
        project_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query for data using semantic search.

        Args:
            project_id: Project identifier
            query: Natural language query
            limit: Maximum number of results

        Returns:
            List of matching data items
        """
        import httpx

        # Use direct HTTP with correct endpoint path
        try:
            url = f"{self.base_url}/api/v1/projects/{project_id}/query"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            payload = {
                "query": query,
                "limit": limit
            }

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            results = data.get('results', [])
            return [
                {
                    "data_key": r.get('data_key', ''),
                    "data": r.get('data', {}),
                    "similarity_score": r.get('similarity_score', 0.0)
                }
                for r in results[:limit]
            ]

        except httpx.HTTPStatusError as e:
            print(f"[ContextEngine] ✗ Query failed: HTTP {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            print(f"[ContextEngine] ✗ Query failed: {type(e).__name__}: {e}")
            raise

    async def subscribe_to_updates(
        self,
        agent_id: str,
        callback: callable
    ):
        """
        Subscribe to real-time updates for an agent.

        Args:
            agent_id: Agent identifier
            callback: Async function to call with updates
                Signature: async def callback(update: Dict[str, Any])
        """
        if not self.redis:
            print(f"[ContextEngine] ⚠ Redis client not available, cannot subscribe")
            return

        channel = self.registered_agents.get(agent_id)
        if not channel:
            print(f"[ContextEngine] ⚠ Agent {agent_id} not registered")
            return

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)

        print(f"[ContextEngine] ✓ Subscribed to updates for {agent_id} on {channel}")

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    try:
                        update = json.loads(message['data'])
                        await callback(update)
                    except Exception as e:
                        print(f"[ContextEngine] ✗ Error processing update: {e}")

                await asyncio.sleep(0.1)

        finally:
            await pubsub.unsubscribe(channel)

    async def get_project_data(
        self,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get all published data for a project.

        Args:
            project_id: Project identifier

        Returns:
            All project data or None if not available
        """
        import httpx

        # Try SDK method first if available
        client = await self._get_client()
        if client:
            try:
                # Try different possible SDK method names
                if hasattr(client, 'get_project_data'):
                    response = await client.get_project_data(project_id=project_id)
                elif hasattr(client, 'get_data'):
                    response = await client.get_data(project_id=project_id)
                elif hasattr(client, 'project_data'):
                    response = await client.project_data(project_id=project_id)
                else:
                    # Fall through to HTTP request
                    response = None

                if response is not None:
                    # Convert response to dict
                    if hasattr(response, 'data'):
                        return response.data
                    elif isinstance(response, dict):
                        return response
                    elif hasattr(response, '__dict__'):
                        return response.__dict__
                    else:
                        return response
            except Exception as e:
                print(f"[ContextEngine] SDK method failed, trying HTTP: {e}")

        # Fallback to direct HTTP request
        try:
            url = f"{self.base_url}/api/v1/projects/{project_id}/data"
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"[ContextEngine] ✗ Failed to get project data: {e}")
            return None

    async def get_agent_context(
        self,
        agent_id: str,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current context for an agent.

        This retrieves the agent's context based on registered needs
        and currently available data.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier

        Returns:
            Agent context or None if not available
        """
        try:
            # Query for all data relevant to this agent using our HTTP-based query method
            results = await self.query(
                project_id=project_id,
                query=f"context for agent {agent_id}"
            )

            if not results:
                return None

            return {
                "agent_id": agent_id,
                "project_id": project_id,
                "context_items": [
                    {
                        "data_key": r.get('data_key', ''),
                        "data": r.get('data', {})
                    }
                    for r in results
                ]
            }

        except Exception as e:
            print(f"[ContextEngine] ✗ Failed to get agent context: {e}")
            return None


# Global instance
_context_engine_client: Optional[ContextEngineClient] = None


def get_context_engine_client() -> Optional[ContextEngineClient]:
    """Get the global Context Engine client instance."""
    return _context_engine_client


async def initialize_context_engine(redis_client: Redis = None) -> ContextEngineClient:
    """
    Initialize the global Context Engine client.

    Args:
        redis_client: Optional Redis client for pub/sub subscriptions

    Returns:
        Context Engine client instance
    """
    global _context_engine_client

    if _context_engine_client is None:
        _context_engine_client = ContextEngineClient(redis_client=redis_client)

        # Check if service is available
        if await _context_engine_client.health_check():
            print("[ContextEngine] ✓ Context Engine is available")
        else:
            print("[ContextEngine] ⚠ Context Engine not available (will retry on use)")

    return _context_engine_client


async def shutdown_context_engine():
    """Shut down the global Context Engine client."""
    global _context_engine_client

    if _context_engine_client:
        await _context_engine_client.close()
        _context_engine_client = None
        print("[ContextEngine] ✓ Context Engine client shut down")

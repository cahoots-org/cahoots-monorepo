"""HTTP client for Context Engine service

This client communicates with the standalone Context Engine service via HTTP API.
The Context Engine uses embedding-based semantic matching to automatically provide
relevant context to agents based on their semantic needs.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
import httpx
from redis.asyncio import Redis


class ContextEngineClient:
    """
    HTTP client for Context Engine.
    
    Features:
    - Agent registration with semantic needs (natural language)
    - Data publishing (any schema)
    - Automatic semantic matching via embeddings
    - Real-time updates via Redis pub/sub
    - Agent catch-up for missed events
    """

    def __init__(self, base_url: str = None, redis_client: Redis = None):
        """
        Initialize Context Engine HTTP client.
        
        Args:
            base_url: Context Engine API URL (default: http://context-engine:8001)
            redis_client: Redis client for pub/sub subscriptions (optional)
        """
        self.base_url = base_url or os.getenv("CONTEXT_ENGINE_URL", "http://context-engine:8001")
        self.redis = redis_client
        self.registered_agents: Dict[str, str] = {}  # agent_id -> notification_channel
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def health_check(self) -> bool:
        """Check if Context Engine is available"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception as e:
            print(f"[ContextEngine] Health check failed: {e}")
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
        
        try:
            response = await client.post(
                f"{self.base_url}/data/publish",
                json={
                    "project_id": project_id,
                    "data_key": data_key,
                    "data": data,
                    "event_type": event_type
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"[ContextEngine] ✓ Published {data_key} for project {project_id} (seq: {result['sequence']})")
            return result["sequence"]
            
        except httpx.HTTPError as e:
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
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/agents/register",
                json={
                    "agent_id": agent_id,
                    "project_id": project_id,
                    "data_needs": data_needs,
                    "last_seen_sequence": last_seen_sequence,
                    "notification_channel": notification_channel
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Store registration
            self.registered_agents[agent_id] = result["notification_channel"]
            
            print(f"[ContextEngine] ✓ Registered agent {agent_id}")
            print(f"[ContextEngine]   Matched needs: {result['matched_needs']}")
            print(f"[ContextEngine]   Caught up: {result['caught_up_events']} events")
            
            return result
            
        except httpx.HTTPError as e:
            print(f"[ContextEngine] ✗ Failed to register agent: {e}")
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
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.base_url}/agents/{agent_id}"
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
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

"""
Context Engine (Contex) client for semantic context routing.

Publishes file content and metadata to the Context Engine for:
- Semantic search across codebase
- Pub/sub delivery to agents
- Code understanding and pattern matching
"""

import httpx
from typing import Optional, List, Dict, Any


class ContextEngineClient:
    """Client for Contex semantic context routing."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> httpx.Response:
        """Make an HTTP request to Context Engine."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{self.base_url}{path}"
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json,
                params=params
            )
            return response

    async def publish_file(
        self,
        project_id: str,
        path: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish file content to Context Engine for semantic indexing."""
        response = await self._request(
            "POST",
            "/api/v1/data/publish",
            json={
                "namespace": project_id,
                "key": path,
                "content": content,
                "metadata": metadata
            }
        )
        if response.status_code >= 400:
            # Context Engine might not be available, log but don't fail
            return {"ok": False, "error": response.text}
        return response.json()

    async def upsert_file(
        self,
        project_id: str,
        path: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert (insert or update) file in Context Engine."""
        # Same as publish - Contex handles upsert by key
        return await self.publish_file(project_id, path, content, metadata)

    async def query(
        self,
        project_id: str,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Query Context Engine for semantically similar content."""
        payload = {
            "project_id": project_id,
            "query": query,
            "max_results": top_k
        }
        if filters:
            payload["filters"] = filters

        response = await self._request(
            "POST",
            f"/api/v1/projects/{project_id}/query",
            json=payload
        )
        if response.status_code >= 400:
            return []
        return response.json().get("results", [])

    async def register_agent(
        self,
        agent_id: str,
        project_id: str,
        context_needs: str
    ) -> Dict[str, Any]:
        """Register an agent with its context needs for pub/sub delivery."""
        response = await self._request(
            "POST",
            "/api/v1/agents/register",
            json={
                "agent_id": agent_id,
                "namespace": project_id,
                "description": context_needs
            }
        )
        if response.status_code >= 400:
            return {"ok": False, "error": response.text}
        return response.json()

    async def delete_file(self, project_id: str, path: str) -> bool:
        """Delete a file from the Context Engine index."""
        response = await self._request(
            "DELETE",
            f"/api/v1/data/{project_id}/{path}"
        )
        return response.status_code < 400

    async def batch_publish(
        self,
        project_id: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Batch publish multiple files to Context Engine."""
        items = [
            {
                "namespace": project_id,
                "key": f["path"],
                "content": f["content"],
                "metadata": f.get("metadata", {})
            }
            for f in files
        ]

        response = await self._request(
            "POST",
            "/api/v1/data/batch",
            json={"items": items}
        )
        if response.status_code >= 400:
            return {"ok": False, "error": response.text}
        return response.json()

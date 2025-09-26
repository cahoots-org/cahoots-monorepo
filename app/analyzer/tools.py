"""Tools that the LLM agent can use to gather context."""

from typing import Dict, Any, List, Optional
import httpx
import asyncio

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


class AnalyzerTools:
    """Tools available to the task analyzer for gathering context."""

    def __init__(self):
        """Initialize tools."""
        self.ddgs = DDGS() if DDGS else None

    async def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search the web for context about a task.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results with title, body, and href
        """
        if not self.ddgs:
            return []

        try:
            # Run synchronous search in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(self.ddgs.text(query, max_results=max_results))
            )

            # Format results
            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", "")
                })

            return formatted

        except Exception as e:
            print(f"Web search error: {e}")
            return []

    async def search_technical_docs(self, technology: str) -> List[Dict[str, str]]:
        """Search for technical documentation about a technology.

        Args:
            technology: Technology to search for (e.g., "React", "Django")

        Returns:
            List of documentation snippets
        """
        queries = [
            f"{technology} official documentation",
            f"{technology} best practices",
            f"{technology} architecture patterns"
        ]

        all_results = []
        for query in queries:
            results = await self.web_search(query, max_results=2)
            all_results.extend(results)

        return all_results

    async def search_similar_projects(self, task_description: str) -> List[Dict[str, str]]:
        """Search for similar projects or tutorials.

        Args:
            task_description: Description of the task

        Returns:
            List of similar project descriptions
        """
        queries = [
            f"{task_description} tutorial",
            f"how to build {task_description}",
            f"{task_description} architecture",
            f"{task_description} implementation guide"
        ]

        all_results = []
        for query in queries[:2]:  # Limit to avoid too many searches
            results = await self.web_search(query, max_results=3)
            all_results.extend(results)

        return all_results

    async def analyze_task_complexity(self, task_description: str) -> Dict[str, Any]:
        """Search for information to help determine task complexity.

        Args:
            task_description: Description of the task

        Returns:
            Dictionary with complexity indicators
        """
        # Search for implementation time estimates
        time_results = await self.web_search(
            f"{task_description} development time estimate hours",
            max_results=3
        )

        # Search for required components
        component_results = await self.web_search(
            f"{task_description} components architecture",
            max_results=3
        )

        return {
            "time_estimates": time_results,
            "components": component_results
        }

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools.

        Returns:
            List of tool descriptions
        """
        return [
            {
                "name": "web_search",
                "description": "Search the web for general information",
                "parameters": ["query: str", "max_results: int = 5"]
            },
            {
                "name": "search_technical_docs",
                "description": "Search for technical documentation about a technology",
                "parameters": ["technology: str"]
            },
            {
                "name": "search_similar_projects",
                "description": "Find similar projects or tutorials",
                "parameters": ["task_description: str"]
            },
            {
                "name": "analyze_task_complexity",
                "description": "Search for complexity indicators",
                "parameters": ["task_description: str"]
            }
        ]
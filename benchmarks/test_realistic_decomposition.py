"""Test benchmarks with more realistic LLM client for actual decomposition."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage import RedisClient, TaskStorage
from app.analyzer import UnifiedAnalyzer, MockLLMClient
from app.cache import CacheManager
from app.processor import TaskProcessor
from app.processor.processing_rules import ProcessingConfig

from benchmarks.performance_tracker import BenchmarkRunner, BenchmarkResult
from benchmarks.comparison_analyzer import ComparisonAnalyzer


class RealisticMockLLMClient(MockLLMClient):
    """Mock LLM client that produces more realistic decomposition trees."""

    async def chat_completion(self, messages, **kwargs):
        """Generate more realistic responses based on task complexity."""
        user_message = messages[-1]["content"]
        description = self._extract_task_description(user_message)

        # Determine if this is analysis or decomposition
        if "analyze the following task" in user_message.lower():
            return await self._generate_analysis(description)
        elif "decompose the following task" in user_message.lower():
            return await self._generate_decomposition(description)
        else:
            return await super().chat_completion(messages, **kwargs)

    def _extract_task_description(self, message: str) -> str:
        """Extract task description from message."""
        lines = message.split('\n')
        for line in lines:
            if 'Task:' in line:
                return line.replace('Task:', '').strip()
        return message

    async def _generate_analysis(self, description: str) -> str:
        """Generate realistic task analysis."""
        # Determine complexity based on keywords
        is_simple = any(word in description.lower() for word in ['hello', 'function', 'calculator', 'factorial'])
        is_complex = any(word in description.lower() for word in ['platform', 'system', 'application', 'management', 'e-commerce'])

        if is_simple:
            return '''```json
{
  "complexity_score": 0.2,
  "is_atomic": true,
  "is_specific": true,
  "confidence": 0.9,
  "reasoning": "Simple function implementation that can be coded directly",
  "suggested_approach": "implement",
  "implementation_hints": "Create a single function with proper error handling",
  "estimated_story_points": 1,
  "requires_human_review": false
}```'''
        elif is_complex:
            return '''```json
{
  "complexity_score": 0.8,
  "is_atomic": false,
  "is_specific": true,
  "confidence": 0.85,
  "reasoning": "Complex system requiring multiple components and integration",
  "suggested_approach": "decompose",
  "implementation_hints": null,
  "estimated_story_points": 21,
  "requires_human_review": false
}```'''
        else:
            return '''```json
{
  "complexity_score": 0.5,
  "is_atomic": false,
  "is_specific": true,
  "confidence": 0.8,
  "reasoning": "Moderate complexity requiring some decomposition",
  "suggested_approach": "decompose",
  "implementation_hints": null,
  "estimated_story_points": 8,
  "requires_human_review": false
}```'''

    async def _generate_decomposition(self, description: str) -> str:
        """Generate realistic task decomposition."""
        if "e-commerce" in description.lower():
            return '''```json
{
  "subtasks": [
    {
      "description": "Set up project structure and dependencies",
      "is_atomic": true,
      "implementation_details": "Initialize Python project with FastAPI, PostgreSQL, Redis",
      "story_points": 2
    },
    {
      "description": "Implement user authentication and registration system",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 8
    },
    {
      "description": "Create product catalog management",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 5
    },
    {
      "description": "Build shopping cart and checkout flow",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 6
    }
  ],
  "decomposition_reasoning": "Split into core infrastructure, user management, product management, and transaction handling"
}```'''
        elif "social media" in description.lower():
            return '''```json
{
  "subtasks": [
    {
      "description": "Create user profiles and authentication",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 5
    },
    {
      "description": "Implement posts and content creation",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 5
    },
    {
      "description": "Build commenting and interaction system",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 5
    },
    {
      "description": "Add real-time notifications with WebSockets",
      "is_atomic": true,
      "implementation_details": "Implement WebSocket server for real-time updates",
      "story_points": 6
    }
  ],
  "decomposition_reasoning": "Split into user management, content creation, interactions, and real-time features"
}```'''
        elif "project management" in description.lower():
            return '''```json
{
  "subtasks": [
    {
      "description": "Implement team and user management",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 5
    },
    {
      "description": "Create task management and tracking system",
      "is_atomic": false,
      "implementation_details": null,
      "story_points": 8
    },
    {
      "description": "Build time tracking functionality",
      "is_atomic": true,
      "implementation_details": "Create time logging API with start/stop functionality",
      "story_points": 3
    },
    {
      "description": "Develop reporting and analytics dashboard",
      "is_atomic": true,
      "implementation_details": "Build charts and metrics for project progress",
      "story_points": 5
    }
  ],
  "decomposition_reasoning": "Split into team management, task tracking, time management, and reporting"
}```'''
        elif "authentication" in description.lower():
            return '''```json
{
  "subtasks": [
    {
      "description": "Create user model and database schema",
      "is_atomic": true,
      "implementation_details": "Define User model with email, password, and profile fields",
      "story_points": 2
    },
    {
      "description": "Implement password hashing and validation",
      "is_atomic": true,
      "implementation_details": "Use bcrypt for secure password hashing",
      "story_points": 2
    },
    {
      "description": "Build JWT token generation and validation",
      "is_atomic": true,
      "implementation_details": "Create JWT tokens with refresh token support",
      "story_points": 3
    },
    {
      "description": "Create login and registration endpoints",
      "is_atomic": true,
      "implementation_details": "REST API endpoints for auth operations",
      "story_points": 1
    }
  ],
  "decomposition_reasoning": "Split into data model, security implementation, token management, and API endpoints"
}```'''
        else:
            # Default decomposition for medium complexity tasks
            return '''```json
{
  "subtasks": [
    {
      "description": "Design and implement core functionality",
      "is_atomic": true,
      "implementation_details": "Main business logic implementation",
      "story_points": 3
    },
    {
      "description": "Add error handling and validation",
      "is_atomic": true,
      "implementation_details": "Comprehensive error handling and input validation",
      "story_points": 2
    },
    {
      "description": "Write tests and documentation",
      "is_atomic": true,
      "implementation_details": "Unit tests and API documentation",
      "story_points": 3
    }
  ],
  "decomposition_reasoning": "Split into core implementation, quality assurance, and documentation"
}```'''


async def setup_realistic_components():
    """Set up components with realistic LLM client."""
    print("Setting up realistic benchmark environment...")

    # Use realistic mock that generates actual decomposition trees
    llm_client = RealisticMockLLMClient()
    analyzer = UnifiedAnalyzer(llm_client)

    # Use separate DB for realistic tests
    redis_client = RedisClient(host="localhost", port=6379, db=14)
    await redis_client.connect()

    # Clear test database
    await redis_client.redis.flushdb()

    storage = TaskStorage(redis_client)

    # Set up cache
    cache_manager = CacheManager(
        redis_client,
        use_semantic_cache=True,
        cache_ttl=3600
    )

    # Configure processor
    config = ProcessingConfig(
        max_depth=4,  # Allow deeper decomposition
        complexity_threshold=0.45,
        batch_sibling_threshold=3,
        use_template_cache=True,
        use_semantic_cache=True
    )

    processor = TaskProcessor(storage, analyzer, cache_manager, config)

    print("✓ Realistic components initialized")
    return processor, redis_client


async def run_realistic_benchmark():
    """Run benchmark with realistic decomposition."""

    # Complex tasks that should generate decomposition trees
    realistic_tasks = [
        {
            "description": "Build a complete e-commerce platform with user management, product catalog, and payment processing",
            "type": "complex",
            "max_depth": 4,
            "context": {
                "tech_stack": {
                    "backend_language": "Python",
                    "frontend_framework": "React",
                    "database": "PostgreSQL",
                    "payment_provider": "Stripe"
                }
            }
        },
        {
            "description": "Create a social media application with posts, comments, likes, and real-time notifications",
            "type": "complex",
            "max_depth": 4,
            "context": {
                "tech_stack": {
                    "backend_language": "Python",
                    "frontend_framework": "React",
                    "database": "PostgreSQL",
                    "websockets": True
                }
            }
        },
        {
            "description": "Create a user authentication system with JWT",
            "type": "medium",
            "max_depth": 3,
            "context": {
                "tech_stack": {
                    "backend_language": "Python",
                    "framework": "FastAPI",
                    "database": "PostgreSQL"
                }
            }
        }
    ]

    try:
        processor, redis_client = await setup_realistic_components()

        print("\nRunning realistic decomposition benchmark...")
        runner = BenchmarkRunner(processor)

        # Run each task twice to test caching
        suite = await runner.run_benchmark_suite(realistic_tasks, runs_per_task=2)

        # Print detailed results
        runner.print_summary()

        # Generate analysis
        analyzer = ComparisonAnalyzer(suite)
        analyzer.print_comparison_report()

        # Print detailed task trees
        print("\n" + "="*60)
        print("DETAILED DECOMPOSITION RESULTS")
        print("="*60)

        for result in suite.results:
            if result.success:
                print(f"\nTask: {result.task_description}")
                print(f"  Type: {result.task_type}")
                print(f"  Time: {result.total_time:.3f}s")
                print(f"  Tasks Created: {result.tasks_created}")
                print(f"  Max Depth: {result.max_depth}")
                print(f"  LLM Calls: {result.llm_calls}")
                print(f"  Cache Hits: {result.cache_hits}")

        return suite

    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run_realistic_benchmark())
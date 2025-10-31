"""Integration test for Context Engine with GitHub agent

Note: This test requires Contex service running.
Start with: docker compose up -d context-engine
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fakeredis import FakeAsyncRedis

from app.services.context_engine_client import ContextEngineClient


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing"""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def mock_llm_generator():
    """Mock the LLM generator to avoid loading actual models"""
    with patch("src.service.LLMContextGenerator") as mock_class:
        mock_instance = Mock()
        mock_instance.initialize = AsyncMock()
        mock_instance.shutdown = AsyncMock()
        mock_instance.generate_context = AsyncMock()

        # Mock the generate_context to return realistic contexts
        from src.models import AgentContext

        async def generate_mock_context(profile, project_state):
            """Generate a mock context based on profile"""
            return AgentContext(
                agent_id=profile.agent_id,
                project_id=project_state.project_id,
                summary=f"Mock context for {profile.agent_type}",
                key_facts=[
                    "Fact 1 about the project",
                    "Fact 2 about the codebase",
                    "Fact 3 about architecture"
                ],
                constraints={
                    "tech_stack": project_state.tech_stack or {},
                    "github_repo": project_state.github_context or {}
                },
                recommendations=[
                    "Recommendation 1 for implementation",
                    "Recommendation 2 for best practices"
                ],
                source_version=project_state.version
            )

        mock_instance.generate_context.side_effect = generate_mock_context
        mock_class.return_value = mock_instance

        yield mock_instance


class TestContextEngineGitHubIntegration:
    """Test Context Engine integration with GitHub agent"""

    @pytest.mark.asyncio
    async def test_github_agent_registration(self, fake_redis, mock_llm_generator):
        """Test that GitHub agent can be registered at startup"""

        client = ContextEngineClient(fake_redis)
        await client.initialize()

        # Register GitHub agent
        agent_id = await client.register_github_agent()

        assert agent_id == "github-analyzer-main"
        assert "github_analyzer" in client.registered_agents
        assert client.registered_agents["github_analyzer"] == agent_id

        await client.shutdown()

    @pytest.mark.asyncio
    async def test_publish_github_context(self, fake_redis, mock_llm_generator):
        """Test publishing GitHub context to Context Engine"""

        client = ContextEngineClient(fake_redis)
        await client.initialize()
        await client.register_github_agent()

        # Give event bus time to start
        await asyncio.sleep(0.2)

        # Simulate GitHub context from GitHubContextEnrichmentAgent
        github_context = {
            "repo_url": "https://github.com/test/repo",
            "repo_info": {
                "owner": "test",
                "repo": "repo",
                "is_public": True
            },
            "repo_summary": "This is a FastAPI-based REST API with React frontend...",
            "file_tree_summary": {
                "total_files": 247,
                "file_types": {"py": 120, "js": 80, "md": 10},
                "directories": ["src", "app", "tests", "frontend"]
            },
            "file_summaries": {
                "app/main.py": "Main FastAPI application entry point...",
                "app/routes/auth.py": "Authentication routes and JWT handling..."
            },
            "context_metadata": {
                "iterations": 2,
                "files_read": 15,
                "api_calls_used": 17,
                "confidence": 0.85
            }
        }

        # Publish GitHub context
        await client.publish_github_context(
            project_id="test-project-123",
            user_id="test-user",
            github_context=github_context
        )

        # Give Context Engine time to process
        await asyncio.sleep(0.3)

        # Verify LLM generator was called to create context for GitHub agent
        assert mock_llm_generator.generate_context.called

        # Verify context can be retrieved
        context = await client.get_agent_context("github_analyzer", "test-project-123")

        assert context is not None
        assert context["summary"] == "Mock context for github_analyzer"
        assert len(context["key_facts"]) > 0
        assert "github_repo" in context["constraints"]

        await client.shutdown()

    @pytest.mark.asyncio
    async def test_publish_existing_features(self, fake_redis, mock_llm_generator):
        """Test publishing existing features analysis"""

        client = ContextEngineClient(fake_redis)
        await client.initialize()
        await client.register_github_agent()

        await asyncio.sleep(0.2)

        # Simulate existing features from feature overlap detection
        existing_features = {
            "summary": {
                "total_requested": 5,
                "already_exist": 2,
                "overlap_percentage": 40.0
            },
            "existing_features": [
                {
                    "requested": "User authentication",
                    "status": "exists",
                    "confidence": 0.95,
                    "evidence": "Found auth routes in app/routes/auth.py"
                },
                {
                    "requested": "OAuth integration",
                    "status": "exists",
                    "confidence": 0.90,
                    "evidence": "OAuth handlers in app/services/oauth.py"
                }
            ]
        }

        # Publish existing features
        await client.publish_existing_features(
            project_id="test-project-123",
            user_id="test-user",
            existing_features=existing_features
        )

        await asyncio.sleep(0.3)

        # Verify the context was updated
        assert mock_llm_generator.generate_context.called

        await client.shutdown()

    @pytest.mark.asyncio
    async def test_complete_workflow_with_github(self, fake_redis, mock_llm_generator):
        """Test complete workflow: GitHub enrichment -> Context Engine -> Agent retrieval"""

        client = ContextEngineClient(fake_redis)
        await client.initialize()

        # Register GitHub agent
        await client.register_github_agent()

        await asyncio.sleep(0.2)

        # Step 1: Publish GitHub context (simulating what happens after enrich_task_context)
        github_context = {
            "repo_url": "https://github.com/cahoots/app",
            "repo_info": {"owner": "cahoots", "repo": "app", "is_public": True},
            "repo_summary": "Event-driven task management system with FastAPI and React...",
            "file_tree_summary": {
                "total_files": 300,
                "file_types": {"py": 150, "js": 100, "tsx": 50},
                "directories": ["app", "frontend", "tests"]
            },
            "file_summaries": {
                "app/processor/task_processor.py": "Processes tasks recursively...",
                "app/analyzer/unified_domain_analyzer.py": "Generates event models..."
            },
            "context_metadata": {
                "iterations": 3,
                "files_read": 20,
                "api_calls_used": 25,
                "confidence": 0.90
            }
        }

        await client.publish_github_context(
            project_id="cahoots-task-456",
            user_id="user-789",
            github_context=github_context
        )

        await asyncio.sleep(0.3)

        # Step 2: Retrieve tailored context for GitHub analyzer
        context = await client.get_agent_context("github_analyzer", "cahoots-task-456")

        assert context is not None
        assert "summary" in context
        assert "key_facts" in context
        assert "recommendations" in context
        assert context["constraints"]["github_repo"] is not None

        print(f"\n✓ GitHub Context Engine Integration Test Complete")
        print(f"  Summary: {context['summary']}")
        print(f"  Key Facts: {len(context['key_facts'])}")
        print(f"  Recommendations: {len(context['recommendations'])}")

        await client.shutdown()

    @pytest.mark.asyncio
    async def test_error_handling_without_context_engine(self, fake_redis):
        """Test that GitHub agent works even if Context Engine fails"""

        # Don't initialize the Context Engine
        client = ContextEngineClient(fake_redis)
        # client.service remains None

        # Publishing should not crash
        github_context = {
            "repo_url": "https://github.com/test/repo",
            "repo_info": {"owner": "test", "repo": "repo", "is_public": True},
            "repo_summary": "Test repo",
            "file_tree_summary": {"total_files": 10},
            "file_summaries": {},
            "context_metadata": {"confidence": 0.8}
        }

        # Should not raise an error
        await client.publish_github_context(
            project_id="test-123",
            user_id="user-456",
            github_context=github_context
        )

        # Retrieving context should return None
        context = await client.get_agent_context("github_analyzer", "test-123")
        assert context is None

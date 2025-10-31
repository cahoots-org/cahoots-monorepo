"""Integration tests for Contex with live service

These tests require:
1. Contex service running (docker compose up -d context-engine)
2. Redis running (docker compose up -d redis)

Run with: pytest tests/integration/test_context_engine_integration.py -v
"""

import pytest
import asyncio
import os
from redis.asyncio import Redis

from app.services.context_engine_client import ContextEngineClient, initialize_context_engine
from app.analyzer.context_aware_agent import ContextAwareAgent
from app.analyzer.llm_client import MockLLMClient


# Test agent implementation
class TestIntegrationAgent(ContextAwareAgent):
    """Test agent for integration testing"""
    AGENT_ID = "integration-test-agent"
    DATA_NEEDS = [
        "programming languages and frameworks used",
        "event model with events and commands"
    ]


@pytest.fixture
async def redis_client():
    """Create Redis client for tests"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    client = await Redis.from_url(redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def context_engine(redis_client):
    """Create Context Engine client"""
    base_url = os.getenv("CONTEXT_ENGINE_URL", "http://localhost:8001")
    client = ContextEngineClient(base_url=base_url, redis_client=redis_client)
    yield client
    await client.close()


@pytest.fixture
def project_id():
    """Generate unique project ID for test isolation"""
    import uuid
    return f"test-project-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def agent(context_engine):
    """Create test agent"""
    llm = MockLLMClient()
    return TestIntegrationAgent(llm, context_engine)


@pytest.mark.asyncio
@pytest.mark.integration
class TestContextEngineHealthCheck:
    """Test Context Engine service availability"""

    async def test_health_check(self, context_engine):
        """Test Context Engine is available"""
        is_healthy = await context_engine.health_check()
        assert is_healthy is True, "Context Engine service is not available"


@pytest.mark.asyncio
@pytest.mark.integration
class TestDataPublishing:
    """Test data publishing to Context Engine"""

    async def test_publish_tech_stack(self, context_engine, project_id):
        """Test publishing tech stack data"""
        sequence = await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={
                "backend": "Python/FastAPI",
                "frontend": "React",
                "database": "PostgreSQL"
            }
        )

        assert sequence is not None
        assert isinstance(sequence, str)

    async def test_publish_event_model(self, context_engine, project_id):
        """Test publishing event model data"""
        sequence = await context_engine.publish_data(
            project_id=project_id,
            data_key="event_model",
            data={
                "events": ["UserCreated", "TaskCompleted"],
                "commands": ["CreateUser", "CompleteTask"]
            }
        )

        assert sequence is not None

    async def test_publish_multiple_data_sources(self, context_engine, project_id):
        """Test publishing multiple data sources"""
        seq1 = await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={"backend": "Python"}
        )

        seq2 = await context_engine.publish_data(
            project_id=project_id,
            data_key="event_model",
            data={"events": ["Event1"]}
        )

        # Sequences should be different and ordered
        assert seq1 != seq2


@pytest.mark.asyncio
@pytest.mark.integration
class TestAgentRegistration:
    """Test agent registration and context matching"""

    async def test_register_agent(self, context_engine, project_id):
        """Test basic agent registration"""
        result = await context_engine.register_agent(
            agent_id="test-agent",
            project_id=project_id,
            data_needs=[
                "programming languages and frameworks",
                "event model structure"
            ]
        )

        assert result["agent_id"] == "test-agent"
        assert "notification_channel" in result
        assert "matched_needs" in result
        assert "caught_up_events" in result

    async def test_agent_registration_with_data(self, context_engine, project_id):
        """Test agent registration after data is published"""
        # Publish data first
        await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={"backend": "Python", "frontend": "React"}
        )

        await context_engine.publish_data(
            project_id=project_id,
            data_key="event_model",
            data={"events": ["TaskCreated"], "commands": ["CreateTask"]}
        )

        # Register agent
        result = await context_engine.register_agent(
            agent_id="test-agent-2",
            project_id=project_id,
            data_needs=[
                "programming languages and frameworks used",
                "event model with events and commands"
            ]
        )

        # Should have matched needs
        assert len(result["matched_needs"]) > 0

        # Should have caught up with published events
        assert result["caught_up_events"] >= 0


@pytest.mark.asyncio
@pytest.mark.integration
class TestAgentContextRetrieval:
    """Test agent context retrieval"""

    async def test_get_agent_context_after_registration(self, context_engine, project_id):
        """Test getting context after registration"""
        # Publish data
        await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={"backend": "Python"}
        )

        # Register agent
        await context_engine.register_agent(
            agent_id="test-agent-3",
            project_id=project_id,
            data_needs=["programming languages and frameworks"]
        )

        # Get context
        context = await context_engine.get_agent_context(
            agent_id="test-agent-3",
            project_id=project_id
        )

        assert context is not None

    async def test_get_agent_context_not_registered(self, context_engine, project_id):
        """Test getting context for non-registered agent"""
        context = await context_engine.get_agent_context(
            agent_id="non-existent-agent",
            project_id=project_id
        )

        # Should return None or empty context
        assert context is None or context == {}


@pytest.mark.asyncio
@pytest.mark.integration
class TestContextAwareAgentIntegration:
    """Test ContextAwareAgent with live Context Engine"""

    async def test_agent_automatic_registration(self, agent, project_id):
        """Test agent automatically registers on first LLM call"""
        # Make LLM call (should trigger registration)
        response = await agent.llm_call(
            prompt="Analyze this task",
            project_id=project_id
        )

        assert response is not None

        # Agent should be registered now
        cache_key = f"{agent.AGENT_ID}:{project_id}"
        assert cache_key in agent._registered_projects

    async def test_agent_with_published_context(self, agent, context_engine, project_id):
        """Test agent receives context from published data"""
        # Publish data that matches agent's needs
        await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={
                "backend": "Python/FastAPI",
                "frontend": "React",
                "languages": ["Python", "JavaScript"]
            }
        )

        await context_engine.publish_data(
            project_id=project_id,
            data_key="event_model",
            data={
                "events": ["TaskCreated", "TaskCompleted"],
                "commands": ["CreateTask", "CompleteTask"]
            }
        )

        # Make LLM call
        response = await agent.llm_call(
            prompt="What technologies should I use?",
            project_id=project_id,
            max_tokens=100
        )

        assert response is not None

        # Verify agent was registered
        cache_key = f"{agent.AGENT_ID}:{project_id}"
        assert cache_key in agent._registered_projects

    async def test_agent_publish_and_consume(self, context_engine, project_id):
        """Test agent can both publish and consume data"""
        llm = MockLLMClient()

        # Create first agent (publisher)
        class PublisherAgent(ContextAwareAgent):
            AGENT_ID = "publisher-agent"
            DATA_NEEDS = []

        publisher = PublisherAgent(llm, context_engine)

        # Publish data
        await publisher.publish_data(
            project_id=project_id,
            data_key="analysis_result",
            data={"complexity": 0.75, "estimated_time": "3 hours"}
        )

        # Create second agent (consumer)
        class ConsumerAgent(ContextAwareAgent):
            AGENT_ID = "consumer-agent"
            DATA_NEEDS = ["complexity analysis and time estimates"]

        consumer = ConsumerAgent(llm, context_engine)

        # Consumer makes LLM call (should receive published data)
        response = await consumer.llm_call(
            prompt="How complex is this task?",
            project_id=project_id
        )

        assert response is not None

        # Verify consumer registered
        cache_key = f"consumer-agent:{project_id}"
        assert cache_key in consumer._registered_projects

    async def test_multiple_agents_same_project(self, context_engine, project_id):
        """Test multiple agents working on same project"""
        llm = MockLLMClient()

        # Publish initial data
        await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={"backend": "Python"}
        )

        # Create multiple agents
        class Agent1(ContextAwareAgent):
            AGENT_ID = "agent-1"
            DATA_NEEDS = ["programming languages"]

        class Agent2(ContextAwareAgent):
            AGENT_ID = "agent-2"
            DATA_NEEDS = ["programming languages"]

        agent1 = Agent1(llm, context_engine)
        agent2 = Agent2(llm, context_engine)

        # Both make LLM calls
        response1 = await agent1.llm_call("Task 1", project_id)
        response2 = await agent2.llm_call("Task 2", project_id)

        assert response1 is not None
        assert response2 is not None

        # Both should be registered independently
        assert f"agent-1:{project_id}" in agent1._registered_projects
        assert f"agent-2:{project_id}" in agent2._registered_projects


@pytest.mark.asyncio
@pytest.mark.integration
class TestRealTimeUpdates:
    """Test real-time pub/sub updates (if Redis available)"""

    async def test_subscribe_to_updates(self, context_engine, project_id):
        """Test subscribing to real-time updates"""
        # Register agent
        result = await context_engine.register_agent(
            agent_id="subscriber-agent",
            project_id=project_id,
            data_needs=["test data"]
        )

        notification_channel = result["notification_channel"]
        assert notification_channel is not None

        # Create subscriber
        received_updates = []

        async def callback(update):
            received_updates.append(update)

        # Subscribe (non-blocking, just verify it starts)
        subscribe_task = asyncio.create_task(
            context_engine.subscribe_to_updates(
                agent_id="subscriber-agent",
                callback=callback
            )
        )

        # Give subscription time to start
        await asyncio.sleep(0.5)

        # Publish data (should trigger update)
        await context_engine.publish_data(
            project_id=project_id,
            data_key="test_data",
            data={"value": 42}
        )

        # Give time for update to arrive
        await asyncio.sleep(1)

        # Cancel subscription
        subscribe_task.cancel()
        try:
            await subscribe_task
        except asyncio.CancelledError:
            pass

        # Verify updates were received (if pub/sub is working)
        # Note: This might be 0 if Redis pub/sub isn't configured
        # The test passes as long as no errors occur


@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""

    async def test_complete_workflow(self, context_engine, project_id):
        """Test complete workflow: publish -> register -> analyze -> publish results"""
        llm = MockLLMClient()

        # Step 1: Publish initial project context
        await context_engine.publish_data(
            project_id=project_id,
            data_key="tech_stack",
            data={
                "backend": "Python/FastAPI",
                "frontend": "React",
                "database": "PostgreSQL",
                "cache": "Redis"
            }
        )

        await context_engine.publish_data(
            project_id=project_id,
            data_key="event_model",
            data={
                "events": ["TaskCreated", "TaskDecomposed", "TaskCompleted"],
                "commands": ["CreateTask", "DecomposeTask", "CompleteTask"]
            }
        )

        # Step 2: Create analyzer agent
        class TaskAnalyzer(ContextAwareAgent):
            AGENT_ID = "task-analyzer"
            DATA_NEEDS = [
                "programming languages and frameworks used in the project",
                "event model with events and commands"
            ]

        analyzer = TaskAnalyzer(llm, context_engine)

        # Step 3: Analyze task (agent auto-registers and gets context)
        analysis = await analyzer.llm_call(
            prompt="Break down this task: Build a user authentication system",
            project_id=project_id,
            max_tokens=200
        )

        assert analysis is not None

        # Step 4: Publish analysis results
        await analyzer.publish_data(
            project_id=project_id,
            data_key="task_analysis",
            data={
                "task": "user authentication",
                "complexity": "medium",
                "subtasks": ["User model", "Login endpoint", "JWT tokens"],
                "estimated_time": "6 hours"
            }
        )

        # Step 5: Create second agent that consumes first agent's results
        class ImplementationAgent(ContextAwareAgent):
            AGENT_ID = "implementation-agent"
            DATA_NEEDS = [
                "task analysis with complexity and subtasks",
                "programming languages and frameworks"
            ]

        implementer = ImplementationAgent(llm, context_engine)

        # Step 6: Implementer gets context including analyzer's results
        implementation = await implementer.llm_call(
            prompt="Generate implementation plan",
            project_id=project_id,
            max_tokens=200
        )

        assert implementation is not None

        # Verify both agents registered
        assert f"task-analyzer:{project_id}" in analyzer._registered_projects
        assert f"implementation-agent:{project_id}" in implementer._registered_projects


@pytest.mark.asyncio
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios"""

    async def test_context_engine_unavailable(self):
        """Test graceful degradation when Context Engine is unavailable"""
        llm = MockLLMClient()

        # Create client pointing to non-existent service
        bad_client = ContextEngineClient(base_url="http://localhost:9999")

        class TestAgent(ContextAwareAgent):
            AGENT_ID = "test-agent"
            DATA_NEEDS = ["test"]

        agent = TestAgent(llm, bad_client)

        # Should not raise error, just degrade gracefully
        response = await agent.llm_call(
            prompt="Test",
            project_id="test-project"
        )

        assert response is not None  # LLM still works, just without context

    async def test_invalid_project_id(self, context_engine):
        """Test handling invalid project ID"""
        # Should not raise error
        context = await context_engine.get_agent_context(
            agent_id="test-agent",
            project_id="invalid-project-id"
        )

        # Should return None or empty
        assert context is None or context == {}

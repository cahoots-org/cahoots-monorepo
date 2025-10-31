"""Unit tests for ContextAwareAgent base class"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.analyzer.context_aware_agent import ContextAwareAgent
from app.analyzer.llm_client import LLMClient
from app.services.context_engine_client import ContextEngineClient


class TestAnalyzer(ContextAwareAgent):
    """Test analyzer for testing ContextAwareAgent"""
    AGENT_ID = "test-analyzer"
    DATA_NEEDS = [
        "programming languages and frameworks",
        "event model structure"
    ]


@pytest.fixture
def mock_llm():
    """Mock LLM client"""
    llm = AsyncMock(spec=LLMClient)
    llm.chat_completion = AsyncMock(return_value="LLM response")
    return llm


@pytest.fixture
def mock_context_engine():
    """Mock Context Engine client"""
    engine = AsyncMock(spec=ContextEngineClient)
    engine.register_agent = AsyncMock(return_value={
        "agent_id": "test-analyzer",
        "matched_needs": {},
        "caught_up_events": 0
    })
    engine.get_agent_context = AsyncMock(return_value=None)
    engine.publish_data = AsyncMock()
    return engine


@pytest.fixture
def agent(mock_llm, mock_context_engine):
    """Create test agent"""
    return TestAnalyzer(mock_llm, mock_context_engine)


@pytest.mark.asyncio
class TestContextAwareAgentInitialization:
    """Test agent initialization"""

    def test_requires_agent_id(self, mock_llm):
        """Test that AGENT_ID must be defined"""
        with pytest.raises(ValueError, match="must define AGENT_ID"):
            class BadAgent(ContextAwareAgent):
                pass

            BadAgent(mock_llm)

    def test_initialization_with_context_engine(self, mock_llm, mock_context_engine):
        """Test initialization with context engine"""
        agent = TestAnalyzer(mock_llm, mock_context_engine)

        assert agent.llm == mock_llm
        assert agent.context_engine == mock_context_engine
        assert agent.AGENT_ID == "test-analyzer"
        assert len(agent.DATA_NEEDS) == 2
        assert agent._registered_projects == {}

    def test_initialization_without_context_engine(self, mock_llm):
        """Test initialization without context engine"""
        agent = TestAnalyzer(mock_llm, context_engine=None)

        assert agent.llm == mock_llm
        assert agent.context_engine is None


@pytest.mark.asyncio
class TestContextAwareAgentRegistration:
    """Test agent registration with Context Engine"""

    async def test_ensure_registered_first_time(self, agent, mock_context_engine):
        """Test agent registers on first call"""
        await agent._ensure_registered("project-1")

        mock_context_engine.register_agent.assert_called_once_with(
            agent_id="test-analyzer",
            project_id="project-1",
            data_needs=[
                "programming languages and frameworks",
                "event model structure"
            ],
            last_seen_sequence="0"
        )

        # Check cached
        assert "test-analyzer:project-1" in agent._registered_projects

    async def test_ensure_registered_cached(self, agent, mock_context_engine):
        """Test agent doesn't re-register when cached"""
        # First call
        await agent._ensure_registered("project-1")
        assert mock_context_engine.register_agent.call_count == 1

        # Second call (should be cached)
        await agent._ensure_registered("project-1")
        assert mock_context_engine.register_agent.call_count == 1

    async def test_ensure_registered_different_projects(self, agent, mock_context_engine):
        """Test agent registers separately for each project"""
        await agent._ensure_registered("project-1")
        await agent._ensure_registered("project-2")

        assert mock_context_engine.register_agent.call_count == 2

        # Check both cached
        assert "test-analyzer:project-1" in agent._registered_projects
        assert "test-analyzer:project-2" in agent._registered_projects

    async def test_ensure_registered_no_context_engine(self, mock_llm):
        """Test registration skipped without context engine"""
        agent = TestAnalyzer(mock_llm, context_engine=None)

        # Should not raise error
        await agent._ensure_registered("project-1")

        assert agent._registered_projects == {}

    async def test_ensure_registered_handles_errors(self, agent, mock_context_engine):
        """Test registration error handling"""
        mock_context_engine.register_agent.side_effect = Exception("Registration failed")

        # Should not raise error, just log
        await agent._ensure_registered("project-1")

        # Should not be cached
        assert "test-analyzer:project-1" not in agent._registered_projects


@pytest.mark.asyncio
class TestContextAwareAgentContextRetrieval:
    """Test context retrieval"""

    async def test_get_context_success(self, agent, mock_context_engine):
        """Test successful context retrieval"""
        mock_context_engine.get_agent_context.return_value = {
            "data_keys": ["tech_stack", "event_model"],
            "needs": ["languages", "events"]
        }

        context = await agent._get_context("project-1")

        assert context is not None
        assert context["data_keys"] == ["tech_stack", "event_model"]

        mock_context_engine.get_agent_context.assert_called_once_with(
            agent_id="test-analyzer",
            project_id="project-1"
        )

    async def test_get_context_no_context_engine(self, mock_llm):
        """Test get context without context engine"""
        agent = TestAnalyzer(mock_llm, context_engine=None)

        context = await agent._get_context("project-1")

        assert context is None

    async def test_get_context_handles_errors(self, agent, mock_context_engine):
        """Test get context error handling"""
        mock_context_engine.get_agent_context.side_effect = Exception("Context fetch failed")

        context = await agent._get_context("project-1")

        assert context is None


@pytest.mark.asyncio
class TestContextFormatting:
    """Test context formatting"""

    def test_format_context_section_empty(self, agent):
        """Test formatting empty context"""
        result = agent._format_context_section(None)

        assert result == ""

    def test_format_context_section_with_data(self, agent):
        """Test formatting context with data"""
        context = {
            "data_keys": ["tech_stack", "event_model"],
            "needs": ["languages", "events"]
        }

        result = agent._format_context_section(context)

        assert "CONTEXT" in result
        assert "Automatically provided by Context Engine" in result
        assert "tech_stack" in result
        assert "event_model" in result
        assert "languages" in result
        assert "events" in result
        assert "=" in result  # Separator

    def test_format_context_section_data_keys_only(self, agent):
        """Test formatting with only data keys"""
        context = {"data_keys": ["tech_stack"]}

        result = agent._format_context_section(context)

        assert "Available Data:" in result
        assert "tech_stack" in result

    def test_format_context_section_needs_only(self, agent):
        """Test formatting with only needs"""
        context = {"needs": ["languages"]}

        result = agent._format_context_section(context)

        assert "Your Semantic Needs" in result
        assert "languages" in result


@pytest.mark.asyncio
class TestLLMCall:
    """Test automatic context injection in LLM calls"""

    async def test_llm_call_simple_prompt(self, agent, mock_llm, mock_context_engine):
        """Test LLM call with simple prompt"""
        mock_context_engine.get_agent_context.return_value = None

        response = await agent.llm_call(
            prompt="Analyze this task",
            project_id="project-1"
        )

        assert response == "LLM response"

        # Verify registration happened
        mock_context_engine.register_agent.assert_called_once()

        # Verify LLM call
        mock_llm.chat_completion.assert_called_once()
        call_args = mock_llm.chat_completion.call_args
        messages = call_args[1]["messages"]

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Analyze this task" in messages[0]["content"]

    async def test_llm_call_with_context(self, agent, mock_llm, mock_context_engine):
        """Test LLM call with context injection"""
        mock_context_engine.get_agent_context.return_value = {
            "data_keys": ["tech_stack"],
            "needs": ["languages"]
        }

        await agent.llm_call(
            prompt="Analyze this",
            project_id="project-1"
        )

        # Verify context was injected
        call_args = mock_llm.chat_completion.call_args
        messages = call_args[1]["messages"]
        content = messages[0]["content"]

        assert "CONTEXT" in content
        assert "tech_stack" in content
        assert "languages" in content
        assert "Analyze this" in content

    async def test_llm_call_with_max_tokens(self, agent, mock_llm, mock_context_engine):
        """Test LLM call with custom max_tokens"""
        mock_context_engine.get_agent_context.return_value = None

        await agent.llm_call(
            prompt="Test",
            project_id="project-1",
            max_tokens=5000
        )

        call_args = mock_llm.chat_completion.call_args
        assert call_args[1]["max_tokens"] == 5000

    async def test_llm_call_with_messages(self, agent, mock_llm, mock_context_engine):
        """Test LLM call with pre-built messages"""
        mock_context_engine.get_agent_context.return_value = {
            "data_keys": ["data1"]
        }

        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Do something"}
        ]

        await agent.llm_call(
            prompt="",  # Ignored when messages provided
            project_id="project-1",
            messages=messages
        )

        # Verify context injected into first user message
        call_args = mock_llm.chat_completion.call_args
        result_messages = call_args[1]["messages"]

        # Should have system message unchanged
        assert result_messages[0]["role"] == "system"
        assert result_messages[0]["content"] == "You are a helper"

        # User message should have context prepended
        assert result_messages[1]["role"] == "user"
        assert "CONTEXT" in result_messages[1]["content"]
        assert "data1" in result_messages[1]["content"]
        assert "Do something" in result_messages[1]["content"]

    async def test_llm_call_no_context_engine(self, mock_llm):
        """Test LLM call without context engine"""
        agent = TestAnalyzer(mock_llm, context_engine=None)

        response = await agent.llm_call(
            prompt="Test",
            project_id="project-1"
        )

        assert response == "LLM response"

        # Should still call LLM, just without context
        mock_llm.chat_completion.assert_called_once()
        call_args = mock_llm.chat_completion.call_args
        messages = call_args[1]["messages"]

        assert messages[0]["content"] == "Test"  # No context added


@pytest.mark.asyncio
class TestPublishData:
    """Test data publishing"""

    async def test_publish_data(self, agent, mock_context_engine):
        """Test publishing data"""
        await agent.publish_data(
            project_id="project-1",
            data_key="analysis_result",
            data={"complexity": 0.75}
        )

        mock_context_engine.publish_data.assert_called_once_with(
            project_id="project-1",
            data_key="analysis_result",
            data={"complexity": 0.75}
        )

    async def test_publish_data_no_context_engine(self, mock_llm):
        """Test publish data without context engine"""
        agent = TestAnalyzer(mock_llm, context_engine=None)

        # Should not raise error
        await agent.publish_data(
            project_id="project-1",
            data_key="key",
            data={"value": 1}
        )

    async def test_publish_data_handles_errors(self, agent, mock_context_engine):
        """Test publish data error handling"""
        mock_context_engine.publish_data.side_effect = Exception("Publish failed")

        # Should not raise error, just log
        await agent.publish_data(
            project_id="project-1",
            data_key="key",
            data={"value": 1}
        )


@pytest.mark.asyncio
class TestRealWorldScenario:
    """Test realistic usage scenarios"""

    async def test_multiple_llm_calls_same_project(self, agent, mock_llm, mock_context_engine):
        """Test multiple LLM calls for same project"""
        mock_context_engine.get_agent_context.return_value = {
            "data_keys": ["tech_stack"]
        }

        # First call
        await agent.llm_call("Task 1", "project-1")

        # Second call (should use cached registration)
        await agent.llm_call("Task 2", "project-1")

        # Third call
        await agent.llm_call("Task 3", "project-1")

        # Should only register once
        assert mock_context_engine.register_agent.call_count == 1

        # Should fetch context 3 times
        assert mock_context_engine.get_agent_context.call_count == 3

        # Should make 3 LLM calls
        assert mock_llm.chat_completion.call_count == 3

    async def test_agent_workflow_with_publish(self, agent, mock_llm, mock_context_engine):
        """Test complete agent workflow"""
        mock_context_engine.get_agent_context.return_value = {
            "data_keys": ["tech_stack"],
            "needs": ["languages"]
        }

        # Analyze task
        result = await agent.llm_call("Analyze task", "project-1")
        assert result == "LLM response"

        # Publish results
        await agent.publish_data(
            project_id="project-1",
            data_key="analysis",
            data={"result": "done"}
        )

        # Verify workflow
        assert mock_context_engine.register_agent.call_count == 1
        assert mock_context_engine.get_agent_context.call_count == 1
        assert mock_context_engine.publish_data.call_count == 1
        assert mock_llm.chat_completion.call_count == 1

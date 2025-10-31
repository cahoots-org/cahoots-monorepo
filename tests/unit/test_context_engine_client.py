"""Unit tests for Context Engine HTTP client"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis

from app.services.context_engine_client import (
    ContextEngineClient,
    initialize_context_engine,
    shutdown_context_engine,
    get_context_engine_client
)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock(spec=Redis)
    redis.pubsub = MagicMock()
    return redis


@pytest.fixture
def client(mock_redis):
    """Create ContextEngineClient instance"""
    return ContextEngineClient(
        base_url="http://test-engine:8001",
        redis_client=mock_redis
    )


@pytest.mark.asyncio
class TestContextEngineClient:
    """Test ContextEngineClient HTTP operations"""

    async def test_initialization(self, mock_redis):
        """Test client initialization"""
        client = ContextEngineClient(
            base_url="http://custom:9000",
            redis_client=mock_redis
        )

        assert client.base_url == "http://custom:9000"
        assert client.redis == mock_redis
        assert client._http_client is None
        assert client.registered_agents == {}

    async def test_initialization_defaults(self):
        """Test client initialization with defaults"""
        with patch.dict('os.environ', {'CONTEXT_ENGINE_URL': 'http://env-engine:8002'}):
            client = ContextEngineClient()
            assert client.base_url == "http://env-engine:8002"

    async def test_get_client_creates_http_client(self, client):
        """Test HTTP client is created on first use"""
        assert client._http_client is None

        http_client = await client._get_client()

        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        assert client._http_client is http_client

    async def test_get_client_reuses_existing(self, client):
        """Test HTTP client is reused"""
        first = await client._get_client()
        second = await client._get_client()

        assert first is second

    async def test_close_http_client(self, client):
        """Test closing HTTP client"""
        http_client = await client._get_client()
        assert client._http_client is not None

        await client.close()

        assert client._http_client is None

    @patch('httpx.AsyncClient.get')
    async def test_health_check_success(self, mock_get, client):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = await client.health_check()

        assert result is True
        mock_get.assert_called_once_with("http://test-engine:8001/")

    @patch('httpx.AsyncClient.get')
    async def test_health_check_failure(self, mock_get, client):
        """Test failed health check"""
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        result = await client.health_check()

        assert result is False

    @patch('httpx.AsyncClient.post')
    async def test_publish_data(self, mock_post, client):
        """Test publishing data to Context Engine"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "published",
            "sequence": "123"
        }
        mock_post.return_value = mock_response

        sequence = await client.publish_data(
            project_id="test-proj",
            data_key="tech_stack",
            data={"backend": "Python", "frontend": "React"}
        )

        assert sequence == "123"
        mock_post.assert_called_once()

        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-engine:8001/data/publish"
        assert call_args[1]['json']['project_id'] == "test-proj"
        assert call_args[1]['json']['data_key'] == "tech_stack"
        assert call_args[1]['json']['data']['backend'] == "Python"

    @patch('httpx.AsyncClient.post')
    async def test_publish_data_with_event_type(self, mock_post, client):
        """Test publishing data with custom event type"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "published", "sequence": "456"}
        mock_post.return_value = mock_response

        await client.publish_data(
            project_id="proj",
            data_key="key",
            data={"value": 1},
            event_type="CustomEvent"
        )

        call_args = mock_post.call_args
        assert call_args[1]['json']['event_type'] == "CustomEvent"

    @patch('httpx.AsyncClient.post')
    async def test_publish_data_http_error(self, mock_post, client):
        """Test publish data handles HTTP errors"""
        mock_post.side_effect = httpx.HTTPError("Server error")

        with pytest.raises(httpx.HTTPError):
            await client.publish_data(
                project_id="proj",
                data_key="key",
                data={"value": 1}
            )

    @patch('httpx.AsyncClient.post')
    async def test_register_agent(self, mock_post, client):
        """Test agent registration"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "agent_id": "test-agent",
            "notification_channel": "agent:test-agent:updates",
            "matched_needs": {"need1": 2, "need2": 1},
            "caught_up_events": 5
        }
        mock_post.return_value = mock_response

        result = await client.register_agent(
            agent_id="test-agent",
            project_id="test-proj",
            data_needs=["need1", "need2"],
            last_seen_sequence="0"
        )

        assert result['agent_id'] == "test-agent"
        assert result['notification_channel'] == "agent:test-agent:updates"
        assert result['matched_needs'] == {"need1": 2, "need2": 1}
        assert result['caught_up_events'] == 5

        # Check agent was registered locally
        assert client.registered_agents["test-agent"] == "agent:test-agent:updates"

        # Verify request
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-engine:8001/agents/register"
        assert call_args[1]['json']['agent_id'] == "test-agent"
        assert call_args[1]['json']['data_needs'] == ["need1", "need2"]

    @patch('httpx.AsyncClient.post')
    async def test_register_agent_with_notification_channel(self, mock_post, client):
        """Test agent registration with custom notification channel"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "agent_id": "agent",
            "notification_channel": "custom:channel",
            "matched_needs": {},
            "caught_up_events": 0
        }
        mock_post.return_value = mock_response

        await client.register_agent(
            agent_id="agent",
            project_id="proj",
            data_needs=[],
            notification_channel="custom:channel"
        )

        call_args = mock_post.call_args
        assert call_args[1]['json']['notification_channel'] == "custom:channel"

    @patch('httpx.AsyncClient.post')
    async def test_register_agent_http_error(self, mock_post, client):
        """Test agent registration handles HTTP errors"""
        mock_post.side_effect = httpx.HTTPError("Registration failed")

        with pytest.raises(httpx.HTTPError):
            await client.register_agent(
                agent_id="agent",
                project_id="proj",
                data_needs=[]
            )

    @patch('httpx.AsyncClient.get')
    async def test_get_agent_context(self, mock_get, client):
        """Test getting agent context"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data_keys": ["tech_stack", "event_model"],
            "needs": ["languages", "events"]
        }
        mock_get.return_value = mock_response

        context = await client.get_agent_context(
            agent_id="test-agent",
            project_id="test-proj"
        )

        assert context is not None
        assert context['data_keys'] == ["tech_stack", "event_model"]
        assert context['needs'] == ["languages", "events"]

        mock_get.assert_called_once_with(
            "http://test-engine:8001/agents/test-agent"
        )

    @patch('httpx.AsyncClient.get')
    async def test_get_agent_context_not_found(self, mock_get, client):
        """Test getting context for non-existent agent"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        context = await client.get_agent_context(
            agent_id="missing-agent",
            project_id="proj"
        )

        assert context is None

    @patch('httpx.AsyncClient.get')
    async def test_get_agent_context_http_error(self, mock_get, client):
        """Test get agent context handles HTTP errors"""
        mock_get.side_effect = httpx.HTTPError("Server error")

        context = await client.get_agent_context(
            agent_id="agent",
            project_id="proj"
        )

        assert context is None

    async def test_subscribe_to_updates_no_redis(self):
        """Test subscribe fails gracefully without Redis"""
        client = ContextEngineClient(redis_client=None)

        callback = AsyncMock()
        await client.subscribe_to_updates("agent", callback)

        # Should not raise error, just log warning
        callback.assert_not_called()

    async def test_subscribe_to_updates_not_registered(self, client):
        """Test subscribe fails if agent not registered"""
        callback = AsyncMock()
        await client.subscribe_to_updates("unregistered-agent", callback)

        # Should not raise error, just log warning
        callback.assert_not_called()


@pytest.mark.asyncio
class TestContextEngineGlobalFunctions:
    """Test global context engine functions"""

    async def test_initialize_context_engine(self, mock_redis):
        """Test global initialization"""
        # Reset global state
        import app.services.context_engine_client as module
        module._context_engine_client = None

        with patch.object(ContextEngineClient, 'health_check', return_value=True):
            client = await initialize_context_engine(redis_client=mock_redis)

            assert client is not None
            assert isinstance(client, ContextEngineClient)
            assert client.redis == mock_redis

    async def test_initialize_context_engine_already_initialized(self, mock_redis):
        """Test initialization returns existing instance"""
        import app.services.context_engine_client as module

        first = ContextEngineClient(redis_client=mock_redis)
        module._context_engine_client = first

        second = await initialize_context_engine(redis_client=mock_redis)

        assert first is second

    async def test_get_context_engine_client(self):
        """Test getting global client"""
        import app.services.context_engine_client as module

        test_client = ContextEngineClient()
        module._context_engine_client = test_client

        result = get_context_engine_client()

        assert result is test_client

    async def test_get_context_engine_client_none(self):
        """Test getting client when not initialized"""
        import app.services.context_engine_client as module
        module._context_engine_client = None

        result = get_context_engine_client()

        assert result is None

    async def test_shutdown_context_engine(self):
        """Test shutting down global client"""
        import app.services.context_engine_client as module

        mock_client = AsyncMock(spec=ContextEngineClient)
        module._context_engine_client = mock_client

        await shutdown_context_engine()

        mock_client.close.assert_called_once()
        assert module._context_engine_client is None

    async def test_shutdown_context_engine_none(self):
        """Test shutdown when no client exists"""
        import app.services.context_engine_client as module
        module._context_engine_client = None

        # Should not raise error
        await shutdown_context_engine()

        assert module._context_engine_client is None

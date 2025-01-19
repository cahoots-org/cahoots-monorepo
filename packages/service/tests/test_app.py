"""Unit tests for FastAPI service."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from service.app import app
from core.models import TeamConfig, AgentConfig

@pytest.fixture
def test_config():
    """Create test team configuration"""
    return TeamConfig(
        project_id="test-project",
        agents={
            "test_agent": AgentConfig(
                name="Test Agent",
                type="test",
                model_name="test-model",
                events={
                    "listen": ["event1"],
                    "publish": ["event2"]
                }
            )
        }
    )

@pytest.fixture
def client(test_config):
    """Create test client"""
    with patch("service.app.TeamConfig.load_from_directory") as mock_load:
        mock_load.return_value = test_config
        with TestClient(app) as client:
            yield client

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_list_agents(client):
    """Test listing agents"""
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "test_agent" in data

def test_get_agent_status(client):
    """Test getting agent status"""
    response = client.get("/agents/test_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "test_agent"
    assert data["status"] == "idle"

def test_get_nonexistent_agent(client):
    """Test getting status of non-existent agent"""
    response = client.get("/agents/nonexistent")
    assert response.status_code == 404

def test_publish_event(client):
    """Test publishing an event"""
    event_data = {
        "task_id": "123",
        "priority": "high"
    }
    
    response = client.post("/events/task_created", json=event_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["event_type"] == "task_created"

def test_publish_event_error(client):
    """Test error handling in event publishing"""
    with patch("service.app.TeamOrchestrator.event_bus.publish") as mock_publish:
        mock_publish.side_effect = Exception("Test error")
        
        response = client.post("/events/test_event", json={})
        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]

def test_metrics(client):
    """Test metrics endpoint"""
    # Generate some metrics
    client.post("/events/test_event", json={})
    client.get("/agents")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    
    assert "agent_metrics" in data
    assert "system_metrics" in data
    assert "event_count" in data["system_metrics"]
    assert "average_latency" in data["system_metrics"]

@pytest.mark.asyncio
async def test_app_lifecycle():
    """Test application lifecycle"""
    with patch("service.app.TeamOrchestrator") as mock_orch:
        # Create mock orchestrator
        mock_instance = Mock()
        mock_orch.return_value = mock_instance
        
        # Test startup
        async with app.router.lifespan_context(app):
            assert hasattr(app.state, "orchestrator")
            mock_instance.start.assert_called_once()
        
        # Test shutdown
        mock_instance.stop.assert_called_once() 
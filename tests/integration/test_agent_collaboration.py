"""Test collaboration between different agent types."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.agents.factory import AgentFactory
from src.utils.event_system import EventSystem
from src.services.github_service import GitHubService

@pytest.fixture
def redis_mock():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.set = AsyncMock()
    mock.delete = MagicMock()
    return mock

@pytest.fixture
def event_system(redis_mock):
    """Create a real event system instance with mocked Redis."""
    system = EventSystem()
    system.redis = redis_mock
    system.is_connected = True  # Skip connection since we're using mocks
    return system

@pytest.fixture
def agent_factory(event_system, mock_github_service, mock_github_config):
    """Create agent factory with real event system."""
    return AgentFactory(
        event_system=event_system,
        github_service=mock_github_service,
        github_config=mock_github_config
    )

@pytest.mark.asyncio
async def test_developer_qa_collaboration(agent_factory):
    """Test collaboration between Developer and QA agents."""
    # Create agents
    developer = agent_factory.create_agent("developer")
    qa_tester = agent_factory.create_agent("qa_tester")
    
    try:
        # Start agents
        await developer.start()
        await qa_tester.start()
        
        # Simulate code review request
        review_request = {
            "story_id": "test-story-1",
            "code_changes": {
                "file": "test.py",
                "diff": "+ def test():\n+     return True"
            }
        }
        
        # Developer submits code for review
        await developer.event_system.publish("code_review_requested", review_request)
        
        # Wait for QA to process
        await asyncio.sleep(1)
        
        # Verify QA received and processed the review
        qa_events = await qa_tester.event_system.get_processed_events()
        assert any(e["type"] == "code_review_requested" for e in qa_events)
        
    finally:
        # Cleanup
        await developer.stop()
        await qa_tester.stop()

@pytest.mark.asyncio
async def test_project_manager_coordination(agent_factory):
    """Test Project Manager's coordination of other agents."""
    # Create agents
    pm = agent_factory.create_agent("project_manager")
    developer = agent_factory.create_agent("developer")
    
    try:
        # Start agents
        await pm.start()
        await developer.start()
        
        # Simulate story assignment
        story = {
            "story_id": "story-1",
            "title": "Test Story",
            "description": "Implement test feature",
            "acceptance_criteria": ["Must have tests", "Must pass QA"]
        }
        
        # PM assigns story
        await pm.event_system.publish("story_assigned", story)
        
        # Wait for developer to process
        await asyncio.sleep(1)
        
        # Verify developer received the story
        dev_events = await developer.event_system.get_processed_events()
        assert any(e["type"] == "story_assigned" for e in dev_events)
        
    finally:
        # Cleanup
        await pm.stop()
        await developer.stop()

@pytest.mark.asyncio
async def test_multi_agent_workflow(agent_factory):
    """Test complete workflow involving multiple agents."""
    # Create all agents
    pm = agent_factory.create_agent("project_manager")
    developer = agent_factory.create_agent("developer")
    qa_tester = agent_factory.create_agent("qa_tester")
    ux_designer = agent_factory.create_agent("ux_designer")
    
    try:
        # Start all agents
        await asyncio.gather(
            pm.start(),
            developer.start(),
            qa_tester.start(),
            ux_designer.start()
        )
        
        # Simulate complete workflow
        story = {
            "story_id": "story-2",
            "title": "Feature with UI",
            "description": "Implement feature with UI component",
            "acceptance_criteria": ["UI must be responsive", "Must pass tests"]
        }
        
        # 1. PM assigns story
        await pm.event_system.publish("story_assigned", story)
        
        # 2. UX Designer creates design
        design = {
            "story_id": "story-2",
            "wireframes": ["button.svg"],
            "specs": {"color": "#000", "size": "2em"}
        }
        await ux_designer.event_system.publish("design_completed", design)
        
        # 3. Developer implements
        implementation = {
            "story_id": "story-2",
            "code_changes": {
                "file": "ui.py",
                "diff": "+ class Button:\n+     pass"
            }
        }
        await developer.event_system.publish("implementation_completed", implementation)
        
        # 4. QA reviews
        await qa_tester.event_system.publish("qa_review_completed", {
            "story_id": "story-2",
            "status": "passed",
            "comments": []
        })
        
        # Wait for all events to process
        await asyncio.sleep(1)
        
        # Verify each agent processed their events
        for agent in [pm, developer, qa_tester, ux_designer]:
            events = await agent.event_system.get_processed_events()
            assert len(events) > 0
            
    finally:
        # Cleanup all agents
        await asyncio.gather(
            pm.stop(),
            developer.stop(),
            qa_tester.stop(),
            ux_designer.stop()
        ) 
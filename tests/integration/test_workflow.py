"""Integration tests for the complete workflow."""
import pytest
import asyncio
from typing import Dict, Any, List, AsyncGenerator
from unittest.mock import AsyncMock, Mock

from src.agents.developer import Developer
from src.agents.project_manager import ProjectManager
from src.agents.tester import Tester
from src.agents.ux_designer import UXDesigner
from src.models.project import Project
from src.models.story import Story
from src.utils.event_system import EventSystem
from src.utils.task_manager import TaskManager

@pytest.fixture
async def workflow_task_manager() -> AsyncGenerator[TaskManager, None]:
    """Create a task manager for workflow tests."""
    manager = TaskManager("workflow")
    yield manager
    await manager.cancel_all()

@pytest.fixture
async def agents(
    event_system: EventSystem,
    workflow_task_manager: TaskManager
) -> AsyncGenerator[Dict[str, Any], None]:
    """Create all agent instances for testing."""
    # Create agents
    pm = ProjectManager(event_system=event_system)
    dev = Developer("test-dev-1", event_system=event_system)
    ux = UXDesigner(event_system=event_system)
    tester = Tester(event_system=event_system)
    
    # Set task manager
    for agent in [pm, dev, ux, tester]:
        agent._task_manager = workflow_task_manager
    
    # Setup events
    await pm.setup_events()
    await dev.setup_events()
    await ux.setup_events()
    await tester.setup_events()
    
    yield {
        "pm": pm,
        "dev": dev,
        "ux": ux,
        "tester": tester
    }
    
    # Cleanup is handled by workflow_task_manager fixture

@pytest.mark.timeout(30)
async def test_complete_workflow(
    agents: Dict[str, Any],
    event_system: EventSystem,
    workflow_task_manager: TaskManager
) -> None:
    """Test complete workflow from project creation to completion.
    
    Verifies:
    1. Project creation and planning
    2. Story assignment and implementation
    3. Design creation and review
    4. Testing and validation
    5. Event system coordination
    """
    pm = agents["pm"]
    dev = agents["dev"]
    ux = agents["ux"]
    tester = agents["tester"]
    
    # Create project
    project_description = "Create a user authentication system with profile management"
    roadmap = await pm.create_roadmap(project_description)
    stories = await pm.create_stories(project_description)
    
    # Verify project creation
    assert len(roadmap["tasks"]) > 0
    assert len(stories) > 0
    
    # Process each story
    for story in stories:
        # Assign story
        assignee = pm.assign_story(story)
        story.assigned_to = assignee
        
        # Publish story assignment
        await event_system.publish("story_assigned", {
            "story_id": story.id,
            "title": story.title,
            "description": story.description,
            "assigned_to": assignee,
            "repo_url": "https://github.com/org/repo"
        })
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify agent responses
        events = []
        while True:
            msg = await event_system.get_message()
            if not msg:
                break
            events.append(msg)
        
        # Verify event flow
        event_types = [e.get("type") for e in events if isinstance(e, dict)]
        if "ui" in story.title.lower():
            assert "design_completed" in event_types
        elif "test" in story.title.lower():
            assert "tests_completed" in event_types
        else:
            assert "implementation_completed" in event_types
            assert "pr_created" in event_types

@pytest.mark.timeout(20)
async def test_error_handling(
    agents: Dict[str, Any],
    event_system: EventSystem,
    workflow_task_manager: TaskManager
) -> None:
    """Test error handling in the workflow.
    
    Verifies:
    1. Invalid project handling
    2. Missing field handling
    3. Service failure handling
    4. Event system error recovery
    """
    pm = agents["pm"]
    dev = agents["dev"]
    
    # Test invalid project
    with pytest.raises(ValueError):
        await pm.create_roadmap("")
    
    # Test missing fields in story assignment
    await event_system.publish("story_assigned", {
        "story_id": "story-1"  # Missing required fields
    })
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify no actions taken
    events = []
    while True:
        msg = await event_system.get_message()
        if not msg:
            break
        events.append(msg)
    
    assert not any(e.get("type") == "implementation_completed" for e in events if isinstance(e, dict))
    
    # Test service failure
    dev.github.clone_repository = AsyncMock(side_effect=Exception("GitHub error"))
    
    await event_system.publish("story_assigned", {
        "story_id": "story-1",
        "title": "Test Story",
        "description": "Test description",
        "assigned_to": dev.developer_id,
        "repo_url": "https://github.com/org/repo"
    })
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify error handling
    events = []
    while True:
        msg = await event_system.get_message()
        if not msg:
            break
        events.append(msg)
    
    error_events = [e for e in events if isinstance(e, dict) and e.get("status") == "error"]
    assert len(error_events) > 0

@pytest.mark.timeout(20)
async def test_concurrent_stories(
    agents: Dict[str, Any],
    event_system: EventSystem,
    workflow_task_manager: TaskManager
) -> None:
    """Test handling of concurrent story assignments.
    
    Verifies:
    1. Concurrent story processing
    2. Resource management
    3. Event ordering
    4. System stability
    """
    pm = agents["pm"]
    dev = agents["dev"]
    ux = agents["ux"]
    tester = agents["tester"]
    
    # Create multiple stories
    stories = [
        Story(
            id=f"story-{i}",
            title=f"Test Story {i}",
            description=f"Test description {i}",
            assigned_to=None,
            status="todo"
        )
        for i in range(3)
    ]
    
    # Assign stories concurrently
    tasks = []
    for story in stories:
        assignee = pm.assign_story(story)
        story.assigned_to = assignee
        
        task = event_system.publish("story_assigned", {
            "story_id": story.id,
            "title": story.title,
            "description": story.description,
            "assigned_to": assignee,
            "repo_url": "https://github.com/org/repo"
        })
        tasks.append(task)
    
    # Wait for all assignments
    await asyncio.gather(*tasks)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Collect all events
    events = []
    while True:
        msg = await event_system.get_message()
        if not msg:
            break
        events.append(msg)
    
    # Verify all stories were processed
    story_ids = {s.id for s in stories}
    processed_ids = {
        e.get("story_id")
        for e in events
        if isinstance(e, dict) and "story_id" in e
    }
    
    assert story_ids.issubset(processed_ids)
    
    # Verify no duplicate processing
    completion_events = [
        e for e in events
        if isinstance(e, dict) and e.get("type") in [
            "implementation_completed",
            "design_completed",
            "tests_completed"
        ]
    ]
    completion_ids = [e.get("story_id") for e in completion_events]
    assert len(completion_ids) == len(set(completion_ids)) 
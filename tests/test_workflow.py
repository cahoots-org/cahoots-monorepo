"""Test the complete development workflow."""
import pytest
import asyncio
from typing import Dict, Any
from src.agents.developer import Developer
from src.agents.project_manager import ProjectManager
from src.agents.tester import Tester
from src.agents.ux_designer import UXDesigner
from src.models.task import Task
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_complete_workflow(
    developer: Developer,
    project_manager: ProjectManager,
    tester: Tester,
    ux_designer: UXDesigner,
    mock_event_system: AsyncMock
):
    """Test the complete development workflow from story to implementation."""
    # Configure mock
    mock_event_system.is_connected.return_value = True
    mock_event_system.verify_connection.return_value = True
    mock_event_system.publish.return_value = None
    
    # Test story for implementing a simple API endpoint
    story = {
        "title": "Implement Health Check Endpoint",
        "description": """
        Create a health check endpoint for the API that:
        - Returns system status and version
        - Checks database connectivity
        - Returns appropriate HTTP status codes
        - Includes basic metrics
        
        Technical Requirements:
        - FastAPI endpoint at /health
        - JSON response with status, version, and timestamps
        - Database connectivity check
        - Response time metrics
        - Proper error handling
        - Unit tests with pytest
        """
    }
    
    # Step 1: Project Manager creates roadmap
    roadmap = await project_manager.create_roadmap(story)
    assert roadmap is not None
    assert "tasks" in roadmap
    
    # Step 2: Developer breaks down story
    tasks = await developer.break_down_story(story)
    assert len(tasks) > 0
    assert all(isinstance(task, Task) for task in tasks)
    
    # Validate task breakdown
    setup_tasks = [t for t in tasks if t.metadata["type"] == "setup"]
    impl_tasks = [t for t in tasks if t.metadata["type"] == "implementation"]
    test_tasks = [t for t in tasks if t.metadata["type"] == "testing"]
    
    assert len(setup_tasks) > 0, "Should have setup tasks"
    assert len(impl_tasks) > 0, "Should have implementation tasks"
    assert len(test_tasks) > 0, "Should have testing tasks"
    
    # Step 3: Developer implements tasks
    implementation_results = await developer.implement_tasks(tasks)
    assert "implementations" in implementation_results
    assert len(implementation_results["implementations"]) > 0
    assert len(implementation_results.get("failed_tasks", [])) == 0
    
    # Step 4: Create pull request
    pr_url = await developer.create_pr(implementation_results)
    assert pr_url is not None and isinstance(pr_url, str)
    
    # Step 5: Tester reviews implementation
    test_results = await tester.test_implementation(pr_url)
    assert test_results["passed"] is True
    assert test_results["coverage_percentage"] >= 80
    
    # Step 6: Project Manager reviews and approves
    review_result = await project_manager.review_implementation(pr_url)
    assert review_result["approved"] is True
    
    # Validate the complete workflow
    assert all([
        len(tasks) > 0,
        len(implementation_results["implementations"]) > 0,
        test_results["passed"],
        review_result["approved"]
    ]), "Complete workflow should succeed" 
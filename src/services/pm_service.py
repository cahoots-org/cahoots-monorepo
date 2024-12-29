from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import asyncio
from src.services.trello_service import TrelloService
from src.services.github_service import GitHubService
from src.utils.event_system import EventSystem, CHANNELS

# Initialize services
trello_service = TrelloService()
github_service = GitHubService()
event_system = EventSystem()

if not os.getenv("TRELLO_API_KEY") or not os.getenv("TRELLO_API_SECRET"):
    raise RuntimeError("TRELLO_API_KEY and TRELLO_API_SECRET environment variables are required")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize event system and subscribe to channels"""
    await event_system.connect()
    await event_system.subscribe(CHANNELS["PR_MERGED"], handle_pr_merged)
    asyncio.create_task(event_system.start_listening())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up event system"""
    await event_system.stop()

async def handle_pr_merged(data: dict):
    """Handle PR merged event"""
    try:
        # Update Trello card status
        trello_service.update_card(
            data["story_id"],
            None,  # Don't update title
            None,  # Don't update description
            "Done"  # Move to Done list
        )
    except Exception as e:
        app.logger.error(f"Failed to handle PR merged event: {str(e)}")

def generate_unique_name(name: str) -> str:
    """Generate a unique name by appending a random identifier"""
    # Generate a short UUID (first 8 characters)
    unique_id = str(uuid.uuid4())[:8]
    # Replace spaces with hyphens and append unique ID
    base_name = name.replace(" ", "-")
    return f"{base_name}-{unique_id}"

class Story(BaseModel):
    id: str
    title: str
    description: str
    status: str = "TODO"
    tasks: List[dict] = []
    assigned_to: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: str
    stories: List[Story] = []
    repo_url: Optional[str] = None

async def assign_story_to_developer(story: Story) -> str:
    """Assign a story to an available developer"""
    # For now, just alternate between two developers
    if story.title.lower().startswith(('ui', 'user interface')):
        return "ux_designer"
    elif "test" in story.title.lower():
        return "tester"
    else:
        # Round-robin between developers
        return f"developer_{hash(story.id) % 2 + 1}"

async def notify_developer(developer_id: str, story: Story, repo_url: str):
    """Notify developer about new story assignment"""
    try:
        # Map developer IDs to service names
        service_names = {
            "developer_1": "developer-1",
            "developer_2": "developer-2",
            "ux_designer": "ux-designer",
            "tester": "tester"
        }
        
        service = service_names.get(developer_id)
        if not service:
            raise ValueError(f"Unknown developer ID: {developer_id}")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{service}:8002/tasks/assign",
                json={
                    "story_id": story.id,
                    "title": story.title,
                    "description": story.description,
                    "repo_url": repo_url
                },
                timeout=30.0  # Add timeout to prevent hanging
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Failed to notify developer {developer_id}: {str(e)}")
        return None

def generate_stories_from_description(project_id: str, description: str) -> List[Story]:
    """Generate stories based on project description"""
    stories = []
    
    # Common story types
    story_types = {
        "setup": {
            "title": "Project Setup",
            "description": "Initialize project structure, configure development environment, and set up CI/CD pipeline."
        },
        "auth": {
            "title": "Authentication System",
            "description": "Implement user authentication and authorization system."
        },
        "api": {
            "title": "API Development",
            "description": "Design and implement core API endpoints."
        },
        "ui": {
            "title": "User Interface",
            "description": "Design and implement the user interface."
        },
        "testing": {
            "title": "Testing Suite",
            "description": "Create comprehensive test suite including unit and integration tests."
        },
        "docs": {
            "title": "Documentation",
            "description": "Create technical documentation and API documentation."
        }
    }
    
    # Add relevant stories based on description keywords
    story_id = 1
    for key, story_type in story_types.items():
        if any(keyword in description.lower() for keyword in [key, story_type["title"].lower()]):
            stories.append(Story(
                id=f"{project_id}-story-{story_id}",
                title=story_type["title"],
                description=story_type["description"]
            ))
            story_id += 1
    
    # If no stories were created, add a default story
    if not stories:
        stories.append(Story(
            id=f"{project_id}-story-1",
            title="Initial Implementation",
            description="Implement the core functionality of the project."
        ))
    
    return stories

@app.get("/health")
async def health_check():
    return {"status": "healthy", "trello": "connected", "github": "connected"}

@app.post("/projects")
async def create_project(project: Project):
    try:
        # Create GitHub repository with initial structure using unique name
        unique_repo_name = generate_unique_name(project.name)
        repo_url = github_service.create_repository(unique_repo_name, project.description)
        project.repo_url = repo_url
        
        # Create Trello board with original name
        board_id = trello_service.create_board(project.name, project.description)
        
        # Create default lists
        trello_service.create_list(board_id, "Backlog")
        trello_service.create_list(board_id, "In Progress")
        trello_service.create_list(board_id, "Review")
        trello_service.create_list(board_id, "Testing")
        trello_service.create_list(board_id, "Done")
        
        # Generate stories based on project description
        stories = generate_stories_from_description(project.id, project.description)
        project.stories = stories
        
        # Create Trello cards and assign developers
        for story in stories:
            card_id = trello_service.create_card(
                story.title,
                story.description,
                board_id,
                "Backlog"
            )
            story.id = card_id  # Update story ID to match Trello card ID
            
            # Assign story to developer
            story.assigned_to = await assign_story_to_developer(story)
            
            # Notify developer through event system
            await event_system.publish(CHANNELS["STORY_ASSIGNED"], {
                "story_id": story.id,
                "title": story.title,
                "description": story.description,
                "repo_url": repo_url,
                "assigned_to": story.assigned_to
            })
        
        return {
            "message": "Project created successfully",
            "project": project.dict(),
            "board_id": board_id,
            "repo_url": repo_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/stories")
async def create_story(project_id: str, story: Story):
    try:
        # Add story to Trello board
        card_id = trello_service.create_card(
            story.title,
            story.description,
            project_id,  # Using project_id as board_id
            "Backlog"  # Add to backlog by default
        )
        
        return {
            "message": "Story created successfully",
            "story": story.dict(),
            "card_id": card_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/stories/{story_id}")
async def get_story(project_id: str, story_id: str):
    try:
        # Get story details from Trello
        card = trello_service.get_card(story_id)
        
        story = Story(
            id=card["id"],
            title=card["name"],
            description=card["desc"],
            status=card["list"]["name"],
            tasks=[]  # Tasks would be checklist items in Trello
        )
        
        return {"message": "Story retrieved", "story": story.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/projects/{project_id}/stories/{story_id}")
async def update_story(project_id: str, story_id: str, story: Story):
    try:
        # Update story in Trello
        trello_service.update_card(
            story_id,
            story.title,
            story.description,
            story.status
        )
        
        return {"message": "Story updated", "story": story.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
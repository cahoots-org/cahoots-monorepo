from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import asyncio
from src.services.github_service import GitHubService
from src.utils.config import Config
from src.utils.event_system import EventSystem, CHANNELS

# Initialize services
config = Config()
github_service = GitHubService()
event_system = EventSystem()
developer_id = os.getenv("DEVELOPER_ID")

app = FastAPI()

class Task(BaseModel):
    id: str
    title: str
    description: str
    code: Optional[str] = None
    status: str = "TODO"

class StoryAssignment(BaseModel):
    story_id: str
    title: str
    description: str
    repo_url: str

class CodeImplementation(BaseModel):
    code: str
    description: str = ""

class StoryBreakdown(BaseModel):
    description: str

@app.on_event("startup")
async def startup_event():
    """Initialize event system and subscribe to channels"""
    await event_system.connect()
    await event_system.subscribe(CHANNELS["STORY_ASSIGNED"], handle_story_assigned)
    asyncio.create_task(event_system.start_listening())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up event system"""
    await event_system.stop()

async def handle_story_assigned(data: Dict):
    """Handle story assignment event"""
    if data.get("assigned_to") != developer_id:
        return
        
    try:
        # Extract repository name from URL
        repo_name = data["repo_url"].split('/')[-1].replace('.git', '')
        
        # Create a feature branch for the story
        branch_name = f"feature/{data['story_id']}"
        github_service.create_branch(repo_name, branch_name)
        
        # Break down story into tasks
        tasks = await break_down_story_internal(data["description"])
        
        # Create initial implementation structure
        initial_files = generate_initial_structure(data["title"], tasks)
        
        # Commit initial structure to feature branch and create PR
        pr_url = github_service.commit_changes(
            repo_name,
            branch_name,
            initial_files,
            f"Initial structure for {data['title']}"
        )
        
        # Extract PR number
        try:
            pr_number = github_service.get_pull_request_number(pr_url)
            
            # Automatically implement and merge the PR
            success = github_service.merge_pull_request(repo_name, pr_number)
            
            if success:
                # Publish PR merged event
                await event_system.publish(CHANNELS["PR_MERGED"], {
                    "story_id": data["story_id"],
                    "pr_number": pr_number,
                    "repo_name": repo_name,
                    "developer_id": developer_id
                })
            
        except ValueError as e:
            app.logger.error(f"Failed to process PR: {str(e)}")
            
    except Exception as e:
        app.logger.error(f"Failed to handle story assignment: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "github": "connected"}

async def break_down_story_internal(description: str) -> List[dict]:
    """Break down a story into specific tasks"""
    if "authentication" in description.lower():
        return [
            {"id": "1", "title": "Set up user model and database", "description": "Create user model with necessary fields"},
            {"id": "2", "title": "Implement authentication endpoints", "description": "Create login/register endpoints"},
            {"id": "3", "title": "Add JWT token handling", "description": "Implement JWT token generation and validation"}
        ]
    elif "api" in description.lower():
        return [
            {"id": "1", "title": "Define API endpoints", "description": "Create OpenAPI specification"},
            {"id": "2", "title": "Implement CRUD operations", "description": "Create basic CRUD endpoints"},
            {"id": "3", "title": "Add input validation", "description": "Implement request validation"}
        ]
    elif "ui" in description.lower():
        return [
            {"id": "1", "title": "Create base components", "description": "Implement reusable UI components"},
            {"id": "2", "title": "Implement layouts", "description": "Create page layouts and navigation"},
            {"id": "3", "title": "Add styling", "description": "Implement CSS and themes"}
        ]
    else:
        return [
            {"id": "1", "title": "Initial setup", "description": "Set up basic structure"},
            {"id": "2", "title": "Core implementation", "description": "Implement main functionality"}
        ]

def generate_initial_structure(title: str, tasks: List[dict]) -> Dict[str, str]:
    """Generate initial file structure based on story type"""
    if "authentication" in title.lower():
        return {
            "src/auth/__init__.py": "",
            "src/auth/models.py": generate_auth_model(),
            "src/auth/routes.py": generate_auth_routes(),
            "tests/test_auth.py": generate_auth_tests()
        }
    elif "api" in title.lower():
        return {
            "src/api/__init__.py": "",
            "src/api/routes.py": generate_api_routes(),
            "src/api/models.py": generate_api_models(),
            "tests/test_api.py": generate_api_tests()
        }
    elif "ui" in title.lower():
        return {
            "src/ui/__init__.py": "",
            "src/ui/components.py": generate_ui_components(),
            "src/ui/templates/base.html": generate_base_template(),
            "tests/test_ui.py": generate_ui_tests()
        }
    else:
        return {
            f"src/{title.lower().replace(' ', '_')}/__init__.py": "",
            f"src/{title.lower().replace(' ', '_')}/main.py": "# TODO: Implement main functionality",
            f"tests/test_{title.lower().replace(' ', '_')}.py": generate_basic_tests()
        }

def generate_auth_model() -> str:
    return """from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
"""

def generate_auth_routes() -> str:
    return """from fastapi import APIRouter, Depends, HTTPException
from .models import User

router = APIRouter()

@router.post("/register")
async def register():
    # TODO: Implement user registration
    pass

@router.post("/login")
async def login():
    # TODO: Implement user login
    pass
"""

def generate_auth_tests() -> str:
    return """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register():
    # TODO: Implement registration tests
    pass

def test_login():
    # TODO: Implement login tests
    pass
"""

def generate_api_routes() -> str:
    return """from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
async def get_items():
    # TODO: Implement get items
    pass

@router.post("/items")
async def create_item():
    # TODO: Implement create item
    pass
"""

def generate_api_models() -> str:
    return """from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    description: str
"""

def generate_api_tests() -> str:
    return """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_items():
    # TODO: Implement get items test
    pass

def test_create_item():
    # TODO: Implement create item test
    pass
"""

def generate_ui_components() -> str:
    return """from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

def render_page(request: Request, template: str, context: dict = None):
    if context is None:
        context = {}
    return templates.TemplateResponse(template, {"request": request, **context})
"""

def generate_base_template() -> str:
    return """<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='style.css') }}">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
"""

def generate_ui_tests() -> str:
    return """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_page_render():
    # TODO: Implement UI tests
    pass
"""

def generate_basic_tests() -> str:
    return """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_functionality():
    # TODO: Implement tests
    pass
"""

@app.post("/tasks/{task_id}/implement")
async def implement_task(task_id: str, implementation: CodeImplementation = None):
    try:
        # Extract repository name and PR number from task context
        repo_name = task_id.split('/')[0]  # Assuming task_id format: repo_name/pr_number
        pr_number = int(task_id.split('/')[1])
        
        # Here we would implement the task and update the PR
        # For now, we'll just merge the PR
        success = github_service.merge_pull_request(repo_name, pr_number)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to merge pull request")
        
        return {
            "message": "Task implemented and PR merged successfully",
            "task_id": task_id,
            "implementation": implementation.dict() if implementation else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    try:
        return {
            "message": "Task status retrieved",
            "task_id": task_id,
            "status": "IN_PROGRESS"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/breakdown")
async def break_down_story(story: StoryBreakdown):
    try:
        tasks = await break_down_story_internal(story.description)
        return {"message": "Story broken down into tasks", "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
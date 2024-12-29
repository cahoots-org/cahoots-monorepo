# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os

app = FastAPI()

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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/projects")
async def create_project(project: Project):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://pm:8001/projects",
                json=project.dict(),
                timeout=60.0  # Increase timeout for project creation
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/stories/{story_id}")
async def get_story(project_id: str, story_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://pm:8001/projects/{project_id}/stories/{story_id}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
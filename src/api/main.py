# src/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.utils.logger import Logger
from src.utils.event_system import EventSystem, CHANNELS
import sys
import asyncio
import json

logger = Logger("API")
event_system = EventSystem()

class Project(BaseModel):
    id: str
    name: str
    description: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app"""
    # Startup
    logger.info("Connecting to Redis")
    await event_system.connect()
    logger.info("Redis connection established")
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    logger.info("Health check requested")
    return {"status": "healthy"}

@app.post("/projects")
async def create_project(project: Project):
    """Create a new project by sending a message to the project manager through Redis."""
    try:
        logger.info(f"Received project creation request: {project.name}")
        logger.info(f"Project details: id={project.id}, description length={len(project.description)}")
        
        # Send message to project manager through Redis
        message = {
            "type": "new_project",
            "project_name": project.name,
            "description": project.description,
            "project_id": project.id
        }
        
        logger.info("Publishing message to project manager")
        await event_system.publish("project_manager", message)
        
        # TODO: Implement response handling through Redis
        # For now, return a simple acknowledgment
        return {"status": "success", "message": "Project creation request sent to project manager"}
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {sys.exc_info()[2]}")
        raise HTTPException(status_code=500, detail=str(e))
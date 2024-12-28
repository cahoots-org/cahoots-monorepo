# src/api/main.py
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
from ..models.project import Project
from ..utils.logger import Logger
import httpx

app = FastAPI()
config.load_incluster_config()
k8s_api = client.CoreV1Api()
logger = Logger("MasterService")

@app.post("/projects/")
async def create_project(project: Project):
    logger.info(f"New project request received: {project.name}")
    
    try:
        # Forward to PM service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://pm-service:8001/process",
                json={"type": "new_project", "project": project.to_dict()}
            )
            
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="PM service error")
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error processing project request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    logger.info(f"Status request for project: {project_id}")
    
    try:
        # Implementation for status check
        pass
        
    except Exception as e:
        logger.error(f"Error checking project status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
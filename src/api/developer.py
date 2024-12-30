from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.developer import Developer

app = FastAPI()
developer = Developer()

class Task(BaseModel):
    id: str
    title: str
    description: str
    status: str = "TODO"

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/tasks")
async def implement_task(task: Task):
    try:
        result = developer.process_message({
            "type": "implement_task",
            "task": task.dict()
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to implement task"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review")
async def review_code(pr_url: str):
    try:
        result = developer.process_message({
            "type": "review_code",
            "pr_url": pr_url
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to review code"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
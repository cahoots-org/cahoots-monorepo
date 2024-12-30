from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.ux_designer import UXDesigner

app = FastAPI()
designer = UXDesigner()

class DesignRequest(BaseModel):
    id: str
    title: str
    description: str
    requirements: List[str]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/design")
async def create_design(request: DesignRequest):
    try:
        result = designer.process_message({
            "type": "create_design",
            "request": request.dict()
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to create design"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review")
async def review_design(design_url: str):
    try:
        result = designer.process_message({
            "type": "review_design",
            "design_url": design_url
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to review design"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
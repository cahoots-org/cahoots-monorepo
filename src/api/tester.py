from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.tester import Tester

app = FastAPI()
tester = Tester()

class TestRequest(BaseModel):
    id: str
    title: str
    description: str
    code_url: str

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/test")
async def create_tests(request: TestRequest):
    try:
        result = tester.process_message({
            "type": "create_tests",
            "request": request.dict()
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to create tests"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
async def run_tests(test_suite_id: str):
    try:
        result = tester.process_message({
            "type": "run_tests",
            "test_suite_id": test_suite_id
        })
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to run tests"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
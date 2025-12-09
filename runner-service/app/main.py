"""
Runner Service - Test execution on Cloud Run Jobs.

Executes code in isolated environments:
- Dispatches jobs to Google Cloud Run
- Supports sidecars for databases and services
- Clones the repo with latest agent changes
- Runs build/test commands
- Streams logs and results back
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, runs

app = FastAPI(
    title="Cahoots Runner Service",
    description="Test execution on Cloud Run Jobs with sidecars",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(runs.router, prefix="/runs", tags=["Runs"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)

"""
Workspace Service - Git-backed file operations for code generation agents.

Provides file operation tools to agents:
- read_file(path) - Read file contents
- write_file(path, content) - Create/overwrite file
- edit_file(path, old, new) - Surgical edit within file
- list_files(path, pattern) - List directory contents
- grep(pattern, path) - Search for code patterns

All write operations automatically commit to the Git repository.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import files, git, health, github

app = FastAPI(
    title="Cahoots Workspace Service",
    description="Git-backed file operations for code generation agents",
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
app.include_router(files.router, prefix="/workspace", tags=["Files"])
app.include_router(git.router, prefix="/workspace", tags=["Git"])
app.include_router(github.router, prefix="/workspace", tags=["GitHub"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

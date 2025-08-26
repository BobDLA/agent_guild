# Subagent Guild - Main Application

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import agents, repositories, downloads, health
from app.web import pages
from config.settings import STATIC_DIR, TEMPLATES_DIR

# Create FastAPI application
app = FastAPI(
    title="Subagent Guild",
    description="Discover, evaluate, and manage Claude Code subagents",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configure templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(repositories.router, prefix="/api/repositories", tags=["repositories"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
app.include_router(health.router, tags=["health"])

# Include web page routers
app.include_router(pages.router, tags=["pages"])

# Basic health endpoint is now handled by the health router

if __name__ == "__main__":
    import uvicorn
    from config.settings import HOST, PORT, DEBUG
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )
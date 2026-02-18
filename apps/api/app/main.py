"""
Newhorse API - FastAPI Application

AI Agent Development Platform based on Claude Agent SDK.
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects_router, chat_router, agents_router, files_router, preview_router, activity_router, skills_router
from app.core import settings, configure_logging, ui
from app.db import Base, engine

logger = logging.getLogger(__name__)

# Configure logging
configure_logging()

# Create FastAPI app
app = FastAPI(
    title="Newhorse API",
    description="AI Agent Development Platform",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(files_router, prefix="/api/projects", tags=["files"])
app.include_router(preview_router, prefix="/api/preview", tags=["preview"])
app.include_router(activity_router, prefix="/api/activity", tags=["activity"])
app.include_router(skills_router, prefix="/api/skills", tags=["skills"])


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "service": "newhorse"}


@app.on_event("startup")
async def on_startup():
    """Application startup handler."""
    # Remove CLAUDECODE env var so Claude Agent SDK subprocess won't refuse to start
    # when the API itself is launched from within a Claude Code session.
    os.environ.pop("CLAUDECODE", None)

    ui.info("Initializing Newhorse API", "Startup")

    # Ensure data directory exists for SQLite database
    if "sqlite" in settings.database_url:
        db_path = settings.database_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            ui.success(f"Database directory: {db_dir}", "Startup")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    ui.success("Database initialized", "Startup")

    # Ensure projects directory exists
    os.makedirs(settings.projects_root, exist_ok=True)
    ui.success(f"Projects root: {settings.projects_root}", "Startup")

    os.makedirs(settings.agents_root, exist_ok=True)
    ui.success(f"Agents root: {settings.agents_root}", "Startup")

    # Show ASCII logo
    ui.ascii_logo()

    # Status line
    ui.status_line({
        "Environment": settings.environment,
        "Port": settings.api_port,
        "Database": "SQLite" if "sqlite" in settings.database_url else "MySQL",
    })

    ui.panel(
        "WebSocket: /api/chat/{project_id}\n"
        "REST API: /api/projects, /api/agents\n"
        "Health: /health",
        title="Available Endpoints",
        style="green"
    )


@app.on_event("shutdown")
async def on_shutdown():
    """Application shutdown handler."""
    ui.info("Shutting down Newhorse API", "Shutdown")
    ui.success("Shutdown complete", "Shutdown")

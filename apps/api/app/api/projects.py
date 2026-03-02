"""
Projects API router
"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.projects import Project
from app.core.config import settings
from app.core.terminal_ui import ui

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    preferred_cli: str = "hello"
    selected_model: str = "claude-sonnet-4-5-20250929"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    selected_model: Optional[str] = None
    override_provider_id: Optional[str] = None
    override_api_key: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    preferred_cli: str
    selected_model: str
    override_provider_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
def list_projects(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """List all projects with pagination."""
    projects = db.query(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit).all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.post("/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project_id = str(uuid.uuid4())[:8]

    # Create project directory
    project_path = os.path.join(settings.projects_root, project_id)
    os.makedirs(project_path, exist_ok=True)

    db_project = Project(
        id=project_id,
        name=project.name,
        description=project.description,
        repo_path=project_path,
        preferred_cli=project.preferred_cli,
        selected_model=project.selected_model,
        status="active",
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    ui.success(f"Created project: {project.name} ({project_id})", "Projects")

    return ProjectResponse.model_validate(db_project)


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}")
def update_project(project_id: str, updates: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project's basic info and sync to agent config."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data = updates.model_dump(exclude_unset=True)

    if updates.name is not None:
        project.name = updates.name
    if updates.description is not None:
        project.description = updates.description
    if updates.selected_model is not None:
        project.selected_model = updates.selected_model
    if "override_provider_id" in data:
        project.override_provider_id = data["override_provider_id"]
    if "override_api_key" in data:
        from app.services.crypto import encrypt_api_key
        raw_key = data["override_api_key"]
        project.override_api_key = encrypt_api_key(raw_key) if raw_key else None

    db.commit()
    db.refresh(project)

    # Sync changes to project's agent.yaml if it exists
    config_path = os.path.join(project.repo_path, ".claude", "agent.yaml")
    if os.path.exists(config_path):
        from app.services.cli.config_loader import load_agent_config, save_project_config
        config = load_agent_config(project.repo_path)
        if updates.name is not None:
            config.name = updates.name
        if updates.description is not None:
            config.description = updates.description
        if updates.selected_model is not None:
            config.model = updates.selected_model
        save_project_config(project.repo_path, config)

    ui.info(f"Updated project: {project_id}", "Projects")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    ui.info(f"Deleted project: {project_id}", "Projects")
    return {"status": "deleted", "id": project_id}

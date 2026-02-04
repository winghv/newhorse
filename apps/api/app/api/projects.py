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


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    preferred_cli: str
    selected_model: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
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

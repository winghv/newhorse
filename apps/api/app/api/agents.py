"""
Agents API router
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.cli import agent_manager
from app.services.cli.config_loader import (
    list_global_templates,
    get_template_config,
    load_agent_config,
    save_project_config,
    save_user_template,
    delete_user_template,
    AgentConfig,
)
from app.core.config import settings
from app.core.terminal_ui import ui

router = APIRouter()


class AgentConfigRequest(BaseModel):
    """Request body for saving agent configuration."""
    name: str
    description: str
    system_prompt: str
    skills: list[str] = []
    model: str = "claude-sonnet-4-5-20250929"
    allowed_tools: list[str] = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]


@router.get("/")
def list_agents():
    """List available agents."""
    return agent_manager.get_available_agents()


@router.get("/{agent_type}/availability")
async def check_availability(agent_type: str):
    """Check agent availability."""
    from app.common.types import AgentType

    agent_enum = AgentType.from_value(agent_type)
    if not agent_enum:
        return {"available": False, "error": f"Unknown agent type: {agent_type}"}

    return await agent_manager.check_availability(agent_enum)


@router.get("/templates")
def get_templates():
    """List all available agent templates."""
    templates = list_global_templates()
    return {"templates": templates}


@router.get("/templates/{template_id}")
def get_template(template_id: str):
    """Get details of a specific agent template."""
    config = get_template_config(template_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    return {
        "id": template_id,
        "config": config.to_dict(),
        "source": config.config_source,
    }


@router.post("/templates")
def create_template(request: AgentConfigRequest):
    """Create a new user agent template."""
    config = AgentConfig(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        skills=request.skills,
        model=request.model,
        allowed_tools=request.allowed_tools,
        config_source="user",
    )

    template_id = save_user_template(config)
    ui.success(f"Created template: {template_id}", "AgentsAPI")

    return {
        "id": template_id,
        "config": config.to_dict(),
    }


@router.put("/templates/{template_id}")
def update_template(template_id: str, request: AgentConfigRequest):
    """Update an existing user template."""
    existing = get_template_config(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    from pathlib import Path
    from app.core.config import settings
    user_path = Path(settings.agents_root) / template_id
    if not user_path.exists():
        raise HTTPException(status_code=403, detail="Cannot modify builtin templates")

    config = AgentConfig(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        skills=request.skills,
        model=request.model,
        allowed_tools=request.allowed_tools,
        config_source=f"user:{template_id}",
    )

    save_user_template(config, template_id=template_id)
    ui.success(f"Updated template: {template_id}", "AgentsAPI")

    return {
        "id": template_id,
        "config": config.to_dict(),
    }


@router.delete("/templates/{template_id}")
def delete_template(template_id: str):
    """Delete a user-created template."""
    success = delete_user_template(template_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found or is builtin: {template_id}"
        )

    ui.success(f"Deleted template: {template_id}", "AgentsAPI")
    return {"success": True, "id": template_id}


@router.get("/projects/{project_id}/config")
def get_project_agent_config(project_id: str):
    """Get agent configuration for a project."""
    import os
    project_path = os.path.join(settings.projects_root, project_id)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")

    config = load_agent_config(project_path)

    return {
        "project_id": project_id,
        "config": config.to_dict(),
        "source": config.config_source,
    }


@router.post("/projects/{project_id}/config")
def save_project_agent_config(project_id: str, request: AgentConfigRequest):
    """Save agent configuration for a project."""
    import os
    project_path = os.path.join(settings.projects_root, project_id)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")

    config = AgentConfig(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        skills=request.skills,
        model=request.model,
        allowed_tools=request.allowed_tools,
        config_source=f"project:{project_id}",
    )

    success = save_project_config(project_path, config)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration")

    ui.success(f"Agent config saved for project {project_id}", "AgentsAPI")

    return {
        "success": True,
        "project_id": project_id,
        "config": config.to_dict(),
    }


@router.post("/projects/{project_id}/config/from-template")
def apply_template_to_project(project_id: str, template_id: str):
    """Apply a global template to a project."""
    import os
    project_path = os.path.join(settings.projects_root, project_id)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")

    template_config = get_template_config(template_id)
    if not template_config:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    # Update source to indicate it's now a project config
    template_config.config_source = f"project:{project_id}"

    success = save_project_config(project_path, template_config)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to apply template")

    return {
        "success": True,
        "project_id": project_id,
        "template_id": template_id,
        "config": template_config.to_dict(),
    }

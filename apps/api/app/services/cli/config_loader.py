"""
Agent Configuration Loader

Loads agent configuration with priority:
1. Project-level: {project_path}/.claude/agent.yaml
2. Global template: extensions/agents/{agent_type}/agent.yaml
3. Code defaults
"""
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.config import settings
from app.core.terminal_ui import ui


@dataclass
class AgentConfig:
    """Agent configuration data structure."""
    name: str = "Default Agent"
    description: str = "A helpful AI assistant"
    system_prompt: str = "You are a helpful AI assistant."
    skills: List[str] = field(default_factory=list)
    model: str = "claude-sonnet-4-5-20250929"
    allowed_tools: List[str] = field(default_factory=lambda: [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep"
    ])

    # Source tracking for debugging
    config_source: str = "default"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "unknown") -> "AgentConfig":
        """Create AgentConfig from dictionary."""
        return cls(
            name=data.get("name", cls.name),
            description=data.get("description", cls.description),
            system_prompt=data.get("system_prompt", cls.system_prompt),
            skills=data.get("skills", []),
            model=data.get("model", cls.model),
            allowed_tools=data.get("allowed_tools", ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]),
            config_source=source,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "skills": self.skills,
            "model": self.model,
            "allowed_tools": self.allowed_tools,
        }


def _parse_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Parse YAML file safely."""
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        ui.warning(f"Failed to parse {path}: {e}", "ConfigLoader")
    return None


def get_project_config_path(project_path: str) -> Path:
    """Get path to project-level agent config."""
    return Path(project_path) / ".claude" / "agent.yaml"


def get_global_template_path(agent_type: str) -> Path:
    """Get path to agent template config (checks builtin then user dirs)."""
    # Check builtin first
    builtin_path = Path(settings.project_root) / "extensions" / "agents" / agent_type / "agent.yaml"
    if builtin_path.exists():
        return builtin_path

    # Then check user templates
    user_path = Path(settings.agents_root) / agent_type / "agent.yaml"
    if user_path.exists():
        return user_path

    # Return builtin path as default (even if doesn't exist)
    return builtin_path


def load_agent_config(
    project_path: str,
    agent_type: str = "hello",
    default_config: Optional[AgentConfig] = None
) -> AgentConfig:
    """Load agent configuration with priority fallback.

    Priority (highest to lowest):
    1. Project-level: {project_path}/.claude/agent.yaml
    2. Global template: extensions/agents/{agent_type}/agent.yaml
    3. Provided default_config or AgentConfig defaults

    Args:
        project_path: Path to the project directory
        agent_type: Type of agent (maps to template directory)
        default_config: Optional default configuration to use as fallback

    Returns:
        AgentConfig with loaded settings
    """
    # 1. Check project-level config
    project_config_path = get_project_config_path(project_path)
    project_data = _parse_yaml_file(project_config_path)

    if project_data:
        ui.info(f"Loading project config from {project_config_path}", "ConfigLoader")
        return AgentConfig.from_dict(project_data, source=f"project:{project_config_path}")

    # 2. Check global template
    global_config_path = get_global_template_path(agent_type)
    global_data = _parse_yaml_file(global_config_path)

    if global_data:
        ui.info(f"Loading global template from {global_config_path}", "ConfigLoader")
        return AgentConfig.from_dict(global_data, source=f"template:{agent_type}")

    # 3. Return default
    if default_config:
        ui.debug("Using provided default config", "ConfigLoader")
        return default_config

    ui.debug("Using built-in default config", "ConfigLoader")
    return AgentConfig(config_source="default")


def save_project_config(project_path: str, config: AgentConfig) -> bool:
    """Save agent configuration to project-level file.

    Args:
        project_path: Path to the project directory
        config: AgentConfig to save

    Returns:
        True if saved successfully, False otherwise
    """
    config_path = get_project_config_path(project_path)

    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                config.to_dict(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

        ui.success(f"Saved config to {config_path}", "ConfigLoader")
        return True

    except Exception as e:
        ui.error(f"Failed to save config: {e}", "ConfigLoader")
        return False


def save_user_template(config: AgentConfig, template_id: Optional[str] = None) -> str:
    """Save agent config as a user template.

    Args:
        config: AgentConfig to save
        template_id: Optional ID, auto-generated if not provided

    Returns:
        template_id
    """
    if not template_id:
        template_id = str(uuid.uuid4())[:8]

    template_dir = Path(settings.agents_root) / template_id
    template_dir.mkdir(parents=True, exist_ok=True)

    config_path = template_dir / "agent.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(
            config.to_dict(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

    ui.success(f"Saved user template: {template_id}", "ConfigLoader")
    return template_id


def delete_user_template(template_id: str) -> bool:
    """Delete a user-created template.

    Only deletes from data/agents/ (user templates), not builtin templates.

    Args:
        template_id: Template directory name

    Returns:
        True if deleted, False if not found or is builtin
    """
    import shutil

    # Only delete user templates (data/agents/), never builtin (extensions/agents/)
    user_path = Path(settings.agents_root) / template_id
    if not user_path.exists():
        return False

    try:
        shutil.rmtree(user_path)
        ui.success(f"Deleted user template: {template_id}", "ConfigLoader")
        return True
    except Exception as e:
        ui.error(f"Failed to delete template {template_id}: {e}", "ConfigLoader")
        return False


def list_global_templates() -> List[Dict[str, Any]]:
    """List all available agent templates (builtin + user-created)."""
    templates = []

    # Builtin templates: extensions/agents/
    builtin_dir = Path(settings.project_root) / "extensions" / "agents"
    if builtin_dir.exists():
        for agent_dir in builtin_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            config_path = agent_dir / "agent.yaml"
            data = _parse_yaml_file(config_path)
            if data:
                templates.append({
                    "id": agent_dir.name,
                    "name": data.get("name", agent_dir.name),
                    "description": data.get("description", ""),
                    "path": str(config_path),
                    "source": "builtin",
                })

    # User-created templates: data/agents/
    user_dir = Path(settings.agents_root)
    if user_dir.exists():
        for agent_dir in user_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            config_path = agent_dir / "agent.yaml"
            data = _parse_yaml_file(config_path)
            if data:
                templates.append({
                    "id": agent_dir.name,
                    "name": data.get("name", agent_dir.name),
                    "description": data.get("description", ""),
                    "path": str(config_path),
                    "source": "user",
                })

    return templates


def get_template_config(template_id: str) -> Optional[AgentConfig]:
    """Get configuration for a specific template.

    Args:
        template_id: Template directory name

    Returns:
        AgentConfig if found, None otherwise
    """
    config_path = get_global_template_path(template_id)
    data = _parse_yaml_file(config_path)

    if data:
        return AgentConfig.from_dict(data, source=f"template:{template_id}")

    return None

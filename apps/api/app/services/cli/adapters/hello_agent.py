"""
Hello Agent - A simple demonstration agent.

This is a minimal agent implementation showing how to extend BaseCLI.
Use this as a template for creating your own agents.
"""
import os
from typing import Any, Dict, Optional

from claude_agent_sdk import ClaudeAgentOptions

from app.common.types import AgentType
from app.core.config import settings
from app.core.terminal_ui import ui
from ..base import BaseCLI, MODEL_MAPPING
from ..config_loader import load_agent_config, AgentConfig


# Default system prompt for the Hello Agent (fallback)
DEFAULT_HELLO_PROMPT = """You are a friendly and helpful AI assistant.

## Your Capabilities
- Answer questions clearly and concisely
- Help with coding tasks
- Explain concepts in simple terms
- Assist with file operations when needed

## Guidelines
- Be helpful and friendly
- Ask clarifying questions when needed
- Provide examples when explaining concepts
- Keep responses focused and relevant
"""


class HelloAgent(BaseCLI):
    """Hello Agent - A demonstration agent for the Newhorse platform.

    This agent shows the basic structure for implementing a custom agent.
    Extend this class or use it as a reference for your own agents.
    """

    def __init__(self):
        super().__init__(AgentType.HELLO)

    async def check_availability(self) -> Dict[str, Any]:
        """Check if the Hello Agent is available."""
        return {
            "available": True,
            "configured": True,
            "models": list(MODEL_MAPPING.keys()),
            "default_model": "sonnet-4.5",
        }

    def init_claude_option(
        self,
        project_id: str,
        claude_session_id: Optional[str],
        model: Optional[str] = None,
        force_new_session: bool = False,
        user_config: Optional[Dict[str, str]] = None,
        agent_type: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Initialize Claude Agent options for Hello Agent."""

        project_path = os.path.join(settings.projects_root, project_id)

        # Load agent configuration (project-level > global template > defaults)
        default_config = AgentConfig(
            name="Hello Agent",
            description="A friendly AI assistant",
            system_prompt=DEFAULT_HELLO_PROMPT,
            model="claude-sonnet-4-5-20250929",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        )
        resolved_agent_type = agent_type or "hello"
        config = load_agent_config(project_path, agent_type=resolved_agent_type, default_config=default_config)

        ui.info(f"Initializing agent ({resolved_agent_type}) for project: {project_id}", "HelloAgent")
        ui.debug(f"Config source: {config.config_source}", "HelloAgent")

        # Resolve model (command parameter overrides config)
        if model:
            cli_model = MODEL_MAPPING.get(model, config.model)
        else:
            cli_model = MODEL_MAPPING.get(config.model, config.model)

        ui.debug(f"Model: {cli_model}", "HelloAgent")

        # Build list of directories to include
        add_dirs = []

        # Global skills directory
        global_skills_dir = os.path.join(settings.project_root, "extensions", "skills")
        if os.path.exists(global_skills_dir):
            add_dirs.append(global_skills_dir)

        # Project-level skills directory
        project_skills_dir = os.path.join(project_path, ".claude", "skills")
        if os.path.exists(project_skills_dir):
            add_dirs.append(project_skills_dir)

        # Add skill directories from config
        for skill in config.skills:
            skill_dir = os.path.join(settings.project_root, "extensions", "skills", skill)
            if os.path.exists(skill_dir) and skill_dir not in add_dirs:
                add_dirs.append(skill_dir)

        if add_dirs:
            ui.debug(f"Skills directories: {add_dirs}", "HelloAgent")

        options = ClaudeAgentOptions(
            # System prompt from config
            system_prompt=config.system_prompt,

            # Working directory for the agent
            cwd=project_path,

            # Model to use
            model=cli_model,

            # Enable file operation tools from config
            allowed_tools=config.allowed_tools,

            # Additional directories to include (for skills)
            add_dirs=add_dirs,

            # Session resumption
            resume=claude_session_id if not force_new_session else None,
        )

        return options

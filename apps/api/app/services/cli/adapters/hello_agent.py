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


# Default system prompt for the Hello Agent
HELLO_AGENT_PROMPT = """You are a friendly and helpful AI assistant.

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
        user_config: Optional[Dict[str, str]] = None
    ) -> ClaudeAgentOptions:
        """Initialize Claude Agent options for Hello Agent."""

        project_path = os.path.join(settings.projects_root, project_id)

        # Resolve model
        cli_model = MODEL_MAPPING.get(model, "claude-sonnet-4-5-20250929") if model else "claude-sonnet-4-5-20250929"

        # Skills directory
        skills_dir = os.path.join(settings.project_root, "extensions", "skills")

        ui.info(f"Initializing Hello Agent for project: {project_id}", "HelloAgent")
        ui.debug(f"Skills directory: {skills_dir}", "HelloAgent")
        ui.debug(f"Model: {cli_model}", "HelloAgent")

        options = ClaudeAgentOptions(
            # System prompt defines the agent's personality and capabilities
            system_prompt=HELLO_AGENT_PROMPT,

            # Working directory for the agent
            cwd=project_path,

            # Model to use
            model=cli_model,

            # Enable file operation tools
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],

            # Additional directories to include (for skills if they exist)
            add_dirs=[skills_dir] if os.path.exists(skills_dir) else [],

            # MCP servers (uncomment and configure as needed)
            # mcp_servers={
            #     "your-mcp-server": {
            #         "url": "http://localhost:8086/mcp"
            #     }
            # },

            # Session resumption
            resume=claude_session_id if not force_new_session else None,
        )

        return options

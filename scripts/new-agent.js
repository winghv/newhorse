/**
 * Create a new agent template
 */
const fs = require('fs');
const path = require('path');

const agentName = process.argv[2];

if (!agentName) {
    console.log('Usage: npm run new:agent <agent-name>');
    console.log('Example: npm run new:agent my-awesome-agent');
    process.exit(1);
}

// Convert to snake_case for Python
const snakeName = agentName.replace(/-/g, '_');
const className = agentName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('');

const adaptersDir = path.join(__dirname, '..', 'apps', 'api', 'app', 'services', 'cli', 'adapters');
const agentFile = path.join(adaptersDir, `${snakeName}_agent.py`);

if (fs.existsSync(agentFile)) {
    console.error(`Agent "${agentName}" already exists at ${agentFile}`);
    process.exit(1);
}

// Create agent file
const agentPy = `"""
${className} Agent

[Describe what this agent does]
"""
import os
from typing import Any, Dict, Optional

from claude_agent_sdk import ClaudeAgentOptions

from app.common.types import AgentType
from app.core.config import settings
from app.core.terminal_ui import ui
from ..base import BaseCLI, MODEL_MAPPING


# System prompt for ${className} Agent
${snakeName.toUpperCase()}_PROMPT = """You are a specialized AI assistant.

## Your Capabilities
- [Capability 1]
- [Capability 2]

## Guidelines
- [Guideline 1]
- [Guideline 2]
"""


class ${className}Agent(BaseCLI):
    """${className} Agent implementation."""

    def __init__(self):
        # Note: You need to add this agent type to app/common/types.py
        super().__init__(AgentType.HELLO)  # TODO: Change to your agent type

    async def check_availability(self) -> Dict[str, Any]:
        """Check if agent is available."""
        return {
            "available": True,
            "configured": True,
            "models": list(MODEL_MAPPING.keys()),
        }

    def init_claude_option(
        self,
        project_id: str,
        claude_session_id: Optional[str],
        model: Optional[str] = None,
        force_new_session: bool = False,
        user_config: Optional[Dict[str, str]] = None
    ) -> ClaudeAgentOptions:
        """Initialize Claude Agent options."""

        project_path = os.path.join(settings.projects_root, project_id)
        cli_model = MODEL_MAPPING.get(model, "claude-sonnet-4-5-20250929") if model else "claude-sonnet-4-5-20250929"
        skills_dir = os.path.join(settings.project_root, "extensions", "skills")

        ui.info(f"Initializing ${className} Agent", "${className}")

        return ClaudeAgentOptions(
            system_prompt=${snakeName.toUpperCase()}_PROMPT,
            cwd=project_path,
            model=cli_model,
            skillsDirectories=[skills_dir] if os.path.exists(skills_dir) else [],
            session_id=claude_session_id if not force_new_session else None,
        )
`;

fs.writeFileSync(agentFile, agentPy);

console.log(`✅ Created agent: ${agentName}`);
console.log(`   ${agentFile}`);
console.log('');
console.log('Next steps:');
console.log('1. Add your agent type to app/common/types.py:');
console.log(`   ${snakeName.toUpperCase()} = "${agentName}"`);
console.log('');
console.log('2. Register in app/services/cli/manager.py:');
console.log(`   from .adapters.${snakeName}_agent import ${className}Agent`);
console.log(`   if agent_type == AgentType.${snakeName.toUpperCase()}:`);
console.log(`       return ${className}Agent()`);
console.log('');
console.log('3. Update the system prompt in the agent file');

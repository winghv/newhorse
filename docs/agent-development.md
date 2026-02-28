# Agent Development Guide

This guide explains how to create custom agents in Newhorse.

## Overview

Agents are specialized AI assistants built on top of the Claude Agent SDK. Each agent has:

- A unique type identifier
- A custom system prompt defining its personality and capabilities
- Optional skills directories
- Optional MCP server configurations

## Creating an Agent

### Step 1: Create Agent File

Create a new file at `apps/api/app/services/cli/adapters/my_awesome_agent_agent.py`.

### Step 2: Register Agent Type

In `apps/api/app/common/types.py`:

```python
class AgentType(str, Enum):
    HELLO = "hello"
    MY_AWESOME_AGENT = "my-awesome-agent"  # Add your agent
```

### Step 3: Register in Manager

In `apps/api/app/services/cli/manager.py`:

```python
from .adapters.my_awesome_agent_agent import MyAwesomeAgentAgent

class AgentManager:
    def _create_agent(self, agent_type: AgentType) -> BaseCLI:
        if agent_type == AgentType.HELLO:
            return HelloAgent()
        elif agent_type == AgentType.MY_AWESOME_AGENT:
            return MyAwesomeAgentAgent()
        # ...

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        return {
            AgentType.HELLO.value: {...},
            AgentType.MY_AWESOME_AGENT.value: {
                "name": "My Awesome Agent",
                "description": "Does awesome things",
                "type": AgentType.MY_AWESOME_AGENT.value,
            }
        }
```

### Step 4: Customize the Agent

Edit the agent file:

```python
MY_AWESOME_AGENT_PROMPT = """You are a specialized assistant for...

## Capabilities
- Capability 1
- Capability 2

## Guidelines
- Be helpful
- Be accurate
"""

class MyAwesomeAgentAgent(BaseCLI):
    def __init__(self):
        super().__init__(AgentType.MY_AWESOME_AGENT)

    async def check_availability(self) -> Dict[str, Any]:
        return {"available": True, "configured": True}

    def init_claude_option(self, project_id, claude_session_id, model=None, **kwargs):
        return ClaudeAgentOptions(
            system_prompt=MY_AWESOME_AGENT_PROMPT,
            cwd=os.path.join(settings.projects_root, project_id),
            model=MODEL_MAPPING.get(model, "claude-sonnet-4-5-20250929"),
            skillsDirectories=[...],
            mcpServers={...},  # Optional
            session_id=claude_session_id,
        )
```

## System Prompt Best Practices

### Structure

```
You are [role description].

## Capabilities
- What you can do
- Your specialties

## Guidelines
- How to behave
- Constraints

## Workflow (optional)
1. Step 1
2. Step 2
```

### Tips

1. **Be specific** - Clearly define the agent's role
2. **List capabilities** - Help the model understand what it can do
3. **Set boundaries** - Define what it shouldn't do
4. **Provide examples** - Show expected behavior

## Adding Skills

Configure skills in `init_claude_option`:

```python
skills_dir = os.path.join(settings.project_root, "extensions", "skills")
custom_skills = os.path.join(project_path, "skills")

return ClaudeAgentOptions(
    skillsDirectories=[
        skills_dir,      # Global skills
        custom_skills,   # Project-specific skills
    ],
    # ...
)
```

## Adding MCP Servers

```python
return ClaudeAgentOptions(
    mcpServers={
        "database": {
            "url": "http://localhost:8086/mcp"
        },
        "external-api": {
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": "Bearer token"}
        }
    },
    # ...
)
```

## Testing Your Agent

1. Start the development server: `npm run dev`
2. Create a project in the UI
3. Select your agent type (may require UI changes)
4. Test various prompts

## Example Agents

### Code Review Agent

```python
CODE_REVIEW_PROMPT = """You are an expert code reviewer.

## Capabilities
- Analyze code for bugs and issues
- Suggest improvements
- Check for security vulnerabilities
- Ensure best practices

## Guidelines
- Be constructive, not critical
- Explain the 'why' behind suggestions
- Prioritize important issues
"""
```

### Documentation Agent

```python
DOCS_PROMPT = """You are a technical documentation specialist.

## Capabilities
- Generate API documentation
- Create README files
- Write user guides
- Document code

## Guidelines
- Write clearly and concisely
- Use examples liberally
- Follow standard formats
"""
```

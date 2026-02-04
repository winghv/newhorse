# Newhorse

AI Agent Development Platform based on Claude Agent SDK.

## Overview

Newhorse is a modern platform for building and deploying AI agents powered by Claude. It provides:

- **Agent Framework** - Build custom AI agents with specialized capabilities
- **Skills System** - Modular, reusable skill definitions for agents
- **Web Interface** - Real-time chat interface with WebSocket support
- **MCP Integration** - Connect to external tools via Model Context Protocol

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Claude API access (via Claude Code CLI)

### Installation

```bash
# Clone the repository
git clone <your-repo-url> newhorse
cd newhorse

# Install dependencies
npm install

# Start development server
npm run dev
```

This will:
1. Create a Python virtual environment
2. Install Python dependencies
3. Start the FastAPI backend (port 8080)
4. Start the Next.js frontend (port 3000)

### Access

- **Web UI**: http://localhost:3000
- **API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## Project Structure

```
newhorse/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   └── app/
│   │       ├── api/            # API routes
│   │       ├── core/           # Config, logging, utils
│   │       ├── models/         # Database models
│   │       └── services/cli/   # Agent implementations
│   │           ├── base.py     # Base agent class
│   │           ├── manager.py  # Agent manager
│   │           └── adapters/   # Agent adapters
│   └── web/                    # Next.js frontend
│       ├── app/                # Pages
│       └── components/         # React components
├── extensions/
│   └── skills/                 # Agent skills
│       └── demo-skill/         # Example skill
├── scripts/                    # Dev scripts
└── docs/                       # Documentation
```

## Creating Agents

Agents are specialized AI assistants with custom system prompts and capabilities.

### 1. Create the Agent File

```bash
npm run new:agent my-agent
```

This creates `apps/api/app/services/cli/adapters/my_agent_agent.py`.

### 2. Register the Agent Type

In `apps/api/app/common/types.py`:

```python
class AgentType(str, Enum):
    HELLO = "hello"
    MY_AGENT = "my-agent"  # Add your agent
```

### 3. Register in Manager

In `apps/api/app/services/cli/manager.py`:

```python
from .adapters.my_agent_agent import MyAgentAgent

def _create_agent(self, agent_type: AgentType) -> BaseCLI:
    if agent_type == AgentType.MY_AGENT:
        return MyAgentAgent()
    # ...
```

### 4. Customize the Agent

Edit the agent file to:
- Define a custom system prompt
- Configure skills directories
- Set up MCP servers (if needed)

## Creating Skills

Skills are modular capabilities that agents can use.

### 1. Create a Skill

```bash
npm run new:skill my-skill
```

This creates:
```
extensions/skills/my-skill/
├── SKILL.md           # Skill definition
├── scripts/           # Helper scripts
└── references/        # Documentation
```

### 2. Define the Skill

Edit `SKILL.md`:

```markdown
---
name: my-skill
description: What this skill does and when to use it
version: 1.0.0
---

# My Skill

## Overview
[Description]

## When to Use
[Trigger conditions]

## Workflow
[Step-by-step process]
```

### 3. Add to Agent

Skills are automatically discovered from the `skillsDirectories` configured in the agent.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# API port
API_PORT=8080

# Database (SQLite by default)
DATABASE_URL=sqlite:///data/newhorse.db

# Projects storage
PROJECTS_ROOT=data/projects

# Environment
THS_TIER=dev

# Optional: Redis for multi-worker support
# REDIS_URL=redis://localhost:6379/0
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/` | GET | List projects |
| `/api/projects/` | POST | Create project |
| `/api/projects/{id}` | GET | Get project |
| `/api/projects/{id}` | DELETE | Delete project |
| `/api/chat/{project_id}` | WebSocket | Real-time chat |
| `/api/agents/` | GET | List available agents |
| `/health` | GET | Health check |

## Development

### Commands

```bash
npm run dev          # Start full dev environment
npm run dev:api      # Start only backend
npm run dev:web      # Start only frontend
npm run new:agent    # Create new agent
npm run new:skill    # Create new skill
```

### Tech Stack

**Backend:**
- FastAPI
- Claude Agent SDK
- SQLAlchemy
- WebSockets

**Frontend:**
- Next.js 14
- React 18
- Tailwind CSS
- TypeScript

## License

MIT

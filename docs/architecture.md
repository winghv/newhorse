# Architecture

Newhorse follows a clean separation between frontend, backend, and agent logic.

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface                         │
│                 Next.js (port 3999)                      │
└─────────────────────┬───────────────────────────────────┘
                      │ WebSocket / REST
┌─────────────────────▼───────────────────────────────────┐
│                    API Server                            │
│                 FastAPI (port 8999)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  Projects   │  │    Chat     │  │   Agents    │      │
│  │    API      │  │    API      │  │    API      │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  Agent Layer                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Agent Manager                       │    │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐  │    │
│  │   │   Hello   │  │  Custom   │  │  Custom   │  │    │
│  │   │   Agent   │  │  Agent 1  │  │  Agent 2  │  │    │
│  │   └───────────┘  └───────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               Claude Agent SDK                           │
│           (subprocess communication)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               Claude Code CLI                            │
│          (local or remote execution)                     │
└─────────────────────────────────────────────────────────┘
```

## Components

### Frontend (apps/web)

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **State**: React hooks
- **Communication**: WebSocket for real-time chat, REST for CRUD

### Backend (apps/api)

- **Framework**: FastAPI
- **Database**: SQLAlchemy ORM (SQLite/MySQL)
- **WebSocket**: Native FastAPI WebSocket support
- **Agent Integration**: Claude Agent SDK

### Agent Layer

- **BaseCLI**: Abstract base class defining the agent contract
- **AgentManager**: Singleton managing agent instances
- **Adapters**: Individual agent implementations

### Skills

- **Location**: `extensions/skills/`
- **Format**: SKILL.md with YAML frontmatter
- **Loading**: Automatic discovery from configured directories

## Data Flow

### Chat Message Flow

1. User sends message via WebSocket
2. Backend receives and routes to appropriate agent
3. Agent processes using Claude Agent SDK
4. SDK streams responses back
5. Backend forwards to WebSocket
6. Frontend renders messages

### Project Creation

1. POST to `/api/projects/`
2. Create database record
3. Create project directory
4. Return project details

## Database Schema

```
projects
├── id (PK)
├── name
├── description
├── repo_path
├── status
├── preferred_cli
├── selected_model
├── created_at
└── updated_at

sessions
├── id (PK)
├── project_id (FK)
├── claude_session_id
├── status
├── created_at
└── updated_at

messages
├── id (PK)
├── project_id
├── session_id
├── role
├── message_type
├── content
├── metadata_json
└── created_at
```

## Extension Points

1. **New Agents**: Add to `services/cli/adapters/`
2. **New Skills**: Add to `extensions/skills/`
3. **New API Routes**: Add to `api/`
4. **MCP Servers**: Configure in agent options

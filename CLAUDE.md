# CLAUDE.md

This file provides guidance for Claude Code working in this repository.

## Project Overview

Newhorse is an AI Agent Development Platform based on Claude Agent SDK. It provides a framework for building custom AI agents with specialized capabilities.

## Architecture

```
newhorse/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   └── app/
│   │       ├── api/            # API routes
│   │       ├── core/           # Config, logging
│   │       ├── models/         # Database models
│   │       └── services/cli/   # Agent implementations
│   └── web/                    # Next.js frontend
├── extensions/
│   └── skills/                 # Agent skills
└── scripts/                    # Dev tools
```

## Key Components

### Agent System

- **BaseCLI** (`apps/api/app/services/cli/base.py`): Abstract base class for agents
- **AgentManager** (`apps/api/app/services/cli/manager.py`): Manages agent lifecycle
- **Adapters** (`apps/api/app/services/cli/adapters/`): Individual agent implementations

### Skills System

- Skills are in `extensions/skills/`
- Each skill has a `SKILL.md` with YAML frontmatter
- Skills can include `scripts/` and `references/`

## Development Commands

```bash
npm run dev          # Start full environment
npm run dev:api      # Backend only
npm run dev:web      # Frontend only
npm run new:agent    # Create agent template
npm run new:skill    # Create skill template
```

## Creating an Agent

1. `npm run new:agent <name>`
2. Add type to `app/common/types.py`
3. Register in `app/services/cli/manager.py`
4. Customize system prompt

## Creating a Skill

1. `npm run new:skill <name>`
2. Edit `SKILL.md` with frontmatter
3. Add scripts/references as needed

## Code Style

- Python: Follow PEP 8
- TypeScript: Follow ESLint rules
- Use type hints in Python
- Prefer async/await for I/O operations

## Git Commits

Format: `feat/fix: concise description`

Examples:
- `feat: add code review agent`
- `fix: websocket reconnection issue`

<div align="center">

```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

**Your personal AI agent platform, powered by Claude.**

Create custom AI agents, equip them with skills, and chat with them — all from your browser.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Getting Started](#quick-start) · [Documentation](docs/) · [Contributing](CONTRIBUTING.md) · [中文](README_CN.md)

</div>

---

## What is Newhorse?

Newhorse is an open-source platform for building, managing, and chatting with custom AI agents. Each agent gets its own workspace with files, skills, and conversation history.

**Key capabilities:**
- **Multi-Agent System** — Create specialized agents with custom prompts, tools, and models
- **Skills System** — Equip agents with modular, reusable capabilities (just Markdown files!)
- **Real-Time Chat** — WebSocket-powered streaming with markdown & code highlighting
- **Project Workspace** — Each project gets isolated files, config, and chat history
- **Template Gallery** — Start from pre-built templates or design your own
- **Multi-Provider** — Use Claude, OpenAI, or other providers with dynamic model selection
- **Access Anywhere** — Control agents from any device with a browser

## Quick Start

**Prerequisites:** Node.js 18+ · Python 3.10+ · Claude API access

```bash
git clone https://github.com/winghv/newhorse.git
cd newhorse
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — create your first agent in seconds.

## How It Works

1. **Create a Project** — Describe what you need, or pick a template
2. **Customize Your Agent** — Set the system prompt, choose a model, enable tools and skills
3. **Start Chatting** — Your agent is ready. Ask anything, watch it work in real time

## Tech Stack

| Frontend | Backend | AI |
|---|---|---|
| Next.js 14 · React 18 | FastAPI · SQLAlchemy | Claude Agent SDK |
| Tailwind CSS · TypeScript | SQLite · WebSocket | Multi-Provider Support |

## Project Structure

```
newhorse/
├── apps/api/          → FastAPI backend (Python)
├── apps/web/          → Next.js frontend (TypeScript)
├── extensions/
│   ├── agents/        → Built-in agent templates
│   └── skills/        → Agent skill packs
├── docs/              → Documentation
└── scripts/           → Dev tooling
```

## Extend It

```bash
npm run new:agent my-agent    # Create a new agent
npm run new:skill my-skill    # Create a new skill
```

Agents are Python classes. Skills are Markdown files. Simple as that.

See [Agent Development Guide](docs/agent-development.md) and [Skill Development Guide](docs/skill-development.md) for details.

## API Documentation

The backend auto-serves interactive API docs:
- **Swagger UI:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc:** [http://localhost:8080/redoc](http://localhost:8080/redoc)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)

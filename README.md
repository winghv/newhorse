<div align="center">

```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

### The Agent Factory. Build anything you can imagine.

Spawn unlimited AI agents. Configure once, deploy forever.
No CLI. No boilerplate. Just open your browser and go.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent_SDK-blueviolet.svg)](https://docs.anthropic.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Quick Start](#quick-start) · [Why Newhorse](#why-newhorse) · [Documentation](docs/) · [Contributing](CONTRIBUTING.md) · [中文](README_CN.md)

[![Watch the intro video](docs/intro-preview.gif)](https://github.com/winghv/newhorse/releases/download/video-assets/intro-video.mp4)

*Click to watch the full video with sound*

</div>

---

## Why Newhorse?

Most agent platforms give you a chatbot. Newhorse gives you a **factory**.

Create specialized AI agents, let them spawn other agents, watch them collaborate in real time — all from a browser UI. No CLI configuration, no YAML headaches. Everything is visual, everything is live, everything just works.

| Problem | Newhorse |
|---|---|
| "Setting up agent configs is painful" | Visual config editor. Click, save, done. |
| "I need agents for different domains" | Create vertical agents with custom prompts, tools, and constraints |
| "Managing agent files is chaos" | Every project gets its own isolated directory — safe and clean |
| "I want agents to work together" | Butler agent delegates to specialists automatically |
| "I can't see what agents are doing" | Real-time streaming, file preview, activity feed — what you see is what's real |
| "Claude Code is powerful but hard" | Same power, zero CLI — visual interface anyone can use |
| "I can only work from my laptop" | Browser-native. Phone, tablet, any device — manage your agents anywhere |

## Core Concepts

### Unlimited Agent Spawning

Newhorse is a workhorse factory. Every agent type — coder, researcher, writer, reviewer, planner, data analyst — is ready to go. Create custom agents from templates or from scratch. There is no limit.

### Agent Teams on Auto-Pilot

The **Butler** agent is your personal orchestrator. Give it a complex task, and it automatically delegates to specialist agents — a planner to design, a coder to implement, a reviewer to verify. Agents managing agents, recursively, intelligently.

### Visual Configuration, Zero CLI

Forget memorizing flags and editing dotfiles. Newhorse provides a full visual interface for agent configuration:

- **System prompts** — Edit in-browser with live preview
- **Model selection** — Switch between Claude Sonnet, Opus, Haiku, or OpenAI models in one click
- **Tool permissions** — Toggle Read, Write, Edit, Bash, and custom MCP tools
- **Skills** — Drag-and-drop Markdown skill files to extend agent capabilities

### Domain-Specific Agents

Building for a specific industry? Create constrained agents with:

- Custom system prompts tailored to your domain
- Restricted tool access for safety
- Pre-loaded skills and knowledge
- Config files that lock down behavior — let agents modify their own constraints for self-optimization

### Sandboxed Project Workspaces

Every project is an island. Isolated directory, isolated config, isolated history. Agents in Project A cannot touch Project B. Safe by design.

```
data/projects/{project-id}/
├── .claude/agent.yaml    # Agent configuration
├── .claude/skills/       # Project-specific skills
└── files/                # Agent workspace
```

### Multi-Agent Collaboration

Not just a single agent chatting — a full **Agent Team**:

- **Butler** orchestrates and delegates tasks
- **Planner** breaks down complex requirements
- **Coder** writes the implementation
- **Reviewer** checks quality and security
- **Researcher** gathers context and references

All coordination happens automatically. You describe the goal; the team delivers.

## Quick Start

**Docker (recommended)**

```bash
docker compose up -d
open http://localhost
```

**Docker Hub (no clone required)**

```bash
docker run -d -p 80:80 --name newhorse newhorse/newhorse:latest
open http://localhost
```

**Local:** Node.js 18+ · Python 3.10+ · Claude API key · [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

```bash
git clone https://github.com/winghv/newhorse.git
cd newhorse
cp .env.example .env && npm install && npm run dev
```

Open [http://localhost:3999](http://localhost:3999).

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                     Browser UI                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐             │
│  │  Chat    │  │  Files   │  │  Preview  │             │
│  │ Streaming│  │  Tree    │  │  Panel    │             │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘             │
│       │              │              │                   │
│       └──────────────┼──────────────┘                   │
│                      │ WebSocket                        │
├──────────────────────┼──────────────────────────────────┤
│                      ▼                                  │
│              ┌───────────────┐                          │
│              │   FastAPI     │                          │
│              │   + Agent     │                          │
│              │   Manager     │                          │
│              └───────┬───────┘                          │
│                      │                                  │
│         ┌────────────┼────────────┐                     │
│         ▼            ▼            ▼                     │
│  ┌────────────┐ ┌─────────┐ ┌─────────┐               │
│  │   Butler   │ │  Coder  │ │ Writer  │  ...           │
│  │ (delegates)│ │         │ │         │               │
│  └────────────┘ └─────────┘ └─────────┘               │
│         │                                               │
│         └──→ Spawns specialist agents on demand         │
└─────────────────────────────────────────────────────────┘
```

1. **Create a project** — Name it, describe it, or pick a template
2. **Configure the agent** — System prompt, model, tools, skills (all visual)
3. **Chat** — Stream responses in real time, watch file changes live
4. **Preview** — See generated HTML/CSS/JS rendered instantly
5. **Iterate** — Agents remember context, refine, and improve

## Built-in Agents

| Agent | Role | Superpower |
|---|---|---|
| **Butler** | Personal orchestrator | Delegates to specialists, manages the full workflow |
| **Coder** | Implementation | Writes, refactors, and debugs code |
| **Researcher** | Analysis | Gathers information, synthesizes findings |
| **Writer** | Content | Documentation, copywriting, technical writing |
| **Reviewer** | Quality | Code review, security audit, best practices |
| **Planner** | Architecture | System design, task breakdown, roadmapping |
| **Data Analyst** | Data | Analysis, visualization, insight extraction |
| **Code Assistant** | General dev | Broad coding help across languages |
| **Writing Assistant** | Editing | Proofreading, style, tone adjustment |

**Want more?** Create your own agent in seconds — just define a YAML config and a system prompt.

## Skills System

Skills are superpowers for your agents — modular capabilities written as Markdown files with YAML frontmatter.

```yaml
---
name: api-designer
description: Design RESTful APIs following OpenAPI 3.0 spec
---

You are an API design expert. When designing endpoints...
```

Drop a `.md` file into your project's skills directory. The agent picks it up instantly. No restart needed.

## Multi-Provider Support

Not locked into one LLM. Switch freely:

| Provider | Models | Status |
|---|---|---|
| **Anthropic** | Claude Sonnet 4, Opus 4.5, Haiku 3.5 | Fully supported |
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | Supported |
| **Custom** | Any OpenAI-compatible API | Configurable |

Manage API keys securely through the Settings page — encrypted at rest, never exposed in logs.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| **Backend** | FastAPI · SQLAlchemy · SQLite/MySQL · WebSocket |
| **AI Runtime** | Claude Agent SDK · Multi-provider routing |
| **Editor** | CodeMirror 6 · Monaco Editor |
| **i18n** | English · 中文 (next-intl) |

## Project Structure

```
newhorse/
├── apps/
│   ├── api/                → FastAPI backend (Python)
│   │   ├── app/api/        → REST & WebSocket routes
│   │   ├── app/models/     → SQLAlchemy models
│   │   ├── app/services/   → Agent adapters & managers
│   │   └── app/core/       → Config, logging, encryption
│   └── web/                → Next.js frontend (TypeScript)
│       ├── src/app/        → App Router pages
│       ├── src/components/ → React components
│       └── messages/       → i18n translations
├── extensions/
│   ├── agents/             → Built-in agent templates
│   └── skills/             → Skill packs
├── data/                   → SQLite DB & project workspaces
├── docs/                   → Architecture & guides
└── scripts/                → Dev tooling
```

## Contributing

We welcome contributions of all kinds — bug fixes, new agents, skills, documentation, and ideas.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE) — use it however you want.

---

<div align="center">

> Raise one lobster, or feed a herd of workhorses.

While others use [OpenClaw](https://github.com/SpaceExplorationTechnology/OpenClaw) to raise a single AI lobster, you command a whole army of agents with Newhorse.
One to watch, a team that works.

**Newhorse** — Stop configuring. Start building.

</div>

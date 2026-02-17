```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

**Your personal AI agent platform, powered by Claude.**

Create custom AI agents, equip them with skills, and chat with them in a modern web interface. Whether you're building agents for your team or just exploring what AI can do — Newhorse gets you there fast.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org) [![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

[中文文档](README_CN.md)

---

## Features

| | Feature | Description |
|---|---|---|
| :robot: | **Multi-Agent System** | Create specialized agents with custom prompts, tools, and models |
| :jigsaw: | **Skills System** | Equip agents with modular, reusable capabilities |
| :speech_balloon: | **Real-Time Chat** | WebSocket-powered chat with markdown & code highlighting |
| :file_folder: | **Project Workspace** | Each project gets its own files, config, and chat history |
| :art: | **Template Gallery** | Start from pre-built agent templates or design your own |
| :gear: | **Full Customization** | Choose models (Sonnet/Opus/Haiku), toggle tools, tune prompts |
| :globe_with_meridians: | **Access Anywhere** | Control your agents from any device, anytime — all you need is a browser |

---

## Quick Start

**Prerequisites:** Node.js 18+ / Python 3.10+ / Claude API access

```bash
# Clone & install
git clone <repo-url> newhorse
cd newhorse
npm install

# Start everything
npm run dev
```

That's it. Open [http://localhost:3000](http://localhost:3000) and create your first agent.

---

## How It Works

1. **Create a Project** — Describe what you need, or pick a template
2. **Customize Your Agent** — Set the system prompt, choose a model, enable tools and skills
3. **Start Chatting** — Your agent is ready. Ask it anything, watch it work in real time

---

## Tech Stack

| Frontend | Backend | AI |
|---|---|---|
| Next.js 14 · React 18 | FastAPI · SQLAlchemy | Claude Agent SDK |
| Tailwind CSS · TypeScript | SQLite · WebSocket | MCP Integration |

## Project Structure

```
newhorse/
├── apps/api/          → FastAPI backend
├── apps/web/          → Next.js frontend
├── extensions/skills/ → Agent skill packs
└── scripts/           → Dev tooling
```

---

## Extend It

```bash
npm run new:agent my-agent    # Create a new agent
npm run new:skill my-skill    # Create a new skill
```

Agents are Python classes. Skills are Markdown files. Simple as that.

---

## License

[MIT](LICENSE)

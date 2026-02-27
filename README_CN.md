<div align="center">

```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

**属于你的 AI Agent 平台，由 Claude 驱动。**

创建自定义 AI Agent，赋予它技能，在浏览器中与它实时对话。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[快速开始](#快速开始) · [文档](docs/) · [参与贡献](CONTRIBUTING.md) · [English](README.md)

</div>

---

## Newhorse 是什么？

Newhorse 是一个开源平台，用于构建、管理和对话自定义 AI Agent。每个 Agent 拥有独立的工作区，包含文件、技能和对话记录。

**核心能力：**
- **多 Agent 系统** — 创建拥有自定义提示词、工具和模型的专属 Agent
- **技能系统** — 为 Agent 装备模块化、可复用的技能（只需 Markdown 文件！）
- **实时对话** — 基于 WebSocket 的流式传输，支持 Markdown 和代码高亮
- **项目工作区** — 每个项目独立管理文件、配置和对话记录
- **模板中心** — 使用预设模板快速开始，或创建你自己的模板
- **多模型支持** — 使用 Claude、OpenAI 或其他供应商，动态选择模型
- **随时随地访问** — 打开浏览器即可操控你的 Agent

## 快速开始

**环境要求：** Node.js 18+ · Python 3.10+ · Claude API 访问权限

```bash
git clone https://github.com/winghv/newhorse.git
cd newhorse
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000) — 几秒钟内创建你的第一个 Agent。

## 使用流程

1. **创建项目** — 描述你的需求，或选择一个模板
2. **配置 Agent** — 设定系统提示词，选择模型，启用工具和技能
3. **开始对话** — Agent 已就绪，尽管提问，实时查看它的工作

## 技术栈

| 前端 | 后端 | AI |
|---|---|---|
| Next.js 14 · React 18 | FastAPI · SQLAlchemy | Claude Agent SDK |
| Tailwind CSS · TypeScript | SQLite · WebSocket | 多模型供应商支持 |

## 项目结构

```
newhorse/
├── apps/api/          → FastAPI 后端 (Python)
├── apps/web/          → Next.js 前端 (TypeScript)
├── extensions/
│   ├── agents/        → 内置 Agent 模板
│   └── skills/        → Agent 技能包
├── docs/              → 文档
└── scripts/           → 开发工具
```

## 扩展开发

```bash
npm run new:agent my-agent    # 创建新 Agent
npm run new:skill my-skill    # 创建新技能
```

Agent 是 Python 类，技能是 Markdown 文件。就这么简单。

详见 [Agent 开发指南](docs/agent-development.md) 和 [技能开发指南](docs/skill-development.md)。

## API 文档

后端自动提供交互式 API 文档：
- **Swagger UI：** [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc：** [http://localhost:8080/redoc](http://localhost:8080/redoc)

## 参与贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

[MIT](LICENSE)

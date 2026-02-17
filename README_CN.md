```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

**属于你的 AI Agent 平台，由 Claude 驱动。**

创建自定义 AI Agent，赋予它技能，在现代 Web 界面中与它实时对话。无论是为团队打造专属 Agent，还是探索 AI 的可能性 — Newhorse 让一切触手可及。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org) [![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

[English](README.md)

---

## 特性

| | 功能 | 说明 |
|---|---|---|
| :robot: | **多 Agent 系统** | 创建拥有自定义提示词、工具和模型的专属 Agent |
| :jigsaw: | **技能系统** | 为 Agent 装备模块化、可复用的技能 |
| :speech_balloon: | **实时对话** | 基于 WebSocket 的聊天，支持 Markdown 和代码高亮 |
| :file_folder: | **项目工作区** | 每个项目独立管理文件、配置和对话记录 |
| :art: | **模板中心** | 使用预设模板快速开始，或创建你自己的模板 |
| :gear: | **完全可定制** | 自由选择模型（Sonnet/Opus/Haiku）、开关工具、调整提示词 |
| :globe_with_meridians: | **随时随地访问** | 打开浏览器即可远程操控你的 Agent，不受设备和地点限制 |

---

## 快速开始

**环境要求：** Node.js 18+ / Python 3.10+ / Claude API 访问权限

```bash
# 克隆并安装
git clone <repo-url> newhorse
cd newhorse
npm install

# 启动
npm run dev
```

搞定。打开 [http://localhost:3000](http://localhost:3000)，创建你的第一个 Agent。

---

## 使用流程

1. **创建项目** — 描述你的需求，或选择一个模板
2. **配置 Agent** — 设定系统提示词，选择模型，启用工具和技能
3. **开始对话** — Agent 已就绪，尽管提问，实时查看它的工作

---

## 技术栈

| 前端 | 后端 | AI |
|---|---|---|
| Next.js 14 · React 18 | FastAPI · SQLAlchemy | Claude Agent SDK |
| Tailwind CSS · TypeScript | SQLite · WebSocket | MCP 集成 |

## 项目结构

```
newhorse/
├── apps/api/          → FastAPI 后端
├── apps/web/          → Next.js 前端
├── extensions/skills/ → Agent 技能包
└── scripts/           → 开发工具
```

---

## 扩展开发

```bash
npm run new:agent my-agent    # 创建新 Agent
npm run new:skill my-skill    # 创建新技能
```

Agent 是 Python 类，技能是 Markdown 文件。就这么简单。

---

## 许可证

[MIT](LICENSE)

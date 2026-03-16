<div align="center">

```
 _   _               _
| \ | |             | |
|  \| | _____      _| |__   ___  _ __ ___  ___
| . ` |/ _ \ \ /\ / / '_ \ / _ \| '__/ __|/ _ \
| |\  |  __/\ V  V /| | | | (_) | |  \__ \  __/
|_| \_|\___| \_/\_/ |_| |_|\___/|_|  |___/\___|
```

### 智能体工厂。实现你所能想象的一切。

无限生成 AI Agent。配置一次，永久运行。
不需要 CLI，不需要模板，打开浏览器就能用。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent_SDK-blueviolet.svg)](https://docs.anthropic.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[快速开始](#快速开始) · [为什么选 Newhorse](#为什么选-newhorse) · [文档](docs/) · [参与贡献](CONTRIBUTING.md) · [English](README.md)

[![观看介绍视频](docs/intro-preview-zh.gif)](https://github.com/winghv/newhorse/releases/download/video-assets/intro-video-zh.mp4)

*点击观看完整带声音视频*

</div>

---

## 为什么选 Newhorse？

大多数 Agent 平台给你一个聊天机器人。Newhorse 给你一座**工厂**。

创建专属 AI Agent，让 Agent 生成 Agent，实时观察它们协作 —— 全部在浏览器里完成。不用装 CLI，不用手写配置文件，不用折腾环境。所有配置可视化，所有操作实时生效，开箱即用。

| 痛点 | Newhorse 的解法 |
|---|---|
| "安装 CLI、写配置太麻烦" | 一切已预配置好，打开浏览器直接用 |
| "想做行业垂类 Agent" | 自定义 Prompt、工具、约束，打造高度受控的专属 Agent |
| "Agent 文件管理混乱" | 每个项目独立目录，安全隔离，互不干扰 |
| "想让多个 Agent 协作" | Butler 管家自动分派任务给专家 Agent，全程自动 |
| "看不到 Agent 在做什么" | 实时流式输出、文件预览、活动记录 —— 所见为实 |
| "Claude Code 很强但门槛太高" | 同等强大的 Agent 能力，零配置可视化操作，小白也能驾驭 |
| "只能在电脑上用" | 浏览器原生，手机、平板、任何设备，随时随地管理你的 Agent 军团 |

## 核心理念

### 无限生成，牛马工厂

Newhorse 是一座 Agent 工厂。Coder、Researcher、Writer、Reviewer、Planner、Data Analyst —— 所有类型的 Agent 开箱即用。从模板创建，或从零定义，没有数量限制。想造多少造多少。

### 全托管，团队协作

**Butler（管家）** 是你的私人调度员。给它一个复杂任务，它会自动拆解、分派给专家 Agent —— Planner 做设计、Coder 写代码、Reviewer 把关质量。Agent 管理 Agent，递归调度，智能协作。

### 全可视化配置，零 CLI

忘掉命令行参数和配置文件吧。Newhorse 提供完整的可视化界面：

- **系统提示词** —— 浏览器内编辑，实时预览效果
- **模型选择** —— Claude Sonnet、Opus、Haiku 或 OpenAI 模型，一键切换
- **工具权限** —— 勾选 Read、Write、Edit、Bash 和自定义 MCP 工具
- **技能管理** —— Markdown 格式的技能文件，拖入即生效

皆可自动生成，一切尽在掌控。文件配置、文件预览，所见为实。

### 行业垂类定制

想做特定领域的 Agent？通过配置文件精准约束：

- 定制化系统提示词，针对你的行业场景
- 限制工具访问权限，确保安全
- 预装领域技能和知识库
- 让 Agent 自己修改配置文件，实现自我优化和更高约束

### 独立项目目录，安全隔离

每个项目是一座孤岛。独立目录、独立配置、独立历史记录。项目 A 的 Agent 无法触碰项目 B 的任何文件。安全隔离，天然设计。

```
data/projects/{project-id}/
├── .claude/agent.yaml    # Agent 配置
├── .claude/skills/       # 项目专属技能
└── files/                # Agent 工作区
```

### 个人助手全托管，多 Agent 协作

不只是单个 Agent 聊天 —— 是完整的 **Agent Team**：

- **Butler（管家）** 统筹调度、分派任务
- **Planner（规划师）** 拆解复杂需求
- **Coder（程序员）** 编写实现代码
- **Reviewer（审查员）** 检查质量与安全
- **Researcher（研究员）** 收集信息、汇总发现

所有协作自动完成。你只需描述目标，团队交付结果。

## 快速开始

**环境要求：** Node.js 18+ · Python 3.10+ · Claude API 密钥

```bash
git clone https://github.com/winghv/newhorse.git
cd newhorse
npm install
npm run dev
```

打开 [http://localhost:3999](http://localhost:3999)，创建项目，开始对话。就这么简单。

> **不需要额外安装 CLI 工具。** 不需要配置守护进程。不需要手写配置文件。
> 一切已预先就绪，开箱即用。

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                     浏览器 UI                            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐             │
│  │  实时    │  │  文件    │  │  实时     │             │
│  │  对话    │  │  管理    │  │  预览     │             │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘             │
│       │              │              │                   │
│       └──────────────┼──────────────┘                   │
│                      │ WebSocket                        │
├──────────────────────┼──────────────────────────────────┤
│                      ▼                                  │
│              ┌───────────────┐                          │
│              │   FastAPI     │                          │
│              │   + Agent     │                          │
│              │   调度中心     │                          │
│              └───────┬───────┘                          │
│                      │                                  │
│         ┌────────────┼────────────┐                     │
│         ▼            ▼            ▼                     │
│  ┌────────────┐ ┌─────────┐ ┌─────────┐               │
│  │  Butler    │ │  Coder  │ │ Writer  │  ...           │
│  │ (自动分派) │ │         │ │         │               │
│  └────────────┘ └─────────┘ └─────────┘               │
│         │                                               │
│         └──→ 按需生成专家 Agent                          │
└─────────────────────────────────────────────────────────┘
```

1. **创建项目** —— 起个名字，描述需求，或直接选模板
2. **配置 Agent** —— 系统提示词、模型、工具、技能（全部可视化）
3. **实时对话** —— 流式输出，实时查看文件变更
4. **即时预览** —— 生成的 HTML/CSS/JS 即刻渲染
5. **持续迭代** —— Agent 记住上下文，不断优化

## 内置 Agent

| Agent | 角色 | 能力 |
|---|---|---|
| **Butler** | 私人管家 | 自动分派任务给专家，全流程管理 |
| **Coder** | 程序员 | 编写、重构、调试代码 |
| **Researcher** | 研究员 | 信息收集、分析总结 |
| **Writer** | 写手 | 文档、文案、技术写作 |
| **Reviewer** | 审查员 | 代码审查、安全检查、最佳实践 |
| **Planner** | 规划师 | 系统设计、任务拆解、路线规划 |
| **Data Analyst** | 数据分析师 | 数据分析、可视化、洞察提取 |
| **Code Assistant** | 编程助手 | 跨语言通用编程辅助 |
| **Writing Assistant** | 写作助手 | 校对、风格调整、润色 |

**想要更多？** 几秒钟就能创建你自己的 Agent —— 只需定义一份 YAML 配置和系统提示词。

## 技能系统

技能是 Agent 的超能力 —— 用 Markdown 文件编写的模块化能力扩展。

```yaml
---
name: api-designer
description: 按照 OpenAPI 3.0 规范设计 RESTful API
---

你是一个 API 设计专家。在设计接口时...
```

将 `.md` 文件放入项目的技能目录，Agent 即刻获得新能力。无需重启。

## 多模型支持

不锁定任何一家 LLM，自由切换：

| 供应商 | 模型 | 状态 |
|---|---|---|
| **Anthropic** | Claude Sonnet 4、Opus 4.5、Haiku 3.5 | 完整支持 |
| **OpenAI** | GPT-4o、GPT-4、GPT-3.5 | 已支持 |
| **自定义** | 任意 OpenAI 兼容 API | 可配置 |

通过设置页面安全管理 API 密钥 —— 加密存储，日志中不暴露。

## 技术栈

| 层级 | 技术 |
|---|---|
| **前端** | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| **后端** | FastAPI · SQLAlchemy · SQLite/MySQL · WebSocket |
| **AI 运行时** | Claude Agent SDK · 多供应商路由 |
| **编辑器** | CodeMirror 6 · Monaco Editor |
| **国际化** | English · 中文 (next-intl) |

## 项目结构

```
newhorse/
├── apps/
│   ├── api/                → FastAPI 后端 (Python)
│   │   ├── app/api/        → REST & WebSocket 路由
│   │   ├── app/models/     → SQLAlchemy 数据模型
│   │   ├── app/services/   → Agent 适配器 & 管理器
│   │   └── app/core/       → 配置、日志、加密
│   └── web/                → Next.js 前端 (TypeScript)
│       ├── src/app/        → App Router 页面
│       ├── src/components/ → React 组件
│       └── messages/       → 多语言翻译
├── extensions/
│   ├── agents/             → 内置 Agent 模板
│   └── skills/             → 技能扩展包
├── data/                   → SQLite 数据库 & 项目工作区
├── docs/                   → 架构文档 & 使用指南
└── scripts/                → 开发工具脚本
```

## 参与贡献

欢迎任何形式的贡献 —— Bug 修复、新 Agent、技能扩展、文档改进、创意建议。

查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

[MIT](LICENSE) —— 随意使用。

---

<div align="center">

> 养一只龙虾，不如喂一群牛马。

别人用 [OpenClaw](https://github.com/openclaw/openclaw) 养一只 AI 龙虾，你用 Newhorse 指挥一整支 Agent 军团。
一个只能养着看，一群能替你干活。

**Newhorse** —— 别再折腾配置了，开始创造吧。

</div>

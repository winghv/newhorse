# AGENTS.md

Newhorse — 基于 Claude Agent SDK 的 AI Agent 开发平台（Codex 视角）。

> 本文件与 `CLAUDE.md` 共享同一套架构、约定与红线，仅"主控模式"一节按 Codex 视角描述。两边 supervisor 共用同一份 `media-ops-supervisor` skill 与脚本。

## 架构

```
apps/api/    → FastAPI 后端，SQLAlchemy + SQLite
apps/web/    → Next.js 14 (App Router) + Tailwind CSS
extensions/skills/  → Agent 技能扩展
scripts/     → Node.js 开发脚本
```

## 命令

```bash
npm run dev          # API + Web 同时启动
npm run dev:api      # 仅后端
npm run dev:web      # 仅前端
npm run doctor       # 环境诊断
```

## 项目约定（不可从代码推断的决策）

### 文件放置

- API 路由: `apps/api/app/api/{resource}.py`，新路由必须在 `main.py` 注册
- 数据模型: `apps/api/app/models/{entity}.py`，新模型必须在 `models/__init__.py` 导入
- Agent 实现: `apps/api/app/services/cli/adapters/`，继承 `BaseCLI`
- 共享类型: `apps/api/app/common/types.py` 集中管理枚举
- `core/` 只放基础设施（配置、日志），不放业务逻辑

### 数据库

- 主键: `String` 类型，代码生成 8 位短 ID
- 所有表必须有 `created_at`，可修改表加 `updated_at`
- JSON 字段命名: `{name}_json`（如 `metadata_json`）
- 新增字段必须有默认值（向后兼容）

### Agent 注册流程

1. `app/common/types.py` → AgentType 枚举加新值
2. `app/services/cli/manager.py` → `_create_agent()` 加映射
3. 模型使用 `BaseCLI.MODEL_MAP` 中已有映射

### 前端

- 暗色主题: zinc 色系为主，蓝色强调
- API 调用走 Next.js rewrite 代理，用相对路径 `/api/...`
- WebSocket 直连后端端口
- Toast 用 sonner: `toast.error()` / `toast.success()`

### 日志

统一用 `app/core/terminal_ui.py` 的 `ui` 实例，格式: `ui.info("消息", "模块名")`

## 红线

- 不硬编码密钥/Token — 走 `.env` + `config.py`
- 不写原始 SQL — 用 SQLAlchemy ORM
- 新增环境变量必须同步更新 `.env.example`
- 不引入功能重叠的依赖

## Git

格式: `类型: 描述`（feat/fix/refactor/chore），英文，一个 commit 一件事

## Media Ops Supervisor 主控模式

Codex 可作为 `media-ops` 团队的 supervisor-led 主控。当用户激活时，读取 `.agents/skills/media-ops-supervisor/SKILL.md` 中的指令，以自然语言驱动媒体运营项目的阶段推进。

### 激活场景

- 想要更高层级编排和诊断时
- 跨项目的批次协调
- 与 Claude Code 主控互为失败转移

### 核心职责

| 职责 | 触发词示例 |
|------|----------|
| 状态诊断 | "看看 xxx 项目进度"、"诊断一下为什么卡住了" |
| 阶段推进 | "把 xxx 推进到发布阶段"、"继续下一阶段" |
| 手动委派 | "让 benchmark-analyst 重跑"、"交给 content-producer" |
| 产出审查 | "检查 xxx 的竞争审校报告"、"看看这个内容包" |
| 干预决策 | "修复 xxx 的素材清单"、"干预发布流程" |

### 状态检测

无状态设计，每次激活时：
1. 读取 `planning/stage-status.json`
2. 扫描关键目录和交付物（`research/`、`benchmarks/`、`content/`、`review/` 等）
3. 交叉验证，输出结构化面板

### 三个真门禁（其余检查都是这 3 个门禁内部的子检查）

- **creative-gate**（生产前）：`build_template_fatigue_report.py` 退出码非 0 或缺 `creative-divergence-brief.json` → 不得进入生产
- **assembly-qa-gate**（审校前）：assembly-qa / subtitle-quality / visual-diversity / visual-production-gate 任一未过 → 不得进入竞争审校
- **publish-gate**（发布前）：竞争审校未 pass、合规未 pass、workflow quality gate=revise·block，或 `rebuild_timeline` 缺 `auto-base-cut-plan.json` → 发布 blocked
- Codex 当前有任务在跑时 → 推进需等 Codex 完成
- research / script / production / review 必须委派 specialist，主控只做 brief + gate + 整合

### 项目目录约定

媒体运营内容包统一放在 `data/media-ops/<content-id>/`，结构见 `docs/media-ops-workflow-spec.md`

# CLAUDE.md

Newhorse — 基于 Claude Agent SDK 的 AI Agent 开发平台。

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
npm run new:agent    # 创建 Agent（需手动注册到 types.py + manager.py）
npm run new:skill    # 创建 Skill
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

1. `npm run new:agent <name>` 生成模板
2. `app/common/types.py` → AgentType 枚举加新值
3. `app/services/cli/manager.py` → `_create_agent()` 加映射
4. 模型使用 `BaseCLI.MODEL_MAP` 中已有映射

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

格式: `类型: 描述`（feat/fix/refactor/chore），英文，一个 commit 一件事 , 不要出现 'Co-Authored-By'

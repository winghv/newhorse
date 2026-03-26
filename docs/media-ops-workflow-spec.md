# Media Ops Workflow Spec

## Goal

为 Newhorse 内置的媒体运营团队定义稳定、可审计的自动化工作流。

## Stages

### 1. Research

输入：

- 账号矩阵
- 平台
- 目标受众
- 时间窗口
- 可用素材

输出：

- `research brief`
- `signal list`
- `evidence`
- `risk notes`

### 2. Topic Selection

输入：

- `research brief`

输出：

- `topic backlog`
- `priority score`
- `content brief`

### 3. Production

输入：

- `content brief`

输出：

- `content packet`
- `platform variants`
- `asset checklist`
- `open questions`

### 4. Review

输入：

- `content packet`

输出：

- `review decision`
- `issues`
- `required fixes`
- `approval_status`

审批状态只允许：

- `pass`
- `revise`
- `block`

### 5. Publishing

输入：

- `content packet`
- `approval_status=pass`
- `publish manifest`

输出：

- `publish result`
- `per-platform status`
- `retry guidance`

## Security Boundaries

- cookie、token、密钥只允许来自环境或外部受控运行时，不落盘到仓库
- 没有明确发布许可时，只允许 dry-run
- 发布日志必须脱敏
- 平台未接入自动化时，只输出手工发布包

## Runtime Rules

- 总控模板 `media-ops-butler` 必须使用 `preferred_cli=butler`
- 专家模板可以走 `hello` runtime，但由 Butler 通过 `delegate_task` 调用
- 项目 runtime 必须与模板 metadata 保持一致

## Verification

- API 测试验证模板 metadata 与 runtime 同步
- E2E 测试验证首页选模板创建项目、项目内套模板
- 前端 build 和后端 pytest 必须通过

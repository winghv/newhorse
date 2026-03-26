---
name: media-ops-orchestration
description: 编排多账号媒体运营全流程。用于研究、选题、制作、审核、发布串联成一条可交接的工作流，并定义每个阶段的输入输出契约。
version: 1.0.0
---

# Media Ops Orchestration

## Overview

把内容运营拆成清晰阶段，而不是让一个 agent 一次性拍脑袋产出整套内容。

推荐阶段顺序：

1. 研究
2. 选题
3. 制作
4. 审核
5. 发布
6. 复盘

## When to Use

在这些场景启用：

- 用户要为多个平台或多个账号做内容运营
- 用户要求从选题到发布跑完整流水线
- 需要不同角色之间清晰交接，不想把所有工作塞到一个 prompt
- 需要沉淀成研究简报、brief、审核单、发布清单

## Workflow

1. 先确认运营目标：品牌曝光、获客、转化、增长、活动支持、私域导流。
2. 确认约束：账号矩阵、目标平台、受众、节奏、可用素材、禁区、审批要求。
3. 研究阶段输出 `research brief`。
4. 选题阶段输出 `topic backlog` 和 `content brief`。
5. 制作阶段输出 `content packet`，包括平台版本和素材需求。
6. 审核阶段输出 `review gate`，结论为 `pass / revise / block`。
7. 发布阶段输出 `publish manifest` 和结果日志。
8. 复盘阶段回填表现数据、结论和下一轮调整建议。

## Handoff Contract

每个阶段最少交付这些字段：

- `objective`: 这条内容要完成什么目标
- `audience`: 面向谁
- `platforms`: 投放平台
- `core_angle`: 核心观点或切入角度
- `evidence`: 关键事实、案例、素材来源
- `risks`: 敏感点、依赖项、待确认项
- `next_action`: 下游应该做什么

## Suggested Workspace Layout

建议将产物保存到这些目录，方便下游角色接手：

- `research/`
- `planning/`
- `content/`
- `review/`
- `publish/`
- `retros/`

## Operating Rules

- 任何阶段都要明确区分事实、推断和建议。
- 如果上游交付物不完整，先指出缺口，不要自行脑补。
- 不要跨平台原样复用同一份文案。
- 发布前必须有审核状态和账号/素材映射。

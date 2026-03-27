---
name: media-ops-orchestration
description: 编排多账号媒体运营全流程。用于研究、对标、选题、角度设计、制作、竞争审校、审核、发布、复盘串联成一条可交接的工作流，并定义每个阶段的输入输出契约。
version: 1.0.0
---

# Media Ops Orchestration

## Overview

把内容运营拆成清晰阶段，而不是让一个 agent 一次性拍脑袋产出整套内容。

推荐阶段顺序：

1. 研究
2. 对标拆解
3. 选题
4. 角度设计
5. 制作
6. 竞争审校
7. 合规审核
8. 发布
9. 复盘

推荐先定义运行模式：

- `autonomous-team`: 由 Butler 负责完整调度，团队按门禁自动推进
- `supervisor-led`: 由外部主控 Agent 或人类主控阶段推进，但团队仍按同一套契约输出

如果 `制作` 的产物是视频，再拆成：

1. 视频形态判定：`short-video` 或 `midlong-video`
2. 中长视频先做片段检索：优先规划来自合法来源的网上片段
3. 素材策略与生成预算门禁：优先真实素材、网上合法片段和确定性编辑，再决定是否启用生成式媒体
4. 配音与字幕后期：默认补齐旁白、字幕和混音说明
5. 平台成片包装：按平台 skill 产出最终包，而不是复用同一份视频文案
6. 后期装配与渲染验证：产出 final cut、render manifest 和 verification 记录

## When to Use

在这些场景启用：

- 用户要为多个平台或多个账号做内容运营
- 用户要求从选题到发布跑完整流水线
- 需要不同角色之间清晰交接，不想把所有工作塞到一个 prompt
- 需要沉淀成研究简报、brief、审核单、发布清单

## Workflow

1. 先确认运营目标：品牌曝光、获客、转化、增长、活动支持、私域导流。
2. 确认约束：账号矩阵、目标平台、受众、节奏、可用素材、禁区、审批要求。
3. 研究阶段输出 `research brief`，同时给出 `benchmark candidates`。
4. 对标阶段输出 `benchmark deck`、`pattern map` 和 `whitespace`。
5. 选题阶段输出 `topic backlog` 和 `selected topic`。
6. 角度设计阶段输出 `angle brief`、`hook hypotheses` 和 `proof plan`。
7. 制作阶段输出 `content packet`，包括平台版本、钩子备选和素材需求。
8. 如果是视频，必须补 `asset_source_map`、`generation_budget_decision`、`subtitle_source`、`voiceover plan`、`assembly_strategy`、`render_plan` 和 `render_manifest`；如果用了网上片段，还要补 `source_manifest`。
9. 竞争审校阶段输出 `competitive scorecard`、`score_by_dimension`、`total_score`，结论为 `pass / revise / block`。
10. 合规审核阶段输出 `review gate` 与 `approval_status`。
11. 发布阶段输出 `publish manifest` 和结果日志。
12. 复盘阶段回填表现数据、结论和下一轮调整建议。

## Handoff Contract

每个阶段最少交付这些字段：

- `objective`: 这条内容要完成什么目标
- `operating_mode`: `autonomous-team` 或 `supervisor-led`
- `audience`: 面向谁
- `platforms`: 投放平台
- `core_angle`: 核心观点或切入角度
- `evidence`: 关键事实、案例、素材来源
- `benchmark_refs`: 关键对标样本
- `hook_hypotheses`: 预期有效的开头与互动触发
- `deliverable_type`: 图文、短视频或中长视频
- `duration_target`: 目标时长
- `aspect_ratio`: 目标画幅
- `risks`: 敏感点、依赖项、待确认项
- `asset_source_map`: 真实素材、截图、AI 图像、AI 视频、TTS、音乐的来源分配
- `source_manifest`: 网上片段来源、用途、许可状态、署名要求和替代片段
- `generation_budget_decision`: 哪些生成动作获批，哪些被挡回，以及原因
- `subtitle_source`: 与最终口播一致的字幕源文本
- `voiceover_plan`: 旁白是否必需、由谁配、如何混音
- `assembly_strategy`: `retime_existing_cut`、`rebuild_timeline` 或其他明确装配策略
- `render_plan`: 后期装配和渲染参数
- `render_manifest`: 最终成片的渲染输出和验证摘要
- `competitive_score`: 竞争力评分或门禁结论
- `score_by_dimension`: 各维度评分明细
- `experiment_plan`: 需要验证的创作假设
- `next_action`: 下游应该做什么

## Suggested Workspace Layout

建议将产物保存到这些目录，方便下游角色接手：

- `research/`
- `benchmarks/`
- `planning/`
- `angles/`
- `content/`
- `assets/`
- `sources/`
- `review/`
- `publish/`
- `retros/`

## Operating Rules

- 任何阶段都要明确区分事实、推断和建议。
- 如果上游交付物不完整，先指出缺口，不要自行脑补。
- 不要跨平台原样复用同一份文案。
- 视频生成预算属于上游制作约束，不能等到发布前才决定。
- 解释型视频默认要求旁白和字幕资产；如果故意不用，必须明确说明原因。
- 中长视频优先用合法来源的网上片段做 B-roll 组装，不默认消耗视频生成额度。
- 对已进入后期装配阶段的视频，必须留下 `render_plan` 和 `render_manifest`，否则视为不可审计。
- 竞争审校不过，不进入合规审核和真实发布。
- 竞争审校必须输出结构化评分卡，不能只给模糊意见。
- 发布前必须有审核状态和账号/素材映射。

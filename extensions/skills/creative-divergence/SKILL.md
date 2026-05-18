---
name: creative-divergence
description: 防止媒体运营内容被固定模板锁死。用于选题、角度、写稿、制作和竞争审校阶段，要求每条作品相对最近作品形成明确的思路差异、叙事差异、证据差异和视觉差异。
version: 1.0.0
---

# Creative Divergence

## Overview

标准化流程解决交付稳定性，但不能把每条内容压成同一种思路。

这个 skill 的目标是：保留流程、交付物和审核口径的稳定，同时要求每条作品在创意路径上有可见差异。用户可以感受到这是同一个账号的连续表达，而不是同一份模板换词。

## When to Use

- 用户反馈内容同质化、像模板批量生成
- 最近几期选题、开头、结构、证据或视觉套路过于相似
- 批量生产前需要为每条内容定义不同实验假设
- 竞争审校需要判断作品是否只是“合格但没必要看”

## Workflow

1. 读取最近 `3-5` 条已发布或已完成内容。
   - 优先读取 `retros/`、`publish/release-record.json`、`planning/topic-selection.json`、`angles/angle-brief.json`、`content/` 和 `review/competitive-scorecard.json`
   - 如果历史产物不足，明确写 `history_signal=incomplete`，但仍要基于可见内容做差异判断
2. 为当前内容输出 `creative-divergence-brief`，至少包含：
   - `recent_similarity_risks`
   - `same_series_reason`: 为什么仍属于同一账号或同一系列
   - `new_thinking_path`: 这期采用的新思考路径
   - `fresh_tension`: 新冲突、新反常识或新代价
   - `evidence_shift`: 证据类型如何不同
   - `narrative_device`: 叙事装置如何不同
   - `visual_language_shift`: 视觉语法或素材类型如何不同
   - `audience_job_shift`: 这期帮用户完成的任务和上期有什么不同
   - `experiment_hypothesis`: 这期验证什么创作假设
   - `forbidden_repeats`: 本期不能继续复用的开头、结构、话术、案例或视觉套路
3. 选题阶段先排除“母题相近且没有新任务”的候选题。
4. 角度阶段至少给出 `3` 种不同 lens，不允许只在同一论点上换标题。
5. 写稿阶段只能锁定少量 hard constraints，中段必须保留 freedom zones。
6. 制作阶段必须让视觉、案例、开头承诺或互动触发中的至少两项发生实质变化。
7. 竞争审校阶段如果模板疲劳明显，即使基础分合格，也只能给 `revise` 或 `block`。

## Divergence Axes

每条内容不需要所有维度都不同，但至少要在以下维度中命中 `3` 个：

- `position`: 立场变化，例如从诊断问题改为拆解机制、从反驳改为给选择标准
- `audience_job`: 用户任务变化，例如避坑、决策、复盘、行动清单、情绪托底
- `conflict`: 冲突变化，例如利益冲突、认知误区、时间代价、身份压力、机会窗口
- `evidence`: 证据变化，例如个人案例、平台数据、评论区样本、截图、实验、反例对照
- `narrative`: 叙事装置变化，例如悬疑拆解、现场复盘、清单挑战、反方辩论、失败案例
- `structure`: 结构变化，例如先结论后证明、先误区后机制、先案例后原则、双线并行
- `visual_language`: 视觉语法变化，例如数据图卡、屏幕证据、人物素材、场景 B-roll、手绘框架
- `interaction`: 评论或收藏触发变化，例如让用户投票、补充案例、对照自查、领取清单

## Output Artifacts

推荐保存为：

- `planning/creative-divergence-brief.json`
- `review/template-fatigue-report.json`

`creative-divergence-brief.json` 最少字段：

- `history_signal`
- `recent_similarity_risks`
- `divergence_axes`
- `same_series_reason`
- `new_thinking_path`
- `fresh_tension`
- `evidence_shift`
- `narrative_device`
- `visual_language_shift`
- `audience_job_shift`
- `experiment_hypothesis`
- `forbidden_repeats`
- `approval_decision`

`template-fatigue-report.json` 最少字段：

- `similarity_score`: `1-5`，分数越高越像模板复用
- `repeated_elements`
- `missing_divergence_axes`
- `audience_value_delta`
- `decision`: `pass`、`revise` 或 `block`
- `required_changes`

## Quality Gate

- 如果当前内容和最近内容只是在标题、措辞或案例名上变化，不算差异化。
- 如果 `similarity_score >= 4`，竞争审校不能 `pass`。
- 如果没有明确 `new_thinking_path`，不能进入制作阶段。
- 如果 `forbidden_repeats` 被当前稿件继续使用，必须退回角度或写稿阶段。
- 系列内容可以结构相近，但每期必须有不同的用户任务、证据抓手或叙事装置。

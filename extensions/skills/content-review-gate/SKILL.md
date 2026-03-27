---
name: content-review-gate
description: 对内容包执行发布前合规门禁，检查事实、品牌口径、敏感表达、合规风险、缺失字段和发布准备状态。
version: 1.0.0
---

# Content Review Gate

## Overview

在竞争审校通过后，阻止高风险内容流入账号。

## When to Use

- 内容已经制作完成，准备审核
- 用户要求校对、风控、品牌一致性检查
- 需要明确能否发布，以及哪些项必须修改
- 竞争审校已经给出结论，需要补最后一道发布门禁

## Review Checklist

- 事实是否有依据
- 竞争审校是否已经通过，是否仍存在明显弱点未修正
- `competitive_scorecard.total_score` 是否达到发布阈值
- `hook_strength`、`proof_strength`、`platform_fit` 是否都不低于 `3`
- 是否存在夸张承诺或误导性措辞
- 是否符合品牌口径和账号定位
- 标题、正文、标签、素材、账号、发布时间是否齐全
- 是否存在敏感词、侵权风险、平台规则冲突
- 如果是视频，封面、标题、字幕、口播、BGM、素材来源和账号映射是否完整
- 如果使用了网上片段，`source_manifest` 是否完整，许可状态是否允许当前用途，是否需要署名
- 如果使用生成式媒体，是否已经有明确的预算批准、密钥隔离和可替代方案

## Decision Model

输出必须是以下之一：

- `pass`: 可以进入发布
- `revise`: 可以修改后复审
- `block`: 当前不应发布

## Output Format

每个问题包含：

- `severity`
- `issue`
- `why_it_matters`
- `fix_recommendation`

## Rule

审核是门禁，不是润色。优先拦截高风险问题，并明确哪些问题必须回退给竞争审校或制作阶段处理。

如果竞争审校未达到发布阈值，合规门禁不能给 `pass`。

如果生成式视频尚未获批，或者素材来源不清晰，审核不能给 `pass`。

如果网上片段的许可状态不清楚，或者存在侵权疑点，审核不能给 `pass`。

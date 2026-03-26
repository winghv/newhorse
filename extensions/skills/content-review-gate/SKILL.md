---
name: content-review-gate
description: 对内容包执行发布前审核，检查事实、品牌口径、敏感表达、合规风险、缺失字段和发布准备状态。
version: 1.0.0
---

# Content Review Gate

## Overview

在发布前阻止高风险内容流入账号。

## When to Use

- 内容已经制作完成，准备审核
- 用户要求校对、风控、品牌一致性检查
- 需要明确能否发布，以及哪些项必须修改

## Review Checklist

- 事实是否有依据
- 是否存在夸张承诺或误导性措辞
- 是否符合品牌口径和账号定位
- 标题、正文、标签、素材、账号、发布时间是否齐全
- 是否存在敏感词、侵权风险、平台规则冲突

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

审核是门禁，不是润色。优先拦截高风险问题。

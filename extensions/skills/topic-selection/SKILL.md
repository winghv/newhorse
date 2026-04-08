---
name: topic-selection
description: 将研究结果与对标拆解转成内容选题池、优先级和单条内容 brief。用于选题判断、排期设计和内容方向取舍。
version: 1.0.0
---

# Topic Selection

## Overview

把“有什么能做”收敛成“下一步最值得做什么”。

## When to Use

- 已经有研究结果，需要排优先级
- 用户要选题、排期、做内容日历
- 需要把宽泛方向转成可制作 brief

## Workflow

1. 先把候选题材写成结构化 seed，而不是直接凭聊天内容做取舍：
   - 默认写到 `planning/topic-pool.json`
   - 每个候选题至少写清：
     - `topic`
     - `core_conflict`
     - `proof_handle`
     - `visual_handle`
     - `series_lane`
     - `why_now`
     - `lenses`
     - `production_cost`
2. 结合对标拆解里的空白位、最近几条已发内容和过饱和信号，运行：

```bash
python3 extensions/skills/topic-selection/scripts/build_topic_backlog.py \
  --project-root data/media-ops/<content-id> \
  --strategy-file data/media-ops/_strategy/<strategy>.json
```

3. 对每个候选题打分：
   - 业务价值
   - 平台适配
   - 题面具体度
   - 冲突张力
   - 证据抓手
   - 画面抓手
   - 系列价值
   - 新鲜度
   - 制作成本
   - 风险
   - 显式补：
     - `repeat_risk`
     - `recent_overlap`
     - `reference_signals`
4. 选出优先级最高的题材。
5. 为每个入选题输出 brief，并给角度设计阶段留下清晰输入：
   - 核心观点
   - 目标受众
   - 平台
   - 钩子
   - 证明素材
   - CTA
   - 禁区
   - 为什么这个题此刻值得做

## Rules

- 必须给出取舍理由，不能只列一堆题目
- 题面优先写“一个具体的人类陷阱”，不要把 `认知 / 框架 / 决策 / 提升` 这类抽象词直接当卖点
- 不同平台可以复用主题，但不能复用完全相同的呈现方式
- 若高分题材缺少关键证据或素材，先标记为待补充
- 如果最近两条内容已经打过相近主题，要显式扣重合分，避免连续输出“换词复读”
- 选题输出必须能让下游角度设计判断“靠什么赢”

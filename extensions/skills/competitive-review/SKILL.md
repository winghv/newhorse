---
name: competitive-review
description: 在发布前审查作品竞争力。用于评估钩子、观点、证据、节奏、视觉和平台适配度，判断内容是否具备与强内容竞争的能力。
version: 1.0.0
---

# Competitive Review

## Overview

这一步不回答“能不能发”，而回答“发出去靠什么赢”。

## When to Use

- 内容包已经完成，准备进入最后一轮质量判断
- 用户要求提高内容竞争力，而不是只做合规检查
- 需要为制作阶段给出更尖锐的修改意见

## Review Checklist

- 开头是否足够强，前 1-3 秒或前两行是否能拉住人
- 观点是否足够新，还是常见空话
- 是否有具体证据、案例、截图、数据或对比支撑
- 结构是否紧凑，信息密度是否足够
- 视觉或镜头提示是否具体
- 是否有评论、收藏、转发的触发点
- 是否符合平台原生表达，而不是模板化文案
- 如果是视频，封面、标题、开场和前 5-10 秒的证据画面是否形成一个闭环
- 是否在脚本还不够强时就试图靠昂贵生成素材硬撑质量

## Scorecard

每条内容必须按以下 7 个维度打分，每项 `1-5` 分：

- `hook_strength`: 开头是否足够抓人
- `novelty`: 角度是否新鲜，有没有避免陈词滥调
- `proof_strength`: 证据、案例、数据和对比是否扎实
- `platform_fit`: 是否真正符合目标平台的表达习惯
- `emotional_pull`: 是否有情绪张力或记忆点
- `save_share_potential`: 是否有收藏、转发、评论诱因
- `series_potential`: 是否值得扩展成系列内容

总分满分 `35`。

## Thresholds

评分结论不是主观印象，而是明确门槛：

- `pass`: 总分 `>= 29`，且没有任何单项低于 `3`
- `revise`: 总分在 `22-28` 之间，或存在任一单项等于 `2`
- `block`: 总分 `<= 21`，或 `hook_strength` / `proof_strength` / `platform_fit` 任一项 `<= 1`

额外规则：

- 即使总分达标，只要 `hook_strength`、`proof_strength`、`platform_fit` 任一项低于 `3`，也不能进入发布
- 如果作品只是“合格”，但没有明显赢点，优先判 `revise` 而不是勉强 `pass`

## Decision Model

输出必须是以下之一：

- `pass`: 有竞争力，可以进入合规门禁
- `revise`: 方向成立，但还不够强
- `block`: 当前版本没有明显赢面，不建议继续推进

## Output Format

- `competitive_scorecard`
- `score_by_dimension`
- `total_score`
- `review_decision`
- `top_issues`
- `why_it_loses`
- `stronger_alternatives`
- `must_fix_before_publish`
- `release_recommendation`

## Quality Gate

- 问题必须可执行，不能只说“更有吸引力一点”
- 优先指出最影响输赢的 1-3 个问题
- 不要把语气偏好误判成结构性问题
- 输出必须能让下游明确知道“这条内容为什么过线 / 没过线”

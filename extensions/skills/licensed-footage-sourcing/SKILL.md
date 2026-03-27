---
name: licensed-footage-sourcing
description: 为中长视频或需要 B-roll 的内容检索和规划合法来源的视频片段。用于生成查询词、片段清单、许可状态、署名要求、替代镜头和组装建议，不允许把无授权素材混入生产链。
version: 1.0.0
---

# Licensed Footage Sourcing

## Overview

中长视频很多时候不需要生成新视频，而是需要把讲解主线配上合适的 B-roll。这个 skill 的工作是把“网上找片段”变成可审计、可交接、可审核的 sourcing 包。

当 MiniMax 视频生成额度受限时，这个 skill 不是 fallback，而是主力方案之一。

## When to Use

- 目标产物是中长视频
- 需要补足情境镜头、转场镜头、气氛镜头或行业通用画面
- 希望减少高成本文本生成视频的使用
- 已知视频生成额度严格受限，例如每天仅 `6` 次、每次 `6` 秒

## Workflow

1. 先读 `angle brief` 或中长视频章节结构，明确每段片子的画面任务。
2. 为每段画面任务生成 `2-5` 组检索关键词：
   - 中文关键词
   - 英文关键词
   - 场景变体
3. 按来源类型组织候选：
   - 公共版权库
   - 已购素材库
   - 品牌自有授权素材
   - 可嵌入或可引用的官方公开视频素材
4. 为每个候选片段记录：
   - `source_url`
   - `shot_purpose`
   - `license_status`
   - `attribution_required`
   - `usage_notes`
   - `fallback_query`
5. 如果许可状态不清楚，直接标成 `hold`，不要混入可执行清单。
6. 使用 `assets/source-manifest.template.json` 作为输出骨架，确保字段完整且可审核。
7. 如需判断来源优先级、许可状态或是否可进生产链，读取 `references/source-tiers.md`。
8. 最后把可用片段串成 `source manifest` 和 `assembly suggestion`。

## Output Contract

最终输出至少包含：

- `clip_queries`
- `source_shortlist`
- `source_manifest`
- `license_summary`
- `attribution_notes`
- `hold_items`
- `assembly_suggestions`
- `fallback_options`

默认保存位置建议：

- `sources/source-manifest.json`
- `sources/clip-query-sheet.md`

## Source Rules

- 不使用来源不明的搬运视频
- 不抓取普通创作者片段来冒充可用 B-roll
- 优先官方、公共版权、已购或品牌自有授权来源
- 许可状态不明等于不可用，不要抱侥幸心理
- 不要只存链接，必须把许可判断写进 `source_manifest`

## Editing Rules

- 片段只服务于章节理解、转场或情境建立，不替代核心证据
- 每个片段都要说明“为什么需要它”
- 没有合适合法片段时，回退到截图动效、图表、录屏或自制镜头
- 对 Bilibili 这类中视频，默认先用合法片段包吃掉大部分 B-roll 需求，再决定是否保留 `1-2` 个生成镜头槽位

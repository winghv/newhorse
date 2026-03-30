---
name: midlong-video-production
description: 生成中长视频母稿。用于 2-12 分钟的教程、案例拆解、vlog 或解释型视频，产出开场承诺、章节、保留点、A-roll/B-roll 和切条机会。
version: 1.0.0
---

# Mid/Long Video Production

## Overview

中长视频不是把短视频拉长，而是要先控制结构、承诺兑现和中段留存。

默认思路是：讲解或叙事做主线，网上合法可用的应景片段做 B-roll 组装，AI 视频只补关键缺口。

## When to Use

- 目标产物是 `2-12` 分钟的中长视频
- 平台以 Bilibili 或其他解释型视频平台为主
- 需要同时兼顾完整观看和后续切条复用

## Workflow

1. 在前 `15-30` 秒先给结果、问题或收益，不要把铺垫写太长。
2. 把正片拆成章节，每个章节都要回答一个明确问题。
3. 每 `20-40` 秒设计一个保留点：
   - 新证据
   - 新反转
   - 新案例
   - 新操作步骤
4. 为每一章写明：
   - `chapter_goal`
   - `A-roll`
   - `B-roll`
   - `sourced_clip_need`
   - `proof_assets`
   - `cutdown_candidate`
   - `required_coverage_seconds`
   - `minimum_candidates`
   - `fallback`
5. 给每一章配置片段检索 brief：
   - 画面意图
   - 查询关键词
   - 来源类型
   - 许可要求
   - 替代镜头
6. 提前规划可以切成短视频的片段，而不是成片后再硬拆。

## Output Contract

最终输出至少包含：

- `working_title`
- `duration_target`
- `aspect_ratio`
- `cold_open`
- `viewer_payoff`
- `cognitive_punch_gate`
- `chapter_outline`
- `retention_beats`
- `master_script`
- `narration_script`
- `subtitle_source_script`
- `a_roll_plan`
- `b_roll_plan`
- `clip_sourcing_brief`
- `chapter_coverage_targets`
- `source_manifest`
- `proof_assets`
- `cutdown_candidates`
- `thumbnail_angles`
- `assembly_strategy`
- `asset_gaps`

## Rules

- 开场要先兑现承诺，不要先讲背景故事
- 每个章节都要推动理解，不允许“信息停滞段”
- 视觉刷新默认不晚于 `20-30` 秒
- 每章默认至少补一种证据：案例、常见错误动作、平台现象、反例或现实后果
- 解释型中视频默认要有清晰旁白主线，不允许只靠配乐和 B-roll 组装
- B-roll 不是装饰，而是帮助解释章节、转场或建立情境
- 默认优先使用合法来源的网上片段，而不是先想文本生成视频
- 如果已有 rough cut，可在母稿里直接说明后续应走 `retime_existing_cut` 还是 `rebuild_timeline`
- 如果某一章没有证据和画面支撑，要回到素材规划阶段补齐
- 如果某一章没有 `required_coverage_seconds`、候选素材数或 fallback，不算进入素材 sourcing gate
- 这只是母稿，不直接等同于最终平台上传包

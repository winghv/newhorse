---
name: content-production
description: 根据角度 brief 生成平台原生内容包。它是制作阶段的路由层，负责把图文、短视频和中长视频分流到对应 skill，并产出可交接的最终素材包。
version: 1.1.0
---

# Content Production

## Overview

从角度 brief 直接产出可执行内容包，并把“能不能赢”落实到开头、证据和视觉节奏里。

这个 skill 不再包办所有最终产物，而是先做路由，再把最终成片要求交给更细的 skill。

## When to Use

- 用户要制作短视频脚本、图文内容、社媒帖子
- 用户要制作中长视频脚本、章节或切条母稿
- 已经完成选题，需要进入具体产出阶段
- 需要把一个核心观点适配成多个平台版本

## Workflow

1. 读取 brief，确认平台、受众、目标动作、竞争优势和禁区。
2. 先判断最终交付物：
   - 图文笔记
   - 短视频
   - 中长视频
   - 长帖/线程
   - 社区帖子
3. 如果是中长视频，先走 `licensed-footage-sourcing`，输出网上合法片段的查询方向、来源清单和许可状态。
4. 如果是视频，再走 `video-asset-planning`，输出素材来源和生成预算决策。
5. 再选择基础产出 skill：
   - 短视频：`short-video-production`
   - 中长视频：`midlong-video-production`
6. 视频母稿完成后，再走 `minimax-narration-postproduction`，补齐旁白、字幕草案、混音说明和交付清单。
7. 再按最终平台生成包装元数据和上传素材说明：
   - 小红书短视频：`xiaohongshu-short-video-packaging`
   - 抖音短视频：`douyin-short-video-packaging`
   - 快手短视频：`kuaishou-short-video-packaging`
   - Bilibili 中长视频：`bilibili-midform-video-packaging`
8. 如果上游已经有 rough cut 或可渲染母版，再走 `video-postproduction-assembly`，产出 final cut、render manifest 和 verification 记录。
9. 非视频平台版本继续输出：
   - 标题/钩子（至少 2-3 个备选）
   - 正文/脚本
   - 视觉或镜头提示
   - 证据插入点
   - 保存/评论/转发触发点
   - CTA
   - 标签建议
10. 生成素材清单、缺口说明和平台成片包。

## Required Output Fields

如果是视频，最终 `content packet` 最少包含：

- `deliverable_type`
- `duration_target`
- `aspect_ratio`
- `master_script`
- `hook_variants`
- `beat_sheet`
- `narration_script`
- `subtitle_source`
- `asset_source_map`
- `source_manifest`
- `generation_budget_decision`
- `quota_snapshot`
- `voiceover_assets`
- `assembly_strategy`
- `render_plan`
- `render_manifest`
- `platform_package`
- `asset_checklist`
- `open_questions`

## Production Rules

- 先路由，再写稿；不要一上来就用一份通用脚本覆盖所有平台
- 平台原生优先，不要跨平台复制粘贴
- 短视频先写前 3 秒，再写主体
- 中长视频先写开场承诺、章节推进和切条点，再补完整细节
- 解释型视频默认要交付可执行的旁白和字幕，不允许只留“后面再补”
- 中长视频默认优先使用合法来源的网上片段做 B-roll 和气氛镜头，再考虑 AI 视频
- MiniMax 视频生成按稀缺资源处理。已知额度为每天 `6` 次、每次 `6` 秒时，默认只把它留给 `1-2` 个关键镜头
- 如果已进入 final cut 阶段，必须把装配策略、渲染计划和验证记录结构化保存，而不是只交一个最终文件
- 任何事实性陈述都要能追溯到 brief 或研究资料
- 高成本视频生成不是默认动作。脚本不过线、镜头替代方案存在、或生成收益不明确时，先不用
- 需要额外素材时直接列出来，不要藏在文字里
- 不只交一份“标准答案”，而要交付最有胜率的主版本和备选钩子

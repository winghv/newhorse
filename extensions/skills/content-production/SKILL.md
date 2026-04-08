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
4.1. 对视频内容，默认还要补：
   - `assets/scene-asset-plan.json`
   - `assets/visual-evidence-map.json`
   - `assets/generation-budget.json`
   - `assets/minimax-shot-plan.json`
   - `assets/generation-ledger.json`
   - `assets/visual-diversity-report.json`
5. 再选择基础产出 skill：
   - 短视频：`short-video-production`
   - 中长视频：`midlong-video-production`
5.1. 如果是知识/认知类中长视频，先走 `script-polishing`，把参考视频稿件沉淀成 `benchmarks/reference-script-patterns.json` 和 `content/script-polish-packet.json`，再进入母稿。
6. 如果是解释型中长视频，先补 `planning/cognitive-punch-gate.json`，至少回答误区、风险、机制、场景和可带走模板。
7. 视频母稿完成后，再走 `minimax-narration-postproduction`，补齐旁白、字幕草案、混音说明和交付清单。
8. 再按最终平台生成包装元数据和上传素材说明：
   - 小红书图文：`xiaohongshu-note-packaging`
   - 小红书短视频：`xiaohongshu-short-video-packaging`
   - 抖音短视频：`douyin-short-video-packaging`
   - 快手短视频：`kuaishou-short-video-packaging`
   - Bilibili 中长视频：`bilibili-midform-video-packaging`
9. 如果上游已经有 rough cut 或可渲染母版，再走 `video-postproduction-assembly`，产出 final cut、render manifest、assembly qa report 和 verification 记录。
10. 非视频平台版本继续输出：
   - 标题/钩子（至少 2-3 个备选）
   - 正文/脚本
   - 视觉或镜头提示
   - 证据插入点
   - 保存/评论/转发触发点
   - CTA
   - 标签建议
11. 生成素材清单、缺口说明和平台成片包。
12. 对视频内容，再补一份 `automation execution plan`，明确哪些步骤走 sourcing runner、哪些走确定性导出、哪些走 render workflow。

如果是小红书图文，必须额外输出：

- 首图承诺
- 页序规划
- 每页 headline / supporting text / visual direction
- 正文、首评、标签和评论诱因
- 是否需要 companion video 或系列联动

## Required Output Fields

如果是视频，最终 `content packet` 最少包含：

- `deliverable_type`
- `duration_target`
- `aspect_ratio`
- `master_script`
- `cognitive_punch_gate`
- `hook_variants`
- `script_polish_packet`
- `beat_sheet`
- `narration_script`
- `subtitle_source`
- `asset_source_map`
- `scene_asset_plan`
- `visual_evidence_map`
- `source_manifest`
- `generation_budget_decision`
- `generation_budget`
- `minimax_shot_plan`
- `generation_ledger`
- `quota_snapshot`
- `voiceover_assets`
- `assembly_strategy`
- `render_plan`
- `render_manifest`
- `automation_execution_plan`
- `platform_package`
- `publish_metadata`
- `asset_checklist`
- `open_questions`

如果是图文笔记，最终 `content packet` 最少包含：

- `deliverable_type`
- `title_variants`
- `cover_title`
- `cover_visual_direction`
- `page_plan`
- `caption`
- `first_comment`
- `tag_suggestions`
- `save_trigger`
- `comment_trigger`
- `follow_trigger`
- `publish_metadata`
- `asset_checklist`
- `open_questions`

## Production Rules

- 先路由，再写稿；不要一上来就用一份通用脚本覆盖所有平台
- 平台原生优先，不要跨平台复制粘贴
- 小红书图文不是长文切片，必须先明确首图承诺和页序
- 短视频先写前 3 秒，再写主体
- 中长视频先写开场承诺、章节推进和切条点，再补完整细节
- 知识/认知类中长视频先把参考稿件打法结构化，再写自己的母稿
- 解释型中长视频在进入配音前，必须先过 `cognitive punch gate`
- 解释型视频默认要交付可执行的旁白和字幕，不允许只留“后面再补”
- 中长视频默认优先使用合法来源的网上片段做 B-roll 和气氛镜头，再考虑 AI 视频
- 中长视频的证据层默认优先使用结构化 prompt proof、图卡和来源可审计的素材，不把人工录屏当默认依赖
- 中长视频每章都要先明确 proof asset / supporting b-roll / fallback graphics，而不是把镜头判断拖到剪辑阶段
- MiniMax 视频生成按稀缺资源处理。已知额度为每天 `6` 次、每次 `6` 秒时，默认只把它留给 `1-2` 个关键镜头
- 如果已进入 final cut 阶段，必须把装配策略、渲染计划和验证记录结构化保存，而不是只交一个最终文件
- 如果平台包装已经完成，必须同时补齐 `publish_metadata`，不要把账号、分区、标签和封面映射留到发布阶段临时猜
- 任何事实性陈述都要能追溯到 brief 或研究资料
- 高成本视频生成不是默认动作。脚本不过线、镜头替代方案存在、或生成收益不明确时，先不用
- 如果 `visual-diversity-report.json` 未过线，先补素材，不要继续堆特效或转场掩盖素材重复
- 需要额外素材时直接列出来，不要藏在文字里
- 不只交一份“标准答案”，而要交付最有胜率的主版本和备选钩子

解释型中长视频可直接用模板起草：

- `extensions/skills/content-production/assets/cognitive-punch-gate.template.json`

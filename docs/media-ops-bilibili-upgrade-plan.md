# Media Ops Bilibili Upgrade Plan

## 目标

把这次 B 站作品复盘，沉淀成可升级、可复用、可自动化执行的 media-ops 生产能力，而不是继续靠一次性的 prompt、人工兜底和主观审片。

本计划默认服务于 `Media Ops Butler` / `Video Production Director` 这条既有 runtime：

- `extensions/agents/`
- `extensions/skills/`
- `data/media-ops/<content-id>/`

不另起一套平行流程。

## 当前暴露出来的结构性问题

这些不是“审美意见”，而是当前 runtime 的明确缺口：

1. `extensions/skills/minimax-narration-postproduction/scripts/build_tts_handoff.py`
   - 目前输出的 segment 只有统一 `voice_id`、统一 `speed`，`emotion` 为空。
   - 这意味着口播“情绪、停顿、轻重音、章节节奏”没有进入结构化 handoff。
2. `extensions/skills/video-postproduction-assembly/scripts/build_render_plan.py`
   - 目前字幕样式是硬编码的 `DEFAULT_SUBTITLE_STYLE`。
   - 目前 SFX/BGM 触发依赖少量硬编码关键词，不能按内容语义生成音频设计。
3. `remotion/src/JudgmentEp01PremiumCut.tsx` 和 `remotion/src/BilibiliMidformRoughCut.tsx`
   - 当前更像“手工写死场景的模板成片”，不是由内容包驱动的 scene manifest。
   - 这会导致素材复用高、画面与章节证据弱绑定、风格难复用也难升级。
4. `data/media-ops/2026-03-27-bilibili-judgment-ep01/`
   - 已有 `voiceover-profile.json`，但缺少标准 `video-automation-plan` 和 `assembly-qa-report` 落地物，说明成片链路仍存在绕开标准 workflow 的旁路。
5. 现有文档对 MiniMax 视频额度默认写成每天 `6` 次，但本轮运营反馈是“每天只有 2 次可用调用”。
   - 这类额度不能继续硬编码在 skill 文案里，必须抽成 project-level quota 配置。

## 设计原则

1. 先升级契约，再升级素材和审美。
2. 所有新增能力都必须落成结构化 artifact，不接受只写 prompt。
3. 优先扩现有 agent，暂不新增 specialist，避免调度复杂度先失控。
4. 高成本生成只做“被预算门禁批准的镜头”，不是默认主力。
5. 任何“看起来高级”的效果，如果无法提升完播、理解或关注转化，就不进入默认流程。

## 五个专项

### 1. 结构增长专项

先解决“为什么这条视频值得被点开、看下去、愿意关注”，否则后面的声画升级只是在放大弱内容。

#### 目标

- 把“播放量 / 完播 / 收藏 / 关注转化”的策略输入前置到 `benchmark -> angle -> production -> review -> retros`。
- 形成可复用的 B 站中视频结构模板，而不是每条都从零写。

#### 运行时改动

- 升级 `extensions/skills/benchmark-analysis/SKILL.md`
- 升级 `extensions/skills/angle-design/SKILL.md`
- 升级 `extensions/skills/competitive-review/SKILL.md`
- 升级 `extensions/skills/performance-retrospective/SKILL.md`
- 升级 `extensions/agents/benchmark-analyst/agent.yaml`
- 升级 `extensions/agents/angle-designer/agent.yaml`
- 升级 `extensions/agents/competitive-reviewer/agent.yaml`
- 升级 `extensions/agents/performance-analyst/agent.yaml`

#### 新增结构化产物

- `benchmarks/bilibili-hook-patterns.json`
- `angles/attention-structure-template.json`
- `angles/follow-conversion-hooks.json`
- `review/opening-scorecard.json`

#### 建议新增脚本

- `extensions/skills/benchmark-analysis/scripts/build_bilibili_pattern_pack.py`
- `extensions/skills/angle-design/scripts/build_attention_structure.py`

#### 专项门禁

- 没有 `attention-structure-template.json`，不得进入视频制作。
- `competitive-review` 必须新增两项：
  - `opening_hold_power`
  - `follow_conversion_power`

当前阶段暂不把真实发布后的开场留存、评论追问、关注转化数据作为 workflow 依赖。
原因：

- Agent 拿不到稳定的真实平台数据
- 当前视频流量不足，数据噪声远大于信号
- 先把发布前结构做对，比过早引入伪复盘更重要

#### 验收

- 每条 B 站中视频都有“前 30 秒结构模板 + 评论触发 + 关注触发”。
- 对标输出可直接复刻为 shot/beat，不再只是文字摘要。

### 2. 口播、字幕、音频设计专项

把“情绪、语速、停顿、字幕准确率、字幕质感、BGM/SFX 节奏”从人工感觉，改成可执行的 postproduction contract。

#### 目标

- 让口播按内容分段变化，不再整条一个平速度、空 emotion。
- 字幕要么准确且有质感，要么明确走“无字幕设计”，不能中间态。
- BGM/SFX 变成按章节和语义触发，而不是硬编码几句关键词。

#### 运行时改动

- 升级 `extensions/skills/minimax-narration-postproduction/SKILL.md`
- 升级 `extensions/skills/video-postproduction-assembly/SKILL.md`
- 升级 `extensions/agents/video-production-director/agent.yaml`
- 升级 `extensions/skills/minimax-narration-postproduction/scripts/build_tts_handoff.py`
- 升级 `extensions/skills/minimax-narration-postproduction/scripts/build_subtitles_from_segments.py`
- 升级 `extensions/skills/video-postproduction-assembly/scripts/build_render_plan.py`
- 升级 `extensions/skills/video-postproduction-assembly/scripts/render_narrated_cut.py`

#### 新增结构化产物

- `content/postproduction/voice-performance-plan.json`
- `content/postproduction/audio-cue-sheet.json`
- `content/postproduction/subtitle-style-pack.json`
- `review/subtitle-quality-report.json`

#### 建议新增脚本

- `extensions/skills/minimax-narration-postproduction/scripts/build_voice_performance_plan.py`
- `extensions/skills/minimax-narration-postproduction/scripts/build_subtitle_style_pack.py`
- `extensions/skills/video-postproduction-assembly/scripts/build_audio_cue_sheet.py`

#### 关键契约变化

- `voiceover-segments.json` 每段至少支持：
  - `emotion`
  - `speed`
  - `pause_after_ms`
  - `intensity`
  - `scene_purpose`
- `subtitle-style-pack.json` 至少支持：
  - `theme`
  - `font_stack`
  - `font_size_rules`
  - `highlight_rules`
  - `safe_margin`
  - `burn_in_mode`
- `audio-cue-sheet.json` 至少支持：
  - `bgm_tracks`
  - `sfx_cues`
  - `ducking_rules`
  - `chapter_audio_beats`

#### 专项门禁

- `emotion=""` 的 segment 数量不能等于全部 segment。
- `subtitle-quality-report.json.status != pass` 时，不进入发布准备。
- 对讲解型视频，`audio-cue-sheet.json` 缺失时，不允许标记为“已完成 sound design”。

#### 验收

- 口播 profile 不再是单一平铺 voice 设置。
- 字幕可输出 `SRT + ASS/样式包`，不是只剩一个基础 SRT。
- 音频设计从关键词猜测升级为章节化 cue sheet。

### 3. 视觉素材与镜头资产专项

解决“画面像 PPT、素材太少、同一素材反复用、没有把 MiniMax 高级能力用在真正值钱镜头上”的问题。

#### 目标

- 把每章“用什么证明、用什么镜头承接、哪些镜头允许生成”做成 machine-readable 计划。
- 优先提高素材多样性和证据感，再决定是否消耗生成额度。

#### 运行时改动

- 升级 `extensions/skills/video-asset-planning/SKILL.md`
- 升级 `extensions/skills/licensed-footage-sourcing/SKILL.md`
- 升级 `extensions/skills/content-production/SKILL.md`
- 升级 `extensions/skills/video-postproduction-assembly/scripts/build_visual_timeline.py`
- 升级 `extensions/skills/media-ops-orchestration/scripts/build_video_automation_plan.py`

#### 新增结构化产物

- `assets/scene-asset-plan.json`
- `assets/visual-evidence-map.json`
- `assets/visual-diversity-report.json`
- `assets/minimax-shot-plan.json`
- `assets/generation-budget.json`
- `assets/generation-ledger.json`

#### 建议新增脚本

- `extensions/skills/video-asset-planning/scripts/build_scene_asset_plan.py`
- `extensions/skills/video-asset-planning/scripts/audit_visual_diversity.py`
- `extensions/skills/video-asset-planning/scripts/build_minimax_shot_plan.py`

#### 关键契约变化

- 每章都要声明：
  - `proof_asset`
  - `supporting_b_roll`
  - `fallback_graphics`
  - `max_repeat_uses`
  - `approved_generation_slots`
- `generation-budget.json` 必须项目级可配置，不再把“每天 2 次 / 6 次”写死在 skill 里。
- `minimax-shot-plan.json` 只允许列入已批准镜头：
  - `text-to-image`
  - `image-to-image`
  - `text-to-video`
  - `image-to-video`
  - `first-last-frame-video`

#### 专项门禁

- `visual-diversity-report.json.status != pass` 时，不进入 final render。
- 单素材重复次数超上限时，`auto-base-cut-plan.json` 必须给出阻塞。
- 未进入 `minimax-shot-plan.json` 的高成本镜头，不允许直接生成。

#### 验收

- 中长视频默认不再靠同一图卡或同一截图多次拉长。
- MiniMax 调用进入可审计 ledger，可复盘“这次调用换来了什么镜头价值”。

### 4. 装配、转场、特效专项

解决“Remotion 产物像模板堆砌、转场不贴内容、特效只是装饰”的问题。

#### 目标

- 从“写死的 composition”升级到“内容包驱动的 scene manifest”。
- 特效、转场、镜头运动和重点强调要跟章节语义绑定。

#### 运行时改动

- 升级 `extensions/skills/video-postproduction-assembly/SKILL.md`
- 升级 `extensions/skills/bilibili-midform-video-packaging/SKILL.md`
- 升级 `remotion/src/JudgmentEp01PremiumCut.tsx`
- 升级 `remotion/src/BilibiliMidformRoughCut.tsx`
- 视情况新增 `remotion/src/media-ops/` 下的 manifest-driven composition

#### 新增结构化产物

- `content/postproduction/scene-manifest.json`
- `content/postproduction/transition-plan.json`
- `content/postproduction/emphasis-fx-plan.json`
- `review/scene-assembly-report.json`

#### 建议新增脚本

- `extensions/skills/video-postproduction-assembly/scripts/build_scene_manifest.py`
- `extensions/skills/video-postproduction-assembly/scripts/build_transition_plan.py`
- `extensions/skills/video-postproduction-assembly/scripts/render_manifest_driven_cut.py`

#### 关键契约变化

- 每个 scene 至少声明：
  - `scene_id`
  - `chapter_id`
  - `scene_goal`
  - `primary_asset`
  - `motion_recipe`
  - `transition_in`
  - `transition_out`
  - `subtitle_mode`
  - `emphasis_fx`
- `transition_plan.json` 只允许语义型转场，不允许“为了有转场而转场”。
- B 站中视频默认要支持：
  - hook section
  - chapter entry
  - framework reveal
  - evidence insert
  - comment CTA

#### 专项门禁

- 没有 `scene-manifest.json` 的 Remotion 成片，不再算标准 workflow 输出。
- `scene-assembly-report.json` 需要校验：
  - 静态镜头占比
  - 重复素材告警
  - 转场密度
  - 字幕与重点词覆盖

#### 验收

- Remotion 从“手写一条视频”变成“渲染一类视频”。
- 章节特效和转场能够被复用到下一条 B 站中视频，而不是复制上一条 TSX。

### 5. 工作流编排、质量门禁、预算治理专项

把前四个专项真正并回 Butler runtime，避免再次出现“有成片，但没留下标准 artifacts 和 QA 记录”的旁路。

#### 目标

- 把专项状态并入 `media-ops-orchestration`。
- 让 `build_video_automation_plan` 能直接告诉操作者哪个专项没过线。
- 让发布门禁读到更细的质量状态，而不是只看 final cut 是否存在。

#### 运行时改动

- 升级 `extensions/skills/media-ops-orchestration/SKILL.md`
- 升级 `docs/media-ops-team.md`
- 升级 `docs/media-ops-workflow-spec.md`
- 升级 `extensions/skills/media-ops-orchestration/scripts/build_video_automation_plan.py`
- 升级 `extensions/skills/media-ops-orchestration/scripts/audit_artifacts.py`
- 升级 `extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py`

#### 新增结构化产物

- `review/workflow-quality-gate.json`
- `review/upgrade-status-board.json`
- `publish/prelive-quality-summary.json`

#### 质量门禁新增维度

- `growth_structure_status`
- `voice_performance_status`
- `subtitle_quality_status`
- `visual_diversity_status`
- `scene_assembly_status`
- `generation_budget_status`

#### 专项门禁

- 任一状态不是 `pass`，`publish manifest` 只能输出 `blocked` 或 `dry_run_only`。
- `build_video_automation_plan.py` 必须直接汇总五个专项，而不是只汇总 sourcing / svg / render。
- `audit_artifacts.py` 必须把新增 artifacts 纳入 required / conditional required。

#### 验收

- 成片、QA、预算、字幕、增长结构有统一状态板。
- 不再允许“成片出了，但工作流没有留下可复查证据”。

## 推荐执行顺序

### Phase 1

先做 `结构增长专项` + `工作流编排专项` 的最小骨架。

原因：

- 先确定“赢什么”和“怎么卡门禁”，再做视听升级，避免做出更精致的弱内容。

### Phase 2

做 `口播、字幕、音频设计专项`。

原因：

- 这是对当前产出质量影响最大的确定性改造，且主要改 Python scripts，收益快。

### Phase 3

做 `视觉素材与镜头资产专项`。

原因：

- 要先有预算 ledger 和 scene asset plan，后面才能稳定调用 MiniMax 高级能力。

### Phase 4

做 `装配、转场、特效专项`。

原因：

- 这一步依赖前面的 scene asset、voice/subtitle 和增长结构输入，适合最后把 Remotion 改成真正可复用的模板引擎。

## 本轮不做的事

- 不先新增一堆 specialist agent。
- 不先接入实时平台抓数或外网研究能力。
- 不把“爆款”抽象成一个万能 prompt。
- 不把 MiniMax 视频当主力内容生成引擎。

## Definition Of Done

当满足以下条件时，认为这套 B 站升级链路真正落地：

1. 任意一个 `data/media-ops/<content-id>` 都能稳定生成五个专项对应的结构化 artifacts。
2. `Video Production Director` 能按标准 workflow 产出成片，不再依赖手工旁路。
3. 竞争审校和发布门禁都能读取这些 artifacts，而不是只读文案和 final cut。
4. 下一条 B 站视频不需要重新讨论“字幕怎么做、情绪怎么调、镜头能不能生成、哪些地方该加音效”，只需要喂内容输入和预算参数。

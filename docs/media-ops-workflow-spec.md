# Media Ops Workflow Spec

## Goal

为 Newhorse 内置的媒体运营团队定义稳定、可审计、以作品竞争力为目标的自动化工作流。

## Operating Modes

系统支持两种运行模式：

- `autonomous-team`
  - 由 `media-ops-butler` 负责阶段推进和 specialist 调度
  - 阶段之间必须通过结构化交付物衔接
  - 真实发布仍受审批和账号门禁约束
- `supervisor-led`
  - 由外部主控 Agent 或人工主控驱动团队
  - 团队仍需交付同样的 handoff artifacts
  - 适合新工作流打磨、品牌敏感内容和高预算内容

无论哪种模式，评分卡、审核状态、发布门禁和渲染记录都不能省略。

## Stages

### 1. Research

输入：

- 账号矩阵
- 平台
- 目标受众
- 时间窗口
- 可用素材

输出：

- `research brief`
- `signal list`
- `evidence`
- `risk notes`
- `benchmark candidates`

### 2. Benchmark Analysis

输入：

- `research brief`
- `benchmark candidates`

输出：

- `benchmark deck`
- `pattern map`
- `whitespace`
- `anti-patterns`

### 3. Topic Selection

输入：

- `research brief`
- `benchmark deck`

输出：

- `topic backlog`
- `priority score`
- `selected topic`

### 4. Angle Design

输入：

- `selected topic`
- `benchmark deck`

输出：

- `angle brief`
- `hook hypotheses`
- `proof plan`
- `kill reasons`

### 5. Production

输入：

- `angle brief`

输出：

- `content packet`
- `platform variants`
- `hook variants`
- `visual plan`
- `asset checklist`
- `asset source map`
- `source manifest`
- `generation budget decision`
- `quota snapshot`
- `voiceover plan`
- `subtitle package`
- `assembly strategy`
- `render plan`
- `render manifest`
- `open questions`

如果产物是视频，`Production` 必须继续细分为：

1. `video shape`: `short-video` 或 `midlong-video`
2. `footage sourcing`: 如果是中长视频，先规划网上合法可用片段和可替代 B-roll
3. `asset planning`: 真实素材、截图、网上合法片段、动效、TTS、AI 图像、AI 视频分别如何分配
4. `narration postproduction`: 产出旁白、字幕草案、混音说明和渲染交接包
5. `platform packaging`: 按平台产出最终成片包，而不是拿一份通用脚本硬改
6. `postproduction assembly`: 把 rough cut、旁白、字幕和混音计划装配成 final cut，并留下渲染验证

推荐 skill 路由：

- `licensed-footage-sourcing`
- `short-video-production`
- `midlong-video-production`
- `video-asset-planning`
- `minimax-narration-postproduction`
- `video-postproduction-assembly`
- `xiaohongshu-short-video-packaging`
- `douyin-short-video-packaging`
- `kuaishou-short-video-packaging`
- `bilibili-midform-video-packaging`

### 6. Competitive Review

输入：

- `content packet`

输出：

- `competitive scorecard`
- `score_by_dimension`
- `total_score`
- `review decision`
- `issues`
- `stronger alternatives`

如果产物是视频，竞争审校至少额外检查：

- 前 `1-3` 秒是否先给结果、冲突或异常点
- 证据或画面证明是否在前 `5-10` 秒内出现
- 镜头与信息节奏是否足以支撑完播
- 封面/标题/开场是否协同
- 中长视频的 B-roll 是否真的服务于章节理解，而不是无意义填空
- 是否为了“看起来高级”而浪费生成预算
- 旁白是否清晰推进理解，而不是只做背景音
- 字幕是否和口播一致，是否影响阅读和看图

审核结论只允许：

- `pass`
- `revise`
- `block`

竞争审校门槛：

- `pass`: 总分 `>= 29/35`，且 `hook_strength`、`proof_strength`、`platform_fit` 都 `>= 3`
- `revise`: 总分 `22-28/35`，或存在单项 `= 2`
- `block`: 总分 `<= 21/35`，或关键单项 `<= 1`

### 7. Compliance Review

输入：

- `content packet`
- `competitive scorecard`

输出：

- `approval_status`
- `issues`
- `required fixes`

审批状态只允许：

- `pass`
- `revise`
- `block`

### 8. Publishing

输入：

- `content packet`
- `approval_status=pass`
- `publish manifest`

输出：

- `publish result`
- `per-platform status`
- `retry guidance`

### 9. Retrospective

输入：

- `publish result`
- `performance data`

输出：

- `performance summary`
- `win/loss factors`
- `next experiment brief`
- `series decision`

## Security Boundaries

- cookie、token、密钥只允许来自环境或外部受控运行时，不落盘到仓库
- 没有明确发布许可时，只允许 dry-run
- 真实发布必须显式 `--live`，并且发布清单 `decision=ready_for_live_publish`
- 发布日志必须脱敏
- 平台未接入自动化时，只输出手工发布包
- 竞争审校未通过时，不进入合规门禁和真实发布

## Handoff Contract

每个阶段最少交付这些字段：

- `objective`: 这条内容要完成什么目标
- `operating_mode`: `autonomous-team` 或 `supervisor-led`
- `audience`: 面向谁
- `platforms`: 投放平台
- `core_angle`: 核心观点或切入角度
- `evidence`: 关键事实、案例、素材来源
- `benchmark_refs`: 关键对标样本与观察点
- `hook_hypotheses`: 预期最有胜率的开头与评论触发点
- `deliverable_type`: 图文、短视频或中长视频
- `duration_target`: 目标时长
- `aspect_ratio`: 画幅，例如 `9:16` 或 `16:9`
- `risks`: 敏感点、依赖项、待确认项
- `asset_source_map`: 真实素材、截图、AI 图像、AI 视频、TTS、音乐的分配方案
- `source_manifest`: 网上素材的来源、用途、许可状态、署名要求和替代片段
- `generation_budget_decision`: 哪些生成动作获批，哪些被禁止，以及原因
- `quota_snapshot`: 当前可用的视频生成额度、已预留槽位、每个槽位对应镜头
- `voiceover_plan`: 是否需要旁白、使用什么 voice、哪些段落要混音控制
- `subtitle_package`: 字幕源、SRT 草案、烧录或外挂策略
- `assembly_strategy`: `retime_existing_cut`、`rebuild_timeline` 或其他明确装配决策
- `render_plan`: 后期装配、混音、字幕和编码参数
- `render_manifest`: final cut 输出、渲染参数和媒体验证摘要
- `competitive_score`: 竞争力评分或审校结论
- `score_by_dimension`: 钩子、证据、平台适配等维度分数
- `experiment_plan`: 这条内容要验证什么假设
- `next_action`: 下游应该做什么

## Suggested Workspace Layout

建议将产物保存到这些目录，方便下游角色接手：

- `research/`
- `benchmarks/`
- `planning/`
- `angles/`
- `content/`
- `assets/`
- `sources/`
- `review/`
- `publish/`
- `retros/`

视频 sourcing 产物建议命名：

- `sources/source-manifest.json`
- `sources/clip-query-sheet.md`

视频 final cut 相关文件建议放在：

- `content/postproduction/render-plan.json`
- `content/postproduction/render-manifest.json`
- `content/final-cut/*.mp4`
- `review/render-verification.md`

项目内可直接用命令跑这一步：

- `/media-render data/media-ops/<content-id>`
- `/media-publish-package data/media-ops/<content-id> --account-name <account>`

## Operating Rules

- 任何阶段都要明确区分事实、推断和建议。
- 如果上游交付物不完整，先指出缺口，不要自行脑补。
- 不要跨平台原样复用同一份文案。
- 视频生成预算属于生产约束，不是发布时才考虑的事；必须在素材规划阶段就做取舍。
- 如果已知 MiniMax 视频生成额度是每天 `6` 次、每次 `6` 秒，则默认把它视为 `36` 秒/天的稀缺镜头预算，而不是可随意试错的创意空间。
- 单条内容默认不应占用超过 `2` 次 MiniMax 视频生成；若计划使用 `3+` 次，必须写明为什么合法片段、录屏、图像动效和自有素材都不够。
- 解释型视频默认要交付旁白与字幕资产；如果刻意不用，必须写明原因与替代叙事方式。
- 中长视频优先组装来自合法来源的片段包，而不是默认走文本生成视频。
- 如果已经进入 final cut 装配阶段，必须保留 `render_plan` 和 `render_manifest`；只有文件没有记录，不算流程完成。
- 竞争审校解决“作品强不强”，合规门禁解决“能不能发”；两者不要混为一谈。
- 竞争审校必须给结构化分数，不能只给“感觉不错”之类的判断。
- 发布前必须有竞争审校结论、审核状态和账号/素材映射。

## Runtime Rules

- 总控模板 `media-ops-butler` 必须使用 `preferred_cli=butler`
- 专家模板可以走 `hello` runtime，但由 Butler 通过 `delegate_task` 调用
- 项目 runtime 必须与模板 metadata 保持一致

## Verification

- API 测试验证模板 metadata 与 runtime 同步
- E2E 测试验证首页选模板创建项目、项目内套模板
- 前端 build 和后端 pytest 必须通过

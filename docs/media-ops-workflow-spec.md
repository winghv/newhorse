# Media Ops Workflow Spec

## Goal

为 Newhorse 内置的媒体运营团队定义稳定、可审计、以作品竞争力为目标的自动化工作流。

## Runtime Source Of Truth

运行时配置真源只有：

- `extensions/agents/`
- `extensions/skills/`
- `<project>/.claude/agent.yaml`

`.agents/` 仅用于开发工具侧的技能包装和说明，不应承担产品运行时配置职责。

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

推荐模板映射：

- `autonomous-team` -> `media-ops-butler`
- `supervisor-led` -> `media-ops-supervisor`

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
- 如果平台包含小红书，还要输出 `search capture terms` 和 `comment question clusters`

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
- 如果平台包含小红书，还要输出 `series lanes` 和 `note_video_mix`

### 4. Angle Design

输入：

- `selected topic`
- `benchmark deck`

输出：

- `angle brief`
- `hook hypotheses`
- `proof plan`
- `kill reasons`
- 对解释型中长视频，还要输出 `cognitive punch gate`

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
- `source shortlist`
- `asset ingest manifest`
- `chapter coverage report`
- `generation budget decision`
- `quota snapshot`
- `voiceover plan`
- `subtitle package`
- `assembly strategy`
- `render plan`
- `render manifest`
- `assembly qa report`
- `automation execution plan`
- `open questions`

如果产物是视频，`Production` 必须继续细分为：

1. `video shape`: `short-video` 或 `midlong-video`
2. `footage sourcing`: 如果是中长视频，先规划网上合法可用片段和可替代 B-roll
3. `asset planning`: 真实素材、截图、网上合法片段、动效、TTS、AI 图像、AI 视频分别如何分配
4. `narration postproduction`: 产出旁白、字幕草案、混音说明和渲染交接包
5. `platform packaging`: 按平台产出最终成片包，而不是拿一份通用脚本硬改
6. `postproduction assembly`: 把 rough cut、旁白、字幕和混音计划装配成 final cut；如果 `assembly_strategy = rebuild_timeline` 且缺少 rough cut，必须自动从图卡、proof pack 和已获批素材拼出基础时间线，并留下渲染验证
7. `automation execution plan`: 把 sourcing、SVG 导出、proof pack、render 这些自动入口整理成可执行计划，避免退化成手工列表

推荐 skill 路由：

- `xiaohongshu-note-packaging`
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

如果产物是小红书图文，`Production` 至少还要交付：

- `cover_title`
- `cover_visual_direction`
- `page_plan`
- `caption`
- `first_comment`
- `tag_suggestions`
- `save_trigger`
- `comment_trigger`
- `follow_trigger`

对解释型中长视频，进入配音或装配前还要先通过：

- `planning/cognitive-punch-gate.json`
- `sources/chapter-coverage-report.json`
- `review/assembly-qa-report.json`

自动化优先规则：

- `B-roll` 默认先走 `licensed-footage-sourcing` runner，不靠人工逐段找素材
- 图卡、封面和其他 SVG 资产默认先走确定性导出，不靠人工截图导图
- Bilibili 封面如果走 AI 生成，默认是 `MiniMax 无字底图 + 本地确定性文字叠加`，不要把中文大字直接交给模型生成
- “AI 给出相反答案”这类证据，默认先产出结构化 `prompt proof pack` + 图卡，不把人工录屏当成默认必需品
- 缺字幕时，默认从 `voiceover-segments.json` + 已生成音频自动产出 `subtitle_draft`，不把人工逐句打轴当成默认步骤
- `rebuild_timeline` 缺 rough cut 时，默认自动生成 `auto-base-cut.mp4`，不再把“先手工剪一个母版”当成前置条件
- `rebuild_timeline` 自动生成的基础时间线必须同时输出质量摘要，例如 `image_slot_ratio`、`max_image_slot_duration_seconds`、`image_motion_enabled_count`，避免自动化可跑通但观感滑落
- 旁白驱动的视频在装配 QA 中必须额外检查 subtitle alignment drift，不能只验证“字幕存在”
- `supervisor-led` 可以增加人工检查，但 `autonomous-team` 不应因为缺少人工录屏或人工 checkpoint 而停住

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

如果产物是小红书图文，竞争审校至少额外检查：

- 首图和标题是否同一个承诺
- 页序是否有推进感，而不是流水账分卡
- 每页是否值得用户继续翻下一页
- 正文和首评是否补足了图上没说清的内容
- 收藏理由是否足够具体

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
- `release record`

发布门禁补充：

- 视频内容进入发布前，必须同时具备 `competitive-scorecard.json`、`review-gate.json`、`publish_metadata` 和 `publish/release-record.json`
- `rebuild_timeline` 视频如果缺少 `content/postproduction/auto-base-cut-plan.json`，或其中 `quality.status != pass`，则 `publish manifest` 只能是 blocked，不得进入 live prep
- Bilibili 中长视频的 `publish_metadata` 至少要包含 `account_name`、`partition`、`partition_name`、`tags` 和封面/上传素材路径；缺任一项都不算 ready
- AI 判断力 / 职场成长类 Bilibili 中长视频，默认分区应为 `知识 -> 职业职场 (209)`，不是 `计算机技术`
- 当前原生 `sau bilibili upload-video` 没有封面参数；Bilibili 自动发布如果带封面，必须走 workflow 内的 repo-local uploader wrapper
- `publish/release-record.json` 里仍要区分 `cover_asset_ready`、`cover_delivery_status` 和 `cover_set`
- 对 Bilibili 已提交稿件，当前自动化仍不支持“原稿刷新”；当 `publish_metadata.publish_status = ready_for_live_refresh` 时，manifest 必须 block，避免重复投稿

### 9. Retrospective

输入：

- `publish result`
- `performance data`

输出：

- `performance summary`
- `win/loss factors`
- `next experiment brief`
- `series decision`
- 如果平台包含小红书，还要输出 `comment insights`、`profile visit signal` 和 `follow conversion readout`

真实发布刚完成时，先运行：

- `python3 extensions/skills/performance-retrospective/scripts/bootstrap_post_publish_followup.py --project-root data/media-ops/<content-id>`

## Security Boundaries

- cookie、token、密钥只允许来自环境或外部受控运行时，不落盘到仓库
- 没有明确发布许可时，只允许 dry-run
- 真实发布必须显式 `--live`，并且 `publish-manifest-prelive.json` 或 `live-execution-plan.json` 明确显示 `decision=ready_for_live_publish`
- 批量投产前先运行 `python3 extensions/skills/media-ops-orchestration/scripts/build_publish_queue.py --media-ops-root data/media-ops`，按 `ready_for_live / blocked` 队列决定执行顺序
- 对 `rebuild_timeline` 视频，`build_publish_queue.py` 必须同时透出 `assembly_strategy` 和 `auto_base_quality_status`，并把 `auto_base_quality_not_passed` / `auto_base_quality_report_missing` 映射成显式阻塞原因
- `publish/release-record.json` 是发布链路的单一真源；最终视频路径、上传版路径、封面路径、voice、runtime、状态回写都以它为准
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
- `account_positioning`: 如果是账号运营任务，说明账号定位和关注理由
- `evidence`: 关键事实、案例、素材来源
- `benchmark_refs`: 关键对标样本与观察点
- `hook_hypotheses`: 预期最有胜率的开头与评论触发点
- `deliverable_type`: 图文、短视频或中长视频
- `series_lanes`: 如果平台包含小红书，说明栏目和系列位
- `note_video_mix`: 如果平台包含小红书，说明图文 / 短视频分工
- `search_capture_terms`: 如果平台包含小红书，说明搜索承接词
- `duration_target`: 目标时长
- `aspect_ratio`: 画幅，例如 `9:16` 或 `16:9`
- `risks`: 敏感点、依赖项、待确认项
- `cognitive_punch_gate`: 对解释型中长视频，记录误区、风险、机制、场景和可带走模板
- `asset_source_map`: 真实素材、截图、AI 图像、AI 视频、TTS、音乐的分配方案
- `source_manifest`: 网上素材的来源、用途、许可状态、署名要求和替代片段
- `chapter_coverage_report`: 每章候选数、已批准时长、单镜头风险和 fallback
- `asset_ingest_manifest`: 已下载入库的外部素材、本地路径、来源 URL 和下载方式
- `generation_budget_decision`: 哪些生成动作获批，哪些被禁止，以及原因
- `quota_snapshot`: 当前可用的视频生成额度、已预留槽位、每个槽位对应镜头
- `voiceover_plan`: 是否需要旁白、使用什么 voice、哪些段落要混音控制
- `subtitle_package`: 字幕源、SRT 草案、烧录或外挂策略
- `assembly_strategy`: `retime_existing_cut`、`rebuild_timeline` 或其他明确装配决策
- `render_plan`: 后期装配、混音、字幕和编码参数
- `render_manifest`: final cut 输出、渲染参数和媒体验证摘要
- `assembly_qa_report`: freeze/static、duration、outro、字幕交付方式等 QA 结果
- `automation_execution_plan`: 自动 sourcing、导图、proof pack、render 的执行顺序与命令入口
- `publish_metadata`: 平台上传所需账号、分区、标签、封面和上传素材映射
- `competitive_score`: 竞争力评分或审校结论
- `score_by_dimension`: 钩子、证据、平台适配等维度分数
- `experiment_plan`: 这条内容要验证什么假设
- `comment_ops_plan`: 这条内容发布后评论区如何承接
- `release_record`: 发布链路唯一真源，记录最新 manifest/result、素材路径和平台返回标识
- `next_action`: 下游应该做什么

## Suggested Workspace Layout

建议将产物保存到这些目录，方便下游角色接手：

- `strategy/`
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

- `planning/cognitive-punch-gate.json`
- `sources/source-manifest.json`
- `sources/source-shortlist.json`
- `sources/chapter-coverage-report.json`
- `sources/clip-query-sheet.md`
- `sources/asset-ingest-manifest.json`

视频 final cut 相关文件建议放在：

- `content/postproduction/render-plan.json`
- `content/postproduction/render-manifest.json`
- `content/final-cut/*.mp4`
- `review/render-verification.md`
- `review/assembly-qa-report.json`
- `publish/release-record.json`

项目内可直接用命令跑这一步：

- `/media-render data/media-ops/<content-id>`
- `/media-source-footage data/media-ops/<content-id> --download-approved`
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
- 解释型中长视频在进入配音前，必须先回答“误区 / 风险 / 机制 / 痛点场景 / 可带走模板”五个问题；答不全就不进入后期。
- 中长视频每章都要声明 `required_coverage_seconds`、候选素材数和 fallback；没有章节覆盖报告，不进入 live 准备。
- 如果已经进入 final cut 装配阶段，必须保留 `render_plan` 和 `render_manifest`；只有文件没有记录，不算流程完成。
- 装配后的 QA 至少要检查 freeze/static、duration 对齐、结尾语义和字幕交付方式；`assembly-qa-report.json` 未通过时，不进入发布门禁。
- 竞争审校解决“作品强不强”，合规门禁解决“能不能发”；两者不要混为一谈。
- 竞争审校必须给结构化分数，不能只给“感觉不错”之类的判断。
- 发布前必须有竞争审校结论、审核状态和账号/素材映射。
- `supervisor-led` 模式可以保留三个固定人工 checkpoint：只看前 `30-60s` punch、只听样音与节奏、只看完整 QA；`autonomous-team` 不以此作为默认阻塞条件。

## Runtime Rules

- 总控模板 `media-ops-butler` 必须使用 `preferred_cli=butler`
- 专家模板可以走 `hello` runtime，但由 Butler 通过 `delegate_task` 调用
- 项目 runtime 必须与模板 metadata 保持一致

## Verification

- API 测试验证模板 metadata 与 runtime 同步
- E2E 测试验证首页选模板创建项目、项目内套模板
- 前端 build 和后端 pytest 必须通过
- 产物治理检查必须可运行：`python3 extensions/skills/media-ops-orchestration/scripts/audit_artifacts.py --media-ops-root data/media-ops`
- 批量生产场景建议追加 `--fail-on-missing-required`，把缺失关键产物的内容包直接拦截到整改队列
- 版本治理建议在发布阶段后执行：`python3 extensions/skills/media-ops-orchestration/scripts/compact_publish_artifacts.py --project-root data/media-ops/<content-id> --apply`，保留关键版本并归档其余文件
- 若要统一编排治理，可直接运行：`python3 extensions/skills/media-ops-orchestration/scripts/run_artifact_maintenance.py --media-ops-root data/media-ops --apply`

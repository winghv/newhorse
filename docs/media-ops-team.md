# 媒体运营 Agent Team

这套内置团队已经从基础的 `研究 -> 选题 -> 制作 -> 审核 -> 发布`，升级为更强调作品竞争力的闭环：

`研究 -> 对标拆解 -> 选题 -> 创意差异 brief -> 角度设计 -> 剧本打磨 -> 制作 -> 竞争审校 -> 合规门禁 -> 发布 -> 复盘`

新增的 `创意差异 brief` 不是为了破坏流程稳定性，而是防止作品被流程模板锁死。流程可以相近，栏目可以稳定，但每条内容必须说明它相对最近作品的新思考路径、证据变化、叙事装置和视觉语言变化。

整条流水线仍由一个总控 Butler 串起来，但现在不仅能“发出去”，还会追求“为什么这条内容有赢面”。

对于视频内容，`制作` 阶段进一步拆成了四层：

- `内容骨架`：先区分短视频还是中长视频
- `素材策略`：先判断真实素材、截图、网上合法片段、动效、TTS、图像、视频生成分别怎么用
- `平台包装`：先按平台 skill 产出最终包的标题、封面、字幕与元数据要求
- `后期装配`：最后把 rough cut、旁白、字幕和混音计划装配成可上传 final cut

## 适用场景

- 同时运营多个平台或多个账号
- 需要把内容生产流程标准化
- 希望把发布动作接到已有自动化上传能力
- 希望每个阶段都有可交接产物，而不是只拿到一段聊天回复

## 团队成员

| Template ID | 角色 | 负责内容 |
| --- | --- | --- |
| `media-ops-butler` | 总控 | 协调整条流水线，决定下一步该交给谁 |
| `media-ops-supervisor` | 主控模板 | 面向 `supervisor-led` 模式，强调阶段批准、可审计交付物和人工复核 |
| `trend-researcher` | 研究 | 趋势、竞品、评论区、历史表现、素材线索 |
| `benchmark-analyst` | 对标拆解 | 拆头部内容的钩子、结构、证据、视觉与互动模式 |
| `topic-strategist` | 选题 | 选题池、优先级、内容日历、单条 brief |
| `angle-designer` | 角度设计 | 生成高胜率切入角度、钩子假设、证明路径与评论诱因 |
| `script-doctor` | 剧本打磨 | 基于优秀参考稿件沉淀写稿打法包、rewrite 契约和 delegate brief |
| `content-producer` | 制作 | 标题、脚本、图文、口播、素材清单、平台改写 |
| `video-production-director` | 视频生产总导演 | 把视频 brief 推进成完整成片包，负责母稿、后期装配与渲染验证 |
| `competitive-reviewer` | 竞争审校 | 评估作品和平台前 10% 内容相比靠什么赢，哪里还不够强 |
| `compliance-reviewer` | 合规门禁 | 事实、品牌口径、敏感表达、缺失项、门禁结论 |
| `distribution-operator` | 发布 | 发布清单、定时、自动上传、dry-run、结果回填 |
| `performance-analyst` | 复盘 | 回填表现、总结赢点与失误，并产出下一轮实验建议 |

## 技能分层

### 编排技能

- `media-ops-orchestration`

### 阶段技能

- `content-research`
- `benchmark-analysis`
- `reference-video-ingest`
- `script-polishing`
- `topic-selection`
- `creative-divergence`
- `angle-design`
- `content-production`
- `xiaohongshu-account-ops`
- `video-asset-planning`
- `minimax-narration-postproduction`
- `licensed-footage-sourcing`
- `video-postproduction-assembly`
- `short-video-production`
- `midlong-video-production`
- `xiaohongshu-note-packaging`
- `xiaohongshu-short-video-packaging`
- `douyin-short-video-packaging`
- `kuaishou-short-video-packaging`
- `bilibili-midform-video-packaging`
- `competitive-review`
- `content-review-gate`
- `multi-platform-publishing`
- `publishing-security-guard`
- `performance-retrospective`

### 已复用的发布技能

- `xiaohongshu-upload`
- `douyin-upload`
- `kuaishou-upload`
- `bilibili-upload`

## 如何使用

1. 在首页选择 `Media Ops Butler`
1.1. 如果你要跑 `supervisor-led`，优先选择 `Media Ops Supervisor`；如果你要跑自治批量生产，优先选择 `Media Ops Butler`
2. 输入你的运营目标，例如平台、账号、受众、节奏、现有素材
3. 如果目标平台包含小红书，先让 Butler 产出账号定位、内容支柱、图文/短视频配比和评论区运营简报
4. Butler 会按阶段调度 specialist，并在项目目录里逐步沉淀研究、对标、角度、内容、审核、发布和复盘产物
4.1. 如果已经拿到可直接拆的参考视频 URL / BV 号，先运行 `python3 extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py --project-root data/media-ops/<content-id> --source-url <video-url>`，把 transcript artifacts 沉淀到 `research/`
4.2. 如果参考视频库已经积累到可用规模，再运行 `python3 extensions/skills/script-polishing/scripts/build_reference_script_patterns.py --project-root data/media-ops/<content-id>`，把优秀稿件的写稿打法沉淀成 `benchmarks/reference-script-patterns.json`
4.3. 如果要重新做 B 站 backlog，不要直接口头列题。先写 `planning/topic-pool.json` 或共享 strategy file，再运行 `python3 extensions/skills/topic-selection/scripts/build_topic_backlog.py --project-root data/media-ops/<content-id> --strategy-file data/media-ops/_strategy/<strategy>.json`，把“候选题 -> 参考信号 -> 打分 -> 去重 -> selected topic”落成 `planning/topic-selection.json`
4.4. 每条内容进入 angle 前必须补 `planning/creative-divergence-brief.json`，明确这期和最近 `3-5` 条内容在哪些维度不同，以及哪些开头、结构、案例或视觉套路本期禁止继续复用
4.5. B 站中视频进入剧本定稿前，先运行 `python3 extensions/skills/content-research/scripts/build_bilibili_material_search_brief.py --project-root data/media-ops/<content-id>`，生成 `research/material-search-brief.json`，把同题候选视频、评论区问题、案例和可视化素材线索交给 `script-polishing`
5. 如果你已经配置了上传环境与账号状态，发布阶段会优先调用现有 upload skills
6. 如果中长视频需要自动找外部素材并把获批片段沉淀到生产链，运行 `/media-source-footage data/media-ops/<content-id> --download-approved`
7. 如果项目里已有图卡、封面或其它 SVG 资产，先运行 `python3 extensions/skills/video-asset-planning/scripts/export_svg_assets.py --project-root data/media-ops/<content-id> --include-root-assets`，统一导出 PNG，而不是人工逐张处理
8. 对解释型中长视频，在进入配音或装配前，先补齐 `planning/cognitive-punch-gate.json`、`sources/chapter-coverage-report.json`、`assets/visual-production-gate.json` 和 `review/assembly-qa-report.json`
9. 同时运行 `python3 extensions/skills/media-ops-orchestration/scripts/build_video_automation_plan.py --project-root data/media-ops/<content-id>`，确认 B-roll、图卡导出、proof pack 和 render workflow 的自动入口都已接通
10. 如果视频内容包已经具备旁白 handoff，也可以直接运行项目命令 `/media-render data/media-ops/<content-id>` 自动生成字幕草案、必要时自动拼出基础时间线、写出 `render-plan.json`、`assembly-qa-report.json` 并执行后期装配
11. 如果是 Butler / specialist 在 `data/projects/<project-id>` 里执行，默认走 `video-production-director` 内置的 runner 命令，而不是手动拼 ffmpeg
12. 发布前可以先运行 `/media-publish-package data/media-ops/<content-id> --account-name <account>`，自动从最新 `render-manifest` 生成 `publish-manifest-auto.json`，并同步维护 `publish/release-record.json`
13. 默认发布 workflow 走 `/media-publish data/media-ops/<content-id> --account-name <account>`，它会自动回填 `publish-result-auto.json`；只有显式加 `--live` 才允许真实发布
14. 每天或每轮批量生产结束后运行 `/media-artifacts-audit data/media-ops`，统一生成 `_registry/artifact-registry.json` 和 `_registry/artifact-registry.md`，用于查看缺失项、状态分布和整改优先级
15. 对版本堆积的内容包运行 `/media-artifacts-compact data/media-ops/<content-id> --apply`，把非关键 manifest/result 归档到 `publish/archive/`，保留最新与里程碑版本
16. 如果希望一键完成治理，直接运行 `/media-artifacts-maintain data/media-ops --apply`，它会自动执行 `audit -> compact -> re-audit`

更正式的阶段输入输出和运行时约束，见 [media-ops-workflow-spec.md](/Users/mac/VscodeProjects/newhorse/docs/media-ops-workflow-spec.md)。

## 运行时真源

运行时真正生效的配置只有这三类：

- 全局模板：`extensions/agents/`
- 全局技能：`extensions/skills/`
- 项目覆盖：`<project>/.claude/agent.yaml`

`.agents/` 只用于本地开发工具的技能元数据，不直接决定产品运行时行为。

## 视频流程说明

视频不再只靠一个通用 `content-production` skill 直接出稿，而是按下面的逻辑路由：

1. `content-production` 先判定这条内容是短视频还是中长视频，以及主投平台
2. 如果主投平台是 Bilibili 中视频，先在 `benchmark-analysis` 和 `angle-design` 阶段补齐增长结构 artifacts：
   - `benchmarks/bilibili-hook-patterns.json`
   - `angles/attention-structure-template.json`
   - `angles/follow-conversion-hooks.json`
2.0. 在进入 angle 之前，优先让 `topic-selection` 先把候选池写成 `planning/topic-pool.json`，并把最近已做题目、参考视频标题信号和 `proof_handle / visual_handle` 一起纳入去重逻辑，避免连续两条只是在复述同一个母题
2.0.1. 在进入 angle 之前，还要补 `planning/creative-divergence-brief.json`。同一个系列可以保持相近栏目结构，但必须至少在用户任务、证据类型、叙事装置、视觉语法或互动触发中改变 `3` 个维度
2.1. 如果 benchmark 阶段已经拿到参考视频 URL / BV 号，优先补 `research/reference-video-metadata.json`、`research/reference-transcript.srt` 和 `research/reference-transcript.md`，再做模式拆解
2.2. 如果参考视频库已经积累到可用规模，再让 `script-doctor` 或 `script-polishing` 补：
   - `benchmarks/reference-script-patterns.json`
   - `content/script-polish-packet.json`
3. 如果是中长视频，优先用 `licensed-footage-sourcing` 规划网上合法可用片段，再进入素材策略
4. `video-asset-planning` 先做素材策略和生成预算门禁，并补齐：
   - `assets/scene-asset-plan.json`
   - `assets/visual-evidence-map.json`
   - `assets/generation-budget.json`
   - `assets/minimax-shot-plan.json`
   - `assets/generation-ledger.json`
   - `assets/visual-diversity-report.json`
5. 对解释型中长视频，先补 `cognitive punch gate`，再进入样音和后期
6. 通用母稿由以下 skill 之一产出：
   - `short-video-production`
   - `midlong-video-production`
7. `minimax-narration-postproduction` 再把母稿补成可执行的旁白、字幕和混音后期包
7.1. 对旁白驱动视频，默认还要补 `voice-performance-plan.json` 和 `subtitle-style-pack.json`
8. 如果最终交付物是小红书图文，直接走 `xiaohongshu-note-packaging`
9. 视频场景的平台包装再交给以下 skill 之一：
   - `xiaohongshu-short-video-packaging`
   - `douyin-short-video-packaging`
   - `kuaishou-short-video-packaging`
   - `bilibili-midform-video-packaging`
10. 竞争审校阶段如果是 Bilibili 中视频，再补 `review/opening-scorecard.json`，专门检查前 `30` 秒 promise -> proof 闭环和结尾桥接
10.1. 竞争审校还要检查模板疲劳。如果作品只是上一期的换词版，输出 `review/template-fatigue-report.json`，并且不能判 `pass`
11. `video-postproduction-assembly` 把 rough cut、旁白、字幕和混音计划装配成 final cut；如果没有 rough cut 且策略是 `rebuild_timeline`，则自动用图卡、proof pack 和已获批 B-roll 拼出基础时间线，再写出 `audio-cue-sheet.json`、render manifest、assembly qa report、subtitle quality report 与验证记录
11.1. 如果 `visual-diversity-report.json` 没过线，不要继续靠转场或配乐掩盖素材重复，先回到素材计划层补章级资产
11.2. 对旁白驱动中视频，进入 render 前默认还要补 `scene-manifest.json`、`transition-plan.json` 和 `emphasis-fx-plan.json`；render 后要补 `scene-assembly-report.json`
12. 发布前还要统一生成：
   - `review/workflow-quality-gate.json`
   - `review/upgrade-status-board.json`
   - `publish/prelive-quality-summary.json`

这样做的目的不是“多加几个 skill”，而是把平台原生差异落到可交接的最终产物里。

如果目标平台是小红书，建议先额外产出一份账号运营简报，至少说明：

- 账号定位与关注理由
- 内容支柱和系列位
- 图文 / 短视频配比
- 搜索承接词
- 评论区运营计划
- 复盘指标和实验池

## 运行模式

这套团队现在支持两种正式运行模式：

- `autonomous-team`
  - 由 `media-ops-butler` 主控，按阶段自动委派 specialist
  - 视频场景默认优先交给 `video-production-director`
  - 只要没有满足审批、账号、素材等门禁，就停在 dry-run 或待审状态
- `supervisor-led`
  - 由外部主控 Agent 或人工主控推进阶段
  - 主控默认通过 specialist 推进阶段，不自己吞掉研究、写稿、审校和发布执行
  - 主控可以直接调用 `media-ops-butler`，也可以按阶段单独调度 specialist
  - 适合在工作流还在打磨、品牌要求高、或需要更强质量把关时使用

建议两者都做：

- 自治模式负责稳定批量生产
- 主控模式负责打磨新流程、发现缺口、定义新 skill 与门禁

对 `supervisor-led`，建议把主控理解成“导演 + 制片”：

- 主控负责：阶段拆解、brief 压缩、门禁判断、结果整合
- specialist 负责：研究、对标、选题、角度、制作、审校、发布执行
- 每次委派都要带结构化 stage brief：
  - `stage`
  - `objective`
  - `inputs`
  - `constraints`
  - `required_artifacts`
  - `acceptance_criteria`
- 每次 specialist 返回后，主控都要先判断：
  - 产物是否齐全
  - 门禁是否满足
  - 是否建议批准下一步

## 外部 Skill 采纳原则

像 `find-skills` 这样的 skill 可以用于发现市场上的能力模块，但外部 skill 在这套工作流里默认只扮演“候选能力源”，而不是主流程契约本身。

采纳外部视频 skill 时至少要过这几关：

- 来源可信，维护状态清楚
- 能明确说明输入输出，而不是只会生成一段泛化结果
- 能在我们的质量门禁之前或之后插入，不破坏主流程
- 能接受密钥只走环境变量，不把 token、cookie 落盘
- 失败时有本地 fallback，不会把整条生产链卡死

对“网上找视频片段来组装”这件事，默认要求也一样：

- 优先公共版权库、已购素材库、品牌自有授权素材
- 每个片段都要留下 `source manifest`，至少记录来源、用途、许可状态和是否需要署名
- 如果已经下载到本地，还要留下 `asset-ingest-manifest`，记录本地路径和下载来源

## 建议输入

为了让自动化更稳定，建议在第一次任务里提供这些信息：

- 账号矩阵与平台
- 小红书图文 / 短视频各自承担什么角色
- 目标受众
- 本周或本月目标
- 想要对标的账号或作品类型
- 品牌/行业禁区
- 素材来源目录
- 是否允许自动发布，还是只做到审核通过

## 发布安全

发布阶段默认遵循以下规则：

- 竞争审校不过，不进入合规门禁与发布
- 竞争审校必须输出评分卡，总分和关键单项都过线才允许进入下一步
- 缺少审批状态时，只做 dry-run
- 缺少素材、cookie、账号映射时，不强行发布
- 真实发布必须显式带 `--live`，并且 `publish-manifest-prelive.json` 或 `live-execution-plan.json` 已经明确 `ready_for_live_publish`
- 批量投产前先运行 `python3 extensions/skills/media-ops-orchestration/scripts/build_publish_queue.py --media-ops-root data/media-ops`，不要人工逐个翻目录判断是否能发
- 对视频 final cut，缺少 `assembly_strategy`、`render_plan` 或 `render_manifest` 时，不算完成
- 对 `rebuild_timeline` 视频，`auto-base-cut-plan.json` 缺失或 `quality.status != pass` 时，不得进入 live prep；发布队列里必须把它标成 `improve_auto_timeline_quality`
- 对 Bilibili 中长视频，没有完整 `publish_metadata` 的账号、分区、标签和封面映射时，不算发布就绪
- `publish/release-record.json` 是发布链路的唯一真源，不再允许多个 manifest/result 各自漂移
- 发布结果文件必须脱敏，不能把 cookie、token、密钥写入项目目录
- 不跨平台原样群发相同文案
- 对未接入的平台，输出手工发布包或待接入方案
- 复盘结论要回流到研究、选题和角度设计，而不是只停在数据报表
- 对 AI 视频生成要设预算门禁：脚本不过线、素材替代方案存在、或日额度不足时，不消耗高价视频生成次数
- MiniMax 视频生成如果是每天 `6` 次、每次 `6` 秒，默认只留给最关键的 `1-2` 个镜头；中视频主体仍以合法片段、录屏、截图动效和旁白驱动
- 对中长视频，默认优先用网上合法片段做 B-roll 组装；AI 视频只补关键且无法替代的镜头
- 对解释型视频，默认要补齐旁白、字幕和混音说明；只有视频和配乐不算完成
- 对旁白驱动视频，`assembly-qa-report.json` 必须额外校验 subtitle alignment drift；字幕存在但和口播边界对不齐，仍然不算过线
- 对解释型中长视频，自治模式默认先跑自动 gate、自动 sourcing、自动导图和自动 render；人工 checkpoint 只属于 `supervisor-led` 复核层，不再是 Production 默认依赖
- 对“AI 对话录屏”这类证据素材，默认先用结构化 prompt proof pack、图卡和可审计的 UI/文本资产替代；人工录屏只作为 fallback

更细的小红书账号运营建议和交付模板见 [xiaohongshu-account-ops.md](/Users/mac/VscodeProjects/newhorse/docs/xiaohongshu-account-ops.md)。

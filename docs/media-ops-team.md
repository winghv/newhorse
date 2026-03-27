# 媒体运营 Agent Team

这套内置团队已经从基础的 `研究 -> 选题 -> 制作 -> 审核 -> 发布`，升级为更强调作品竞争力的闭环：

`研究 -> 对标拆解 -> 选题 -> 角度设计 -> 制作 -> 竞争审校 -> 合规门禁 -> 发布 -> 复盘`

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
| `trend-researcher` | 研究 | 趋势、竞品、评论区、历史表现、素材线索 |
| `benchmark-analyst` | 对标拆解 | 拆头部内容的钩子、结构、证据、视觉与互动模式 |
| `topic-strategist` | 选题 | 选题池、优先级、内容日历、单条 brief |
| `angle-designer` | 角度设计 | 生成高胜率切入角度、钩子假设、证明路径与评论诱因 |
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
- `topic-selection`
- `angle-design`
- `content-production`
- `video-asset-planning`
- `minimax-narration-postproduction`
- `licensed-footage-sourcing`
- `video-postproduction-assembly`
- `short-video-production`
- `midlong-video-production`
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
2. 输入你的运营目标，例如平台、账号、受众、节奏、现有素材
3. Butler 会按阶段调度 specialist，并在项目目录里逐步沉淀研究、对标、角度、内容、审核、发布和复盘产物
4. 如果你已经配置了上传环境与账号状态，发布阶段会优先调用现有 upload skills
5. 如果视频内容包已经具备 rough cut、旁白和字幕，也可以直接运行项目命令 `/media-render data/media-ops/<content-id>` 自动生成 `render-plan.json` 并执行后期装配
6. 如果是 Butler / specialist 在 `data/projects/<project-id>` 里执行，默认走 `video-production-director` 内置的 runner 命令，而不是手动拼 ffmpeg
7. 发布前可以先运行 `/media-publish-package data/media-ops/<content-id> --account-name <account>`，自动从最新 `render-manifest` 生成 `publish-manifest-auto.json`
8. 默认发布 workflow 走 `/media-publish data/media-ops/<content-id> --account-name <account>`，它会自动回填 `publish-result-auto.json`；只有显式加 `--live` 才允许真实发布

更正式的阶段输入输出和运行时约束，见 [media-ops-workflow-spec.md](/Users/mac/VscodeProjects/newhorse/docs/media-ops-workflow-spec.md)。

## 视频流程说明

视频不再只靠一个通用 `content-production` skill 直接出稿，而是按下面的逻辑路由：

1. `content-production` 先判定这条内容是短视频还是中长视频，以及主投平台
2. 如果是中长视频，优先用 `licensed-footage-sourcing` 规划网上合法可用片段，再进入素材策略
3. `video-asset-planning` 先做素材策略和生成预算门禁
4. 通用母稿由以下 skill 之一产出：
   - `short-video-production`
   - `midlong-video-production`
5. `minimax-narration-postproduction` 再把母稿补成可执行的旁白、字幕和混音后期包
6. 平台包装再交给以下 skill 之一：
   - `xiaohongshu-short-video-packaging`
   - `douyin-short-video-packaging`
   - `kuaishou-short-video-packaging`
   - `bilibili-midform-video-packaging`
7. `video-postproduction-assembly` 把 rough cut、旁白、字幕和混音计划装配成 final cut，并写出 render manifest 与验证记录

这样做的目的不是“多加几个 skill”，而是把平台原生差异落到可交接的最终产物里。

## 运行模式

这套团队现在支持两种正式运行模式：

- `autonomous-team`
  - 由 `media-ops-butler` 主控，按阶段自动委派 specialist
  - 视频场景默认优先交给 `video-production-director`
  - 只要没有满足审批、账号、素材等门禁，就停在 dry-run 或待审状态
- `supervisor-led`
  - 由外部主控 Agent 或人工主控推进阶段
  - 主控可以直接调用 `media-ops-butler` 或单独调度 `video-production-director`
  - 适合在工作流还在打磨、品牌要求高、或需要更强质量把关时使用

建议两者都做：

- 自治模式负责稳定批量生产
- 主控模式负责打磨新流程、发现缺口、定义新 skill 与门禁

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
- 不抓取无授权创作者内容来充当 B-roll
- 每个片段都要留下 `source manifest`，至少记录来源、用途、许可状态和是否需要署名

## 建议输入

为了让自动化更稳定，建议在第一次任务里提供这些信息：

- 账号矩阵与平台
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
- 真实发布必须显式带 `--live`，并且 `publish-manifest-auto.json` 的 `decision` 已经是 `ready_for_live_publish`
- 对视频 final cut，缺少 `assembly_strategy`、`render_plan` 或 `render_manifest` 时，不算完成
- 发布结果文件必须脱敏，不能把 cookie、token、密钥写入项目目录
- 不跨平台原样群发相同文案
- 对未接入的平台，输出手工发布包或待接入方案
- 复盘结论要回流到研究、选题和角度设计，而不是只停在数据报表
- 对 AI 视频生成要设预算门禁：脚本不过线、素材替代方案存在、或日额度不足时，不消耗高价视频生成次数
- MiniMax 视频生成如果是每天 `6` 次、每次 `6` 秒，默认只留给最关键的 `1-2` 个镜头；中视频主体仍以合法片段、录屏、截图动效和旁白驱动
- 对中长视频，默认优先用网上合法片段做 B-roll 组装；AI 视频只补关键且无法替代的镜头
- 对解释型视频，默认要补齐旁白、字幕和混音说明；只有视频和配乐不算完成

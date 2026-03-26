# 媒体运营 Agent Team

这套内置团队把内容运营拆成 `研究 -> 选题 -> 制作 -> 审核 -> 发布` 五段流水线，并通过一个总控 Butler 串起来。

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
| `topic-strategist` | 选题 | 选题池、优先级、内容日历、单条 brief |
| `content-producer` | 制作 | 标题、脚本、图文、口播、素材清单、平台改写 |
| `compliance-reviewer` | 审核 | 事实、品牌口径、敏感表达、缺失项、门禁结论 |
| `distribution-operator` | 发布 | 发布清单、定时、自动上传、dry-run、结果回填 |

## 技能分层

### 编排技能

- `media-ops-orchestration`

### 阶段技能

- `content-research`
- `topic-selection`
- `content-production`
- `content-review-gate`
- `multi-platform-publishing`
- `publishing-security-guard`

### 已复用的发布技能

- `xiaohongshu-upload`
- `douyin-upload`
- `kuaishou-upload`
- `bilibili-upload`

## 如何使用

1. 在首页选择 `Media Ops Butler`
2. 输入你的运营目标，例如平台、账号、受众、节奏、现有素材
3. Butler 会按阶段调度 specialist，并在项目目录里逐步沉淀研究、内容、审核和发布产物
4. 如果你已经配置了上传环境与账号状态，发布阶段会优先调用现有 upload skills

更正式的阶段输入输出和运行时约束，见 [media-ops-workflow-spec.md](/Users/mac/VscodeProjects/newhorse/docs/media-ops-workflow-spec.md)。

## 建议输入

为了让自动化更稳定，建议在第一次任务里提供这些信息：

- 账号矩阵与平台
- 目标受众
- 本周或本月目标
- 品牌/行业禁区
- 素材来源目录
- 是否允许自动发布，还是只做到审核通过

## 发布安全

发布阶段默认遵循以下规则：

- 缺少审批状态时，只做 dry-run
- 缺少素材、cookie、账号映射时，不强行发布
- 不跨平台原样群发相同文案
- 对未接入的平台，输出手工发布包或待接入方案

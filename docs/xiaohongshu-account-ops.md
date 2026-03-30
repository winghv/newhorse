# 小红书账号运营工作流

## 目标

把小红书从“支持发布的平台”升级成 media-ops 里的完整账号运营轨道。

这条轨道默认同时管理：

- 账号定位
- 内容支柱
- 图文 / 短视频分工
- 评论区运营
- 复盘与实验池

## 推荐运行方式

### 第一阶段：Supervisor-led

先由主控或人工审核跑通：

- 账号运营简报
- 图文包装包
- 短视频包装包
- dry-run 发布清单
- 评论区回复模板

目标是先稳定出结构化产物，而不是一开始就自动 live。

### 第二阶段：半自动

允许系统自动生成：

- 选题池和内容日历
- 小红书图文发布包
- 小红书短视频发布包
- 发布 dry-run 和定时建议

保留人工审核：

- 栏目是否继续
- 标题与首图是否过线
- 是否进入真实发布

### 第三阶段：有限自动发布

只有在满足这些条件后再进入真实投产：

- 账号定位和栏目矩阵已经稳定
- 图文和短视频至少各跑过一轮复盘
- 评论区运营模板已验证不过度营销
- 发布 manifest 决策已到 `ready_for_live_publish`
- cookie / 账号状态稳定且可审计

## 核心交付物

### 账号层

- `strategy/xiaohongshu-account-brief.json`
- `strategy/xiaohongshu-content-pillars.md`
- `strategy/xiaohongshu-experiment-backlog.json`

### 单条内容层

- `content/xiaohongshu-note.json`
- `content/xiaohongshu-short-video.json`
- `review/competitive-scorecard.json`
- `review/review-gate.json`
- `publish/publish-manifest-auto.json`
- `publish/publish-result-auto.json`

### 复盘层

- `retros/xiaohongshu-performance-summary.md`
- `retros/comment-insights.json`
- `retros/next-experiment-brief.json`

## 小红书特有判断标准

### 图文

- 首图和标题是否给了明确承诺
- 页序是否让人愿意继续翻
- 是否具备收藏理由
- 正文和首评是否补足图片信息

### 短视频

- 前 1-3 秒是否给结果或冲突
- 是否适合与图文形成 companion pair
- 评论区是否有明确追问入口

### 账号

- 内容是否在强化同一个关注理由
- 图文和短视频是否各自承担不同职责
- 是否持续积累搜索词和系列位
- 收藏、主页访问、关注转化是否一起改善

## 投产前检查

- 小红书账号运营简报已存在且最近一次复盘后已更新
- 选题 brief 明确标出这是图文还是短视频
- 图文包包含首图承诺、页序、正文、首评、标签
- 发布 workflow 默认为 dry-run，live 仅在显式批准时执行
- 批量投产前运行 `python3 extensions/skills/media-ops-orchestration/scripts/build_publish_queue.py --media-ops-root data/media-ops --platform xiaohongshu`，先看哪些包 `ready_for_live`、哪些包还被门禁卡住
- 发布结果不回写 cookie、token 或密钥
- 复盘会回流到栏目和实验池，而不是停在单条数据汇总

## 发布后接管

- 真实发布刚完成时，运行 `python3 extensions/skills/performance-retrospective/scripts/bootstrap_post_publish_followup.py --project-root data/media-ops/<content-id>`
- 先生成 `retros/comment-insights.json`、`retros/profile-visit-signal.json`、`retros/follow-conversion-readout.json` 和 `retros/live-monitoring-checklist.md`
- 如果当前只能人工看评论和数据，再运行 `python3 extensions/skills/performance-retrospective/scripts/bootstrap_comment_ops_packet.py --project-root data/media-ops/<content-id>`
- 它会补 `retros/manual-observation-log.json` 和 `retros/comment-reply-playbook.md`
- 再按 `T+2h / T+24h / T+48h` 回填评论、主页访问和关注转化，不要把 live 后观察继续写在 dry-run 文案里
- 如果 `comment-insights.json` 里已经出现明确的 follow-up 方向，再运行 `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_followup_note_package.py --project-root data/media-ops/<content-id>`，直接起下一条图文包
- follow-up 图文包起好后，再运行 `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_note_review.py --project-root data/media-ops/<new-content-id>`，先完成竞争审校和 review gate
- 如果 review 结果是“竞争力通过但缺视觉稿”，保持 `reviewed_not_ready`，先补页卡资产，不要硬进 publish
- 如果缺的是页卡视觉稿，再运行 `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_note_asset_brief.py --project-root data/media-ops/<new-content-id>`，把设计 brief、每页输出路径和 prompt 文档一次性补齐

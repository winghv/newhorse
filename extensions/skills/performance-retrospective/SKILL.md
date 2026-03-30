---
name: performance-retrospective
description: 对已发布内容做复盘。用于总结表现、拆解赢点与失误，并输出下一轮选题、角度和创作实验建议。
version: 1.0.0
---

# Performance Retrospective

## Overview

复盘不是报流水账，而是把结果转成下一轮更强的输入。

## When to Use

- 内容已经发布，拿到了平台反馈或业务结果
- 用户想从账号历史中提炼可复制打法
- 需要为研究、选题和角度设计回流经验

## Workflow

1. 收集结果：
   - 曝光
   - 完播/停留
   - 收藏/转发/评论
   - 主页访问
   - 关注转化
   - 私信/线索/转化
2. 对比发布前假设：
   - 哪个钩子兑现了
   - 哪个证明点有效
   - 哪些地方流失严重
3. 归因：
   - 赢点
   - 失误
   - 偶然因素
4. 输出下一轮建议：
   - 继续放大的模式
   - 应该停止的模式
   - 下一条实验假设
5. 如果内容刚完成真实发布，先运行 `python3 extensions/skills/performance-retrospective/scripts/bootstrap_post_publish_followup.py --project-root data/media-ops/<content-id>`，自动生成监测 checklist、评论洞察模板和转化回填文件，再开始人工观测。
6. 如果平台没有评论/指标读取 API，再运行 `python3 extensions/skills/performance-retrospective/scripts/bootstrap_comment_ops_packet.py --project-root data/media-ops/<content-id>`，生成人工观测日志和评论回复 playbook。
7. 如果内容包还没真实发布，但已经完成 dry-run 或 ready-for-live 准备，先运行 `python3 extensions/skills/performance-retrospective/scripts/bootstrap_prepublish_retros.py --project-root data/media-ops/<content-id>`，补齐 `retro-plan`、初始 `performance_summary` 和 `next-experiment-brief`，保证审计与后续观测契约完整。

如果平台是小红书，额外关注：

- 首图和标题是否带来了高质量点击
- 收藏是否来自真正有用的信息密度，而不是只靠情绪标题
- 评论区是否出现可继续做下一条的高频追问
- 主页访问和关注转化是否说明账号定位越来越清晰

推荐回填文件：

- `retros/comment-insights.json`
- `retros/profile-visit-signal.json`
- `retros/follow-conversion-readout.json`
- `retros/live-monitoring-checklist.md`
- `retros/manual-observation-log.json`
- `retros/comment-reply-playbook.md`

## Output Template

- `performance_summary`
- `win_factors`
- `loss_factors`
- `next_experiments`
- `series_decision`
- `feedback_to_research`

## Quality Gate

- 明确区分数据、推断和建议
- 不把单条偶然爆发误判为稳定规律
- 复盘结论必须能回流给上游阶段继续用

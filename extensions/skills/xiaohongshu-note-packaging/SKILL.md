---
name: xiaohongshu-note-packaging
description: 把图文母稿包装成小红书原生图文笔记发布包，输出首图承诺、页序规划、标题、正文、首评、标签、评论诱因和发布元数据。
version: 1.0.0
---

# Xiaohongshu Note Packaging

## Overview

把图文母稿转成适合小红书发布的最终笔记包，而不是只给一段正文。

## When to Use

- 最终平台是小红书
- 交付物是图文笔记、知识卡片、清单帖或教程帖
- 需要结构化的标题、页序、正文、首评和标签

## Packaging Rules

- 首图和标题必须说同一件事，优先给结果、误区或对比
- 页序必须有推进感，不要把一整篇长文拆成多张废卡
- 每页只承担一个主要信息点，并说明用户为什么值得继续翻
- 正文不是逐页抄图，要补背景、限制条件和评论触发点
- 结尾页优先触发收藏、评论、关注或系列期待
- 如果这条图文适合联动短视频，要明确 companion video 方案

## Output Contract

最终输出至少包含：

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

## Page Plan Requirements

`page_plan` 至少说明：

- `page`
- `role`
- `headline`
- `supporting_text`
- `visual_direction`
- `evidence`
- `handoff_note`

## Rules

- 没有首图承诺和页序，不算最终图文发布包
- 图文应优先满足“可保存、可搜索、可复看”
- 一条图文最多只保留一个主承诺，不要一贴塞三个主题
- 标签要服务搜索和人群进入，不要机械堆热点词

## Templates

需要结构化产物时，优先复用：

- `assets/xiaohongshu-note-package.template.json`

如果要从一条已经真实发布的小红书内容继续起 follow-up 图文包，运行：

- `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_followup_note_package.py --project-root data/media-ops/<content-id>`

它会基于 `retros/next-experiment-brief.json` 和 `retros/comment-insights.json` 自动生成新的 `research/`、`planning/`、`angles/` 和 `content/xiaohongshu-note.json`。

如果要把图文包推进到 review 阶段，运行：

- `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_note_review.py --project-root data/media-ops/<content-id>`

它会生成 `review/competitive-scorecard.json` 和 `review/review-gate.json`。如果内容方向强但视觉稿未补齐，脚本会保持 `approval_status=revise`，不会误判为可发。

如果 review gate 提示“缺视觉稿”，再运行：

- `python3 extensions/skills/xiaohongshu-note-packaging/scripts/bootstrap_note_asset_brief.py --project-root data/media-ops/<content-id>`

它会生成 `assets/note/note-asset-brief.json`、`assets/note/image-prompts.md`，并把 `content/xiaohongshu-note.json` 的 `image_plan` 落到具体页卡输出路径。

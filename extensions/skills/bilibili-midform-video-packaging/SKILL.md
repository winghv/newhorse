---
name: bilibili-midform-video-packaging
description: 把中长视频母稿包装成 Bilibili 原生视频成片包，输出标题、封面方向、简介、章节、置顶评论、切条标记和上传元数据。
version: 1.0.0
---

# Bilibili Midform Video Packaging

## Overview

把中长视频母稿变成适合 Bilibili 发布的完整上传包，并保留后续切条空间。

## When to Use

- 最终平台是 Bilibili
- 产物是 `2-12` 分钟的中长视频

## Packaging Rules

- 前 `15-30` 秒必须先给收益、结果或关键问题
- 标题和封面要共同承诺一个明确收益
- 正文简介用于补背景、链接、时间轴和资料，不复读口播
- 章节划分要利于回看和收藏
- 默认交付完整旁白与字幕包，除非这是故意设计的无口播作品
- 提前标出可切成短视频的片段

## Output Contract

最终输出至少包含：

- `title_variants`
- `cover_text`
- `cover_visual_direction`
- `video_description`
- `chapter_markers`
- `pinned_comment`
- `runtime_target`
- `subtitle_package`
- `voiceover_mix_notes`
- `thumbnail_options`
- `cutdown_markers`
- `publish_metadata`

## Rules

- 不要把短视频口播直接拉长后当成中长视频
- 对讲解型 B 站视频，没有字幕包和旁白混音说明时，不算最终上传包
- 如果最终要交付可上传成片，继续把包装结果交给 `video-postproduction-assembly`
- 没有章节结构和封面方向时，不算最终上传包
- `publish_metadata` 不能只写平台名；至少要补齐 `account_name`、`partition`、`partition_name`、`tags`、`cover_asset` 和 `upload_asset`
- AI 判断力 / 职场成长这类 Bilibili 知识向内容，默认优先放 `知识 -> 职业职场 (209)`，不要再机械落到 `计算机技术`
- 封面如果走 MiniMax 自动化，模型只负责无字底图；中文标题、标签和视觉层级必须走本地确定性叠加，避免中文失真

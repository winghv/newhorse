---
name: douyin-short-video-packaging
description: 把短视频母稿包装成抖音原生短视频成片包，输出强开场、字幕节奏、标题、描述、标签和发布元数据。
version: 1.0.0
---

# Douyin Short Video Packaging

## Overview

抖音包的重点是开场冲击、节奏推进和早证据，不是把别的平台文案直接挪过来。

## When to Use

- 最终平台是抖音
- 产物是 `15-60s` 的竖版短视频

## Packaging Rules

- 第一秒就给结论、冲突或异常点
- 前 `3-5` 秒必须有画面证据或结果预告
- 字幕密度要支撑节奏，但不能遮住关键画面
- 默认每 `2-4` 秒有一次信息或镜头推进
- CTA 更直接，优先评论、关注或进入下一条

## Output Contract

最终输出至少包含：

- `title_variants`
- `description`
- `subtitle_strategy`
- `hook_overlay_text`
- `runtime_target`
- `beat_switch_notes`
- `tag_suggestions`
- `cta_line`
- `publish_metadata`

## Rules

- 不能只把小红书正文压缩一下就当抖音包
- 如果前 `3-5` 秒没有强证明，优先回退母稿而不是硬发

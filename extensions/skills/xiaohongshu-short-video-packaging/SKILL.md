---
name: xiaohongshu-short-video-packaging
description: 把短视频母稿包装成小红书原生短视频成片包，输出封面大字、标题、正文、首评、标签、镜头节奏和发布元数据。
version: 1.0.0
---

# Xiaohongshu Short Video Packaging

## Overview

把短视频母稿转成适合小红书发布的最终包，而不是简单复述脚本。

## When to Use

- 最终平台是小红书
- 产物是短视频或竖版视频
- 需要封面、标题、正文、首评和发布包

## Packaging Rules

- 开场优先“结果先给”或“误区先打”
- 封面大字要能独立成立，默认 `8-12` 个字内
- 正文不要逐字抄口播，要补充背景、方法和评论触发点
- 画面与字幕要偏“可保存、可复看”，不要只是快节奏堆字
- 结尾优先触发收藏、评论或下一条系列期待

## Output Contract

最终输出至少包含：

- `title_variants`
- `cover_text`
- `cover_visual_direction`
- `caption`
- `first_comment`
- `tag_suggestions`
- `runtime_target`
- `shot_rhythm_notes`
- `save_trigger`
- `publish_metadata`

## Rules

- 标题、封面、开场三者必须同一个承诺
- 如果这条内容适合和图文联动，要在包里说明 companion note 方案
- 没有独立封面方案时，不算最终成片包

---
name: reference-video-ingest
description: 提取参考视频的元数据与字幕。用于把 B 站 URL/BV 号这类对标样本，沉淀成可审计的 transcript artifacts，供 benchmark、剧本打磨和 competitive review 使用。
version: 1.0.0
---

# Reference Video Ingest

## Overview

对标研究里，最容易退化成手工动作的一步，就是“看别人视频、抄一点笔记、再凭记忆总结”。

这个 skill 把参考视频采集结构化：

- 输入参考视频 URL 或 B 站 BV 号
- 先尝试提取现成字幕
- 没有现成字幕时，再尝试下载音频并走 ASR fallback
- 写出 metadata、SRT、可读 transcript 和来源说明
- 如果没有字幕，也明确标记需要后续 ASR，而不是静默失败

当前版本优先支持 Bilibili，后续可以扩展到 YouTube 等平台。

## When to Use

- 需要拆解某条参考视频的结构、语言、节奏和案例
- 需要把参考视频转成可搜索、可引用的 transcript
- 需要为 benchmark analysis、剧本打磨或 competitive review 准备证据输入

## Workflow

1. 提供参考视频 URL，或对 Bilibili 提供 BV 号。
2. 用 `yt-dlp` 先拉 metadata，判断是否存在官方字幕或自动字幕。
3. 优先提取官方字幕；没有时再尝试自动字幕。
4. 如果没有现成字幕，再尝试下载音频并用本机 ASR CLI 转写。
5. 统一写出：
   - `research/reference-video-metadata.json`
   - `research/reference-transcript.srt`
   - `research/reference-transcript.md`
   - `research/reference-transcript-source.json`
6. 如果没有可提取字幕且没有可用 ASR，仍然写 metadata 和 source artifact，并把状态标成 `needs_asr`。

## Workflow Runner

```bash
python3 extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py \
  --project-root data/media-ops/<content-id> \
  --bvid BV1YjwyzTEHB
```

或：

```bash
python3 extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py \
  --project-root data/media-ops/<content-id> \
  --source-url https://www.bilibili.com/video/BV1YjwyzTEHB
```

## Output Contract

- `reference_video_metadata`
- `reference_transcript_srt`
- `reference_transcript_markdown`
- `reference_transcript_source`

## Rules

- 不把字幕提取能力误当成事实判断能力；下游仍然要自己拆结构和论点。
- 没有字幕时，不允许伪造 transcript。
- 如果 transcript 来自 ASR fallback，要在 source artifact 里明确标记，不要伪装成官方字幕。
- 结果里必须保留原始 URL、提取方式、语言和是否需要 ASR fallback。
- 当前版本优先服务 research / benchmark，不直接替代最终发布字幕链。

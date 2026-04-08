---
name: minimax-narration-postproduction
description: 用 MiniMax TTS 和本地 FFmpeg 为视频生成配音、字幕草案、混音说明和交付清单。用于补齐短视频和中长视频成片里经常缺失的旁白与字幕资产。
version: 1.0.0
---

# MiniMax Narration Postproduction

## Overview

把已经通过脚本与素材规划的视频母稿，继续推进成真正可剪、可审、可发布的“后期包”。

默认目标不是炫技，而是补齐这几类关键资产：

- 可执行的 `narration_script`
- 可直接送入 TTS 的 `tts_input`
- `voice-performance-plan.json`
- 与口播一致的 `subtitle_source`
- `srt_draft`
- `subtitle-style-pack.json`
- `mix_notes`
- `delivery_checklist`

## When to Use

- 视频已经有 `master_script` 或 `narration_script`
- 需要补旁白、字幕、BGM 压混说明
- 最终平台要求完整观看体验，不能只交纯画面和配乐
- 已决定使用 MiniMax 做 TTS，或至少要输出一个随时可切换到 MiniMax 的后期包

## External Skill Dependency

优先复用官方已安装 skill：`minimax-multimodal-toolkit`

默认检查点：

- `~/.codex/skills/minimax-multimodal-toolkit/SKILL.md`
- `MINIMAX_API_HOST`
- `MINIMAX_API_KEY`
- `ffmpeg`
- `jq`

如果官方 skill 已安装，优先使用其中的：

- `scripts/tts/generate_voice.sh`
- `scripts/media_tools.sh`

如果官方 skill 尚未安装，或运行环境没有配置密钥：

- 仍然输出完整的后期 handoff 包
- 明确标注 `generation_status=not_run`
- 不得伪造“已经生成成功”的音频或字幕文件

## Workflow

1. 读取上游交付物：
   - `master_script`
   - `narration_script`
   - `beat_sheet` 或 `chapter_outline`
   - `cognitive_punch_gate`
   - `asset_source_map`
   - `generation_budget_decision`
2. 先判断是否真的需要旁白：
   - 解释型、教程型、拆解型视频默认需要
   - 纯情绪 montage 或纯现场收音视频，必须明确说明为何不需要
3. 生成单人讲解视频时，默认使用单一 narrator voice。
4. 只有在以下情况才拆成多段或多角色：
   - 存在 narrator 与角色对白
   - 文本超过单次 TTS 限制
   - 明确需要章节之间改变语气或说话人
5. 把口播文本整理成：
   - `tts_input`
   - `tts_segments`
   - `subtitle_source`
6. 先补 `voice-performance-plan.json`，把每段口播的 `emotion`、`speed`、`pause_after_ms`、`intensity` 和 `scene_purpose` 结构化，而不是整条只有一个平铺 voice 设置。
6.1. 对知识类中长视频，默认 `delivery_profile=tight_explanatory`：
   - 语速略快于普通讲解
   - 句间停顿尽量短
   - 只有 hook、框架切换、CTA 等少数位置允许明显停顿
6.2. 如果内容确实需要更沉稳或更抒情，才显式改成 `measured_explainer` 或自定义 profile。
7. 生成 `srt_draft` 时，先保证与口播文本一致，再处理断句和重点强调；同时补 `subtitle-style-pack.json`，不要只剩基础 SRT。
   对 B 站知识向中视频，默认产出中英双语字幕：中文在上，英文在下；如果暂时没有英文对照，也要把双语要求写进 style pack 和后续 QA。
7.1. 如果已经拿到 `minimax-output/tmp/segment_*.mp3`，优先按 segment 音频时间线对齐字幕，再做句内断句；不要只按字数均分总时长。
8. 为剪辑阶段输出 `mix_notes`：
   - BGM 什么时候进出
   - 哪些段落需要 ducking
   - 哪些证据镜头需要让位给口播
9. 如果可以执行 MiniMax：
   - 在当前工作目录创建 `minimax-output/`
   - 使用官方 skill 生成 `voiceover.mp3`
   - 保留命令、模型、voice_id、输入文本版本
10. 如果 final cut 要进入真实渲染，继续把结果交给 `video-postproduction-assembly`，产出 `audio-cue-sheet.json`、`render_plan`、`render_manifest`、`subtitle-quality-report.json` 和 verification 记录。
11. 如果当前轮不能执行生成，也要留下后续一键执行所需参数。

## Workflow Runner

如果当前项目已经有 `narration_script`，先把它整理成 MiniMax 可执行 handoff：

```bash
python3 extensions/skills/minimax-narration-postproduction/scripts/build_tts_handoff.py \
  --project-root data/media-ops/<content-id>
```

这会产出：

- `content/postproduction/voice-performance-plan.json`
- `content/postproduction/voiceover-tts-input.txt`
- `content/postproduction/voiceover-segments.json`
- `content/postproduction/voiceover-profile.json`
- `content/postproduction/subtitle-style-pack.json`

如果环境变量已就绪，再用官方已安装 toolkit 生成音频：

```bash
python3 extensions/skills/minimax-narration-postproduction/scripts/generate_voiceover_with_timing.py \
  --project-root data/media-ops/<content-id>
```

这个 wrapper 会：

- 逐段调用 MiniMax TTS
- 保留 `tmp/segment_*.mp3`
- 按 `pause_after_ms` 真实插入句间停顿
- 输出 `voiceover-generation-manifest.json`

## Output Contract

最终输出至少包含：

- `voiceover_required`
- `generation_status`
- `voice_strategy`
- `voice_id_plan`
- `voice_performance_plan`
- `tts_input`
- `tts_segments`
- `subtitle_source`
- `srt_draft`
- `subtitle_style_pack`
- `mix_notes`
- `bgm_ducking_plan`
- `render_handoff`
- `delivery_checklist`
- `fallback_plan`

## MiniMax Defaults

- 中国大陆账号默认使用 `MINIMAX_API_HOST=https://api.minimaxi.com`
- 解释型视频默认优先单 narrator voice
- 默认优先使用高质量 TTS，而不是先消耗视频生成额度
- 背景音乐默认纯 instrumental，不与旁白抢信息
- 若无必要，不做多角色配音设计

## Subtitle Rules

- 字幕文本必须来自最终口播定稿文本，时间轴必须基于最终口播音频重新生成，不允许口播和字幕两套说法
- 如果存在逐段 TTS 音频，优先使用 segment 音频时间线做强对齐；只有缺少逐段音频时才退回时长估算
- 口播语速和句间停顿一旦调整，字幕必须重新按最新口播生成，不允许沿用旧字幕
- 每条字幕先服务理解，再服务装饰
- 长句要按语义断开，不要整段堆屏
- 重点词可以单独成句，但不能为了“卡点”破坏可读性
- 如果当前阶段只能输出草案，必须写明需要在剪辑阶段做最终对时

## Quality Gate

以下情况不得进入“可发布”状态：

- 有配乐但没有旁白，且视频类型本应依赖讲解
- 有旁白脚本但字幕与口播不一致
- `voiceover-segments.json` 仍然是统一空 `emotion`、统一语速，没有分段表达计划
- 只给了 TTS 命令，没有给字幕源和混音说明
- 有字幕，但没有 `subtitle-style-pack.json` 或最终字幕质感方案
- 使用了 MiniMax，但没有记录 voice_id、模型和输出文件位置
- 解释型中长视频缺 `cognitive_punch_gate`，或 gate 还没通过

## Security Rules

- `MINIMAX_API_KEY` 只能来自环境变量
- 不在仓库、日志、产物里回写密钥
- 不把 cookie、token、账号态信息写进字幕或交付包

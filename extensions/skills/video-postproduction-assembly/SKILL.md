---
name: video-postproduction-assembly
description: 把视频母稿、旁白、字幕和混音计划装配成最终成片。用于产出 final cut、render plan、render manifest 和可审计的渲染验证记录。
version: 1.0.0
---

# Video Postproduction Assembly

## Overview

把已经通过脚本、素材规划和旁白设计的视频，推进成真正可上传的成片包。

这一步解决的不是“写什么”，而是“怎么稳定地把已有资产装配成最终文件，并留下可复查记录”。

如果项目缺少现成 rough cut，但已经有旁白、图卡、proof pack 和获批素材，这个 skill 也应该自动补出基础时间线，而不是把项目打回人工剪辑。

## When to Use

- 已经有 `rough cut`，或者至少有可自动重建时间线的图卡 / proof pack / 获批素材
- 已经有 `voiceover_audio` 或至少有可执行的旁白生成结果
- 已经有 `subtitle_draft`、`subtitle_source`，或者至少有 `voiceover-segments.json`
- 需要把后期步骤沉淀成 `audio-cue-sheet.json`、`render_plan`、`render_manifest`、`assembly_qa_report`、`subtitle-quality-report.json` 和 `render_verification`

## Workflow

1. 读取上游交付物：
   - `rough_cut_path`
   - `voiceover_profile`
   - `voiceover_audio`
   - `subtitle_draft`
   - `subtitle_style_pack`
   - `audio_cue_sheet`
   - `scene_manifest`
   - `transition_plan`
   - `emphasis_fx_plan`
   - `mix_notes`
   - `platform_package`
2. 先决定装配策略，只允许以下之一：
   - `retime_existing_cut`
   - `rebuild_timeline`
   - `review_only`
3. 如果已有 rough cut 且主要缺口只是正式旁白与字幕，优先考虑 `retime_existing_cut`。
4. 如果旁白重写导致章节顺序、停顿或证据镜头变化过大，改走 `rebuild_timeline`，不要盲目压缩旧 cut。
5. 缺字幕或字幕早于最新口播时，先从 `voiceover-segments.json` + 已生成音频自动重建 `subtitle_draft`。
6. 如果是 `rebuild_timeline` 且没有 rough cut，先自动生成 `auto-base-cut.mp4`，再进入最终 render。
7. 生成 `render_plan.json`，至少包含：
   - `workspace_root`
   - `source_video`
   - `voiceover_audio`
   - `subtitles`
   - `output_video`
   - `render_manifest_output`
   - `verification_output`
   - `qa_report_output`
   - `assembly_strategy`
   - `retime`
   - `mix`
   - `subtitle_style`
   - `subtitle_quality_report_output`
   - `scene_assembly_report_output`
   - 如果是 B 站中视频，优先把前 30 秒 hook BGM 和关键结构节点 SFX 也写进 `mix`
   - B 站知识向中视频默认使用 `bilingual_hardsub`，字幕按“中文在上、英文在下”烧录，不再默认单语硬字幕
   - 场景主画面默认禁止纯文字卡片；文字只能作为覆盖层打在图片或视频底材上，若只有 `graphics-card` 兜底，应在装配报告里标成 `revise`
8. 如果是“已有视频 + 新旁白 + 字幕”的装配场景，优先先落 plan，再执行本 skill 自带脚本：

```bash
python3 extensions/skills/video-postproduction-assembly/scripts/build_render_plan.py \
  --project-root data/media-ops/<content-id>

python3 extensions/skills/video-postproduction-assembly/scripts/render_narrated_cut.py \
  --plan content/postproduction/render-plan.json
```

9. 如果希望一步跑完，直接使用 workflow runner：

```bash
python3 extensions/skills/video-postproduction-assembly/scripts/run_render_workflow.py \
  --project-root data/media-ops/<content-id>
```

如果你是在 `data/projects/<project-id>/` 这样的 specialist 工作目录里执行，优先使用稳定的相对路径版本：

```bash
python3 ../../../extensions/skills/video-postproduction-assembly/scripts/run_render_workflow.py \
  --media-ops-root ../../media-ops \
  --content-id <content-id>
```

10. 在 Claude Code 里，也可以直接运行项目命令：

```text
/media-render data/media-ops/<content-id>
```

11. 渲染完成后，必须检查：
   - final cut 是否存在
   - 输出时长是否与旁白目标基本一致
   - 字幕是否已烧录或已明确外挂策略
   - 字幕边界是否和真实口播停顿基本对齐，不能只检查“有字幕文件”
   - `render_manifest`、`assembly_qa_report`、`subtitle-quality-report.json`、`scene-assembly-report.json` 与 `render_verification` 是否已写出

## Output Contract

最终输出至少包含：

- `assembly_strategy`
- `render_plan`
- `render_manifest`
- `assembly_qa_report`
- `subtitle_quality_report`
- `scene_assembly_report`
- `verification_output`
- `final_cut_path`
- `duration_alignment`
- `subtitle_delivery_mode`
- `mix_applied`
- `remaining_risks`

## Script Notes

内置脚本说明：

- `scripts/build_render_plan.py`
  - 从内容包自动推导 `source_video`、`voiceover_audio`、`subtitles`、`output_video`
  - 缺字幕或字幕早于最新口播时自动调用 `build_subtitles_from_segments.py`
  - 缺 `subtitle-style-pack.json` 时自动调用 `build_subtitle_style_pack.py`
  - 缺 `audio-cue-sheet.json` 时自动调用 `build_audio_cue_sheet.py`
  - 缺 `scene-manifest.json` 时自动调用 `build_scene_manifest.py`
  - 缺 `transition-plan.json` 或 `emphasis-fx-plan.json` 时自动调用 `build_transition_plan.py`
  - `rebuild_timeline` 缺 rough cut 时自动调用 `build_visual_timeline.py`
  - 对 `midlong-video` 自动补声音设计默认值：hook BGM、结构节点 SFX、sidechain ducking；如果已有 cue sheet，则缺什么补什么
  - 标准化写出 `render-plan.json`
  - 支持 `--content-id + --media-ops-root`，方便 specialist 在项目目录里调用
- `scripts/run_render_workflow.py`
  - 一步执行字幕补齐 / 基础时间线重建 / build + render
- `scripts/build_visual_timeline.py`
  - 用图卡、proof pack 和已获批 B-roll 自动拼出 `auto-base-cut.mp4`
  - 对图卡自动补基础镜头运动，并在 `auto-base-cut-plan.json` 里写出质量摘要，防止自动时间线长期退化成纯静态拼接
- `../minimax-narration-postproduction/scripts/build_subtitles_from_segments.py`
  - 用 `voiceover-segments.json` 和真实音频时长自动产出 `subtitle_draft`
- `scripts/render_narrated_cut.py`
  - 根据 `render-plan.json` 做最终 retime、混音和字幕烧录
  - 自动产出 `assembly-qa-report.json`
  - 自动产出 `subtitle-quality-report.json`
  - 自动产出 `scene-assembly-report.json`
  - 自动检查 freeze/static、duration alignment、字幕交付方式、subtitle alignment drift、sound design 落地状态，以及 scene/transition/fx 计划是否齐全
  - 对启用了双语字幕要求的项目，检查字幕是否真正交付成双行中英对照
  - 检查 `scene-manifest.json` 是否仍把纯文字卡片当成主画面，避免装配层悄悄退化回旧模板

其中 `scripts/render_narrated_cut.py` 适用于这类确定性场景：

- 已有 rough cut
- 需要根据旁白时长对视频做整体 retime
- 需要把字幕烧录进成片
- 需要保留或压低原音轨，再与旁白混音
- 需要在装配后自动检查 freeze/static、duration alignment 和结尾语义

如果你的场景不是“装配”而是“重剪”，先回到母稿与时间线阶段，不要强行拿这一步替代剪辑。
但如果只是缺一个可审计的基础母版，优先让 `rebuild_timeline` 自动补齐，不要默认退回人工操作。

## Quality Gate

以下情况不得标记为可发布：

- 需要旁白的视频没有真实旁白音轨
- 最终字幕和真实口播不一致
- 字幕和口播的边界偏移明显，但 `assembly-qa-report.json` 仍未修正到 `pass`
- `subtitle-quality-report.json` 不是 `pass`
- `scene-assembly-report.json` 不是 `pass`
- `render_plan` 已要求 BGM / SFX，但最终成片没有对应 sound design 记录
- 有 render 输出但没有 `render_manifest`
- 时长严重失配，却没有说明为何仍可发布
- `assembly-qa-report.json` 仍是 `revise` / `block`

## Security Rules

- 只记录本地文件路径和渲染参数，不记录密钥、cookie、token
- 如果旁白由外部服务生成，密钥仍只允许来自环境变量
- 发布前验证记录里不得回写账号态信息

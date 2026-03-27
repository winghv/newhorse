---
name: video-postproduction-assembly
description: 把视频母稿、旁白、字幕和混音计划装配成最终成片。用于产出 final cut、render plan、render manifest 和可审计的渲染验证记录。
version: 1.0.0
---

# Video Postproduction Assembly

## Overview

把已经通过脚本、素材规划和旁白设计的视频，推进成真正可上传的成片包。

这一步解决的不是“写什么”，而是“怎么稳定地把已有资产装配成最终文件，并留下可复查记录”。

## When to Use

- 已经有 `rough cut` 或可渲染母版
- 已经有 `voiceover_audio` 或至少有可执行的旁白生成结果
- 已经有 `subtitle_draft` 或 `subtitle_source`
- 需要把后期步骤沉淀成 `render_plan`、`render_manifest` 和 `render_verification`

## Workflow

1. 读取上游交付物：
   - `rough_cut_path`
   - `voiceover_profile`
   - `voiceover_audio`
   - `subtitle_draft`
   - `mix_notes`
   - `platform_package`
2. 先决定装配策略，只允许以下之一：
   - `retime_existing_cut`
   - `rebuild_timeline`
   - `review_only`
3. 如果已有 rough cut 且主要缺口只是正式旁白与字幕，优先考虑 `retime_existing_cut`。
4. 如果旁白重写导致章节顺序、停顿或证据镜头变化过大，改走 `rebuild_timeline`，不要盲目压缩旧 cut。
5. 生成 `render_plan.json`，至少包含：
   - `workspace_root`
   - `source_video`
   - `voiceover_audio`
   - `subtitles`
   - `output_video`
   - `render_manifest_output`
   - `verification_output`
   - `assembly_strategy`
   - `retime`
   - `mix`
6. 如果是“已有视频 + 新旁白 + 字幕”的装配场景，优先先落 plan，再执行本 skill 自带脚本：

```bash
python3 extensions/skills/video-postproduction-assembly/scripts/build_render_plan.py \
  --project-root data/media-ops/<content-id>

python3 extensions/skills/video-postproduction-assembly/scripts/render_narrated_cut.py \
  --plan content/postproduction/render-plan.json
```

7. 如果希望一步跑完，直接使用 workflow runner：

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

8. 在 Claude Code 里，也可以直接运行项目命令：

```text
/media-render data/media-ops/<content-id>
```

9. 渲染完成后，必须检查：
   - final cut 是否存在
   - 输出时长是否与旁白目标基本一致
   - 字幕是否已烧录或已明确外挂策略
   - `render_manifest` 与 `render_verification` 是否已写出

## Output Contract

最终输出至少包含：

- `assembly_strategy`
- `render_plan`
- `render_manifest`
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
  - 标准化写出 `render-plan.json`
  - 支持 `--content-id + --media-ops-root`，方便 specialist 在项目目录里调用
- `scripts/run_render_workflow.py`
  - 一步执行 build + render
- `scripts/render_narrated_cut.py`
  - 根据 `render-plan.json` 做最终 retime、混音和字幕烧录

其中 `scripts/render_narrated_cut.py` 适用于这类确定性场景：

- 已有 rough cut
- 需要根据旁白时长对视频做整体 retime
- 需要把字幕烧录进成片
- 需要保留或压低原音轨，再与旁白混音

如果你的场景不是“装配”而是“重剪”，先回到母稿与时间线阶段，不要强行拿这一步替代剪辑。

## Quality Gate

以下情况不得标记为可发布：

- 需要旁白的视频没有真实旁白音轨
- 最终字幕和真实口播不一致
- 有 render 输出但没有 `render_manifest`
- 时长严重失配，却没有说明为何仍可发布

## Security Rules

- 只记录本地文件路径和渲染参数，不记录密钥、cookie、token
- 如果旁白由外部服务生成，密钥仍只允许来自环境变量
- 发布前验证记录里不得回写账号态信息

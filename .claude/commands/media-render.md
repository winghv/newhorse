---
description: 从媒体运营内容包生成 render-plan.json 并执行成片装配
argument-hint: [content-package-dir] [optional overrides]
allowed-tools:
  - Bash(python3 extensions/skills/video-postproduction-assembly/scripts/run_render_workflow.py:*)
  - Read
  - Glob
  - Grep
---

使用 `video-postproduction-assembly` workflow 处理用户提供的媒体内容包。

执行要求：

1. 先检查参数里是否给了内容包目录；如果没有，直接提示缺少 `content-package-dir`。
2. 检查内容包目录是否存在，并确认至少能找到这些关键资产：
   - `content/postproduction/voiceover-profile.json`
   - 旁白音频
   - 字幕文件
   - `content/final-cut/` 下的 rough cut
3. 运行项目级 workflow：

!python3 extensions/skills/video-postproduction-assembly/scripts/run_render_workflow.py --project-root $ARGUMENTS

4. 读取 workflow 生成的：
   - `content/postproduction/render-plan.json`
   - `content/postproduction/render-manifest.json`
   - `review/render-verification-auto.md`
5. 用中文给出结果，必须包含：
   - 使用了哪个 source video
   - 自动生成的 output video 路径
   - 是否保留原音轨
   - 装配策略
   - 若失败，缺了什么或哪一步卡住

如果用户额外传了 `--source-video`、`--output-video`、`--no-retain-original-audio` 等参数，原样透传给 workflow runner。

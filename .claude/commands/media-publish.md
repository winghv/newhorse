---
description: 执行项目级发布 workflow，默认 dry-run，显式 --live 才真实发布
argument-hint: [content-package-dir] --account-name <account> [--live] [optional overrides]
allowed-tools:
  - Bash(python3 extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py:*)
  - Read
  - Glob
  - Grep
---

使用 `multi-platform-publishing` workflow 处理用户提供的媒体内容包，并优先读取最新 `render-manifest.json`。

执行要求：

1. 参数里必须提供内容包目录，以及 `--account-name`。
2. 检查内容包目录下是否存在：
   - `content/postproduction/render-manifest.json`
   - `content/final-cut/` 下的最终视频
3. 运行项目级 workflow：

!python3 extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py --project-root $ARGUMENTS

4. 读取 workflow 生成的：
   - `publish/publish-manifest-auto.json`
   - `publish/publish-result-auto.json`
   - `content/postproduction/render-manifest.json`
5. 用中文返回：
   - 当前 `mode` 是 `dry_run` 还是 `live`
   - 解析出的 final cut
   - 生成的 publish manifest 路径
   - 生成的 publish result 路径
   - 当前 `decision`
   - 当前 `status`
   - 缺失项或阻塞项

默认不要追加 `--live`。只有用户明确批准真实发布时，才把 `--live` 原样透传给 workflow runner。

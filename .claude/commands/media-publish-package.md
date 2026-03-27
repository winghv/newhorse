---
description: 从最新 render-manifest 生成 publish-manifest-auto.json
argument-hint: [content-package-dir] --account-name <account> [optional overrides]
allowed-tools:
  - Bash(python3 extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py:*)
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
3. 运行：

!python3 extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py --project-root $ARGUMENTS

4. 读取生成的：
   - `publish/publish-manifest-auto.json`
   - `content/postproduction/render-manifest.json`
5. 用中文返回：
   - 解析出的 final cut
   - 生成的 publish manifest 路径
   - 当前 `decision`
   - 缺失项或阻塞项

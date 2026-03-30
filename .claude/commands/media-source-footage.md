---
description: 为中长视频自动搜索外部素材并把获批片段沉淀到生产链
argument-hint: [content-package-dir] [optional overrides]
allowed-tools:
  - Bash(python3 extensions/skills/licensed-footage-sourcing/scripts/run_external_footage_workflow.py:*)
  - Read
  - Glob
  - Grep
---

使用 `licensed-footage-sourcing` workflow 处理用户提供的媒体内容包。

执行要求：

1. 参数里必须提供内容包目录。
2. 检查内容包目录下是否存在中长视频 content packet，并且里面至少有 `clip_sourcing_brief`。
3. 运行：

!python3 extensions/skills/licensed-footage-sourcing/scripts/run_external_footage_workflow.py --project-root $ARGUMENTS

4. 读取生成的：
   - `sources/source-manifest.json`
   - `sources/source-shortlist.json`
   - `sources/asset-ingest-manifest.json`
   - `sources/clip-query-sheet.md`
5. 用中文返回：
   - 实际使用了哪些 provider
   - 找到了多少 approved / hold 候选
   - 下载入库了多少素材
   - 生成的 manifest 路径
   - 如果卡住，缺了什么凭证或输入字段

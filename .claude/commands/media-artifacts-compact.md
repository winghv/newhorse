---
description: 收敛发布版本文件，保留关键版本并归档其余历史文件
argument-hint: [content-package-dir] [--apply]
allowed-tools:
  - Bash(python3 extensions/skills/media-ops-orchestration/scripts/compact_publish_artifacts.py:*)
  - Read
  - Glob
  - Grep
---

使用发布产物收敛脚本，整理 `publish/` 目录中的 manifest/result 版本文件。

执行要求：

1. 参数里必须提供内容包目录。
2. 默认先 dry-run：

!python3 extensions/skills/media-ops-orchestration/scripts/compact_publish_artifacts.py --project-root $ARGUMENTS

3. 用户明确确认后，再透传 `--apply` 执行真实归档：

!python3 extensions/skills/media-ops-orchestration/scripts/compact_publish_artifacts.py --project-root $ARGUMENTS --apply

4. 读取并汇报：
   - 保留了哪些文件（及原因）
   - 归档了哪些文件
   - 归档批次路径（`publish/archive/<batch>/archive-report.json`）
   - 是否生成 `publish/archive/archive-index.json`

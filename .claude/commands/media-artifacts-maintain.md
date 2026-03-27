---
description: 一键执行 media-ops 产物治理（audit -> compact -> re-audit）
argument-hint: [media-ops-root-dir] [--apply] [--fail-on-missing-required]
allowed-tools:
  - Bash(python3 extensions/skills/media-ops-orchestration/scripts/run_artifact_maintenance.py:*)
  - Read
  - Glob
  - Grep
---

使用一键治理脚本执行完整维护流程。

执行要求：

1. 如果参数为空，默认扫描 `data/media-ops`。
2. 默认 dry-run：

!python3 extensions/skills/media-ops-orchestration/scripts/run_artifact_maintenance.py --media-ops-root $ARGUMENTS

3. 若用户明确要求落地归档，追加 `--apply`。
4. 读取并汇报：
   - 治理前后 sprawl 包数量
   - 实际执行了多少次 compaction
   - 每个 compaction 的移动文件数量
   - 治理后是否仍有缺失 required artifacts

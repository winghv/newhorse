---
description: 扫描 media-ops 产物并生成 registry 与健康检查摘要
argument-hint: [media-ops-root-dir] [--fail-on-missing-required]
allowed-tools:
  - Bash(python3 extensions/skills/media-ops-orchestration/scripts/audit_artifacts.py:*)
  - Read
  - Glob
  - Grep
---

使用 `media-ops-orchestration` 的产物治理脚本盘点内容包完整度，并输出结构化 registry。

执行要求：

1. 如果参数为空，默认扫描 `data/media-ops`。
2. 运行：

!python3 extensions/skills/media-ops-orchestration/scripts/audit_artifacts.py --media-ops-root $ARGUMENTS

3. 读取生成的：
   - `data/media-ops/_registry/artifact-registry.json`
   - `data/media-ops/_registry/artifact-registry.md`
4. 用中文返回：
   - 扫描了多少个内容包
   - 各 lifecycle 状态数量
   - 缺失最频繁的 required artifacts
   - 当前风险最高的内容包（按 missing required + warnings 排序）

如果用户显式要求“缺失项必须拦截”，透传 `--fail-on-missing-required`。

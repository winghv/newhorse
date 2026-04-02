---
name: multi-platform-publishing
description: 准备并执行多平台发布。用于生成发布清单、适配平台元数据、调用上传 skill 或输出 dry-run 发布包。
version: 1.0.0
---

# Multi-Platform Publishing

## Overview

把审核通过的内容包变成真实的发布动作或可执行的 dry-run 清单。

## When to Use

- 用户要发布、定时发布、批量分发内容
- 需要为不同平台整理标题、文案、标签、素材路径和时间
- 需要调用现有上传 skill

## Supported Skill Hand-off

优先复用仓库里已有的上传 skill：

- `xiaohongshu-upload`
- `douyin-upload`
- `kuaishou-upload`
- `bilibili-upload`

如果目标平台没有现成上传 skill：

- 生成手工发布包
- 或输出待接入 API/CLI 方案

## Workflow

1. 默认直接运行项目级 publish workflow。它会在缺少 manifest 时自动先生成 `publish-manifest-auto.json`，再写出 `publish-result-auto.json`：

```bash
python3 extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py \
  --project-root data/media-ops/<content-id> \
  --account-name <account>
```

或在 specialist 的项目目录里：

```bash
python3 ../../../extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py \
  --media-ops-root ../../media-ops \
  --content-id <content-id> \
  --account-name <account>
```

2. 如果你只想先生成发布清单、不执行 publish workflow，再单独运行：

```bash
python3 extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py \
  --project-root data/media-ops/<content-id> \
  --account-name <account>
```

或在 specialist 的项目目录里：

```bash
python3 ../../../extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py \
  --media-ops-root ../../media-ops \
  --content-id <content-id> \
  --account-name <account>
```

3. 校验发布清单：
   - 账号
   - 平台
   - 素材路径
   - 标题/正文/标签
   - 发布时间
   - 审核状态
4. 生成或刷新 `publish/release-record.json`，把最终视频路径、上传版路径、封面路径、voice、runtime、最新 manifest/result 和平台返回标识统一写回单一真源。
4.1. 发布前同时生成或刷新：
   - `review/workflow-quality-gate.json`
   - `review/upgrade-status-board.json`
   - `publish/prelive-quality-summary.json`
5. 对视频内容，素材路径优先取自 `render-manifest` 的最新 final cut，不手工猜版本号。
6. 按平台改写元数据，禁止原样群发。
7. 如果 `assembly_strategy = rebuild_timeline`，先确认 `content/postproduction/auto-base-cut-plan.json` 存在且 `quality.status = pass`；否则只允许输出 blocked manifest，不进入 live prep。
8. 对 Bilibili 中长视频，发布前必须有完整 `publish_metadata`，至少补齐 `account_name`、`partition`、`partition_name`、`tags` 和封面/上传素材路径。
9. 能自动发布的平台直接调用对应 skill。
10. 无法自动发布的平台生成 dry-run 包和待办清单。
11. 汇总每个平台的结果、失败原因和重试建议。

## Publishing Rules

- 未审批通过时只能做 dry-run
- 缺素材、缺 cookie、缺账号映射时不要硬发
- 如果有 `render-manifest`，发布阶段必须优先使用它解析出来的 final cut
- 发布状态、素材路径和平台回写标识必须优先看 `publish/release-record.json`
- 发布结果必须回填为结构化摘要，方便复盘
- 真实发布必须显式追加 `--live`
- `publish-manifest-auto.json` 的 `decision` 不是 `ready_for_live_publish` 时，workflow 必须拒绝 live publish
- `review/workflow-quality-gate.json` 的 `overall_status` 不是 `pass` 时，workflow 必须阻塞 live publish
- `publish/prelive-quality-summary.json` 必须明确透出 workflow gate 的各维状态，避免只看局部门禁就误放行
- `rebuild_timeline` 视频的 `auto_base_quality_status` 不是 `pass` 时，`publish-manifest-prelive.json` 和 `live-execution-plan.json` 都不能进入 `ready_for_live_publish`
- 发布队列里必须透出 `assembly_strategy` 和 `auto_base_quality_status`，方便批量判断哪些包需要先修自动时间线
- 发布结果日志必须脱敏，不能回写 cookie、token、密钥
- Bilibili 原生 `sau` CLI 没有封面参数；workflow 需要改走 repo-local uploader wrapper，用 `biliup upload --cover` 补齐自动封面
- `publish/release-record.json` 仍然要把 `cover_asset_ready`、`cover_delivery_status` 和 `cover_set` 分开写，避免把“待上传”误记成“已上传”
- 对 Bilibili 已提交稿件，当前自动化不支持原地刷新；如果 `publish_status=ready_for_live_refresh`，workflow 必须阻塞 live，避免重复投稿

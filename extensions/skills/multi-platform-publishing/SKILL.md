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
4. 对视频内容，素材路径优先取自 `render-manifest` 的最新 final cut，不手工猜版本号。
5. 按平台改写元数据，禁止原样群发。
6. 能自动发布的平台直接调用对应 skill。
7. 无法自动发布的平台生成 dry-run 包和待办清单。
8. 汇总每个平台的结果、失败原因和重试建议。

## Publishing Rules

- 未审批通过时只能做 dry-run
- 缺素材、缺 cookie、缺账号映射时不要硬发
- 如果有 `render-manifest`，发布阶段必须优先使用它解析出来的 final cut
- 发布结果必须回填为结构化摘要，方便复盘
- 真实发布必须显式追加 `--live`
- `publish-manifest-auto.json` 的 `decision` 不是 `ready_for_live_publish` 时，workflow 必须拒绝 live publish
- 发布结果日志必须脱敏，不能回写 cookie、token、密钥

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

1. 校验发布清单：
   - 账号
   - 平台
   - 素材路径
   - 标题/正文/标签
   - 发布时间
   - 审核状态
2. 按平台改写元数据，禁止原样群发。
3. 能自动发布的平台直接调用对应 skill。
4. 无法自动发布的平台生成 dry-run 包和待办清单。
5. 汇总每个平台的结果、失败原因和重试建议。

## Publishing Rules

- 未审批通过时只能做 dry-run
- 缺素材、缺 cookie、缺账号映射时不要硬发
- 发布结果必须回填为结构化摘要，方便复盘

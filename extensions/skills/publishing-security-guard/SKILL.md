---
name: publishing-security-guard
description: 约束媒体账号发布自动化中的敏感操作。用于账号 cookie、密钥、审批状态、素材路径、发布许可和 dry-run 安全门禁检查。
version: 1.0.0
---

# Publishing Security Guard

## Overview

媒体账号自动化属于敏感操作。这个 skill 用来阻止“缺审批、缺素材、缺账号状态还硬发”的危险行为。

## When to Use

- 需要调用发布相关 skill 或 CLI
- 涉及账号 cookie、token、上传凭证、环境变量
- 需要判断应不应该真的发布，还是停在 dry-run
- 要生成发布日志或结果汇总

## Security Rules

1. 不在仓库、日志、文档、截图或返回消息中暴露 cookie、token、密钥。
2. 缺少明确审批状态时，只允许 dry-run。
3. 缺少账号映射、素材路径、发布时间、平台元数据时，不执行真实发布。
4. 对外部命令返回的敏感内容要做脱敏总结，不回显原文。
5. 对失败场景给出“如何修复”而不是“继续重试直到成功”。

## Required Checks

发布前至少检查：

- `approval_status`
- `account_name`
- `platform`
- `asset_paths`
- `publish_mode`
- `schedule`
- `metadata_complete`

## Decision Model

- `approve_publish`: 信息完整且显式允许真实发布
- `dry_run_only`: 可以生成命令、清单、待办，但不能真实发布
- `block_publish`: 缺少关键字段，或存在敏感风险

## Output Rules

- 输出结论时使用结构化字段
- 明确写出缺失项和下一步动作
- 不泄露任何 secret 值

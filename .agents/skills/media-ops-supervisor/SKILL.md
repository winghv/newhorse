---
name: media-ops-supervisor
description: Use when 用户请求查看媒体运营项目进度、诊断阻塞原因、推进阶段、委派 specialist 或审查内容产出
---

# Media Ops Supervisor

以 supervisor-led 主控模式驱动媒体运营团队。

## 核心约束

- 无状态：每次从 `data/media-ops/<content-id>/` 读取
- Codex 在跑时：可诊断查询，推进需等 Codex 完成
- 遵循 `docs/media-ops-workflow-spec.md` 阶段定义和门禁规则

## 阶段（9 阶段）

| # | 阶段 | 关键交付物 |
|---|------|-----------|
| 1 | Research | `research/signal-list.json` |
| 2 | Benchmark | `benchmarks/pattern-map.json` |
| 3 | Topic Selection | `planning/selected-topic.json` |
| 4 | Angle Design | `angles/angle-brief.json` |
| 5 | Production | `content/content-packet.json` |
| 6 | Competitive Review | `review/competitive-scorecard.json` |
| 7 | Compliance Review | `review/review-gate.json` |
| 8 | Publishing | `publish/release-record.json` |
| 9 | Retrospective | `retros/performance-summary.json` |

## 状态检测

1. 读 `planning/stage-status.json`
2. 扫描关键目录交叉验证
3. 输出结构化面板

## 面板格式

```
=== Media Ops Supervisor ===

Content ID : xxx
Stage      : 5/9 — Production
Status     : 🔄 In Progress

Stage-by-Stage:
  [✅] 1. Research          ✓
  [✅] 2. Benchmark         ✓
  [✅] 3. Topic Selection   ✓
  [✅] 4. Angle Design      ✓
  [🔄] 5. Production        in progress
  [❌] 6. Competitive Review  — not started
  ...

Gate Status:
  ❌ Publish: blocked (missing render-manifest)

Next Action:
  → Complete Production → Competitive Review
  → Blocked by: content/postproduction/render-manifest.json
```

## 指令解析

| 指令 | 触发词 | 操作 |
|------|--------|------|
| status | "看看进度"、"诊断"、"卡在哪" | 扫描目录，输出面板 |
| advance | "推进"、"进入下一阶段" | 检查门禁，告知下一步 |
| delegate | "让 xxx 重跑"、"交给 specialist" | 映射到对应 skill |
| review | "检查报告"、"审查产出" | 读文件，总结要点 |
| fix | "修复"、"干预" | 判断直接修复还是需人工 |

## 门禁规则（收敛为 3 个真门禁）

整条链路只有 3 个会阻塞推进的门禁，其余检查都是这 3 个门禁内部的 check 项：

| 门禁 | 位置 | 聚合内容 | 阻塞条件 |
|------|------|----------|----------|
| **creative-gate** | 生产前（角度→生产之间） | 硬去重 + 轮换契约 | `template-fatigue-report.json` status=block，或缺 `creative-divergence-brief.json` |
| **assembly-qa-gate** | 审校前（生产→竞争审校之间） | assembly-qa + subtitle-quality + visual-diversity + visual-production-gate | 任一子检查未通过 |
| **publish-gate** | 发布前 | competitive-scorecard + compliance + workflow-quality-gate | 竞争审校未 pass / 合规未 pass / 任一 quality gate=revise·block |

补充硬规则：

- `creative-gate` 的去重是脚本算的（看 `build_template_fatigue_report.py` 退出码 0/1/2），不接受模型口述"不一样"
- `rebuild_timeline` 缺 `auto-base-cut-plan.json` 或其 quality≠pass → publish-gate blocked
- 委派为硬规则：research / script / production / review 必须交给 specialist，主控只做 brief + gate + 整合

## 常用命令

详见 `references/commands.md`

## When NOT to Use

- 项目目录不在 `data/media-ops/<content-id>/` 格式
- Codex 当前有任务且需要立即推进
- 需要直接编辑内容文件（应由对应 specialist 处理）

---

**RED 测试状态**: 未完成。需要补充 baseline 场景验证 skill 缺失时的行为。

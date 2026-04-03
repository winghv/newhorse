---
name: benchmark-analysis
description: 对平台头部内容、同类创作者和竞品案例做对标拆解。用于找到有效钩子、结构、证据、视觉模式、互动触发点和可复制打法。
version: 1.0.0
---

# Benchmark Analysis

## Overview

不是“看看竞品”，而是拆清楚强内容为什么强，弱内容为什么弱。

## When to Use

- 已有研究简报，需要进一步拆头部样本
- 用户要提高作品竞争力，而不是只求稳定产出
- 需要给选题、角度设计和制作阶段提供可复制模式

## Workflow

1. 确定对标范围：平台、题材、受众、时间窗口、样本数量。
2. 选样本：头部内容、同题材高互动内容、同受众强创作者。
3. 如果已经拿到参考视频 URL / BV 号，先用 `reference-video-ingest` 把 metadata 和 transcript artifacts 沉淀出来，再开始拆结构。
3. 拆每个样本：
   - 开头钩子
   - 结构节奏
   - 证据和案例
   - 视觉或镜头模式
   - 评论/收藏/转发触发点
4. 对比强样本和普通样本：
   - 哪些模式反复有效
   - 哪些套路已经过饱和
   - 哪些空白位还没被占满
5. 如果目标平台是 Bilibili 中视频，额外把开场、结构、证据和关注桥拆成结构化 `pattern pack`，不要只留一份读后感式文档。
6. 输出对标包，给选题和角度设计直接接手。

## Workflow Runner

对 Bilibili 中视频，优先把 benchmark deck 整理成结构化模式包：

```bash
python3 extensions/skills/benchmark-analysis/scripts/build_bilibili_pattern_pack.py \
  --project-root data/media-ops/<content-id>
```

这会产出：

- `benchmarks/bilibili-hook-patterns.json`

## Output Template

至少包含：

- `reference`
- `hook_pattern`
- `narrative_pattern`
- `proof_pattern`
- `visual_pattern`
- `engagement_driver`
- `follow_conversion_bridge`
- `saturation_risk`
- `whitespace`
- `reusable_play`
- `bilibili_hook_patterns`

## Quality Gate

- 观察必须来自真实样本，不要用想象代替拆解
- 明确哪些结论是事实，哪些是推断
- 结果必须能回答“下一条作品靠什么赢”
- 如果上游已经拿到参考视频字幕，优先引用 `research/reference-transcript.srt` / `research/reference-transcript.md`，不要只靠二次转述
- 对 Bilibili 中视频，至少要回答：
  - 前 `30` 秒怎么留人
  - 第一层证明怎么前置
  - 收藏理由在哪里
  - 结尾怎样把“看完”变成“愿意继续关注下一条”

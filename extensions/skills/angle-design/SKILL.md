---
name: angle-design
description: 把入选题材收敛成高胜率内容角度。用于生成核心切入点、钩子假设、证明路径、评论诱因和备选角度。
version: 1.0.0
---

# Angle Design

## Overview

选题决定做什么，角度设计决定这条内容为什么值得看、愿意存、愿意转。

## When to Use

- 已经选出主题，需要进一步收敛成单条作品
- 用户要提升作品竞争力和平台原生感
- 需要在制作前做“赢面判断”

## Workflow

1. 读取 `selected topic`、研究证据和 `benchmark deck`。
2. 读取或补齐 `planning/creative-divergence-brief.json`，先确认这期不能继续复用的开头、结构、案例和视觉套路。
3. 生成 3-5 个候选角度，每个角度都明确：
   - 核心冲突
   - 新鲜度
   - 证据抓手
   - 情绪张力
   - 平台适配方式
   - 与最近内容的差异轴
   - 不能退回的模板化写法
4. 对候选角度打分：
   - `novelty`
   - `creative_divergence`
   - `proof_strength`
   - `emotional_pull`
   - `platform_fit`
   - `save_share_potential`
   - `series_potential`
5. 选出主角度和备选角度。
6. 如果目标平台是 Bilibili 中视频，再把主角度补成发布前可执行的增长结构：
   - `attention-structure-template.json`
   - `follow-conversion-hooks.json`
7. 输出制作 brief，包括钩子假设、证明路径、禁区、CTA 和本期创意差异约束。

## Workflow Runner

```bash
python3 extensions/skills/angle-design/scripts/build_attention_structure.py \
  --project-root data/media-ops/<content-id>
```

这会产出：

- `angles/attention-structure-template.json`
- `angles/follow-conversion-hooks.json`

## Output Template

- `primary_angle`
- `backup_angles`
- `hook_hypotheses`
- `proof_plan`
- `creative_divergence_brief`
- `divergence_axes`
- `forbidden_repeats`
- `comment_prompt`
- `cta`
- `kill_reasons`
- `attention_structure_template`
- `follow_conversion_hooks`

## Quality Gate

- 不要把“观点正确”误当成“作品有吸引力”
- 至少保留一个主角度和一个备选角度
- 不要把 3-5 个角度写成同一个观点的标题变体；候选角度必须来自不同 lens
- 如果主角度无法说明相对最近作品的新思考路径，退回选题阶段
- 如果没有足够证据支撑角度，明确降级或退回选题阶段
- 对 Bilibili 中视频，没有前 `30` 秒结构和结尾桥接时，不算可执行 brief

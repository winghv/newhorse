---
name: script-polishing
description: 用优秀参考视频稿件打磨知识类中长视频剧本。用于把 reference transcript、对标观察和角度 brief 沉淀成可复用的写稿打法包、rewrite 契约和 script-doctor brief，而不是只写一份临时 prompt。
version: 1.0.0
---

# Script Polishing

## Overview

这层不是替代创作，而是把“优秀作品为什么好看、为什么越看越想看”的写稿打法结构化。

目标不是把大模型写死成固定模版，而是：

- 锁住少量真正决定输赢的 `hard constraints`
- 给中段论证、案例顺序、反例插入和表达风格保留 `freedom zones`
- 让参考视频的稿件变成可复用的 rewrite 契约

## When to Use

- 用户要做 B 站知识/认知类中长视频，且已经积累了参考视频稿件
- 你感觉当前 workflow 只会“防空”，不会“把稿子写厚、写透、写出节奏”
- 需要把 benchmark 学到的写稿打法沉淀成 agent prompt、delegate brief 和结构化 artifacts
- 需要在 `benchmark -> production` 之间插入一层专门的剧本打磨

## Workflow

1. 先读取参考视频库：
   - 默认优先看 `data/media-ops/_reference-videos/index.json`
   - 优先消费 `research/reference-transcript.md`
2. 先用参考库生成一份可复用的写稿打法包：

```bash
python3 extensions/skills/script-polishing/scripts/build_reference_script_patterns.py \
  --project-root data/media-ops/<content-id>
```

3. 再结合当前项目的：
   - `planning/topic-selection.json`
   - `planning/creative-divergence-brief.json`
   - `angles/angle-brief.json`
   - `angles/attention-structure-template.json`
   - `content/*.json`
   生成项目级剧本打磨包：

```bash
python3 extensions/skills/script-polishing/scripts/build_script_polish_packet.py \
  --project-root data/media-ops/<content-id>
```

4. `script-doctor`、`content-producer` 或 `video-production-director` 在真正写稿前，先消费：
   - `benchmarks/reference-script-patterns.json`
  - `content/script-polish-packet.json`

4.1. 在 `supervisor-led` 模式下，真正的写稿 / 改稿默认必须委派给 `script-doctor`：
   - 主控只负责整理输入、下发 brief、做 gate 和整合结果
   - 不要由主控直接写完整母稿，或直接吞掉大段改稿工作
   - 默认从 `content/script-polish-packet.json` 里的 `delegate_brief_template` 发起

补充：

- 如果 `angle-brief.json` 或 `content/bilibili-midform-video.json` 已经声明 `duration_target`，`script-polish-packet.json` 必须把这个时长目标显式推进到：
  - `runtime_strategy`
  - `section_blueprint`
  - `delegate_brief_template`
- 对约 `12-15` 分钟的中视频，不允许沿用 8-9 分钟的默认章节密度，必须显式扩写中段。
- 对认知/知识类账号，`script-polish-packet.json` 还要显式约束“观众心理接受度”：
  - 不能只会诊断观众的问题
  - 要同时提供机制解释、认知增量和情绪托底
  - 要兼顾宏观系统视角与贴身生活细节
- 默认每条作品都应完整收束。
  - 只有显式声明 `multipart` / `上下集` 时，结尾才允许把关键解释留到下一条。
- 默认每条作品还要显式处理“模板疲劳”：
  - 不允许连续复用同一种开头承诺、同一种三段式解释、同一种案例顺序或同一种结尾 CTA
  - `hard_constraints` 只能锁定胜负关键，不得把整篇稿件压成固定段落模板
  - `freedom_zones` 必须包含至少 `2` 个可以改变叙事装置、证据顺序或表达风格的位置
  - rewrite loop 必须检查 `forbidden_repeats` 是否被重新带回稿件

## Output Artifacts

- `benchmarks/reference-script-patterns.json`
  - 从参考视频库里抽出开头装置、承诺方式、推进手法、金句策略和常见反模式
- `content/script-polish-packet.json`
  - 项目级的写稿契约，包括：
    - `duration_target`
    - `runtime_strategy`
    - `audience_psychology_contract`
    - `hard_constraints`
    - `freedom_zones`
    - `creative_divergence_contract`
    - `forbidden_repeats`
    - `opening_contract`
    - `section_blueprint`
    - `borrowed_plays`
    - `rewrite_loop`
    - `delegation_contract`
    - `delegate_brief_template`

## Quality Gate

- 不要把参考视频照抄成“换词模版”
- 只锁死最关键的硬约束，不把中段所有论证顺序写死
- 如果当前稿件和最近作品只是换题面但沿用同一思考路径，必须判为需要重写，而不是只做润色
- 如果 `creative-divergence-brief` 缺失，先补齐或明确阻塞，不要直接进入母稿定稿
- 输出必须能回答：
  - 这条视频前 `30` 秒必须做到什么
  - 中段怎样变厚，而不是一直重复同一种解释
  - 哪些写法值得借，哪些套路要避开
  - 如果主控把任务委派给 `script-doctor`，应该给什么 brief
- 如果参考 transcript 是 `ASR tiny`，优先提结构和表达打法，不直接逐字引用

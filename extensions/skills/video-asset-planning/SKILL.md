---
name: video-asset-planning
description: 在视频制作前规划素材来源与生成预算。用于决定真实素材、截图、动效、TTS、AI 图像、AI 视频如何分配，并给出是否批准高成本生成的门禁结论。
version: 1.0.0
---

# Video Asset Planning

## Overview

先决定素材怎么来，再决定脚本怎么落。高成本生成式媒体不是默认解。

## When to Use

- 目标产物是短视频或中长视频
- 需要决定是否调用 TTS、图像生成、视频生成、音乐生成
- 已知生成预算有限，尤其是视频生成额度稀缺

## Planning Priority

默认优先级从高到低：

1. 真实拍摄素材 / 录屏 / 用户已有资产
2. 现有截图、文档、UI 界面做成动效
3. 合法来源的网上片段 / 已购素材库 / 公共版权库
4. AI 图像
5. TTS / 音乐 / 音效
6. AI 视频

只有前面的方案不足以支撑关键画面时，才考虑往后走。

对中长视频，`3` 通常是默认主力，而不是例外。

## MiniMax Budget Gate

当前默认约束：

- MiniMax 视频生成每天最多 `6` 次调用
- 单次调用默认只产出 `6` 秒
- 每日可支配的原生生成时长上限按 `36` 秒计算

在这套工作流里，视频生成额度按“镜头槽位”管理，而不是按“想试就试”管理。

默认策略：

- 普通解释型视频：`0` 次
- 需要补强开场或结尾英雄镜头：`1-2` 次
- 单条内容计划使用 `3+` 次时，必须视为高消耗方案并显式说明原因

只有同时满足下面条件，才批准文本生成视频：

- 脚本主版本已经过竞争力预审
- 要生成的镜头对整条内容的输赢有实质影响
- 没有更低成本的真实素材、网上合法片段或图像动效替代
- 分镜、镜头目标和 prompt 已经锁定
- 生成结果可以复用到封面、长图或后续切条，而不是一次性消耗
- 当日额度还有余量

如果任一条件不满足，输出 `no-gen fallback`，继续推进可执行方案。

## Output Contract

最终输出至少包含：

- `asset_source_map`
- `must_capture_list`
- `existing_asset_reuse`
- `source_manifest`
- `video_generation_quota`
- `quota_snapshot`
- `reserved_generation_slots`
- `approved_generated_assets`
- `blocked_generated_assets`
- `generation_budget_decision`
- `tts_strategy`
- `subtitle_strategy`
- `music_strategy`
- `no_gen_fallback`
- `prompt_pack_if_approved`

## Security Rules

- MiniMax、TTS、图像、视频、音乐相关密钥只允许来自环境变量
- 不在仓库、日志、发布包里写入密钥、token、cookie
- 如果用户没有明确提供或配置密钥，不假装已经接通生成能力

## Quality Rules

- 不要用生成视频掩盖脚本弱、证据弱的问题
- 对解释型视频，优先确保 TTS 与字幕资产完整，再讨论视频生成镜头
- 对短视频，优先保证前 `1-3` 秒和前 `5-10` 秒的关键画面
- 对中长视频，优先保证章节证据和过渡，而不是堆砌花哨镜头
- 对中长视频，优先让网上合法片段承担情境、转场和气氛镜头，核心证明仍由自有素材或可验证证据承担
- 任何获批的生成式素材都要说明它具体提高了哪一项竞争力
- 单条内容默认不应吞掉当天大部分 MiniMax 视频额度；如果要用 `3+` 次，先给出更便宜方案为何不够用

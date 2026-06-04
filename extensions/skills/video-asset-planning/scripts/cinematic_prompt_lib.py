#!/usr/bin/env python3
"""Cinematic prompt library — deterministic camera/lighting/composition vocab.

把"电影质感"从模型自由发挥变成脚本可控的确定性注入：
- 提供 shot / lighting / composition / depth / color_grade / lens / atmosphere 词库
- 按 chapter index 与本期 visual_grammar 组合，保证同期内 134 张图有变化梯度
- 不依赖任何外部库

被 build_minimax_shot_plan.py 调用，为每个生成 slot 拼出带电影语言的 prompt。
"""

from __future__ import annotations

from typing import Any

# 镜头景别：远→近循环，制造画面节奏。
SHOT_TYPES = [
    "极致特写 (extreme close-up)",
    "特写 (close-up)",
    "中近景 (medium close-up)",
    "中景 (medium shot)",
    "中远景 (medium wide shot)",
    "广角全景 (wide establishing shot)",
    "过肩视角 (over-the-shoulder)",
    "俯拍 (high-angle top-down)",
    "低角度仰拍 (low-angle)",
]

LIGHTING = [
    "伦勃朗光，单侧硬光勾勒轮廓",
    "逆光剪影，主体边缘发光",
    "黄金时刻暖光，柔和长投影",
    "低调照明 (low-key)，大面积阴影",
    "高调照明 (high-key)，干净通透",
    "霓虹混合光，冷暖撞色",
    "窗边自然散射光，柔和过渡",
    "顶光聚焦，戏剧化压暗周边",
]

COMPOSITION = [
    "三分法构图，主体偏置",
    "中心对称构图，强稳定感",
    "引导线构图，视线被牵向焦点",
    "框架式构图，前景遮挡形成画框",
    "对角线动势构图",
    "负空间留白，主体孤立",
    "前后景分层，纵深叠置",
]

DEPTH = [
    "浅景深，背景奶油虚化",
    "焦点拉移 (rack focus) 的瞬间",
    "深景深，前后景皆清晰",
    "微距浅焦，仅一点实焦",
]

COLOR_GRADE = [
    "青橙色调电影分级",
    "低饱和纪实色调",
    "暖调胶片质感，轻微颗粒",
    "冷蓝忧郁色调",
    "高对比黑金色调",
    "柔和莫兰迪低对比色调",
]

LENS = [
    "35mm 人文视角",
    "85mm 人像压缩，背景压扁",
    "24mm 广角带轻微透视畸变",
    "50mm 标准视角，接近肉眼",
    "微距镜头，极近距离细节",
]

ATMOSPHERE = [
    "空气中漂浮微尘，光束可见",
    "薄雾弥漫，远景柔化",
    "雨后反光的潮湿质感",
    "安静克制的室内氛围",
    "都市夜景的孤独感",
    "清晨冷冽的通透空气",
]

# 通用质量后缀，统一钉死分辨率与无字要求（中文大字交给本地叠加，不让模型生成）。
QUALITY_SUFFIX = (
    "16:9 横构图，电影级质感，真实材质细节，无任何文字与水印，"
    "photorealistic，high detail，cinematic still"
)


def _pick(pool: list[str], seed: int) -> str:
    """确定性轮换取值：不同 seed 取不同项，同 seed 稳定可复现。"""
    return pool[seed % len(pool)] if pool else ""


def build_cinematic_prompt(
    *,
    subject: str,
    slot_index: int,
    chapter_index: int = 0,
    visual_grammar_keywords: list[str] | None = None,
    scene_goal: str = "",
) -> dict[str, Any]:
    """为一个生成 slot 拼出电影语言 prompt。

    subject: 该镜头要表达的核心画面内容（来自模型/章节意图）
    slot_index: 全片内的镜头序号，用来在词库里轮换，保证变化梯度
    visual_grammar_keywords: 本期 rotation 选定的视觉语法关键词（来自 divergence contract）
    """
    visual_grammar_keywords = visual_grammar_keywords or []
    # 用 slot_index 与 chapter_index 错位组合，避免相邻镜头雷同。
    shot = _pick(SHOT_TYPES, slot_index)
    light = _pick(LIGHTING, slot_index + chapter_index)
    comp = _pick(COMPOSITION, slot_index * 2 + chapter_index)
    depth = _pick(DEPTH, slot_index + chapter_index * 3)
    color = _pick(COLOR_GRADE, chapter_index)  # 同章统一色调，整体更连贯
    lens = _pick(LENS, slot_index + 1)
    atmos = _pick(ATMOSPHERE, slot_index * 3 + chapter_index)

    grammar_clause = ("，".join(visual_grammar_keywords)) if visual_grammar_keywords else ""

    parts = [
        subject.strip() or scene_goal.strip(),
        shot,
        comp,
        light,
        depth,
        lens,
        color,
        atmos,
    ]
    if grammar_clause:
        parts.append(grammar_clause)
    parts.append(QUALITY_SUFFIX)
    prompt = "，".join(p for p in parts if p)

    return {
        "prompt": prompt,
        "cinematic": {
            "shot_type": shot,
            "lighting": light,
            "composition": comp,
            "depth": depth,
            "color_grade": color,
            "lens": lens,
            "atmosphere": atmos,
            "visual_grammar": visual_grammar_keywords,
        },
    }


def diversity_metrics(slots: list[dict[str, Any]]) -> dict[str, Any]:
    """统计一批 slot 的电影维度多样性，供门禁检查"是否一个调调"。"""
    def uniq(key: str) -> int:
        return len({(s.get("cinematic") or {}).get(key) for s in slots if isinstance(s, dict)})

    total = len(slots)
    return {
        "slot_count": total,
        "unique_shot_types": uniq("shot_type"),
        "unique_lighting": uniq("lighting"),
        "unique_composition": uniq("composition"),
        "unique_color_grade": uniq("color_grade"),
    }

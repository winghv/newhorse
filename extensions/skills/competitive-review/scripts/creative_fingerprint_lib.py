#!/usr/bin/env python3
"""Shared helpers for creative fingerprinting and deterministic cross-episode similarity.

零外部依赖：相似度只用标准库 difflib + 字符级 n-gram 集合的 Jaccard。
被 competitive-review/build_template_fatigue_report.py 与
creative-divergence/build_divergence_contract.py 复用。
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# creative-divergence-brief.json 的 divergence_dimensions 五维，作为指纹核心。
DIVERGENCE_DIMENSIONS = (
    "user_task",
    "evidence_type",
    "narrative_device",
    "visual_language",
    "interaction_trigger",
)

# 命中即判为高度同质的核心维度（这几维相似就是"换词复用"）。
CORE_DIMENSIONS = ("narrative_device", "visual_language", "evidence_type")

# 中文停用词与噪声 token，避免相似度被高频虚词拉高。
_STOPWORDS = {
    "的", "了", "和", "是", "在", "也", "都", "就", "把", "被", "不", "你", "我",
    "他", "她", "它", "们", "这", "那", "一个", "一种", "一直", "很多", "自己",
    "其实", "只是", "因为", "所以", "但是", "而是", "不是", "没有", "如何", "为什么",
}


def repo_root() -> Path:
    """extensions/skills/<skill>/scripts/<file>.py -> repo root."""
    return Path(__file__).resolve().parents[4]


def default_media_ops_root() -> Path:
    return repo_root() / "data" / "media-ops"


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize(text: str) -> str:
    """去标点、归一化空白，保留中英文与数字。"""
    text = re.sub(r"[^\w一-鿿]+", " ", str(text or ""))
    return re.sub(r"\s+", " ", text).strip().lower()


def keyword_set(text: str) -> set[str]:
    """抽取关键词集合：英文按词、中文按 2-gram，剔除停用词。"""
    norm = _normalize(text)
    tokens: set[str] = set()
    for chunk in norm.split():
        if chunk.isascii():
            if chunk and chunk not in _STOPWORDS:
                tokens.add(chunk)
            continue
        # 中文：滑动 2-gram，过滤停用词。
        chars = [c for c in chunk if "一" <= c <= "鿿"]
        for i in range(len(chars) - 1):
            bigram = chars[i] + chars[i + 1]
            if bigram not in _STOPWORDS:
                tokens.add(bigram)
        if len(chars) == 1 and chars[0] not in _STOPWORDS:
            tokens.add(chars[0])
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0


def text_overlap(a: str, b: str) -> float:
    """两个维度文本的重叠度：关键词 Jaccard 与字符序列比的较大者，取 0-1。"""
    kw = jaccard(keyword_set(a), keyword_set(b))
    seq = SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()
    return round(max(kw, seq), 4)


def extract_fingerprint(
    content_id: str,
    angle_brief: dict[str, Any],
    divergence_brief: dict[str, Any],
    topic_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """从一期产物抽取结构化指纹。所有字段缺失时降级为空串，不报错。"""
    topic_selection = topic_selection or {}
    dims = divergence_brief.get("divergence_dimensions") or {}
    selected = topic_selection.get("selected_topic") or {}

    fingerprint: dict[str, Any] = {
        "content_id": content_id,
        "series_name": str(divergence_brief.get("series_name") or ""),
        "series_lane": str(selected.get("series_lane") or ""),
        "mother_theme": str(divergence_brief.get("new_thinking_path") or ""),
        "core_angle": str(angle_brief.get("core_angle") or ""),
        "topic": str(selected.get("topic") or divergence_brief.get("current_topic") or ""),
        "dimensions": {dim: str(dims.get(dim) or "") for dim in DIVERGENCE_DIMENSIONS},
    }
    # 预计算关键词集合，方便去重脚本与去重报告复用（存为 list 便于 JSON 序列化）。
    fingerprint["core_angle_keywords"] = sorted(keyword_set(fingerprint["core_angle"]))
    return fingerprint


def compare_fingerprints(current: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    """逐维度比较两期指纹，返回 overlap 明细与综合分。"""
    cur_dims = current.get("dimensions") or {}
    pri_dims = prior.get("dimensions") or {}
    dimension_overlap = {
        dim: text_overlap(cur_dims.get(dim, ""), pri_dims.get(dim, ""))
        for dim in DIVERGENCE_DIMENSIONS
    }
    angle_overlap = text_overlap(current.get("core_angle", ""), prior.get("core_angle", ""))
    mother_overlap = text_overlap(current.get("mother_theme", ""), prior.get("mother_theme", ""))
    core_max = max((dimension_overlap[d] for d in CORE_DIMENSIONS), default=0.0)
    # 综合：核心维度权重更高。
    composite = round(
        0.5 * core_max
        + 0.2 * (sum(dimension_overlap.values()) / len(dimension_overlap))
        + 0.2 * angle_overlap
        + 0.1 * mother_overlap,
        4,
    )
    return {
        "prior_content_id": prior.get("content_id", ""),
        "dimension_overlap": dimension_overlap,
        "core_dimension_max_overlap": round(core_max, 4),
        "angle_overlap": angle_overlap,
        "mother_theme_overlap": mother_overlap,
        "composite_overlap": composite,
    }


def composite_to_score(composite: float) -> int:
    """把 0-1 的 composite overlap 映射成 1-5 的 similarity_score。"""
    if composite >= 0.62:
        return 5
    if composite >= 0.46:
        return 4
    if composite >= 0.32:
        return 3
    if composite >= 0.18:
        return 2
    return 1

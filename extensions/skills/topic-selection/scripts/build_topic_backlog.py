#!/usr/bin/env python3
"""Build a research-backed topic backlog and select the next content topic."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


TITLE_SIGNAL_RULES = {
    "why_question": {
        "description": "优先用“为什么 / 当…”把题目压成一个具体困局，而不是抽象概念介绍。",
        "keywords": ("为什么", "当"),
    },
    "myth_reversal": {
        "description": "用“不是…而是… / 真正… / 最大的谎言 / 被骗了”快速改写旧认知。",
        "keywords": ("不是", "而是", "真正", "最大的谎言", "被骗", "真相"),
    },
    "cost_or_danger": {
        "description": "让观众先感受到代价、危险、损失或被困住，而不是先听道理。",
        "keywords": ("危险", "昂贵", "代价", "亏掉", "障碍", "困住", "没变", "越难", "逃避"),
    },
    "specific_promise": {
        "description": "用步骤、路径、公式、实验或具体结果承诺继续看的收益。",
        "keywords": ("六", "四", "三个", "公式", "路径", "方法", "实验", "学会", "看完"),
    },
}

WEAK_TOPIC_PATTERNS = [
    "题面只剩“认知 / 框架 / 决策 / 提升”这类抽象词，没有具体代价、具体症状或具体误判场景。",
    "看起来像课程目录或方法总结，而不是拆一个普通人正在付成本的现实困局。",
    "和最近几条内容高度同义，观众会感觉还在重复讲同一套判断/框架。",
    "证据抓手和画面抓手太弱，后期容易重新退化成讲得通但不好看的图卡视频。",
]

CONCRETE_PROOF_KEYWORDS = (
    "截图",
    "案例",
    "对比",
    "账单",
    "课程",
    "收藏",
    "笔记",
    "日历",
    "评论",
    "聊天",
    "feed",
    "推送",
    "offer",
    "分歧",
    "实验",
    "清单",
    "记录",
    "界面",
)

CONCRETE_VISUAL_KEYWORDS = (
    "界面",
    "截图",
    "屏幕",
    "聊天",
    "日历",
    "收藏夹",
    "笔记",
    "账单",
    "场景",
    "对照",
    "卡片",
    "黑板",
    "白板",
    "手机",
    "网页",
    "视频",
)

ABSTRACT_TOPIC_KEYWORDS = ("认知", "框架", "决策", "独立思考", "成长", "提升", "方法论", "判断力")
STRONG_CONFLICT_KEYWORDS = ("没变", "越难", "危险", "昂贵", "骗", "逃避", "困住", "拖", "亏", "自我安慰")
RECENT_REPEAT_KEYWORDS = ("判断", "框架", "平台", "AI")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--reference-library-root",
        help="Reference video library root. Defaults to repo-local data/media-ops/_reference-videos.",
    )
    parser.add_argument(
        "--strategy-file",
        help="Strategy/topic-pool JSON file. Defaults to planning/topic-pool.json under the project root.",
    )
    parser.add_argument(
        "--output",
        default="planning/topic-selection.json",
        help="Output path relative to the project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_media_ops_root() -> Path:
    return repo_root() / "data" / "media-ops"


def default_reference_library_root() -> Path:
    return default_media_ops_root() / "_reference-videos"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def resolve_media_ops_root(args: argparse.Namespace) -> Path:
    if args.media_ops_root:
        return Path(args.media_ops_root).resolve()
    return default_media_ops_root().resolve()


def resolve_reference_library_root(args: argparse.Namespace) -> Path:
    if args.reference_library_root:
        return Path(args.reference_library_root).resolve()
    return default_reference_library_root().resolve()


def resolve_strategy_file(args: argparse.Namespace, project_root: Path) -> Path:
    if args.strategy_file:
        return Path(args.strategy_file).resolve()
    return (project_root / "planning" / "topic-pool.json").resolve()


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


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def normalize_text(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value).lower()


def parse_transcript_lines(path: Path) -> list[str]:
    raw_text = path.read_text(encoding="utf-8")
    if "## Transcript" in raw_text:
        raw_text = raw_text.split("## Transcript", 1)[1]

    lines: list[str] = []
    for raw_line in raw_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- title:") or stripped.startswith("- source_url:"):
            continue
        if stripped.startswith("- uploader:") or stripped.startswith("- subtitle_track_type:"):
            continue
        if stripped.startswith("- language:"):
            continue
        cleaned = stripped.removeprefix("- ").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def build_reference_signals(reference_library_root: Path) -> dict[str, Any]:
    index_payload = load_json(reference_library_root / "index.json")
    entries = [item for item in index_payload.get("entries", []) if isinstance(item, dict) and item.get("platform") == "bilibili"]

    titles: list[str] = []
    opening_lines: list[str] = []
    for entry in entries:
        title = entry.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
        transcript_rel = entry.get("primary_transcript")
        if isinstance(transcript_rel, str) and transcript_rel:
            transcript_path = reference_library_root / transcript_rel
            if transcript_path.exists():
                opening_lines.extend(parse_transcript_lines(transcript_path)[:4])

    strong_patterns: list[dict[str, Any]] = []
    joined_openings = " ".join(opening_lines)
    for label, rule in TITLE_SIGNAL_RULES.items():
        count = sum(1 for title in titles if any(keyword in title for keyword in rule["keywords"]))
        if count == 0 and any(keyword in joined_openings for keyword in rule["keywords"]):
            count = 1
        if count:
            strong_patterns.append(
                {
                    "label": label,
                    "count": count,
                    "description": rule["description"],
                }
            )

    strong_patterns.sort(key=lambda item: item["count"], reverse=True)
    return {
        "reference_count": len(entries),
        "strong_title_patterns": strong_patterns,
        "weak_topic_patterns": WEAK_TOPIC_PATTERNS,
    }


def load_recent_topics(media_ops_root: Path, current_project_root: Path, window: int, platform: str) -> list[str]:
    topic_records: list[tuple[str, str]] = []
    for directory in sorted(path for path in media_ops_root.iterdir() if path.is_dir() and not path.name.startswith("_")):
        if directory.resolve() == current_project_root.resolve():
            continue
        payload = load_json(directory / "planning" / "topic-selection.json")
        payload_platform = str(payload.get("platform") or "")
        if platform:
            if payload_platform:
                if payload_platform != platform:
                    continue
            elif platform not in directory.name:
                continue
        selected_topic = payload.get("selected_topic")
        topic = ""
        if isinstance(selected_topic, dict):
            topic = str(selected_topic.get("topic") or "")
        elif isinstance(selected_topic, str):
            topic = selected_topic
        if topic:
            topic_records.append((directory.name, topic.strip()))
    return [topic for _, topic in topic_records[-window:]]


def sequence_similarity(left: str, right: str) -> float:
    return SequenceMatcher(a=normalize_text(left), b=normalize_text(right)).ratio()


def concrete_keyword_score(value: str, keywords: tuple[str, ...]) -> int:
    hits = sum(1 for keyword in keywords if keyword in value)
    if hits >= 4:
        return 5
    if hits >= 2:
        return 4
    if hits == 1:
        return 3
    if len(value.strip()) >= 14:
        return 3
    return 2


def specificity_score(topic: str) -> int:
    score = 2
    if "为什么" in topic or topic.startswith("当"):
        score += 1
    if any(keyword in topic for keyword in STRONG_CONFLICT_KEYWORDS):
        score += 1
    if any(keyword in topic for keyword in ABSTRACT_TOPIC_KEYWORDS) and not any(
        keyword in topic for keyword in STRONG_CONFLICT_KEYWORDS
    ):
        score -= 1
    if "，" in topic or "?" in topic or "？" in topic:
        score += 1
    return max(1, min(score, 5))


def conflict_score(topic: str, core_conflict: str) -> int:
    score = 2
    combined = f"{topic} {core_conflict}"
    if any(keyword in combined for keyword in STRONG_CONFLICT_KEYWORDS):
        score += 2
    if "以为" in combined or "其实" in combined or "不是" in combined:
        score += 1
    return max(1, min(score, 5))


def theme_fit_score(lenses: list[str], mother_theme: str) -> int:
    score = 2
    if mother_theme.strip():
        score += 1
    score += min(len([item for item in lenses if item]), 2)
    return max(1, min(score, 5))


def platform_fit_score(topic: str, proof_handle_score: int, visual_handle_score: int) -> int:
    score = 2
    if "为什么" in topic:
        score += 1
    if any(keyword in topic for keyword in ("不是", "而是", "最危险", "越", "没变")):
        score += 1
    if proof_handle_score >= 4 or visual_handle_score >= 4:
        score += 1
    return max(1, min(score, 5))


def production_efficiency_score(production_cost: str, proof_handle_score: int, visual_handle_score: int) -> int:
    score_map = {
        "low": 5,
        "medium": 4,
        "high": 3,
    }
    score = score_map.get(production_cost.lower(), 4)
    if proof_handle_score <= 2 or visual_handle_score <= 2:
        score -= 1
    return max(1, min(score, 5))


def repeat_risk(topic: str, recent_topics: list[str]) -> int:
    if not recent_topics:
        return 1
    max_similarity = max(sequence_similarity(topic, recent) for recent in recent_topics)
    repeated_keywords = sum(1 for keyword in RECENT_REPEAT_KEYWORDS if keyword in topic)
    abstract_overlap = any(keyword in topic for keyword in ABSTRACT_TOPIC_KEYWORDS) and not any(
        keyword in topic for keyword in STRONG_CONFLICT_KEYWORDS
    )
    score = 1
    if max_similarity >= 0.55:
        score += 3
    elif max_similarity >= 0.35:
        score += 2
    elif max_similarity >= 0.2:
        score += 1
    if repeated_keywords >= 2:
        score += 1
    elif repeated_keywords == 1 and abstract_overlap:
        score += 1
    if abstract_overlap:
        score += 1
    return max(1, min(score, 5))


def freshness_score(topic: str, recent_topics: list[str]) -> int:
    return 6 - repeat_risk(topic, recent_topics)


def selection_reason(candidate: dict[str, Any], recent_topics: list[str]) -> list[str]:
    reasons = [
        f"这条题面的核心冲突是：{candidate['core_conflict']}",
        f"可抓住的第一层证明是：{candidate['proof_handle']}",
        f"主要画面抓手是：{candidate['visual_handle']}",
    ]
    if recent_topics:
        reasons.append("它和最近几条‘判断/框架/平台’题面有明显区隔，更适合做新的系列展开。")
    if candidate.get("why_now"):
        reasons.append(str(candidate["why_now"]))
    return reasons


def recent_overlap_notes(topic: str, recent_topics: list[str]) -> list[dict[str, Any]]:
    rows = []
    for recent in recent_topics:
        similarity = round(sequence_similarity(topic, recent), 3)
        rows.append({"topic": recent, "similarity": similarity})
    rows.sort(key=lambda item: item["similarity"], reverse=True)
    return rows[:3]


def split_signal_parts(value: str) -> list[str]:
    parts = [item.strip("「」\"' ") for item in re.split(r"[、，,；;。/\n]+", value) if item.strip()]
    return parts


def extract_mechanism_focus(core_conflict: str, topic: str) -> str:
    clauses = [item.strip("「」\"' ") for item in re.split(r"[；;。！？!?]+", core_conflict) if item.strip()]
    if clauses:
        return max(clauses, key=len)
    return topic


def build_selected_risks(candidate: dict[str, Any]) -> list[str]:
    topic = str(candidate.get("topic") or "").strip()
    core_conflict = str(candidate.get("core_conflict") or "").strip()
    proof_items = split_signal_parts(str(candidate.get("proof_handle") or ""))
    visual_items = split_signal_parts(str(candidate.get("visual_handle") or ""))
    mechanism_focus = extract_mechanism_focus(core_conflict, topic)

    evidence_bits = [item for item in (proof_items[:1] + proof_items[-1:] + visual_items[:1]) if item]
    unique_evidence_bits: list[str] = []
    for item in evidence_bits:
        if item not in unique_evidence_bits:
            unique_evidence_bits.append(item)

    evidence_label = "、".join(unique_evidence_bits[:3]) if unique_evidence_bits else "关键案例和画面证据"

    return [
        f"不要把「{topic}」重新讲成抽象方法论，开场必须先落到观众熟悉的具体处境。",
        f"中段不能只下判断，必须把「{mechanism_focus}」讲成一条可验证的现实机制。",
        f"必须准备 {evidence_label} 这些可见证据，否则很容易退化成空讲道理。",
    ]


def build_selected_next_action(candidate: dict[str, Any]) -> str:
    topic = str(candidate.get("topic") or "").strip()
    core_conflict = str(candidate.get("core_conflict") or "").strip()
    proof_items = split_signal_parts(str(candidate.get("proof_handle") or ""))
    visual_items = split_signal_parts(str(candidate.get("visual_handle") or ""))

    chain_start = proof_items[0] if proof_items else (visual_items[0] if visual_items else topic)
    chain_end = proof_items[-1] if len(proof_items) >= 2 else (visual_items[-1] if visual_items else extract_mechanism_focus(core_conflict, topic))
    if chain_start == chain_end:
        chain_end = extract_mechanism_focus(core_conflict, topic)

    return f"进入 angle brief，优先把「{chain_start} -> {chain_end}」的证明链和关键画面写死。"


def build_candidate_row(candidate: dict[str, Any], recent_topics: list[str], mother_theme: str) -> dict[str, Any]:
    topic = str(candidate.get("topic") or "").strip()
    core_conflict = str(candidate.get("core_conflict") or "").strip()
    proof_handle = str(candidate.get("proof_handle") or "").strip()
    visual_handle = str(candidate.get("visual_handle") or "").strip()
    lenses = [str(item) for item in candidate.get("lenses", []) if item]
    production_cost = str(candidate.get("production_cost") or "medium")

    proof_score = concrete_keyword_score(proof_handle, CONCRETE_PROOF_KEYWORDS)
    visual_score = concrete_keyword_score(visual_handle, CONCRETE_VISUAL_KEYWORDS)
    row = {
        "topic": topic,
        "series_lane": candidate.get("series_lane"),
        "core_conflict": core_conflict,
        "proof_handle": proof_handle,
        "visual_handle": visual_handle,
        "why_now": candidate.get("why_now"),
        "lenses": lenses,
        "specificity_score": specificity_score(topic),
        "conflict_score": conflict_score(topic, core_conflict),
        "proof_handle_score": proof_score,
        "visual_handle_score": visual_score,
        "theme_fit_score": theme_fit_score(lenses, mother_theme),
        "platform_fit_score": platform_fit_score(topic, proof_score, visual_score),
        "production_efficiency_score": production_efficiency_score(production_cost, proof_score, visual_score),
        "freshness_score": freshness_score(topic, recent_topics),
        "repeat_risk": repeat_risk(topic, recent_topics),
        "recent_overlap": recent_overlap_notes(topic, recent_topics),
    }
    row["priority_score"] = (
        row["specificity_score"]
        + row["conflict_score"]
        + row["proof_handle_score"]
        + row["visual_handle_score"]
        + row["theme_fit_score"]
        + row["platform_fit_score"]
        + row["production_efficiency_score"]
        + row["freshness_score"]
        - (row["repeat_risk"] - 1)
    )
    return row


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    media_ops_root = resolve_media_ops_root(args)
    reference_library_root = resolve_reference_library_root(args)
    strategy_path = resolve_strategy_file(args, project_root)
    strategy = load_json(strategy_path)
    selection_context = strategy.get("selection_context") if isinstance(strategy.get("selection_context"), dict) else {}

    recent_package_window = int(selection_context.get("recent_package_window") or 3)
    platform = str(strategy.get("platform") or "bilibili")
    recent_topics = load_recent_topics(media_ops_root, project_root, recent_package_window, platform)
    mother_theme = str(selection_context.get("mother_theme") or strategy.get("account_thesis") or "")

    topic_backlog = [
        build_candidate_row(candidate, recent_topics, mother_theme)
        for candidate in strategy.get("candidates", [])
        if isinstance(candidate, dict) and str(candidate.get("topic") or "").strip()
    ]
    topic_backlog.sort(key=lambda item: item["priority_score"], reverse=True)

    if not topic_backlog:
        raise SystemExit("no valid candidates found in strategy file")

    selected = topic_backlog[0]
    selected_payload = {
        "topic": selected["topic"],
        "series_lane": selected.get("series_lane"),
        "reason_to_choose": selection_reason(selected, recent_topics),
        "risks_to_watch": build_selected_risks(selected),
        "next_action": build_selected_next_action(selected),
    }

    output_path = (project_root / args.output).resolve()
    payload = {
        "date": strategy.get("date"),
        "platform": platform,
        "objective": strategy.get("objective"),
        "account_thesis": strategy.get("account_thesis"),
        "selection_context": {
            "series_name": selection_context.get("series_name"),
            "mother_theme": mother_theme,
            "recent_package_window": recent_package_window,
        },
        "reference_signals": build_reference_signals(reference_library_root),
        "recent_account_topics": recent_topics,
        "source_paths": {
            "strategy_file": relative_to_project(strategy_path, project_root),
            "reference_library_index": relative_to_project(reference_library_root / "index.json", project_root),
        },
        "topic_backlog": topic_backlog,
        "selected_topic": selected_payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "selected_topic": selected_payload["topic"],
                "candidate_count": len(topic_backlog),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

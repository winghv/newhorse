#!/usr/bin/env python3
"""Build a structured Bilibili growth pattern pack from benchmark notes."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENING_KEYWORDS = ("开头", "冲突", "反转", "痛点", "钩子", "题面")
RETENTION_KEYWORDS = ("结构", "步骤", "清单", "章节", "框架", "保存", "回看")
PROOF_KEYWORDS = ("截图", "案例", "证据", "证明", "真实", "界面", "样本")
ENGAGEMENT_KEYWORDS = ("评论", "互动", "收藏", "转发", "领取", "参与")
FOLLOW_KEYWORDS = ("下一条", "系列", "关注", "继续看", "后续")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--output",
        default="benchmarks/bilibili-hook-patterns.json",
        help="JSON output path relative to the project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_media_ops_root() -> Path:
    return repo_root() / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_field_bullet(line: str) -> tuple[str, str] | None:
    match = re.match(r"-\s+`([^`]+)`:\s*(.+)$", line.strip())
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def parse_benchmark_deck(path: Path) -> dict[str, Any]:
    payload = {
        "reusable_patterns": [],
        "whitespace": [],
        "anti_patterns": [],
    }
    if not path.exists():
        return payload

    current_section = ""
    current_pattern: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_pattern:
                payload["reusable_patterns"].append(current_pattern)
                current_pattern = None
            current_section = stripped.removeprefix("## ").strip().lower()
            continue
        if stripped.startswith("### "):
            if current_pattern:
                payload["reusable_patterns"].append(current_pattern)
            label = re.sub(r"^\d+\.\s*", "", stripped.removeprefix("### ").strip())
            current_pattern = {"label": label}
            continue
        if current_pattern:
            field = parse_field_bullet(stripped)
            if field:
                key, value = field
                current_pattern[key] = value
                continue
        if current_section == "whitespace" and stripped.startswith("- "):
            payload["whitespace"].append(stripped.removeprefix("- ").strip())
            continue
        if current_section == "anti-patterns" and stripped.startswith("- "):
            payload["anti_patterns"].append(stripped.removeprefix("- ").strip())
            continue

    if current_pattern:
        payload["reusable_patterns"].append(current_pattern)
    return payload


def matches_keywords(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def category_payload(pattern: dict[str, str]) -> dict[str, str]:
    return {
        "label": pattern.get("label", ""),
        "pattern": pattern.get("pattern", ""),
        "why_it_works": pattern.get("why_it_works", ""),
        "reusable_play": pattern.get("reusable_play", ""),
    }


def derive_follow_patterns(patterns: list[dict[str, str]]) -> list[dict[str, str]]:
    derived: list[dict[str, str]] = []
    for pattern in patterns:
        trigger = pattern.get("reusable_play", "")
        if not trigger:
            continue
        if matches_keywords(trigger, FOLLOW_KEYWORDS) or matches_keywords(pattern.get("pattern", ""), FOLLOW_KEYWORDS):
            derived.append(
                {
                    "label": pattern.get("label", ""),
                    "trigger": trigger,
                    "why_it_works": pattern.get("why_it_works", ""),
                }
            )
    return derived


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)

    benchmark_path = project_root / "benchmarks" / "benchmark-deck.md"
    topic_selection_path = project_root / "planning" / "topic-selection.json"
    topic_selection = load_json(topic_selection_path)
    selected_topic = topic_selection.get("selected_topic") if isinstance(topic_selection.get("selected_topic"), dict) else {}
    parsed_deck = parse_benchmark_deck(benchmark_path)
    reusable_patterns = parsed_deck["reusable_patterns"]

    opening_patterns: list[dict[str, str]] = []
    retention_patterns: list[dict[str, str]] = []
    proof_patterns: list[dict[str, str]] = []
    engagement_patterns: list[dict[str, str]] = []

    for pattern in reusable_patterns:
        combined = " ".join(
            [
                pattern.get("label", ""),
                pattern.get("pattern", ""),
                pattern.get("why_it_works", ""),
                pattern.get("reusable_play", ""),
            ]
        )
        entry = category_payload(pattern)
        if matches_keywords(combined, OPENING_KEYWORDS):
            opening_patterns.append(entry)
        if matches_keywords(combined, RETENTION_KEYWORDS):
            retention_patterns.append(entry)
        if matches_keywords(combined, PROOF_KEYWORDS):
            proof_patterns.append(entry)
        if matches_keywords(combined, ENGAGEMENT_KEYWORDS):
            engagement_patterns.append(entry)

    follow_conversion_patterns = derive_follow_patterns(reusable_patterns)
    if not follow_conversion_patterns and engagement_patterns:
        first = engagement_patterns[0]
        follow_conversion_patterns.append(
            {
                "label": first["label"],
                "trigger": first["reusable_play"] or "下一条继续拆这个框架。",
                "why_it_works": first["why_it_works"],
            }
        )

    output_path = (project_root / args.output).resolve()
    payload = {
        "content_id": project_root.name,
        "platform": topic_selection.get("platform") or "bilibili",
        "objective": topic_selection.get("objective"),
        "selected_topic": selected_topic.get("topic"),
        "source_paths": {
            "benchmark_deck": relative_to_project(benchmark_path, project_root) if benchmark_path.exists() else None,
            "topic_selection": relative_to_project(topic_selection_path, project_root) if topic_selection_path.exists() else None,
        },
        "opening_patterns": opening_patterns,
        "retention_patterns": retention_patterns,
        "proof_patterns": proof_patterns,
        "engagement_patterns": engagement_patterns,
        "follow_conversion_patterns": follow_conversion_patterns,
        "whitespace": parsed_deck["whitespace"],
        "anti_patterns": parsed_deck["anti_patterns"],
        "recommended_next_artifacts": [
            "angles/attention-structure-template.json",
            "angles/follow-conversion-hooks.json",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "opening_pattern_count": len(opening_patterns),
                "follow_conversion_pattern_count": len(follow_conversion_patterns),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a reusable script pattern pack from the shared reference-video library."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENING_DEVICE_RULES = {
    "question_or_counterintuition": (
        "用反直觉问题或代价感开头，先把观众拉进冲突，而不是先交代背景。",
        ("为什么", "如果", "你有没有", "你觉得", "你以为", "是不是", "会不会", "最大的谎言", "被骗"),
    ),
    "hard_contrast_reframe": (
        "用“不是…而是…”或“看起来…其实…”重写旧认知，快速建立新框架。",
        ("不是", "而是", "其实", "却", "反而", "真相"),
    ),
    "framework_tease": (
        "提前承诺后面会交付清晰框架、路径或步骤，给用户继续看的理由。",
        ("四个", "六个", "六条", "三个", "四步", "方法", "路径", "公式", "框架"),
    ),
    "case_or_analogy_lede": (
        "用实验、寓言、现实案例或类比，把抽象概念变成可想象的场景。",
        ("实验", "农民", "一亩地", "两个年轻人", "想象", "比如", "有一天"),
    ),
}

LINE_TACTIC_RULES = {
    "audience_self_interrogation": (
        "让观众先审视自己，而不是先被动听结论。",
        ("你有没有", "你觉得", "你以为", "如果你"),
    ),
    "specific_numeric_contrast": (
        "用具体数字或比例制造损失感和可信度。",
        ("%", "百分之", "小时", "年", "月", "470", "500"),
    ),
    "promise_of_takeaway": (
        "明确承诺看完能拿到什么，不让观众只听概念。",
        ("看完", "你会", "接下来", "今天这期", "带你", "给你", "拿到"),
    ),
    "myth_reversal": (
        "先点破常识，再把观众带到新的解释框架里。",
        ("最大的谎言", "被骗", "并不是", "不是", "而是", "真相"),
    ),
}


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
        "--output",
        default="benchmarks/reference-script-patterns.json",
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


def default_reference_library_root() -> Path:
    return default_media_ops_root() / "_reference-videos"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def resolve_reference_library_root(args: argparse.Namespace) -> Path:
    if args.reference_library_root:
        return Path(args.reference_library_root).resolve()
    return default_reference_library_root().resolve()


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
    return str(path.resolve().relative_to(project_root.resolve()))


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\u3000", " ")).strip(" -\t")


def parse_transcript_lines(path: Path) -> list[str]:
    raw_text = path.read_text(encoding="utf-8")
    if "## Transcript" in raw_text:
        raw_text = raw_text.split("## Transcript", 1)[1]

    lines: list[str] = []
    for raw_line in raw_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- title:") or stripped.startswith("- source_url:") or stripped.startswith("- uploader:"):
            continue
        if stripped.startswith("- subtitle_track_type:") or stripped.startswith("- language:"):
            continue
        cleaned = normalize_line(stripped.removeprefix("- ").strip())
        if cleaned:
            lines.append(cleaned)
    return lines


def match_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_examples(lines: list[str], keywords: tuple[str, ...], *, limit: int = 2) -> list[str]:
    examples: list[str] = []
    for line in lines:
        if match_any(line, keywords):
            examples.append(line)
        if len(examples) >= limit:
            break
    return examples


def detect_opening_devices(opening_lines: list[str]) -> list[str]:
    joined = " ".join(opening_lines)
    labels: list[str] = []
    for label, (_, keywords) in OPENING_DEVICE_RULES.items():
        if match_any(joined, keywords):
            labels.append(label)
    return labels


def build_reference_card(entry: dict[str, Any], transcript_lines: list[str]) -> dict[str, Any]:
    opening_lines = transcript_lines[:8]
    devices = detect_opening_devices(opening_lines)
    promise_excerpt = next(
        (line for line in transcript_lines[:18] if match_any(line, LINE_TACTIC_RULES["promise_of_takeaway"][1])),
        "",
    )
    return {
        "video_id": entry.get("video_id"),
        "title": entry.get("title"),
        "uploader": entry.get("uploader"),
        "opening_excerpt": opening_lines[:4],
        "opening_devices": devices,
        "promise_excerpt": promise_excerpt,
    }


def build_counter_rows(
    labels: list[str],
    *,
    description_map: dict[str, tuple[str, tuple[str, ...]]],
    examples_map: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows = []
    counts = Counter(labels)
    for label, count in counts.most_common():
        description, _ = description_map[label]
        rows.append(
            {
                "label": label,
                "count": count,
                "description": description,
                "examples": examples_map.get(label, [])[:3],
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    reference_library_root = resolve_reference_library_root(args)
    index_path = reference_library_root / "index.json"
    index_payload = load_json(index_path)
    entries = [item for item in index_payload.get("entries", []) if isinstance(item, dict) and item.get("platform") == "bilibili"]

    opening_labels: list[str] = []
    line_tactic_labels: list[str] = []
    opening_examples: dict[str, list[str]] = {label: [] for label in OPENING_DEVICE_RULES}
    line_examples: dict[str, list[str]] = {label: [] for label in LINE_TACTIC_RULES}
    reference_cards: list[dict[str, Any]] = []

    for entry in entries:
        transcript_rel = entry.get("primary_transcript")
        if not isinstance(transcript_rel, str) or not transcript_rel:
            continue
        transcript_path = reference_library_root / transcript_rel
        if not transcript_path.exists():
            continue
        transcript_lines = parse_transcript_lines(transcript_path)
        if not transcript_lines:
            continue

        opening_lines = transcript_lines[:8]
        for label, (_, keywords) in OPENING_DEVICE_RULES.items():
            if match_any(" ".join(opening_lines), keywords):
                opening_labels.append(label)
                opening_examples[label].extend(extract_examples(opening_lines, keywords))

        for label, (_, keywords) in LINE_TACTIC_RULES.items():
            if any(match_any(line, keywords) for line in transcript_lines[:18]):
                line_tactic_labels.append(label)
                line_examples[label].extend(extract_examples(transcript_lines[:18], keywords))

        reference_cards.append(build_reference_card(entry, transcript_lines))

    dominant_opening_devices = build_counter_rows(
        opening_labels,
        description_map=OPENING_DEVICE_RULES,
        examples_map=opening_examples,
    )
    line_tactics = build_counter_rows(
        line_tactic_labels,
        description_map=LINE_TACTIC_RULES,
        examples_map=line_examples,
    )

    writing_principles = [
        "开头先给问题、损失或反直觉结论，不先讲长背景。",
        "前 30 秒必须同时完成承诺和第一层证明，不能只堆钩子。",
        "中段每推进一节，都要新增机制、证据、对照或操作步骤，避免解释空转。",
        "框架和方法论要交付到可截图、可保存的程度，不只停在观点。",
        "结尾不只收束观点，还要把观众桥接到下一次判断或下一条内容。",
    ]
    anti_patterns = [
        "开头先铺设大量背景，真正冲突和收益出现太晚。",
        "中段一直重复同一种解释，没有新证据、新对照或新动作。",
        "结尾只有情绪收束，没有明确可执行的判断动作或下一条桥接。",
    ]

    output_path = (project_root / args.output).resolve()
    payload = {
        "content_id": project_root.name,
        "platform": "bilibili",
        "reference_library_root": str(reference_library_root),
        "source_index": str(index_path),
        "reference_count": len(reference_cards),
        "dominant_opening_devices": dominant_opening_devices,
        "line_tactics": line_tactics,
        "writing_principles": writing_principles,
        "anti_patterns": anti_patterns,
        "reference_cards": reference_cards,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output_path": relative_to_project(output_path, project_root),
                "reference_count": len(reference_cards),
                "opening_device_count": len(dominant_opening_devices),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

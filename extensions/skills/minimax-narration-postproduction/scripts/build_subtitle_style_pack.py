#!/usr/bin/env python3
"""Build a subtitle style pack for narrated videos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FONT_STACK = [
    "Arial Unicode MS",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
]


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
        default="content/postproduction/subtitle-style-pack.json",
        help="Subtitle style pack output path relative to the project root.",
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


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"no content packet found under {content_dir}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_priority_phrases(notes: list[str]) -> list[str]:
    phrases: list[str] = []
    for note in notes:
        if "关键句上屏：" in note:
            phrases.append(note.split("关键句上屏：", maxsplit=1)[1].strip())
    return phrases


def build_ass_force_style(font_name: str, font_size: int, margin_v: int) -> str:
    return (
        f"FontName={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2.2,Shadow=0,"
        "BackColour=&H4A101010,BorderStyle=1,"
        f"MarginV={margin_v},Alignment=2"
    )


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet

    subtitle_package = primary.get("subtitle_package") if isinstance(primary.get("subtitle_package"), dict) else {}
    notes = [str(item) for item in subtitle_package.get("notes", []) if item]
    priority_phrases = extract_priority_phrases(notes)
    font_name = DEFAULT_FONT_STACK[0]
    is_midlong = primary.get("deliverable_type") == "midlong-video"
    font_size = 18 if is_midlong else 18
    margin_v = 44 if is_midlong else 32
    subtitle_layout = "zh_en_dual_line"
    translation_language = "en"

    payload = {
        "content_id": primary.get("content_id") or project_root.name,
        "theme": "bilibili-midform-bilingual" if is_midlong else "default-bilingual",
        "font_stack": DEFAULT_FONT_STACK,
        "font_size_rules": {
            "base": font_size,
            "highlight": font_size + 2,
        },
        "subtitle_layout": subtitle_layout,
        "subtitle_mode": "bilingual_hardsub",
        "language_order": ["zh-CN", "en"],
        "translation_language": translation_language,
        "translation_required": True,
        "translation_source_priority": [
            "voiceover-segments.translation_en",
            "voiceover-segments.translation",
            "voiceover-segments.english_text",
            "subtitle_package.translation_map",
        ],
        "highlight_rules": {
            "priority_phrases": priority_phrases,
            "highlight_mode": "phrase-first",
        },
        "safe_margin": {
            "margin_v": margin_v,
            "alignment": 2,
        },
        "line_break_policy": subtitle_package.get("style") or "中文在上、英文在下；按意群断句；中文单行 14-20 字优先，英文保持短句对照",
        "burn_in_mode": "hardsub",
        "ass_force_style": build_ass_force_style(font_name, font_size, margin_v),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": str(output_path), "theme": payload["theme"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
